"""
Rule Classifier - Categorize Ruff rules by safety level
Groups rules into: SAFE (auto-fix), RISKY (needs review), SUGGEST (info-only)
"""
from enum import Enum
from typing import Dict, List

class RuleCategory(Enum):
    SAFE = "safe"           # 100% safe to auto-fix
    RISKY = "risky"         # Risky, needs human review
    SUGGEST = "suggest"     # Informational only

class RuleClassifier:
    """Classify rules by safety and provide metadata"""
    
    # 100% SAFE TO AUTO-FIX
    SAFE_RULES = {
        'F401': {'name': 'Unused import', 'safety': 100},
        'F541': {'name': 'Useless f-string', 'safety': 100},
        'W291': {'name': 'Trailing whitespace', 'safety': 100},
        'W292': {'name': 'No newline at EOF', 'safety': 100},
        'W293': {'name': 'Blank line with whitespace', 'safety': 100},
        'E701': {'name': 'Multiple statements on one line', 'safety': 100},
        'E702': {'name': 'Unnecessary semicolon', 'safety': 100},
        'E711': {'name': 'Comparison to None', 'safety': 100},
        'E712': {'name': 'Comparison to True/False', 'safety': 100},
    }
    
    # RISKY - NEEDS HUMAN REVIEW
    RISKY_RULES = {
        'F841': {'name': 'Unused variable', 'safety': 50},
        'E501': {'name': 'Line too long', 'safety': 30},
        'C901': {'name': 'Function too complex', 'safety': 20},
        'F401': {'name': 'Unused import with side effects', 'safety': 40},
    }
    
    # SUGGESTIONS ONLY
    SUGGEST_RULES = {
        'D100': {'name': 'Missing module docstring', 'safety': 0},
        'D101': {'name': 'Missing class docstring', 'safety': 0},
        'D102': {'name': 'Missing function docstring', 'safety': 0},
        'D103': {'name': 'Missing method docstring', 'safety': 0},
    }
    
    def __init__(self):
        self.all_rules = {**self.SAFE_RULES, **self.RISKY_RULES, **self.SUGGEST_RULES}
    
    def classify(self, rule_code: str) -> Dict:
        """Get classification for a rule"""
        if rule_code in self.SAFE_RULES:
            return {
                'code': rule_code,
                'category': RuleCategory.SAFE,
                'safety_score': 100,
                **self.SAFE_RULES[rule_code]
            }
        elif rule_code in self.RISKY_RULES:
            return {
                'code': rule_code,
                'category': RuleCategory.RISKY,
                'safety_score': self.RISKY_RULES[rule_code]['safety'],
                **self.RISKY_RULES[rule_code]
            }
        else:
            return {
                'code': rule_code,
                'category': RuleCategory.SUGGEST,
                'safety_score': 0,
                'name': f'Rule {rule_code}'
            }
    
    def group_by_category(self, issues: List[Dict]) -> Dict[str, List[Dict]]:
        """Group issues by safety category"""
        grouped = {'safe': [], 'risky': [], 'suggest': []}
        
        for issue in issues:
            classified = self.classify(issue['code'])
            category = classified['category'].value
            grouped[category].append({**issue, **classified})
        
        return grouped
    
    def get_summary(self, issues: List[Dict]) -> Dict:
        """Get summary statistics"""
        grouped = self.group_by_category(issues)
        
        return {
            'total': len(issues),
            'safe': len(grouped['safe']),
            'risky': len(grouped['risky']),
            'suggest': len(grouped['suggest']),
            'auto_fixable': len(grouped['safe']),
            'grouped': grouped
        }
