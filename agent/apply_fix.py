"""Stage 5: Apply the fix by modifying files."""
import os
import json
from groq import Groq
from typing import Dict, List
from tools import read_file, write_file, run_command


def apply_fix(repo_path: str, plan: Dict, files: Dict, groq_client: Groq, 
              system_prompt: str, max_retries: int = 3) -> Dict:
    """Apply fix to files based on plan.
    
    Args:
        repo_path: Path to repository
        plan: Fix plan from Stage 4
        files: Files from Stage 3
        groq_client: Groq API client
        system_prompt: System prompt
        max_retries: Maximum build retry attempts
        
    Returns:
        Dict with applied_changes list
    """
    print("[Stage 5] Applying fix...", end=" ", flush=True)
    
    applied_changes = []
    files_to_change = plan.get('files_to_change', [])
    
    # Get file contents
    file_map = {f['path']: f['content'] for f in files['relevant_files']}
    
    for file_path in files_to_change:
        if file_path not in file_map:
            # Try to read file
            full_path = os.path.join(repo_path, file_path)
            if os.path.exists(full_path):
                file_map[file_path] = read_file(full_path)
            else:
                continue
        
        # Find change description for this file
        change_desc = None
        for change in plan.get('changes', []):
            if change.get('file') == file_path:
                change_desc = change.get('description', '')
                break
        
        if not change_desc:
            change_desc = "Apply fix as described in the plan"
        
        # Ask AI to generate fixed code
        user_prompt = f"""Generate the COMPLETE updated file content for this fix.

File: {file_path}

Current Content:
```go
{file_map[file_path]}
```

Change to make: {change_desc}

Return the COMPLETE updated file content. Do NOT return a diff, return the entire file with changes applied.
Start with 'package' and include everything."""
        
        try:
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2
            )
            
            new_content = response.choices[0].message.content.strip()
            
            # Remove markdown code fences if present
            if new_content.startswith('```'):
                lines = new_content.split('\n')
                # Find first line that starts with 'package'
                start_idx = 0
                for i, line in enumerate(lines):
                    if line.strip().startswith('package '):
                        start_idx = i
                        break
                # Find last ``` line
                end_idx = len(lines)
                for i in range(len(lines) - 1, -1, -1):
                    if lines[i].strip() == '```':
                        end_idx = i
                        break
                new_content = '\n'.join(lines[start_idx:end_idx])
            
            # Write to file
            full_path = os.path.join(repo_path, file_path)
            write_file(full_path, new_content)
            
            applied_changes.append({
                'file': file_path,
                'status': 'modified'
            })
            
        except Exception as e:
            applied_changes.append({
                'file': file_path,
                'status': 'failed',
                'error': str(e)
            })
    
    print("✓")
    
    # Try to build
    retry_count = 0
    while retry_count < max_retries:
        print(f"[Stage 5] Building... (attempt {retry_count + 1}/{max_retries})", end=" ", flush=True)
        stdout, stderr, returncode = run_command(['go', 'build', './...'], cwd=repo_path)
        
        if returncode == 0:
            print("✓")
            break
        else:
            print(f"✗")
            print(f"  Build error: {stderr[:200]}")
            
            if retry_count < max_retries - 1:
                # Try to fix build errors
                print(f"[Stage 5] Attempting to fix build errors...", end=" ", flush=True)
                
                fix_prompt = f"""The Go build failed with this error:

{stderr[:1000]}

For file: {files_to_change[0] if files_to_change else 'unknown'}

Current content:
```go
{file_map.get(files_to_change[0], 'N/A')[:1000]}
```

Generate the COMPLETE fixed file content that will resolve the build error.
Return ONLY the complete Go file content, no explanation."""
                
                try:
                    fix_response = groq_client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": fix_prompt}
                        ],
                        temperature=0.2
                    )
                    
                    fixed_content = fix_response.choices[0].message.content.strip()
                    
                    # Remove markdown
                    if fixed_content.startswith('```'):
                        lines = fixed_content.split('\n')
                        start_idx = 0
                        for i, line in enumerate(lines):
                            if line.strip().startswith('package '):
                                start_idx = i
                                break
                        end_idx = len(lines)
                        for i in range(len(lines) - 1, -1, -1):
                            if lines[i].strip() == '```':
                                end_idx = i
                                break
                        fixed_content = '\n'.join(lines[start_idx:end_idx])
                    
                    # Write fixed content
                    if files_to_change:
                        full_path = os.path.join(repo_path, files_to_change[0])
                        write_file(full_path, fixed_content)
                        print("✓")
                except:
                    print("✗")
            
            retry_count += 1
    
    return {
        'applied_changes': applied_changes,
        'build_success': returncode == 0
    }
