"""Pipeline orchestrator - coordinates all stages."""
import os
import sys
import subprocess
from typing import Dict

from agent.build_repo_map import build_repo_map
from agent.fetch_issue import fetch_issue
from agent.analyze_issue import analyze_issue
from agent.explore_repo_v2 import explore_repo_with_map
from agent.analyze_dependencies import analyze_dependencies, get_dependency_constraint_prompt
from agent.plan_fix import plan_fix
from agent.apply_fix import apply_fix, test_hardcoded_edit
from agent.validate import validate
from agent.generate_pr import generate_pr_summary
from agent.llm_client import get_llm_client
from tools import write_file, get_git_diff


def git_stash(repo_path: str) -> bool:
    """Stash current changes.
    
    Returns True if successful, False otherwise.
    """
    try:
        result = subprocess.run(
            ['git', 'stash'],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except Exception as e:
        print(f"[Rollback] Git stash failed: {e}")
        return False


def git_stash_pop(repo_path: str) -> bool:
    """Restore stashed changes.
    
    Returns True if successful, False otherwise.
    """
    try:
        result = subprocess.run(
            ['git', 'stash', 'pop'],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print("[Rollback] Restored repo to original state")
            return True
        else:
            print(f"[Rollback] Git stash pop failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"[Rollback] Git stash pop failed: {e}")
        return False


def git_stash_drop(repo_path: str) -> bool:
    """Discard the stash.
    
    Returns True if successful, False otherwise.
    """
    try:
        result = subprocess.run(
            ['git', 'stash', 'drop'],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except Exception as e:
        print(f"[Rollback] Git stash drop failed: {e}")
        return False


def run_pipeline(issue_url: str, repo_path: str, config) -> Dict:
    """Run the complete pipeline with git rollback support.
    
    Args:
        issue_url: GitHub issue URL
        repo_path: Path to cloned repository
        config: Configuration module
        
    Returns:
        Dict with pipeline results
    """
    # Create output directory
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    
    # Stage 0: Build repository map
    repo_map = build_repo_map(repo_path)
    
    # Stage 1: Fetch issue
    issue_data = fetch_issue(issue_url, config.APPROVED_REPOS)
    
    # Stage 2: Analyze issue
    analysis = analyze_issue(issue_data, None, config.SYSTEM_PROMPT, config=config)
    
    # Stage 3: Explore repository with map
    files = explore_repo_with_map(
        repo_path, 
        analysis, 
        repo_map,
        None,
        config.SYSTEM_PROMPT,
        max_files=config.MAX_RELEVANT_FILES,
        max_lines=config.MAX_FILE_LINES,
        config=config
    )
    
    # Stage 3.5: Analyze dependencies
    dependencies = analyze_dependencies(repo_path)
    
    # TEST: Verify hardcoded edit works (sanity check for apply mechanism)
    print("[TEST] Verifying apply mechanism with hardcoded edit...", end=" ", flush=True)
    try:
        test_hardcoded_edit(repo_path)
        print("✓")
    except Exception as e:
        print(f"✗ FAILED: {e}")
        sys.exit(1)
    
    # Stage 4: Plan fix
    plan = plan_fix(
        issue_data, 
        analysis, 
        files, 
        None, 
        config.SYSTEM_PROMPT,
        dependencies=dependencies,
        config=config
    )
    
    # Stash changes before applying fix
    print("[Rollback] Stashing current state...", end=" ", flush=True)
    if not git_stash(repo_path):
        print("✗ (warning: stash failed, proceeding anyway)")
    else:
        print("✓")
    
    # Stage 5: Apply fix (with rollback on failure)
    try:
        changes = apply_fix(
            repo_path, 
            plan, 
            files, 
            max_retries=config.MAX_BUILD_RETRIES
        )
    except Exception as e:
        print(f"\n✗ Stage 5 FAILED: {str(e)}")
        print("[Rollback] Restoring repo to original state...", end=" ", flush=True)
        if git_stash_pop(repo_path):
            print("✓")
        else:
            print("✗ (manual rollback may be needed)")
        sys.exit(1)
    
    # Stage 6: Validate
    validation = validate(repo_path)
    
    # Check if validation failed
    if validation.get('overall_status') == 'failed':
        print("\n✗ Validation FAILED")
        print("[Rollback] Restoring repo to original state...", end=" ", flush=True)
        if git_stash_pop(repo_path):
            print("✓")
        else:
            print("✗ (manual rollback may be needed)")
        sys.exit(1)
    
    # Success! Drop the stash
    print("[Rollback] Fix successful, discarding backup...", end=" ", flush=True)
    if git_stash_drop(repo_path):
        print("✓")
    else:
        print("✗ (warning: could not drop stash, but fix is applied)")
    
    # Stage 7: Generate PR summary
    pr_summary = generate_pr_summary(
        repo_path,
        issue_data,
        analysis,
        plan,
        validation,
        None,
        config.SYSTEM_PROMPT,
        config=config
    )
    
    # Stage 8: Save outputs
    print("[Stage 8] Saving outputs...", end=" ", flush=True)
    
    # Save git diff
    diff = get_git_diff(repo_path)
    diff_path = os.path.join(config.OUTPUT_DIR, "patch.diff")
    write_file(diff_path, diff)
    
    # Save PR summary
    pr_path = os.path.join(config.OUTPUT_DIR, "pr_summary.md")
    pr_content = f"""# {pr_summary['title']}

{pr_summary['body']}
"""
    write_file(pr_path, pr_content)
    
    print("✓")
    
    # Print summary
    print("\n" + "="*60)
    print("PIPELINE COMPLETE")
    print("="*60)
    print(f"Issue: #{issue_data['number']} - {issue_data['title']}")
    print(f"Files modified: {len(changes.get('applied_changes', []))}")
    print(f"Build status: {'✓' if changes.get('build_success') else '✗'}")
    print(f"Validation status: {validation.get('overall_status', 'unknown')}")
    print(f"\nOutputs saved to:")
    print(f"  - {diff_path}")
    print(f"  - {pr_path}")
    print("="*60)
    
    return {
        'issue': issue_data,
        'analysis': analysis,
        'files': files,
        'plan': plan,
        'changes': changes,
        'validation': validation,
        'pr_summary': pr_summary,
        'output_files': {
            'diff': diff_path,
            'pr_summary': pr_path
        }
    }
