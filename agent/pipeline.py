"""Pipeline orchestrator - coordinates all stages."""
import os
from groq import Groq
from typing import Dict

from agent.fetch_issue import fetch_issue
from agent.analyze_issue import analyze_issue
from agent.explore_repo import explore_repo
from agent.plan_fix import plan_fix
from agent.apply_fix import apply_fix
from agent.validate import validate
from agent.generate_pr import generate_pr_summary
from tools import write_file, get_git_diff


def run_pipeline(issue_url: str, repo_path: str, config) -> Dict:
    """Run the complete pipeline.
    
    Args:
        issue_url: GitHub issue URL
        repo_path: Path to cloned repository
        config: Configuration module
        
    Returns:
        Dict with pipeline results
    """
    # Initialize Groq client
    if not config.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY environment variable not set")
    
    groq_client = Groq(api_key=config.GROQ_API_KEY)
    
    # Create output directory
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    
    # Stage 1: Fetch issue
    issue_data = fetch_issue(issue_url, config.APPROVED_REPOS)
    
    # Stage 2: Analyze issue
    analysis = analyze_issue(issue_data, groq_client, config.SYSTEM_PROMPT)
    
    # Stage 3: Explore repository
    files = explore_repo(
        repo_path, 
        analysis, 
        max_files=config.MAX_RELEVANT_FILES,
        max_lines=config.MAX_FILE_LINES
    )
    
    # Stage 4: Plan fix
    plan = plan_fix(issue_data, analysis, files, groq_client, config.SYSTEM_PROMPT)
    
    # Stage 5: Apply fix
    changes = apply_fix(
        repo_path, 
        plan, 
        files, 
        groq_client, 
        config.SYSTEM_PROMPT,
        max_retries=config.MAX_BUILD_RETRIES
    )
    
    # Stage 6: Validate
    validation = validate(repo_path)
    
    # Stage 7: Generate PR summary
    pr_summary = generate_pr_summary(
        repo_path,
        issue_data,
        analysis,
        plan,
        validation,
        groq_client,
        config.SYSTEM_PROMPT
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
