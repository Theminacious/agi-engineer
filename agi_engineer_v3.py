#!/usr/bin/env python3
"""
AGI Engineer v3 - Smart Code Fixing with Intelligence
Features: Rule classification, fix planning, safety checking, explanations
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

from analyze import run_ruff
from git_ops import (
    clone_repo, create_branch, commit_changes, 
    push_branch, create_pull_request,
    generate_branch_name, generate_pr_body, get_repo_info
)
from rule_classifier import RuleClassifier, RuleCategory
from fix_orchestrator import FixOrchestrator
from explainer import ExplainerEngine
from safety_checker import SafetyChecker
from ai_analyzer import AIAnalyzer
from file_reader import read_file


def print_header(text: str):
    """Print formatted header"""
    print(f"\n🤖 {text}")
    print("═" * 60)


def print_section(title: str):
    """Print section header"""
    print(f"\n{title}")
    print("─" * 60)


def display_classification(classifier: RuleClassifier, issues: list):
    """Display issues grouped by safety category"""
    summary = classifier.get_summary(issues)
    grouped = summary['grouped']
    
    print_section("📋 ISSUE CLASSIFICATION")
    
    # Safe rules
    if grouped['safe']:
        print(f"\n✅ SAFE TO AUTO-FIX ({len(grouped['safe'])} issues)")
        by_code = {}
        for issue in grouped['safe']:
            code = issue['code']
            by_code[code] = by_code.get(code, 0) + 1
        
        for code, count in sorted(by_code.items()):
            rule_info = classifier.classify(code)
            print(f"   • {code}: {rule_info['name']} ({count})")
    
    # Risky rules
    if grouped['risky']:
        print(f"\n⚠️  NEEDS REVIEW ({len(grouped['risky'])} issues)")
        by_code = {}
        for issue in grouped['risky']:
            code = issue['code']
            by_code[code] = by_code.get(code, 0) + 1
        
        for code, count in sorted(by_code.items()):
            rule_info = classifier.classify(code)
            print(f"   • {code}: {rule_info['name']} ({count})")
    
    # Suggestions
    if grouped['suggest']:
        print(f"\n💡 SUGGESTIONS ({len(grouped['suggest'])} items)")
        by_code = {}
        for issue in grouped['suggest']:
            code = issue['code']
            by_code[code] = by_code.get(code, 0) + 1
        
        for code, count in sorted(by_code.items()):
            rule_info = classifier.classify(code)
            print(f"   • {code}: {rule_info['name']} ({count})")


def display_explanations(explainer: ExplainerEngine, grouped_issues: dict, only_safe: bool = False):
    """Display detailed explanations for fixes"""
    print_section("📝 EXPLANATIONS")
    
    issues_to_explain = grouped_issues['safe'] if only_safe else grouped_issues['safe']
    
    seen = set()
    for issue in issues_to_explain:
        code = issue['code']
        if code not in seen:
            print(explainer.format_explanation(code, len([i for i in issues_to_explain if i['code'] == code])))
            seen.add(code)


def main():
    parser = argparse.ArgumentParser(
        description="AGI Engineer v3 - Smart code fixing with intelligence",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Smart mode - only fix safe issues
  python3 agi_engineer_v3.py /path/to/repo --smart
  
  # Clone, analyze, and create PR
  python3 agi_engineer_v3.py https://github.com/user/repo --smart --pr
  
  # Get detailed report without fixing
  python3 agi_engineer_v3.py /path/to/repo --analyze-only
        """
    )
    
    parser.add_argument('repo', help='Repository path or Git URL')
    parser.add_argument('--smart', action='store_true', help='Smart mode: classify and explain fixes')
    parser.add_argument('--ai', action='store_true', help='Enable AI-powered suggestions')
    parser.add_argument('--analyze-only', action='store_true', help='Only analyze, don\'t fix')
    parser.add_argument('--branch', help='Custom branch name')
    parser.add_argument('--pr', action='store_true', help='Create pull request')
    parser.add_argument('--push', action='store_true', help='Push to remote')
    parser.add_argument('--no-cleanup', action='store_true', help='Keep cloned repo')
    
    args = parser.parse_args()

    repo_path = args.repo
    cleanup_needed = False
    temp_dir = None

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

        # Show header
        print_header("AGI Engineer v3 - Smart Code Fixer")
        
        repo_info = get_repo_info(repo_path)
        if 'error' not in repo_info:
            print(f"📁 Repository: {repo_path}")
            print(f"🌿 Branch: {repo_info['current_branch']}")

        # Scan
        print("\n🔍 Scanning repository with Ruff...")
        issues = run_ruff(repo_path)
        print(f"📊 Found {len(issues)} issues\n")

        if not issues:
            print("✨ No issues found! Repository is clean.")
            return 0

        # Initialize smart tools
        classifier = RuleClassifier()
        orchestrator = FixOrchestrator()
        explainer = ExplainerEngine()
        safety_checker = SafetyChecker()
        
        # Initialize AI analyzer if enabled
        ai_analyzer = None
        if args.ai:
            ai_analyzer = AIAnalyzer()
            if not ai_analyzer.enabled:
                ai_analyzer = None
            else:
                print("🤖 AI analyzer enabled")

        # Display classification
        if args.smart:
            display_classification(classifier, issues)

        # Plan fixes
        plan = orchestrator.plan_fixes(issues, safety_mode='safe')
        
        if args.smart:
            print_section("🔧 FIX PLAN")
            summary = plan['summary']
            print(f"Will auto-fix: {summary['will_fix']} issues")
            print(f"Needs review: {summary['needs_review']} issues")
            print(f"Suggestions: {summary['suggestions']} issues")

        # Analyze only mode
        if args.analyze_only:
            if args.smart:
                grouped = classifier.group_by_category(issues)
                display_explanations(explainer, grouped)
            
            # AI analysis if enabled
            if ai_analyzer:
                print_section("🤖 AI ANALYSIS")
                # Get unique files with issues
                files_with_issues = list(set(issue['filename'] for issue in issues))
                
                for file_path in files_with_issues[:3]:  # Analyze up to 3 files
                    abs_path = os.path.join(repo_path, file_path)
                    if os.path.exists(abs_path):
                        code = read_file(abs_path)
                        if code:
                            print(f"\n📄 {file_path}")
                            suggestions = ai_analyzer.analyze_code_quality(code, file_path)
                            if suggestions:
                                print(suggestions)
            
            print("\n✨ Analysis complete!")
            return 0

        # Record before state
        print("\n📸 Recording initial state...")
        safety_checker.record_before(repo_path)

        # Create branch if needed
        branch_name = args.branch
        if args.push or args.pr:
            if not branch_name:
                branch_name = generate_branch_name()
            
            success, error = create_branch(repo_path, branch_name)
            if not success:
                print(f"❌ Failed to create branch: {error}")
                return 1

        # Apply fixes
        print("\n🔧 Applying fixes...")
        orchestrator.execute_plan(repo_path, safety_mode='safe')

        # Record after state
        print("📸 Recording final state...")
        safety_checker.record_after(repo_path)

        # Check for regressions
        regression_report = safety_checker.check_regressions()
        fixed_count = regression_report['net_fixed']

        # Display results
        print_header(f"✅ RESULTS - Fixed {fixed_count} issues")
        
        if args.smart:
            print(safety_checker.format_report())
            
            # Show what was fixed
            grouped = classifier.group_by_category(issues)
            if grouped['safe']:
                display_explanations(explainer, grouped, only_safe=True)
        
        # AI suggestions after fixes
        if ai_analyzer and fixed_count > 0:
            print_section("🤖 AI SUGGESTIONS")
            print("Analyzing remaining code quality issues...")
            
            # Get files that were modified
            modified_files = list(set(issue['filename'] for issue in issues if classifier.classify(issue['code'])[0] == 'SAFE'))
            
            for file_path in modified_files[:2]:  # Analyze up to 2 modified files
                abs_path = os.path.join(repo_path, file_path)
                if os.path.exists(abs_path):
                    code = read_file(abs_path)
                    if code:
                        print(f"\n📄 {file_path}")
                        suggestions = ai_analyzer.analyze_code_quality(code, file_path)
                        if suggestions:
                            print(suggestions)

        if fixed_count == 0:
            print("⏭  No issues were auto-fixed")
            return 0

        # Commit and push
        if args.push or args.pr:
            commit_msg = f"🤖 AGI Engineer v3: Fixed {fixed_count} code issues\n\nFixed automatically by AGI Engineer v3\nSafety check: PASSED ✓"
            success, error = commit_changes(repo_path, commit_msg)
            
            if not success:
                print(f"❌ Failed to commit: {error}")
                return 1

            success, error = push_branch(repo_path, branch_name)
            if not success:
                print(f"❌ Failed to push: {error}")
                return 1

            if args.pr:
                pr_title = f"🤖 AGI Engineer v3: Fixed {fixed_count} code issues"
                pr_body = generate_pr_body(fixed_count, issues[:fixed_count])
                
                pr_url, success, error = create_pull_request(args.repo, branch_name, pr_title, pr_body)
                
                if success:
                    print(f"\n🎉 Pull Request: {pr_url}")

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
            print(f"\n🧹 Cleaning up...")
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    sys.exit(main())
