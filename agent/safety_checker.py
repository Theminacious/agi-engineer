"""
Safety Checker - Verify fixes don't introduce regressions
"""
import subprocess
import sys
import json
from typing import Dict, List

class SafetyChecker:
    """Verify that fixes don't break anything"""
    
    def __init__(self):
        self.initial_scan = None
        self.final_scan = None
    
    def scan_repo(self, repo_path: str) -> List[Dict]:
        """Scan repository and return all issues"""
        cmd = [sys.executable, "-m", "ruff", "check", ".", "--output-format", "json", "--exit-zero"]
        
        result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True)
        
        if not result.stdout.strip():
            return []
        
        try:
            data = json.loads(result.stdout)
            return data
        except:
            return []
    
    def record_before(self, repo_path: str) -> Dict:
        """Record issues before fixes"""
        self.initial_scan = self.scan_repo(repo_path)
        return {
            'total': len(self.initial_scan),
            'by_code': self._group_by_code(self.initial_scan)
        }
    
    def record_after(self, repo_path: str) -> Dict:
        """Record issues after fixes"""
        self.final_scan = self.scan_repo(repo_path)
        return {
            'total': len(self.final_scan),
            'by_code': self._group_by_code(self.final_scan)
        }
    
    def check_regressions(self) -> Dict:
        """Check if new issues were introduced"""
        if self.initial_scan is None or self.final_scan is None:
            return {'status': 'incomplete', 'message': 'Before/after scans not recorded'}
        
        initial_codes = {i['code'] for i in self.initial_scan}
        final_codes = {i['code'] for i in self.final_scan}
        
        new_issues = final_codes - initial_codes
        fixed_issues = initial_codes - final_codes
        
        return {
            'status': 'ok' if not new_issues else 'warning',
            'new_issues': list(new_issues),
            'fixed_issues': list(fixed_issues),
            'issues_before': len(self.initial_scan),
            'issues_after': len(self.final_scan),
            'net_fixed': len(self.initial_scan) - len(self.final_scan)
        }
    
    def _group_by_code(self, issues: List[Dict]) -> Dict[str, int]:
        """Group issues by rule code"""
        grouped = {}
        for issue in issues:
            code = issue['code']
            grouped[code] = grouped.get(code, 0) + 1
        return grouped
    
    def format_report(self) -> str:
        """Format safety check report"""
        regression_check = self.check_regressions()
        
        text = f"""
🛡️ SAFETY CHECK REPORT
{'═' * 50}
Status: {regression_check['status'].upper()}
Issues before: {regression_check['issues_before']}
Issues after: {regression_check['issues_after']}
Net fixed: {regression_check['net_fixed']}

"""
        
        if regression_check['new_issues']:
            text += f"⚠️ NEW ISSUES INTRODUCED: {', '.join(regression_check['new_issues'])}\n"
        else:
            text += "✅ No new issues introduced\n"
        
        if regression_check['fixed_issues']:
            text += f"✓ Fixed rules: {', '.join(regression_check['fixed_issues'])}\n"
        
        return text
