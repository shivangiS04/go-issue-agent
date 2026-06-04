"""Stage 6: Validate changes with tests and checks."""
from typing import Dict
from tools import run_command


def validate(repo_path: str) -> Dict:
    """Run validation checks on the changes.
    
    Args:
        repo_path: Path to repository
        
    Returns:
        Dict with validation results
    """
    print("[Stage 6] Validating changes...")
    
    results = {
        'test_status': 'not_run',
        'fmt_status': 'not_run',
        'vet_status': 'not_run',
        'failures': []
    }
    
    # Run go test
    print("  Running go test...", end=" ", flush=True)
    stdout, stderr, returncode = run_command(['go', 'test', './...'], cwd=repo_path)
    
    if returncode == 0:
        print("✓")
        results['test_status'] = 'passed'
        # Count tests from output
        if 'PASS' in stdout:
            results['test_output'] = stdout
    else:
        print("✗")
        results['test_status'] = 'failed'
        results['test_output'] = stderr
        results['failures'].append({
            'type': 'test',
            'message': stderr[:500]
        })
    
    # Run go fmt check
    print("  Running go fmt...", end=" ", flush=True)
    stdout, stderr, returncode = run_command(['go', 'fmt', './...'], cwd=repo_path)
    
    if returncode == 0:
        print("✓")
        results['fmt_status'] = 'passed'
    else:
        print("✗")
        results['fmt_status'] = 'failed'
        results['failures'].append({
            'type': 'fmt',
            'message': 'Code not properly formatted'
        })
    
    # Run go vet
    print("  Running go vet...", end=" ", flush=True)
    stdout, stderr, returncode = run_command(['go', 'vet', './...'], cwd=repo_path)
    
    if returncode == 0:
        print("✓")
        results['vet_status'] = 'passed'
    else:
        print("✗")
        results['vet_status'] = 'failed'
        results['vet_output'] = stderr
        results['failures'].append({
            'type': 'vet',
            'message': stderr[:500]
        })
    
    # Overall status
    results['overall_status'] = 'passed' if len(results['failures']) == 0 else 'failed'
    
    print(f"[Stage 6] Validation complete - {results['overall_status']}")
    
    return results
