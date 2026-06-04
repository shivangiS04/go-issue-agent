"""Stage 1: Fetch GitHub issue details using REST API."""
import re
import requests
from typing import Dict, Optional


def parse_issue_url(url: str) -> Optional[Dict[str, str]]:
    """Parse GitHub issue URL to extract owner, repo, and issue number.
    
    Args:
        url: GitHub issue URL
        
    Returns:
        Dict with 'owner', 'repo', 'number' keys, or None if invalid
    """
    pattern = r'https://github\.com/([^/]+)/([^/]+)/issues/(\d+)'
    match = re.match(pattern, url)
    
    if match:
        return {
            'owner': match.group(1),
            'repo': match.group(2),
            'number': int(match.group(3))
        }
    return None


def is_approved_repo(owner: str, repo: str, approved_repos) -> bool:
    """Check if repository is in approved list.
    
    Args:
        owner: Repository owner
        repo: Repository name
        approved_repos: List of (owner, repo) tuples
        
    Returns:
        True if approved, False otherwise
    """
    return (owner, repo) in approved_repos


def fetch_issue(issue_url: str, approved_repos) -> Dict:
    """Fetch issue details from GitHub API.
    
    Args:
        issue_url: Full GitHub issue URL
        approved_repos: List of approved (owner, repo) tuples
        
    Returns:
        Dict with issue details: title, body, comments, labels, etc.
        
    Raises:
        ValueError: If URL is invalid or repository not approved
        requests.RequestException: If API call fails
    """
    print("[Stage 1] Fetching issue...", end=" ", flush=True)
    
    # Parse URL
    parsed = parse_issue_url(issue_url)
    if not parsed:
        raise ValueError(f"Invalid GitHub issue URL: {issue_url}")
    
    owner = parsed['owner']
    repo = parsed['repo']
    number = parsed['number']
    
    # Check if approved
    if not is_approved_repo(owner, repo, approved_repos):
        approved_list = ", ".join([f"{o}/{r}" for o, r in approved_repos])
        raise ValueError(
            f"Repository {owner}/{repo} is not approved. "
            f"Approved repositories: {approved_list}"
        )
    
    # Fetch issue from GitHub API
    api_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{number}"
    
    try:
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        issue_data = response.json()
        
        # Fetch comments
        comments_url = issue_data.get('comments_url')
        comments_data = []
        if comments_url:
            comments_response = requests.get(comments_url, timeout=30)
            if comments_response.status_code == 200:
                comments_data = comments_response.json()
        
        # Build result
        result = {
            'owner': owner,
            'repo': repo,
            'number': number,
            'title': issue_data.get('title', ''),
            'body': issue_data.get('body', ''),
            'labels': [label['name'] for label in issue_data.get('labels', [])],
            'state': issue_data.get('state', ''),
            'comments': [
                {
                    'author': comment.get('user', {}).get('login', ''),
                    'body': comment.get('body', '')
                }
                for comment in comments_data
            ]
        }
        
        print("✓")
        return result
        
    except requests.RequestException as e:
        print("✗")
        raise ValueError(f"Failed to fetch issue: {e}")
