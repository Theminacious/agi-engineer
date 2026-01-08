"""
Explainer Engine - Generate human-readable explanations for fixes
"""
from typing import Dict, Optional

class ExplainerEngine:
    """Generate detailed explanations for each code fix"""
    
    EXPLANATIONS = {
        'F401': {
            'title': '🗑️ Removed unused import',
            'description': 'Module imported but never used in code',
            'why_safe': 'Code that is not referenced cannot affect behavior',
            'impact': 'Reduces clutter, improves performance slightly',
            'safety_score': 100
        },
        'F541': {
            'title': '📝 Fixed useless f-string',
            'description': 'f-string without placeholders is wasteful',
            'why_safe': 'Replacing f"text" with "text" has identical behavior',
            'impact': 'Removes unnecessary runtime overhead',
            'safety_score': 100
        },
        'W291': {
            'title': '✂️ Removed trailing whitespace',
            'description': 'Extra spaces at end of line',
            'why_safe': 'Whitespace at end has no effect on code',
            'impact': 'Improves code consistency and cleanliness',
            'safety_score': 100
        },
        'W292': {
            'title': '➕ Added newline at EOF',
            'description': 'Files should end with newline',
            'why_safe': 'POSIX standard, no effect on code behavior',
            'impact': 'Prevents warnings from many tools',
            'safety_score': 100
        },
        'E711': {
            'title': '🔍 Fixed None comparison',
            'description': 'Should use `is None` not `== None`',
            'why_safe': '`is` checks identity; `== None` can be overridden',
            'impact': 'More Pythonic, follows PEP 8',
            'safety_score': 100
        },
        'F841': {
            'title': '⚠️ Unused variable assignment',
            'description': 'Variable assigned but never used',
            'why_safe': 'Might be intentional (e.g., placeholder)',
            'impact': 'Could indicate incomplete logic or debugging leftover',
            'safety_score': 50
        },
        'E501': {
            'title': '📏 Line too long',
            'description': 'Line exceeds character limit',
            'why_safe': 'Requires manual refactoring decisions',
            'impact': 'Affects readability on narrow screens',
            'safety_score': 30
        }
    }
    
    def explain(self, rule_code: str) -> Dict:
        """Get explanation for a rule"""
        return self.EXPLANATIONS.get(rule_code, {
            'title': f'Rule {rule_code}',
            'description': 'Code quality issue',
            'why_safe': 'Unknown',
            'impact': 'See Ruff docs',
            'safety_score': 0
        })
    
    def format_explanation(self, rule_code: str, count: int = 1) -> str:
        """Format explanation as readable text"""
        exp = self.explain(rule_code)
        
        plural = 's' if count > 1 else ''
        text = f"""
{exp['title']}
{'─' * 50}
Issues found: {count}{plural}
Description: {exp['description']}
Why safe: {exp['why_safe']}
Impact: {exp['impact']}
Safety score: {exp['safety_score']}/100
"""
        return text
    
    def get_all_explanations(self) -> Dict[str, Dict]:
        """Get all rule explanations"""
        return self.EXPLANATIONS
