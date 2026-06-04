"""Stage 3: Explore repository to find relevant files."""
import os
from typing import Dict, List
from tools import search_code, read_file


def explore_repo(repo_path: str, analysis: Dict, max_files: int = 4, max_lines: int = 300) -> Dict:
    """Search repository for relevant files based on analysis.
    
    Args:
        repo_path: Path to cloned repository
        analysis: Analysis result from Stage 2
        max_files: Maximum number of files to return
        max_lines: Maximum lines per file
        
    Returns:
        Dict with relevant_files list containing file paths and content
    """
    print("[Stage 3] Exploring repo...", end=" ", flush=True)
    
    search_terms = analysis.get('search_terms', [])
    relevant_files = {}  # filepath -> score
    
    # Search for each term
    for term in search_terms:
        results = search_code(repo_path, term)
        for filepath, line_num, line_content in results:
            # Normalize path
            if filepath.startswith(repo_path):
                filepath = filepath[len(repo_path):].lstrip('/')
            
            # Skip test files for now (we'll add them back later)
            if '_test.go' in filepath:
                continue
            
            # Skip vendor directories
            if 'vendor/' in filepath:
                continue
            
            # Score files based on number of matches
            if filepath not in relevant_files:
                relevant_files[filepath] = 0
            relevant_files[filepath] += 1
    
    # Sort by score and take top N
    sorted_files = sorted(relevant_files.items(), key=lambda x: x[1], reverse=True)
    top_files = [f[0] for f in sorted_files[:max_files]]
    
    # Read file contents
    file_contents = []
    for filepath in top_files:
        full_path = os.path.join(repo_path, filepath)
        try:
            content = read_file(full_path)
            lines = content.split('\n')
            
            # Truncate if too long
            if len(lines) > max_lines:
                content = '\n'.join(lines[:max_lines]) + '\n... (truncated)'
            
            file_contents.append({
                'path': filepath,
                'content': content
            })
            
            # Also look for corresponding test file
            if filepath.endswith('.go'):
                test_filepath = filepath[:-3] + '_test.go'
                test_full_path = os.path.join(repo_path, test_filepath)
                if os.path.exists(test_full_path):
                    test_content = read_file(test_full_path)
                    test_lines = test_content.split('\n')
                    if len(test_lines) > max_lines:
                        test_content = '\n'.join(test_lines[:max_lines]) + '\n... (truncated)'
                    
                    file_contents.append({
                        'path': test_filepath,
                        'content': test_content
                    })
        except Exception as e:
            # Skip files that can't be read
            continue
    
    print(f"✓ found {len(file_contents)} relevant files")
    
    return {
        'relevant_files': file_contents
    }
