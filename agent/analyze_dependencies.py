"""Stage 3.5: Analyze project dependencies from go.mod and go.sum."""
import os
import re
from typing import Dict, List


def analyze_dependencies(repo_path: str) -> Dict:
    """Read go.mod and go.sum to extract dependency information.
    
    Args:
        repo_path: Path to cloned repository
        
    Returns:
        Dict with dependencies list and constraint summary
    """
    print("[Stage 3.5] Analyzing dependencies...", end=" ", flush=True)
    
    go_mod_path = os.path.join(repo_path, 'go.mod')
    go_sum_path = os.path.join(repo_path, 'go.sum')
    
    dependencies = {
        'direct_deps': [],  # Direct dependencies from go.mod
        'all_deps': [],     # All deps (from go.sum)
        'stdlib_packages': [],  # Standard library imports
        'constraint_summary': '',
    }
    
    # Parse go.mod
    if os.path.exists(go_mod_path):
        try:
            with open(go_mod_path, 'r') as f:
                content = f.read()
            
            # Extract module name
            module_match = re.search(r'^module\s+(\S+)', content, re.MULTILINE)
            module_name = module_match.group(1) if module_match else 'unknown'
            
            # Extract go version requirement
            go_version_match = re.search(r'^go\s+(\S+)', content, re.MULTILINE)
            go_version = go_version_match.group(1) if go_version_match else 'unknown'
            
            # Extract require block
            require_block = re.search(
                r'^require\s*\(([^)]*)\)',
                content,
                re.MULTILINE | re.DOTALL
            )
            
            if require_block:
                require_lines = require_block.group(1).strip().split('\n')
                for line in require_lines:
                    line = line.strip()
                    if line and not line.startswith('//'):
                        parts = line.split()
                        if len(parts) >= 2:
                            pkg_name = parts[0]
                            version = parts[1]
                            dependencies['direct_deps'].append({
                                'package': pkg_name,
                                'version': version
                            })
            else:
                # Single require line
                single_requires = re.findall(r'^require\s+(\S+)\s+(\S+)', content, re.MULTILINE)
                for pkg, version in single_requires:
                    dependencies['direct_deps'].append({
                        'package': pkg,
                        'version': version
                    })
            
            # Build constraint summary
            constraint_summary = f"""
Go Module: {module_name}
Go Version: {go_version}
Direct Dependencies ({len(dependencies['direct_deps'])}):
"""
            for dep in dependencies['direct_deps']:
                constraint_summary += f"  - {dep['package']} {dep['version']}\n"
            
            dependencies['constraint_summary'] = constraint_summary
        
        except Exception as e:
            dependencies['constraint_summary'] = f"Error reading go.mod: {e}\n"
    
    # Parse go.sum (for reference)
    if os.path.exists(go_sum_path):
        try:
            with open(go_sum_path, 'r') as f:
                go_sum_lines = f.readlines()
            
            # Extract unique modules (first word before version)
            modules_set = set()
            for line in go_sum_lines:
                if line.strip():
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        modules_set.add(parts[0])
            
            dependencies['all_deps'] = sorted(list(modules_set))
        
        except Exception as e:
            pass
    
    print(f"✓ found {len(dependencies['direct_deps'])} direct dependencies")
    
    return dependencies


def get_dependency_constraint_prompt(dependencies: Dict) -> str:
    """Generate a prompt fragment about dependency constraints for the AI.
    
    Args:
        dependencies: Dependencies dict from analyze_dependencies
        
    Returns:
        String to include in AI prompt
    """
    prompt = f"""
IMPORTANT CONSTRAINT: Dependency Management
============================================
{dependencies.get('constraint_summary', '')}

The fix MUST satisfy these constraints:
1. Do NOT introduce new external dependencies
2. Do NOT modify go.mod or go.sum
3. Use ONLY packages and modules that are already listed above
4. Any imports must come from existing dependencies or the Go standard library
5. The fix must compile without running `go get` or adding new modules

If the issue requires a feature that needs a new dependency, propose an alternative using only existing dependencies.
"""
    
    return prompt
