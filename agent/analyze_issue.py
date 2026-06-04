"""Stage 2: Analyze issue using Groq API to extract structured information."""
import json
from groq import Groq
from typing import Dict


def analyze_issue(issue_data: Dict, groq_client: Groq, system_prompt: str) -> Dict:
    """Analyze issue using AI to extract structured metadata.
    
    Args:
        issue_data: Issue data from Stage 1
        groq_client: Groq API client
        system_prompt: System prompt for AI
        
    Returns:
        Dict with: issue_type, summary, expected_behavior, current_behavior,
                   search_terms, affected_areas
    """
    print("[Stage 2] Analyzing issue...", end=" ", flush=True)
    
    # Build analysis prompt
    user_prompt = f"""Analyze this GitHub issue and extract structured information.

Issue Title: {issue_data['title']}

Issue Body:
{issue_data['body']}

Labels: {', '.join(issue_data['labels'])}

Extract the following information and return as JSON:
- issue_type: (bug_fix, feature, enhancement, documentation, etc.)
- summary: (one-sentence summary of the issue)
- expected_behavior: (what should happen)
- current_behavior: (what actually happens)
- search_terms: (list of keywords to search in the codebase, 5-10 terms)
- affected_areas: (list of likely affected components/packages)

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
        
        # Parse response
        response_text = response.choices[0].message.content.strip()
        
        # Remove markdown code fences if present
        if response_text.startswith('```'):
            # Remove first line (```json or ```)
            lines = response_text.split('\n')
            response_text = '\n'.join(lines[1:-1])
        
        result = json.loads(response_text)
        
        print("✓")
        return result
        
    except json.JSONDecodeError as e:
        print("✗")
        # Fallback to simple extraction
        return {
            'issue_type': 'unknown',
            'summary': issue_data['title'],
            'expected_behavior': 'Not specified',
            'current_behavior': 'Not specified',
            'search_terms': extract_keywords(issue_data['title'] + ' ' + issue_data['body']),
            'affected_areas': []
        }
    except Exception as e:
        print(f"✗ (Error: {e})")
        raise


def extract_keywords(text: str) -> list:
    """Simple keyword extraction as fallback.
    
    Args:
        text: Text to extract keywords from
        
    Returns:
        List of keywords
    """
    # Simple extraction: words longer than 3 chars, lowercase
    words = text.lower().split()
    keywords = [w.strip('.,;:()[]{}') for w in words if len(w) > 3]
    # Remove duplicates while preserving order
    seen = set()
    unique = []
    for k in keywords:
        if k not in seen:
            seen.add(k)
            unique.append(k)
    return unique[:10]
