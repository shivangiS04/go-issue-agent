"""Stage 4: Generate fix plan using AI."""
import json
from groq import Groq
from typing import Dict


def plan_fix(issue_data: Dict, analysis: Dict, files: Dict, groq_client: Groq, system_prompt: str) -> Dict:
    """Generate a fix plan using AI.
    
    Args:
        issue_data: Issue data from Stage 1
        analysis: Analysis from Stage 2
        files: Files from Stage 3
        groq_client: Groq API client
        system_prompt: System prompt
        
    Returns:
        Dict with fix plan: files_to_change, changes (description), tests_to_add
    """
    print("[Stage 4] Planning fix...", end=" ", flush=True)
    
    # Build planning prompt
    files_summary = "\n\n".join([
        f"File: {f['path']}\n```go\n{f['content'][:1000]}\n```"
        for f in files['relevant_files'][:3]  # Include first 3 files only
    ])
    
    user_prompt = f"""Plan a fix for this issue.

Issue Summary: {analysis.get('summary', issue_data['title'])}
Issue Type: {analysis.get('issue_type', 'unknown')}
Current Behavior: {analysis.get('current_behavior', 'See issue')}
Expected Behavior: {analysis.get('expected_behavior', 'See issue')}

Relevant Files:
{files_summary}

Create a fix plan and return as JSON:
{{
  "files_to_change": ["path/to/file.go", ...],
  "changes": [
    {{
      "file": "path/to/file.go",
      "description": "what to change",
      "location": {{"line": 42, "function": "FunctionName"}}
    }}
  ],
  "tests_to_add": ["path/to/test_file.go", ...]
}}

Return ONLY valid JSON, no markdown formatting."""
    
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # Remove markdown code fences if present
        if response_text.startswith('```'):
            lines = response_text.split('\n')
            response_text = '\n'.join(lines[1:-1])
        
        plan = json.loads(response_text)
        
        print("✓")
        return plan
        
    except json.JSONDecodeError as e:
        print(f"✗ (JSON error: {e})")
        # Return minimal plan
        return {
            'files_to_change': [files['relevant_files'][0]['path']] if files['relevant_files'] else [],
            'changes': [{
                'file': files['relevant_files'][0]['path'] if files['relevant_files'] else 'unknown',
                'description': 'Fix issue as described',
                'location': {'line': 0, 'function': 'unknown'}
            }],
            'tests_to_add': []
        }
    except Exception as e:
        print(f"✗ (Error: {e})")
        raise
