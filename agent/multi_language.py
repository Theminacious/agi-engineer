"""
Multi-language support for AGI Engineer
Extends analysis to JavaScript/TypeScript via ESLint
"""
import subprocess
import json
import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class MultiLanguageAnalyzer:
    """Analyze multiple language repositories"""
    
    PYTHON_EXTENSIONS = {'.py'}
    JS_TS_EXTENSIONS = {'.js', '.ts', '.jsx', '.tsx', '.mjs'}
    
    def __init__(self):
        self.eslint_available = self._check_eslint()
    
    def _check_eslint(self) -> bool:
        """Check if ESLint is available"""
        try:
            result = subprocess.run(['npm', 'list', '-g', 'eslint'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False
    
    def detect_language(self, repo_path: str) -> List[str]:
        """Detect languages in repository"""
        languages = []
        
        # Check for Python files
        for root, dirs, files in os.walk(repo_path):
            # Skip hidden dirs and common excludes
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', 'venv', '__pycache__']]
            
            for file in files:
                _, ext = os.path.splitext(file)
                
                if ext in self.PYTHON_EXTENSIONS and 'python' not in languages:
                    languages.append('python')
                elif ext in self.JS_TS_EXTENSIONS:
                    if ext in {'.ts', '.tsx'} and 'typescript' not in languages:
                        languages.append('typescript')
                    elif ext in {'.js', '.jsx', '.mjs'} and 'javascript' not in languages:
                        languages.append('javascript')
        
        return languages if languages else ['python']
    
    def analyze_js_ts(self, repo_path: str, config_rules: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Analyze JavaScript/TypeScript with ESLint"""
        if not self.eslint_available:
            logger.warning("ESLint not available, skipping JS/TS analysis")
            return []
        
        issues = []
        
        try:
            # Build ESLint command
            cmd = ['npx', 'eslint', repo_path, '--format', 'json', '--ext', '.js,.ts,.jsx,.tsx']
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.stdout:
                eslint_results = json.loads(result.stdout)
                
                for file_result in eslint_results:
                    for message in file_result.get('messages', []):
                        issues.append({
                            'code': message.get('ruleId', 'UNKNOWN'),
                            'message': message.get('message', ''),
                            'filename': file_result['filePath'],
                            'line': message.get('line', 0),
                            'column': message.get('column', 0),
                            'severity': 'error' if message.get('severity') == 2 else 'warning',
                            'language': 'javascript' if file_result['filePath'].endswith(('.js', '.jsx', '.mjs')) else 'typescript'
                        })
        except subprocess.TimeoutExpired:
            logger.error("ESLint analysis timed out")
        except json.JSONDecodeError:
            logger.error("Failed to parse ESLint output")
        except Exception as e:
            logger.error(f"ESLint analysis failed: {e}")
        
        return issues
    
    def merge_issues(self, python_issues: List[Dict], js_ts_issues: List[Dict]) -> List[Dict]:
        """Merge issues from multiple languages"""
        # Add language field to Python issues if not present
        for issue in python_issues:
            if 'language' not in issue:
                issue['language'] = 'python'
        
        # Sort by file and line
        all_issues = python_issues + js_ts_issues
        all_issues.sort(key=lambda x: (x.get('filename', ''), x.get('line', 0)))
        
        return all_issues
    
    def get_summary_by_language(self, issues: List[Dict]) -> Dict[str, int]:
        """Get issue count by language"""
        summary = {}
        
        for issue in issues:
            lang = issue.get('language', 'unknown')
            summary[lang] = summary.get(lang, 0) + 1
        
        return summary
