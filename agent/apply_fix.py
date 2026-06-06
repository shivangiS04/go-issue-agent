"""Stage 5: Apply structured fix plan mechanically - NO AI calls in this stage."""
import os
import sys
from typing import Dict, List, Optional
from tools import read_file, write_file, run_command


def apply_fix(repo_path: str, plan: Dict, files: Dict, groq_client=None, 
              system_prompt: str = "", max_retries: int = 3) -> Dict:
    """Apply structured fix plan mechanically to files.
    
    This stage receives a structured plan and applies it mechanically.
    NO AI is used in this stage - the plan must contain exact code strings.
    
    Supported operations:
    - "insert_after": Insert code after the target line
    - "insert_before": Insert code before the target line
    - "replace": Replace the target code with new code
    
    Args:
        repo_path: Path to repository
        plan: Structured fix plan from Stage 4 with format:
            {
                "files_to_change": ["file.go"],
                "changes": [
                    {
                        "file": "file.go",
                        "type": "insert_after",
                        "target": "exact code to find",
                        "location_hint": "human readable hint",
                        "code": "code to insert"
                    }
                ]
            }
        files: Files from Stage 3 (unused, kept for compatibility)
        groq_client: Unused, kept for compatibility
        system_prompt: Unused, kept for compatibility
        max_retries: Maximum build retry attempts
        
    Returns:
        Dict with applied_changes list
        
    Raises:
        Exception if edits fail to apply
    """
    print("[Stage 5] Applying fix...", end=" ", flush=True)
    
    applied_changes = []
    files_to_change = plan.get('files_to_change', [])
    
    if not files_to_change:
        print("✓ (no files to change)")
        return {
            'applied_changes': [],
            'build_success': True
        }
    
    # Group changes by file
    changes_by_file = {}
    for change in plan.get('changes', []):
        file_path = change.get('file')
        if file_path not in changes_by_file:
            changes_by_file[file_path] = []
        changes_by_file[file_path].append(change)
    
    # Process each file
    for file_path, changes in changes_by_file.items():
        full_path = os.path.join(repo_path, file_path)
        
        if not os.path.exists(full_path):
            raise Exception(f"File to modify not found: {file_path}")
        
        # Read current file content
        current_content = read_file(full_path)
        print(f"\n[DEBUG] Processing {file_path} ({len(current_content)} chars)", file=sys.stderr)
        
        # Apply each change to this file
        for change in changes:
            change_type = change.get('type')
            target = change.get('target', '')
            code = change.get('code', '')
            location_hint = change.get('location_hint', '')
            
            print(f"[DEBUG] Change type: {change_type}", file=sys.stderr)
            print(f"[DEBUG] Location hint: {location_hint}", file=sys.stderr)
            print(f"[DEBUG] Target: {target[:100]}...", file=sys.stderr)
            
            if not target:
                raise Exception(f"Empty target in change for {file_path}")
            
            if not code:
                raise Exception(f"Empty code in change for {file_path}")
            
            # Find the target in the file
            if target not in current_content:
                raise Exception(
                    f"Target code not found in {file_path}.\n"
                    f"Location hint: {location_hint}\n"
                    f"Expected to find:\n{target}\n\n"
                    f"Please verify the target string matches exactly."
                )
            
            # Apply the change based on type
            if change_type == 'insert_after':
                # Insert code after the target
                idx = current_content.find(target)
                insert_pos = idx + len(target)
                updated = current_content[:insert_pos] + '\n' + code + current_content[insert_pos:]
                
            elif change_type == 'insert_before':
                # Insert code before the target
                idx = current_content.find(target)
                updated = current_content[:idx] + code + '\n' + current_content[idx:]
                
            elif change_type == 'replace':
                # Replace target with new code
                updated = current_content.replace(target, code, 1)
                
            else:
                raise Exception(f"Unknown change type: {change_type}")
            
            # Update current content for next change
            current_content = updated
            
            print(f"[DEBUG] Applied {change_type} successfully", file=sys.stderr)
        
        # Write the updated file
        write_file(full_path, current_content)
        print(f"[DEBUG] Wrote {file_path}", file=sys.stderr)
        
        applied_changes.append({
            'file': file_path,
            'status': 'modified',
            'changes_count': len(changes)
        })
    
    print("✓")
    
    # Try to build
    retry_count = 0
    build_success = False
    last_stderr = ""
    
    while retry_count < max_retries:
        print(f"[Stage 5] Building... (attempt {retry_count + 1}/{max_retries})", end=" ", flush=True)
        stdout, stderr, returncode = run_command(['go', 'build', './...'], cwd=repo_path)
        
        if returncode == 0:
            print("✓")
            build_success = True
            break
        else:
            print(f"✗")
            print(f"  Build error: {stderr[:150]}", file=sys.stderr)
            last_stderr = stderr
            retry_count += 1
    
    if not build_success:
        raise Exception(f"Build failed after applying fixes. Build errors:\n{last_stderr[:500]}")
    
    return {
        'applied_changes': applied_changes,
        'build_success': True
    }


def test_hardcoded_edit(repo_path: str) -> bool:
    """Test that the apply mechanism works with a hardcoded edit.
    
    This tests a minimal edit to verify string matching works.
    
    Args:
        repo_path: Path to repository
        
    Returns:
        True if test passed, raises Exception otherwise
    """
    print("\n[DEBUG] Testing hardcoded edit mechanism...", file=sys.stderr)
    
    command_go_path = os.path.join(repo_path, 'command.go')
    content = read_file(command_go_path)
    
    # Test a simple, real edit: change a comment or add debug logging
    old_code = "// LocalFlags returns all flags specific to this command."
    new_code = "// LocalFlags returns all flags specific to this command.\n\t// Note: shadowing flags are handled correctly."
    
    print(f"[DEBUG] Looking for test code in command.go", file=sys.stderr)
    
    if old_code not in content:
        print(f"[DEBUG] Test code not found, attempting alternative test...", file=sys.stderr)
        # Alternative: test on a different file
        old_code = "package cobra"
        new_code = "package cobra\n\n// This package provides cobra CLI framework"
    
    if old_code not in content:
        raise Exception(f"Hardcoded test: Could not find any test code to replace in command.go")
    
    print(f"[DEBUG] Test code found! Applying replacement...", file=sys.stderr)
    
    updated = content.replace(old_code, new_code, 1)
    
    # Verify change was made
    if new_code not in updated:
        raise Exception(f"Hardcoded test: NEW_CODE not in updated file after replacement")
    
    print(f"[DEBUG] Replacement verified in file", file=sys.stderr)
    
    # Write back
    write_file(command_go_path, updated)
    
    # Try to build
    print(f"[DEBUG] Building with test edit...", file=sys.stderr)
    stdout, stderr, returncode = run_command(['go', 'build', './...'], cwd=repo_path)
    
    # Revert regardless of build result
    write_file(command_go_path, content)
    
    if returncode == 0:
        print(f"[DEBUG] Build PASSED - apply mechanism works!", file=sys.stderr)
        return True
    else:
        raise Exception(f"Hardcoded test: Build failed. This indicates the apply mechanism is broken. Errors:\n{stderr[:500]}")
