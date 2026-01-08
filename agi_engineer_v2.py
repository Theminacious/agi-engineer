#!/usr/bin/env python3
"""
AGI Engineer v2 - Using Ruff's native --fix capability
Simpler and more reliable than manual patching
"""
import os
import sys
import argparse
import shutil
import tempfile
import subprocess
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AGENT_DIR = os.path.join(BASE_DIR, "agent")

if AGENT_DIR not in sys.path:
    sys.path.insert(0, AGENT_DIR)

from git_ops import (
    clone_repo, create_branch, commit_changes, 
    push_branch, create_pull_request,
    generate_branch_name, generate_pr_body, get_repo_info
)


def run_ruff_scan(repo_path, select_rules=None):
    """Scan repository and return issues."""
    cmd = [sys.executable, "-m", "ruff", "check", ".", "--output-format", "json", "--exit-zero"]
    
    if select_rules:
        cmd.extend(["--select", ",".join(select_rules)])
    
    result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True)
    
    if not result.stdout.strip():
        return []
    
    data = json.loads(result.stdout)
    issues = []
    
    for item in data:
        issues.append({
            "filename": os.path.abspath(os.path.join(repo_path, item["filename"])),
            "line": item["location"]["row"],
            "code": item["code"],
            "message": item["message"],
        })
    
    return issues


def run_ruff_fix(repo_path, select_rules=None):
    """Run Ruff --fix to automatically fix issues."""
    cmd = [sys.executable, "-m", "ruff", "check", ".", "--fix", "--exit-zero"]
    
    if select_rules:
        cmd.extend(["--select", ",".join(select_rules)])
    
    result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True)
    
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(
        description="AGI Engineer v2 - Automated code fixing bot (using Ruff --fix)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fix local repository
  python3 agi_engineer_v2.py /path/to/repo

  # Clone and fix a GitHub repo
  python3 agi_engineer_v2.py https://github.com/user/repo

  # Fix and create a PR
  python3 agi_engineer_v2.py https://github.com/user/repo --pr

  # Fix specific rules only
  python3 agi_engineer_v2.py /path/to/repo --rules F401,F541
        """
    )
    
    parser.add_argument('repo', help='Repository path or Git URL')
    parser.add_argument('--branch', help='Branch name (auto-generated if not provided)')
    parser.add_argument('--pr', action='store_true', help='Create a pull request')
    parser.add_argument('--push', action='store_true', help='Push changes to remote')
    parser.add_argument('--no-cleanup', action='store_true', help='Keep cloned repo')
    parser.add_argument('--rules', help='Comma-separated rules to fix (e.g., F401,F541)')
    
    args = parser.parse_args()

    repo_path = args.repo
    cleanup_needed = False
    temp_dir = None
    select_rules = args.rules.split(',') if args.rules else None

    try:
        # Clone if URL
        if args.repo.startswith(('http://', 'https://', 'git@')):
            temp_dir = tempfile.mkdtemp(prefix='agi_engineer_')
            repo_name = args.repo.rstrip('/').split('/')[-1].replace('.git', '')
            clone_path = os.path.join(temp_dir, repo_name)
            
            repo_path, success, error = clone_repo(args.repo, clone_path)
            if not success:
                print(f"❌ Failed to clone: {error}")
                return 1
            
            cleanup_needed = not args.no_cleanup
        else:
            if not os.path.exists(args.repo):
                print(f"❌ Path does not exist: {args.repo}")
                return 1
            repo_path = os.path.abspath(args.repo)

        # Show info
        print("🤖 AGI Engineer v2 - Automated Code Fixer")
        print("=" * 60)
        
        repo_info = get_repo_info(repo_path)
        if 'error' not in repo_info:
            print(f"📁 Repository: {repo_path}")
            print(f"🌿 Branch: {repo_info['current_branch']}")
            if 'remote_url' in repo_info:
                print(f"🔗 Remote: {repo_info['remote_url']}")
        print()

        # Scan before
        print("🔍 Scanning repository...")
        issues_before = run_ruff_scan(repo_path, select_rules)
        print(f"📊 Found {len(issues_before)} issues\n")

        if not issues_before:
            print("✨ No issues found! Repository is clean.")
            return 0

        # Create branch if needed
        branch_name = args.branch
        if (args.push or args.pr):
            if not branch_name:
                branch_name = generate_branch_name()
            
            success, error = create_branch(repo_path, branch_name)
            if not success:
                print(f"❌ Failed to create branch: {error}")
                return 1

        # Fix with Ruff
        print("🔧 Applying automatic fixes...")
        run_ruff_fix(repo_path, select_rules)

        # Scan after
        issues_after = run_ruff_scan(repo_path, select_rules)
        fixed_count = len(issues_before) - len(issues_after)

        print(f"✅ Fixed {fixed_count} issues")
        print(f"📊 Remaining: {len(issues_after)} issues\n")

        if fixed_count == 0:
            print("⏭  No issues could be auto-fixed")
            return 0

        # Commit and push
        if fixed_count > 0:
            if args.push or args.pr:
                commit_msg = f"🤖 Auto-fix: Resolved {fixed_count} code issues\n\nFixed by AGI Engineer Bot"
                success, error = commit_changes(repo_path, commit_msg)
                
                if not success:
                    print(f"❌ Failed to commit: {error}")
                    return 1

                if args.push or args.pr:
                    success, error = push_branch(repo_path, branch_name)
                    if not success:
                        print(f"❌ Failed to push: {error}")
                        return 1

                if args.pr:
                    pr_title = f"🤖 Auto-fix: Resolved {fixed_count} code issues"
                    pr_body = generate_pr_body(fixed_count, issues_before[:fixed_count])
                    
                    pr_url, success, error = create_pull_request(
                        args.repo, branch_name, pr_title, pr_body
                    )
                    
                    if success:
                        print(f"\n🎉 Pull Request: {pr_url}")
                    else:
                        print(f"\n⚠️  Could not create PR: {error}")

        print("\n✨ Done!")
        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        if cleanup_needed and temp_dir and os.path.exists(temp_dir):
            print("\n🧹 Cleaning up...")
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    sys.exit(main())
