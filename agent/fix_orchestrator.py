"""
Fix Orchestrator - Plan and execute fixes in optimal order
"""
import subprocess
import sys
from typing import Dict, List
from rule_classifier import RuleClassifier

class FixOrchestrator:
    """Orchestrate the application of fixes in safe order"""
    
    def __init__(self):
        self.classifier = RuleClassifier()
    
    def plan_fixes(self, issues: List[Dict], safety_mode: str = 'safe') -> Dict:
        """
        Plan which fixes to apply based on safety mode
        
        safety_mode:
        - 'safe': Only auto-fix 100% safe rules
        - 'smart': Auto-fix safe, ask for risky
        - 'all': Auto-fix everything (dangerous)
        """
        grouped = self.classifier.group_by_category(issues)
        
        plan = {
            'to_fix': [],      # Rules to apply
            'to_review': [],   # Rules needing human review
            'to_suggest': [],  # Informational only
            'summary': {}
        }
        
        # Always include safe rules
        plan['to_fix'].extend(grouped['safe'])
        
        # Based on safety mode
        if safety_mode == 'safe':
            plan['to_review'].extend(grouped['risky'])
            plan['to_suggest'].extend(grouped['suggest'])
        elif safety_mode == 'smart':
            plan['to_review'].extend(grouped['risky'])
            plan['to_suggest'].extend(grouped['suggest'])
        elif safety_mode == 'all':
            plan['to_fix'].extend(grouped['risky'])
            plan['to_suggest'].extend(grouped['suggest'])
        
        # Group fixes by rule code for statistics
        fix_counts = {}
        for issue in plan['to_fix']:
            code = issue['code']
            fix_counts[code] = fix_counts.get(code, 0) + 1
        
        plan['summary'] = {
            'total_issues': len(issues),
            'will_fix': len(plan['to_fix']),
            'needs_review': len(plan['to_review']),
            'suggestions': len(plan['to_suggest']),
            'fixes_by_rule': fix_counts
        }
        
        return plan
    
    def execute_plan(self, repo_path: str, safety_mode: str = 'safe') -> bool:
        """Execute Ruff --fix on the repository"""
        cmd = [sys.executable, "-m", "ruff", "check", ".", "--fix", "--exit-zero"]
        
        # Could filter by specific rules if needed
        # cmd.extend(["--select", ",".join(selected_rules)])
        
        result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True)
        return result.returncode == 0
    
    def format_plan(self, plan: Dict) -> str:
        """Format the plan as readable output"""
        summary = plan['summary']
        
        text = f"""
📋 FIX PLAN
{'═' * 50}
Total issues found: {summary['total_issues']}
Will auto-fix: {summary['will_fix']}
Needs review: {summary['needs_review']}
Suggestions: {summary['suggestions']}

Fixes by rule:
"""
        for code, count in summary['fixes_by_rule'].items():
            text += f"  • {code}: {count} issue{'s' if count > 1 else ''}\n"
        
        return text
