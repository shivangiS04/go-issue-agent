"""Stage 4: Generate fix plan using AI with structured representation."""
import json
from typing import Dict, Optional, List
from agent.analyze_dependencies import get_dependency_constraint_prompt
from agent.llm_client import call_llm


def get_minimal_edit_constraints() -> str:
    """Get constraints for minimal, targeted editing."""
    return """
CRITICAL EDITING CONSTRAINTS:
- Never add new imports or rewrite import blocks
- Never rewrite existing functions completely
- Never modify test files unless absolutely necessary
- Only add or modify the minimum code necessary
- Make surgical, targeted edits only
- Never remove code unless explicitly stated as required
- Never touch unrelated functions or code sections
- Prioritize modifying existing logic over adding new functions
- Read the issue comments carefully. If the reporter identifies a specific function or line number, target ONLY that function.
- Never modify struct definitions or type declarations to fix a bug.
"""


def plan_fix(issue_data: Dict, analysis: Dict, files: Dict, groq_client, system_prompt: str, dependencies: Dict = None, target_function: Optional[str] = None, config=None) -> Dict:
    """Generate a fix plan using AI with structured representation.
    
    Args:
        issue_data: Issue data from Stage 1
        analysis: Analysis from Stage 2
        files: Files from Stage 3
        groq_client: Deprecated - kept for compatibility
        system_prompt: System prompt
        dependencies: Dependencies info from Stage 3.5 (optional)
        target_function: Deprecated - ignored
        config: Configuration module (required for multi-provider support)
        
    Returns:
        Dict with structured fix plan:
        {
            "files_to_change": ["path/to/file.go", ...],
            "changes": [
                {
                    "file": "path/to/file.go",
                    "type": "insert_after" | "insert_before" | "replace",
                    "target": "exact code string to find",
                    "location_hint": "human-readable location description",
                    "code": "code to insert/replace with"
                }
            ]
        }
    """
    print("[Stage 4] Planning fix...", end=" ", flush=True)
    
    # Build planning prompt with first 3 files
    files_summary = "\n\n".join([
        f"File: {f['path']}\n```go\n{f['content'][:1500]}\n```"
        for f in files['relevant_files'][:3]
    ])
    
    # Add dependency constraints if available
    dependency_constraint = ""
    if dependencies:
        dependency_constraint = get_dependency_constraint_prompt(dependencies)
    
    # Add minimal edit constraints
    minimal_edit_constraints = get_minimal_edit_constraints()
    
    issue_body = issue_data['body'][:1500]
    issue_title = issue_data['title']
    issue_summary = analysis.get('summary', issue_data['title'])
    issue_type = analysis.get('issue_type', 'unknown')
    current_behavior = analysis.get('current_behavior', 'See issue')
    expected_behavior = analysis.get('expected_behavior', 'See issue')
    
    user_prompt = f"""Analyze this GitHub issue and generate a STRUCTURED fix plan.

Issue Title: {issue_title}
Issue Summary: {issue_summary}
Issue Type: {issue_type}
Current Behavior: {current_behavior}
Expected Behavior: {expected_behavior}

Issue Body:
{issue_body}

Relevant Files:
{files_summary}

{dependency_constraint}

{minimal_edit_constraints}

IMPORTANT: Return a STRUCTURED JSON plan with EXACT code strings. The "target" field must be an EXACT code snippet that appears in the file.

JSON Schema:
{{
  "files_to_change": ["path/to/file.go"],
  "changes": [
    {{
      "file": "path/to/file.go",
      "type": "insert_after",
      "target": "c.lflags.AddFlag(f)",
      "location_hint": "inside addToLocal closure in LocalFlags() function",
      "code": "if f.Changed {{\\n\\tc.lflags.Lookup(f.Name).Changed = true\\n}}"
    }}
  ]
}}

VALID OPERATIONS:
- "insert_after": Insert code after the target line
- "insert_before": Insert code before the target line  
- "replace": Replace the target code with the new code

CRITICAL RULES:
1. The "target" must be an EXACT string that appears in the file (copy it verbatim from the file content above)
2. For "insert_after", the target should be a single line or short code block
3. For "replace", the target should be the exact code to replace
4. The "code" field should be properly formatted Go code with correct indentation
5. Use \\t for tabs and \\n for newlines in the code field
6. "location_hint" is for human reference - describe where the target is located

EXAMPLE for adding code after a line:
{{
  "file": "command.go",
  "type": "insert_after",
  "target": "c.lflags.AddFlag(f)",
  "location_hint": "inside the addToLocal closure after AddFlag call",
  "code": "if f.Changed {{\\n\\tc.lflags.Lookup(f.Name).Changed = true\\n}}"
}}

Return ONLY valid JSON, no markdown formatting, no explanation."""

    try:
        # Use unified LLM client
        response_text = call_llm(
            messages=[{"role": "user", "content": user_prompt}],
            system_prompt=system_prompt,
            config=config,
            temperature=0.1
        )
        
        # Remove markdown code fences if present
        if response_text.startswith('```'):
            lines = response_text.split('\n')
            response_text = '\n'.join(lines[1:-1])
        
        plan = json.loads(response_text)
        
        # Validate plan structure
        if 'files_to_change' not in plan or 'changes' not in plan:
            raise ValueError("Plan missing required fields: files_to_change or changes")
        
        # Validate each change has required fields
        for i, change in enumerate(plan['changes']):
            if 'file' not in change or 'type' not in change or 'target' not in change or 'code' not in change:
                raise ValueError(f"Change {i} missing required fields: file, type, target, or code")
            if change['type'] not in ['insert_after', 'insert_before', 'replace']:
                raise ValueError(f"Change {i} has invalid type: {change['type']}")
        
        print("✓")
        return plan
        
    except json.JSONDecodeError as e:
        print(f"✗ (JSON error: {e})")
        # Return minimal plan
        first_file = files['relevant_files'][0]['path'] if files['relevant_files'] else 'unknown'
        return {
            'files_to_change': [first_file],
            'changes': [{
                'file': first_file,
                'type': 'replace',
                'target': '',
                'location_hint': 'unknown location',
                'code': ''
            }]
        }
    except Exception as e:
        print(f"✗ (Error: {e})")
        raise
