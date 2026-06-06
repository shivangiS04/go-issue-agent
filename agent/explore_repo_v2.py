"""Stage 3 (v2): Explore repository using repo map and AI reasoning."""
import os
import json
from typing import Dict, List
from tools import read_file
from agent.llm_client import call_llm


def explore_repo_with_map(repo_path: str, analysis: Dict, repo_map: Dict, groq_client, 
                          system_prompt: str, max_files: int = 4, max_lines: int = 300, config=None) -> Dict:
    """Find relevant files using repo map and AI reasoning.
    
    Args:
        repo_path: Path to cloned repository
        analysis: Analysis result from Stage 2
        repo_map: Repository map from Stage 0
        groq_client: Deprecated - kept for compatibility
        system_prompt: System prompt for AI
        max_files: Maximum number of files to return
        max_lines: Maximum lines per file
        config: Configuration module (required for multi-provider support)
        
    Returns:
        Dict with relevant_files list containing file paths and content
    """
    print("[Stage 3] Exploring repo...", end=" ", flush=True)
    
    issue_title = analysis.get('summary', '')
    issue_description = analysis.get('expected_behavior', '')
    search_terms = analysis.get('search_terms', [])
    
    # Build context about the codebase for the AI
    repo_context = f"""
Repository Structure:
- Packages: {', '.join(list(repo_map['packages'].keys())[:20])}
- Total files: {len(repo_map['files'])}
- Key types: {', '.join(list(repo_map['types'].keys())[:30])}
- Key functions: {', '.join(list(repo_map['functions'].keys())[:30])}

File inventory:
"""
    
    for filepath, info in list(repo_map['files'].items())[:50]:
        repo_context += f"\n- {filepath} (pkg: {info['package']}, types: {', '.join(info['types'][:3])}, funcs: {', '.join(info['functions'][:3])})"
    
    # Ask AI to identify relevant files
    ai_prompt = f"""You are analyzing a GitHub issue to identify which source files need to be modified.

Issue: {issue_title}
Description: {issue_description}
Search terms: {', '.join(search_terms)}

{repo_context}

Based on the issue and the codebase structure, identify the TOP {max_files} most relevant .go files that likely need changes.
Return ONLY a JSON list of file paths, nothing else. Example: ["file1.go", "file2.go"]"""
    
    try:
        # Use unified LLM client
        response_text = call_llm(
            messages=[{"role": "user", "content": ai_prompt}],
            system_prompt=system_prompt,
            config=config,
            temperature=0.2
        )
        
        # Parse JSON response
        try:
            # Try to extract JSON from response
            if '[' in response_text:
                json_start = response_text.index('[')
                json_end = response_text.rindex(']') + 1
                json_text = response_text[json_start:json_end]
                suggested_files = json.loads(json_text)
            else:
                suggested_files = json.loads(response_text)
        except:
            # Fallback: return empty list
            suggested_files = []
        
    except Exception as e:
        suggested_files = []
    
    # Validate suggested files exist in repo map
    files_to_read = []
    for filepath in suggested_files:
        if filepath in repo_map['files']:
            files_to_read.append(filepath)
        # Also try without leading ./
        elif filepath.lstrip('./') in repo_map['files']:
            files_to_read.append(filepath.lstrip('./'))
    
    # If AI didn't find files, fall back to searching by function/type names
    if not files_to_read:
        files_to_read = _fallback_file_search(repo_map, search_terms, max_files)
    
    # Read file contents
    file_contents = []
    for filepath in files_to_read[:max_files]:
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
            continue
    
    print(f"✓ identified {len(file_contents)} relevant files")
    
    return {
        'relevant_files': file_contents
    }


def _fallback_file_search(repo_map: Dict, search_terms: List[str], max_files: int) -> List[str]:
    """Fallback: Search for files by matching function/type names.
    
    Args:
        repo_map: Repository map
        search_terms: Search terms from issue analysis
        max_files: Maximum files to return
        
    Returns:
        List of relevant file paths
    """
    scored_files = {}
    
    for term in search_terms:
        term_lower = term.lower()
        
        # Search in function names
        for func_name, locations in repo_map['functions'].items():
            if term_lower in func_name.lower():
                for filepath, pkg in locations:
                    scored_files[filepath] = scored_files.get(filepath, 0) + 2
        
        # Search in type names
        for type_name, locations in repo_map['types'].items():
            if term_lower in type_name.lower():
                for filepath, pkg in locations:
                    scored_files[filepath] = scored_files.get(filepath, 0) + 2
        
        # Search in filenames
        for filepath in repo_map['files'].keys():
            if term_lower in filepath.lower():
                scored_files[filepath] = scored_files.get(filepath, 0) + 1
    
    # Sort by score and return top files
    sorted_files = sorted(scored_files.items(), key=lambda x: x[1], reverse=True)
    return [f[0] for f in sorted_files[:max_files]]
