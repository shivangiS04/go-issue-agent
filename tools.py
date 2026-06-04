"""Helper tools for file operations, code search, and command execution."""
import os
import subprocess
from typing import List, Tuple


def read_file(path: str) -> str:
    """Read file content from path.
    
    Args:
        path: File path to read
        
    Returns:
        File content as string
        
    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file cannot be read
    """
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


def write_file(path: str, content: str) -> None:
    """Write content to file.
    
    Args:
        path: File path to write
        content: Content to write
        
    Raises:
        IOError: If file cannot be written
    """
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def search_code(repo_path: str, query: str) -> List[Tuple[str, int, str]]:
    """Search for query in code files using grep.
    
    Args:
        repo_path: Path to repository
        query: Search term
        
    Returns:
        List of tuples (filepath, line_number, line_content)
    """
    results = []
    
    try:
        # Run grep to search for the query
        cmd = [
            'grep', '-rn',  # recursive, with line numbers
            '--include=*.go',  # only .go files
            query,
            repo_path
        ]
        
        stdout, stderr, returncode = run_command(cmd, cwd=repo_path)
        
        if returncode == 0:  # grep found matches
            for line in stdout.strip().split('\n'):
                if line:
                    # Parse grep output: filepath:line_number:line_content
                    parts = line.split(':', 2)
                    if len(parts) >= 3:
                        filepath = parts[0]
                        line_number = int(parts[1])
                        line_content = parts[2]
                        results.append((filepath, line_number, line_content))
    except Exception as e:
        # If grep fails, return empty results
        pass
    
    return results


def run_command(cmd: List[str], cwd: str = None) -> Tuple[str, str, int]:
    """Run a shell command and return output.
    
    Args:
        cmd: Command as list of strings
        cwd: Working directory for command
        
    Returns:
        Tuple of (stdout, stderr, returncode)
    """
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timed out", 1
    except Exception as e:
        return "", str(e), 1


def get_git_diff(repo_path: str) -> str:
    """Get git diff of uncommitted changes.
    
    Args:
        repo_path: Path to git repository
        
    Returns:
        Git diff output as string
    """
    stdout, stderr, returncode = run_command(
        ['git', 'diff', 'HEAD'],
        cwd=repo_path
    )
    
    if returncode == 0:
        return stdout
    else:
        return f"Error getting diff: {stderr}"
