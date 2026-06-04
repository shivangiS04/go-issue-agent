#!/usr/bin/env python3
"""
Go Issue Agent - Main entry point.

Usage:
    python run.py --issue <github_issue_url> --repo <path_to_repo>

Example:
    python run.py --issue https://github.com/spf13/cobra/issues/1989 --repo ./cobra
"""
import argparse
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from agent.pipeline import run_pipeline


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="AI agent for solving GitHub issues in Go repositories"
    )
    parser.add_argument(
        "--issue",
        required=True,
        help="GitHub issue URL (e.g., https://github.com/spf13/cobra/issues/123)"
    )
    parser.add_argument(
        "--repo",
        required=True,
        help="Path to cloned repository (e.g., ./cobra)"
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    if not os.path.isdir(args.repo):
        print(f"Error: Repository path does not exist: {args.repo}")
        sys.exit(1)
    
    if not os.path.isdir(os.path.join(args.repo, ".git")):
        print(f"Error: Not a git repository: {args.repo}")
        sys.exit(1)
    
    if not config.GROQ_API_KEY:
        print("Error: GROQ_API_KEY environment variable not set")
        print("Please set it with: export GROQ_API_KEY=your_key_here")
        sys.exit(1)
    
    print("="*60)
    print("GO ISSUE AGENT")
    print("="*60)
    print(f"Issue: {args.issue}")
    print(f"Repository: {args.repo}")
    print("="*60)
    print()
    
    try:
        # Run pipeline
        result = run_pipeline(args.issue, args.repo, config)
        
        print("\n✓ Success! Check the output/ directory for results.")
        sys.exit(0)
        
    except KeyboardInterrupt:
        print("\n\n✗ Interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
