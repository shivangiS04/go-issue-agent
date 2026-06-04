"""Stage 7: Generate PR summary using AI."""
import json
from groq import Groq
from typing import Dict
from tools import get_git_diff


def generate_pr_summary(repo_path: str, issue_data: Dict, analysis: Dict, 
                       plan: Dict, validation: Dict, groq_client: Groq, 
                       system_prompt: str) -> Dict:
    """Generate PR title and body.
    
    Args:
        repo_path: Path to repository
        issue_data: Issue data from Stage 1
        analysis: Analysis from Stage 2
        plan: Plan from Stage 4
        validation: Validation results from Stage 6
        groq_client: Groq API client
        system_prompt: System prompt
        
    Returns:
        Dict with 'title' and 'body' for PR
    """
    print("[Stage 7] Generating PR summary...", end=" ", flush=True)
    
    # Get git diff
    diff = get_git_diff(repo_path)
    
    # Build prompt
    validation_summary = f"""Test Status: {validation.get('test_status', 'unknown')}
Format Status: {validation.get('fmt_status', 'unknown')}
Vet Status: {validation.get('vet_status', 'unknown')}"""
    
    if validation.get('failures'):
        validation_summary += "\n\nFailures:\n"
        for failure in validation['failures']:
            validation_summary += f"- {failure['type']}: {failure['message'][:100]}\n"
    
    user_prompt = f"""Generate a pull request title and body for this fix.

Issue: #{issue_data['number']} - {issue_data['title']}
Issue Summary: {analysis.get('summary', issue_data['title'])}

Changes Made:
{chr(10).join([f"- {c['file']}: {c.get('description', 'Modified')}" for c in plan.get('changes', [])])}

Git Diff:
```
{diff[:2000]}
```

Validation Results:
{validation_summary}

Generate a PR in this format:
{{
  "title": "Fix: Brief description (max 70 chars)",
  "body": "Markdown formatted PR body with:\\n## Overview\\n\\n## Changes\\n\\n## Testing\\n\\nFixes #{issue_data['number']}"
}}

Return ONLY valid JSON."""
    
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
        
        # Remove markdown code fences
        if response_text.startswith('```'):
            lines = response_text.split('\n')
            response_text = '\n'.join(lines[1:-1])
        
        pr_data = json.loads(response_text)
        
        print("✓")
        return pr_data
        
    except Exception as e:
        print(f"✗ (Error: {e})")
        # Return minimal PR
        return {
            'title': f"Fix: {analysis.get('summary', issue_data['title'])[:60]}",
            'body': f"""## Overview

Fixes #{issue_data['number']} - {issue_data['title']}

## Changes

{chr(10).join([f"- Modified `{c['file']}`" for c in plan.get('changes', [])])}

## Testing

{validation_summary}
"""
        }
