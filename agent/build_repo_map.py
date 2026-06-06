"""Stage 0: Build repository map by scanning all .go files."""
import os
import re
import json
from typing import Dict, List


def build_repo_map(repo_path: str) -> Dict:
    """Scan all .go files and extract code structure.
    
    Args:
        repo_path: Path to cloned repository
        
    Returns:
        Dict with files, packages, functions, types, imports
    """
    print("[Stage 0] Building repository map...", end=" ", flush=True)
    
    repo_map = {
        'files': {},  # filepath -> file_info
        'packages': {},  # package_name -> list of files
        'functions': {},  # function_name -> list of (file, pkg)
        'types': {},  # type_name -> list of (file, pkg)
        'imports': {},  # package -> list of files that import it
    }
    
    go_files = []
    
    # Walk directory tree
    for root, dirs, files in os.walk(repo_path):
        # Skip vendor, .git, testdata, and other non-source directories
        dirs[:] = [d for d in dirs if d not in ['vendor', '.git', '.github', 'testdata', 'site', 'assets', 'doc']]
        
        for file in files:
            if file.endswith('.go') and not file.endswith('_test.go'):
                go_files.append(os.path.join(root, file))
    
    # Parse each file
    for filepath in go_files:
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Relative path for storage
            rel_path = filepath[len(repo_path):].lstrip('/')
            
            # Extract package name
            pkg_match = re.search(r'^\s*package\s+(\w+)', content, re.MULTILINE)
            package_name = pkg_match.group(1) if pkg_match else 'main'
            
            # Extract imports
            imports = re.findall(r'^\s*import\s+\(\s*(.*?)\s*\)', content, re.MULTILINE | re.DOTALL)
            import_list = []
            if imports:
                for imp_block in imports:
                    imp_lines = re.findall(r'["\']([^"\']+)["\']', imp_block)
                    import_list.extend(imp_lines)
            else:
                # Single line imports
                single_imports = re.findall(r'^\s*import\s+["\']([^"\']+)["\']', content, re.MULTILINE)
                import_list.extend(single_imports)
            
            # Extract function names (func keyword, but not methods on types)
            functions = re.findall(r'^\s*func\s+(?:\([^)]*\)\s+)?(\w+)\s*\(', content, re.MULTILINE)
            
            # Extract type definitions (struct, interface, etc.)
            types = re.findall(r'^\s*type\s+(\w+)\s+(?:struct|interface|\w+)', content, re.MULTILINE)
            
            # Store file info
            repo_map['files'][rel_path] = {
                'package': package_name,
                'functions': functions,
                'types': types,
                'imports': import_list,
                'full_path': filepath
            }
            
            # Index by package
            if package_name not in repo_map['packages']:
                repo_map['packages'][package_name] = []
            repo_map['packages'][package_name].append(rel_path)
            
            # Index functions
            for func in functions:
                if func not in repo_map['functions']:
                    repo_map['functions'][func] = []
                repo_map['functions'][func].append((rel_path, package_name))
            
            # Index types
            for type_name in types:
                if type_name not in repo_map['types']:
                    repo_map['types'][type_name] = []
                repo_map['types'][type_name].append((rel_path, package_name))
            
            # Index imports
            for imp in import_list:
                if imp not in repo_map['imports']:
                    repo_map['imports'][imp] = []
                repo_map['imports'][imp].append(rel_path)
        
        except Exception as e:
            # Skip files that can't be parsed
            continue
    
    print(f"✓ scanned {len(go_files)} files")
    
    return repo_map


def save_repo_map(repo_map: Dict, output_path: str) -> None:
    """Save repository map to JSON file for inspection.
    
    Args:
        repo_map: Repository map dict
        output_path: Path to save JSON
    """
    # Convert to JSON-serializable format
    serializable = {
        'files': repo_map['files'],
        'packages': repo_map['packages'],
        'functions': {k: v for k, v in repo_map['functions'].items()},
        'types': {k: v for k, v in repo_map['types'].items()},
        'imports': repo_map['imports'],
    }
    
    with open(output_path, 'w') as f:
        json.dump(serializable, f, indent=2)
