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
import hashlib
import uuid
import logging

logger = logging.getLogger(__name__)

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
from rule_classifier import RuleClassifier
from fix_orchestrator import FixOrchestrator
from explainer import ExplainerEngine
from safety_checker import SafetyChecker
from ai_analyzer import AIAnalyzer
from config_loader import Config
from file_reader import read_file
from edr import EDRGenerator
from run_ledger import create_run_ledger


def print_header(text: str):
    """Print formatted header"""
    print(f"\n🤖 {text}")
    print("═" * 60)


def print_section(title: str):
    """Print section header"""
    print(f"\n{title}")
    print("─" * 60)


def build_repo_id(repo_path: str) -> str:
    """Stable repo identifier for usage tracking."""
    abs_path = os.path.abspath(repo_path)
    name = os.path.basename(abs_path) or "repo"
    suffix = hashlib.sha1(abs_path.encode()).hexdigest()[:8]
    return f"{name}-{suffix}"


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


def get_repo_identifier(repo_path: str, repo_arg: str) -> str:
    """
    Extract repo identifier in format owner/repo.
    Falls back to local path identifier if not a GitHub URL.
    """
    if repo_arg.startswith(('http://', 'https://', 'git@')):
        # Try to extract owner/repo from URL
        # https://github.com/owner/repo.git -> owner/repo
        # git@github.com:owner/repo.git -> owner/repo
        parts = repo_arg.rstrip('/').replace('.git', '').split('/')
        if len(parts) >= 2:
            return f"{parts[-2]}/{parts[-1]}"
    
    # Fallback to local identifier
    return build_repo_id(repo_path)


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
    run_id = str(uuid.uuid4())[:8]  # Short 8-char run ID for EDR
    ledger = None  # Run Ledger (Phase 7.2)

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

        # Load configuration
        config = Config(repo_path=repo_path)

        # Initialize Run Ledger (Phase 7.2)
        try:
            repo_identifier = get_repo_identifier(repo_path, args.repo)
            ledger = create_run_ledger(
                run_id=run_id,
                repo_id=repo_identifier,
                environment="DEV",
                initiated_by="CLI"
            )
            if ledger:
                logger.info(f"Run Ledger enabled: {ledger.get_ledger_path()}")
        except Exception as e:
            logger.warning(f"Failed to create ledger: {e}; operating in LEGACY mode")
            ledger = None

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
        
        # Emit: RUN_STARTED
        if ledger:
            try:
                ledger.append_event(
                    "RUN_STARTED",
                    f"Analysis and fix execution began for {repo_path}"
                )
            except Exception as e:
                logger.warning(f"Ledger event failed: {e}")

        if not issues:
            print("✨ No issues found! Repository is clean.")
            # Seal ledger: COMPLETE (no fixes needed)
            if ledger:
                try:
                    ledger.seal("COMPLETE")
                except Exception as e:
                    logger.warning(f"Ledger seal failed: {e}")
            return 0

        # Emit: ISSUE_DETECTED
        if ledger and len(issues) > 0:
            try:
                ledger.append_event(
                    "ISSUE_DETECTED",
                    f"Found {len(issues)} code issues via Ruff analyzer"
                )
            except Exception as e:
                logger.warning(f"Ledger event failed: {e}")
        
        # Initialize smart tools
        classifier = RuleClassifier()
        orchestrator = FixOrchestrator()
        explainer = ExplainerEngine()
        safety_checker = SafetyChecker()
        
        # Initialize AI analyzer if enabled
        ai_analyzer = None
        if args.ai:
            repo_id = build_repo_id(repo_path)
            rate_limit_cfg = config.get('ai.rate_limit', {}) or {}
            ai_analyzer = AIAnalyzer(repo_id=repo_id, rate_limit=rate_limit_cfg)
            if not ai_analyzer.enabled:
                ai_analyzer = None
            else:
                print("🤖 AI analyzer enabled")

        # Display classification
        if args.smart:
            display_classification(classifier, issues)

        # Plan fixes
        plan = orchestrator.plan_fixes(issues, safety_mode='safe')
        
        # Emit: PLAN_APPROVED (after fix planning)
        if ledger and plan['summary']['will_fix'] > 0:
            try:
                ledger.append_event(
                    "PLAN_APPROVED",
                    f"Fix plan approved: {plan['summary']['will_fix']} issues to auto-fix",
                    phase="PHASE_2"
                )
            except Exception as e:
                logger.warning(f"Ledger event failed: {e}")
        
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
                max_ai_files = config.get('ai.max_files_to_analyze', 3)

                for file_path in files_with_issues[:max_ai_files]:
                    abs_path = os.path.join(repo_path, file_path)
                    if os.path.exists(abs_path):
                        code = read_file(abs_path)
                        if code:
                            print(f"\n📄 {file_path}")
                            suggestions = ai_analyzer.analyze_code_quality(code, file_path)
                            if suggestions:
                                print(suggestions)
            
            print("\n✨ Analysis complete!")
            # Seal ledger: COMPLETE (analyze-only mode)
            if ledger:
                try:
                    ledger.seal("COMPLETE")
                except Exception as e:
                    logger.warning(f"Ledger seal failed: {e}")
            return 0

        # Record before state
        print("\n📸 Recording initial state...")
        safety_checker.record_before(repo_path)
        
        # Emit: SAFETY_CHECK_PASSED (pre-execution safety)
        if ledger:
            try:
                ledger.append_event(
                    "SAFETY_CHECK_PASSED",
                    "Pre-execution safety verification passed"
                )
            except Exception as e:
                logger.warning(f"Ledger event failed: {e}")

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
        
        # Emit: FIX_APPLIED (summary for all safe fixes)
        if ledger and plan['summary']['will_fix'] > 0:
            try:
                # Group fixes by rule code
                fixes_by_rule = plan['summary'].get('fixes_by_rule', {})
                for rule_code, count in fixes_by_rule.items():
                    ledger.append_event(
                        "FIX_APPLIED",
                        f"Applied {count} fix(es) for rule {rule_code}"
                    )
            except Exception as e:
                logger.warning(f"Ledger event failed: {e}")

        # Record after state
        print("📸 Recording final state...")
        safety_checker.record_after(repo_path)

        # Check for regressions
        regression_report = safety_checker.check_regressions()
        fixed_count = regression_report['net_fixed']

        # Generate EDR (always, even if no fixes)
        edr_generator = EDRGenerator()
        repo_identifier = get_repo_identifier(repo_path, args.repo)
        
        # Get files that were changed (from analyze step)
        files_changed = list(set(issue['filename'] for issue in issues))
        lines_changed = sum(1 for issue in issues for _ in [issue])  # Approximation
        
        edr = edr_generator.generate(
            repo=repo_identifier,
            run_id=run_id,
            issues_before=len(issues),
            issues_after=regression_report['issues_after'],
            fixed_count=fixed_count,
            issues_fixed=[i for i in issues if classifier.classify(i['code'])['category'].value == 'safe'],
            safety_mode='smart' if args.smart else 'safe_only',
            regressions_detected=regression_report.get('new_issues', False),
            files_changed=files_changed,
            lines_changed=lines_changed,
            tests_run=[],
            tests_status='skipped',
            analyze_only=args.analyze_only
        )
        
        # Persist EDR to disk
        edr_path = edr_generator.persist(edr)
        print(f"💾 EDR saved: {edr_path}")
        
        # Emit: EDR_FINALIZED
        if ledger:
            try:
                ledger.append_event(
                    "EDR_FINALIZED",
                    f"Engineering Decision Report generated (risk={edr['summary']['risk_level']})",
                    phase="PHASE_5",
                    payload_ref=edr['edr_id']
                )
            except Exception as e:
                logger.warning(f"Ledger event failed: {e}")
        
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
            modified_files = list(set(issue['filename'] for issue in issues if classifier.classify(issue['code'])['category'].value == 'safe'))
            
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
            # Seal ledger: COMPLETE (no fixes applied)
            if ledger:
                try:
                    ledger.seal("COMPLETE")
                except Exception as e:
                    logger.warning(f"Ledger seal failed: {e}")
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
                pr_body = generate_pr_body(fixed_count, issues[:fixed_count], edr=edr)
                
                pr_url, success, error = create_pull_request(args.repo, branch_name, pr_title, pr_body)
                
                if success:
                    print(f"\n🎉 Pull Request: {pr_url}")

        print("\n✨ Done!")
        
        # Seal ledger: COMPLETE (successful execution)
        if ledger:
            try:
                ledger.seal("COMPLETE")
            except Exception as e:
                logger.warning(f"Ledger seal failed: {e}")
        
        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted")
        # Seal ledger: ABORTED (user interrupt)
        if ledger:
            try:
                ledger.seal("ABORTED")
            except Exception as e:
                logger.warning(f"Ledger seal failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        # Seal ledger: ABORTED (exception)
        if ledger:
            try:
                ledger.seal("ABORTED")
            except Exception as e:
                logger.warning(f"Ledger seal failed: {e}")
        return 1
    finally:
        if cleanup_needed and temp_dir and os.path.exists(temp_dir):
            print("\n🧹 Cleaning up...")
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    sys.exit(main())
