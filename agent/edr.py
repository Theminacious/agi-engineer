"""
Engineering Decision Report (EDR) - Generate and persist fix reports
"""
import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional


class EDRGenerator:
    """Generate Engineering Decision Reports for fix runs"""
    
    def __init__(self):
        self.edr_dir = os.path.expanduser("~/.agi-engineer/edr")
        self._ensure_edr_dir()
    
    def _ensure_edr_dir(self):
        """Create EDR directory if it doesn't exist"""
        os.makedirs(self.edr_dir, exist_ok=True)
    
    def generate(
        self,
        repo: str,
        run_id: str,
        issues_before: int,
        issues_after: int,
        fixed_count: int,
        issues_fixed: List[Dict],
        safety_mode: str,
        regressions_detected: bool,
        files_changed: List[str],
        lines_changed: int,
        tests_run: List[str],
        tests_status: str = "skipped",
        analyze_only: bool = False
    ) -> Dict:
        """
        Generate an EDR based on fix execution results
        
        Args:
            repo: Repository identifier (owner/repo)
            run_id: Unique run identifier
            issues_before: Number of issues before fixes
            issues_after: Number of issues after fixes
            fixed_count: Number of issues fixed
            issues_fixed: List of issue dicts with 'code' and 'message'
            safety_mode: 'safe_only' or 'smart'
            regressions_detected: Whether new issues were introduced
            files_changed: List of modified files
            lines_changed: Number of lines changed
            tests_run: List of test runners used (e.g. ['pytest', 'jest'])
            tests_status: 'passed', 'failed', or 'skipped'
            analyze_only: Whether this was analyze-only mode
        
        Returns:
            EDR dict
        """
        # Calculate confidence score based on success ratio
        confidence = self._calculate_confidence(
            fixed_count=fixed_count,
            issues_before=issues_before,
            regressions_detected=regressions_detected,
            analyze_only=analyze_only
        )
        
        # Determine risk level
        risk_level = self._determine_risk_level(
            fixed_count=fixed_count,
            regressions_detected=regressions_detected,
            issues_after=issues_after
        )
        
        # Generate title
        title = self._generate_title(fixed_count, analyze_only, regressions_detected)
        
        # Extract rules fixed
        rules_fixed = self._extract_rules(issues_fixed)
        
        # Build EDR
        edr = {
            "edr_id": str(uuid.uuid4()),
            "repo": repo,
            "run_id": run_id,
            "created_at": datetime.utcnow().isoformat() + "Z",
            
            "summary": {
                "title": title,
                "risk_level": risk_level,
                "confidence": round(confidence, 2)
            },
            
            "issues": {
                "total_found": issues_before,
                "fixed": fixed_count,
                "needs_review": 0,
                "suggestions": 0,
                "rules_fixed": sorted(rules_fixed)
            },
            
            "changes": {
                "files_changed": sorted(files_changed),
                "lines_changed": lines_changed
            },
            
            "safety": {
                "mode": safety_mode,
                "regressions_detected": regressions_detected,
                "before_issues": issues_before,
                "after_issues": issues_after
            },
            
            "tests": {
                "tests_run": tests_run,
                "status": tests_status
            },
            
            "rollback": {
                "strategy": "git revert",
                "instruction": "git revert <commit_sha>"
            }
        }
        
        return edr
    
    def _calculate_confidence(
        self,
        fixed_count: int,
        issues_before: int,
        regressions_detected: bool,
        analyze_only: bool
    ) -> float:
        """Calculate confidence score (0.0 to 1.0)"""
        if analyze_only:
            return 0.0  # Analyze-only mode doesn't execute fixes
        
        if issues_before == 0:
            return 1.0  # No issues to fix = perfect
        
        # Base confidence: ratio of issues fixed
        fix_ratio = fixed_count / issues_before
        confidence = fix_ratio * 100
        
        # Penalty for regressions
        if regressions_detected:
            confidence -= 15
        
        # Cap between 0 and 100, convert to percentage
        confidence = max(0, min(100, confidence)) / 100.0
        
        return confidence
    
    def _determine_risk_level(
        self,
        fixed_count: int,
        regressions_detected: bool,
        issues_after: int
    ) -> str:
        """Determine risk level: low, medium, or high"""
        if regressions_detected:
            return "high"
        
        if issues_after > 50:
            return "medium"
        
        if fixed_count == 0:
            return "low"
        
        if fixed_count < 10:
            return "low"
        
        if fixed_count < 50:
            return "medium"
        
        return "high"
    
    def _generate_title(
        self,
        fixed_count: int,
        analyze_only: bool,
        regressions_detected: bool
    ) -> str:
        """Generate human-readable EDR title"""
        if analyze_only:
            return "Code analysis completed (preview mode)"
        
        if fixed_count == 0:
            return "No issues were auto-fixed"
        
        if regressions_detected:
            return f"Fixed {fixed_count} issues (regressions detected)"
        
        if fixed_count == 1:
            return "Fixed 1 code issue"
        
        return f"Fixed {fixed_count} code issues"
    
    def _extract_rules(self, issues_fixed: List[Dict]) -> List[str]:
        """Extract unique rule codes from fixed issues"""
        rules = set()
        for issue in issues_fixed:
            if isinstance(issue, dict) and 'code' in issue:
                rules.add(issue['code'])
        return list(rules)
    
    def persist(self, edr: Dict) -> str:
        """
        Save EDR to disk
        
        Args:
            edr: EDR dict from generate()
        
        Returns:
            Path to saved EDR file
        """
        run_id = edr['run_id']
        file_path = os.path.join(self.edr_dir, f"{run_id}.json")
        
        with open(file_path, 'w') as f:
            json.dump(edr, f, indent=2)
        
        return file_path
    
    def format_for_pr(self, edr: Dict) -> str:
        """
        Format EDR as markdown for PR appendix
        
        Args:
            edr: EDR dict from generate()
        
        Returns:
            Markdown string for PR body
        """
        summary = edr['summary']
        issues = edr['issues']
        safety = edr['safety']
        
        # Build markdown
        md = "---\n\n"
        md += "## 🤖 Engineering Decision Report\n\n"
        md += f"**Risk:** {summary['risk_level'].capitalize()}  \n"
        md += f"**Confidence:** {int(summary['confidence'] * 100)}%\n\n"
        
        # Fixed issues section
        if issues['rules_fixed']:
            md += "### Fixed Issues\n"
            for rule_code in issues['rules_fixed']:
                md += f"- `{rule_code}`\n"
            md += "\n"
        
        # Safety section
        md += "### Safety\n"
        md += f"- **Mode:** {safety['mode']}\n"
        md += f"- **Regressions:** {'Detected ⚠️' if safety['regressions_detected'] else 'None ✓'}\n"
        md += f"- **Before:** {safety['before_issues']} issues\n"
        md += f"- **After:** {safety['after_issues']} issues\n\n"
        
        # Rollback section
        md += "### Rollback\n"
        md += f"```\n{edr['rollback']['instruction']}\n```\n"
        
        return md
