"""Security Agent - Vulnerability and security issue detection."""

import re
import time
from pathlib import Path
from typing import Dict, List, Any
import ast

from .base_agent import BaseAgent, AgentResult, AgentType, AgentIssue, IssueSeverity


class SecurityAgent(BaseAgent):
    """Specialized agent for security vulnerability detection."""
    
    # Common security patterns
    SECURITY_PATTERNS = {
        'hardcoded_password': {
            'pattern': r'(password|passwd|pwd)\s*=\s*["\'][^"\']+["\']',
            'severity': IssueSeverity.CRITICAL,
            'title': 'Hardcoded Password Detected',
            'description': 'Password found in source code',
            'recommendation': 'Use environment variables or secure credential management',
        },
        'hardcoded_api_key': {
            'pattern': r'(api[_-]?key|apikey|access[_-]?key)\s*=\s*["\'][a-zA-Z0-9]{20,}["\']',
            'severity': IssueSeverity.CRITICAL,
            'title': 'Hardcoded API Key Detected',
            'description': 'API key found in source code',
            'recommendation': 'Store API keys in environment variables or secure vault',
        },
        'sql_injection': {
            'pattern': r'(execute|cursor\.execute|query)\s*\(\s*["\'].*%s.*["\'].*\%',
            'severity': IssueSeverity.HIGH,
            'title': 'Potential SQL Injection',
            'description': 'String formatting used in SQL query',
            'recommendation': 'Use parameterized queries or ORM',
        },
        'eval_usage': {
            'pattern': r'\beval\s*\(',
            'severity': IssueSeverity.HIGH,
            'title': 'Dangerous eval() Usage',
            'description': 'eval() can execute arbitrary code',
            'recommendation': 'Avoid eval(), use safe alternatives like ast.literal_eval()',
        },
        'exec_usage': {
            'pattern': r'\bexec\s*\(',
            'severity': IssueSeverity.HIGH,
            'title': 'Dangerous exec() Usage',
            'description': 'exec() can execute arbitrary code',
            'recommendation': 'Avoid exec(), refactor to use functions or safe alternatives',
        },
        'debug_mode': {
            'pattern': r'(DEBUG\s*=\s*True|app\.debug\s*=\s*True)',
            'severity': IssueSeverity.MEDIUM,
            'title': 'Debug Mode Enabled',
            'description': 'Debug mode should not be enabled in production',
            'recommendation': 'Set DEBUG=False in production environments',
        },
        'weak_crypto': {
            'pattern': r'\b(md5|sha1|DES|RC4)\s*\(',
            'severity': IssueSeverity.HIGH,
            'title': 'Weak Cryptographic Algorithm',
            'description': 'Using deprecated or weak cryptographic algorithm',
            'recommendation': 'Use SHA-256, SHA-3, or bcrypt for hashing',
        },
        'missing_csrf_protection': {
            'pattern': r'@app\.route.*methods.*POST.*(?!.*csrf)',
            'severity': IssueSeverity.HIGH,
            'title': 'Missing CSRF Protection',
            'description': 'POST endpoint without CSRF protection',
            'recommendation': 'Add CSRF token validation for state-changing operations',
        },
        'insecure_random': {
            'pattern': r'\brandom\.(random|randint|choice)\s*\(',
            'severity': IssueSeverity.MEDIUM,
            'title': 'Insecure Random Number Generation',
            'description': 'Using predictable random for security-sensitive operations',
            'recommendation': 'Use secrets module for cryptographic randomness',
        },
        'path_traversal': {
            'pattern': r'(open|read).*\+.*user.*\+',
            'severity': IssueSeverity.HIGH,
            'title': 'Potential Path Traversal',
            'description': 'User input in file path without validation',
            'recommendation': 'Validate and sanitize file paths, use safe path joining',
        },
        'hardcoded_secret': {
            'pattern': r'(secret[_-]?key|jwt[_-]?secret|encryption[_-]?key)\s*=\s*["\'][^"\']+["\']',
            'severity': IssueSeverity.CRITICAL,
            'title': 'Hardcoded Secret Key',
            'description': 'Secret key or encryption key hardcoded in source',
            'recommendation': 'Use environment variables or secure secrets management',
        },
        'unsafe_deserialization': {
            'pattern': r'(pickle\.loads|yaml\.load)\s*\(',
            'severity': IssueSeverity.HIGH,
            'title': 'Unsafe Deserialization',
            'description': 'Deserializing untrusted data can lead to code execution',
            'recommendation': 'Use safe_load() for YAML, avoid pickle for untrusted data',
        },
        'shell_injection': {
            'pattern': r'(os\.system|subprocess\.(call|run|Popen))\s*\(.*\+',
            'severity': IssueSeverity.HIGH,
            'title': 'Potential Shell Injection',
            'description': 'Command constructed with string concatenation',
            'recommendation': 'Use parameterized commands with list arguments',
        },
        'open_redirect': {
            'pattern': r'redirect\s*\(\s*request\.',
            'severity': IssueSeverity.MEDIUM,
            'title': 'Potential Open Redirect',
            'description': 'Redirecting to user-supplied URL',
            'recommendation': 'Validate redirect URLs against whitelist',
        },
    }
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize SecurityAgent."""
        super().__init__(AgentType.SECURITY, config)
        self.patterns_enabled = config.get('patterns', list(self.SECURITY_PATTERNS.keys()))
    
    async def analyze(self, repo_path: str, files: List[str]) -> AgentResult:
        """Analyze repository for security issues.
        
        Args:
            repo_path: Path to repository root
            files: List of files to analyze
            
        Returns:
            AgentResult with security findings
        """
        start_time = time.time()
        issues = []
        
        # Filter to supported files
        python_files = self.filter_files(files, ['.py'])
        js_files = self.filter_files(files, ['.js', '.ts', '.jsx', '.tsx'])
        
        self.log_analysis_start(repo_path, len(python_files) + len(js_files))
        
        # Analyze Python files
        for file_path in python_files:
            full_path = Path(repo_path) / file_path
            issues.extend(self._analyze_python_file(str(full_path), file_path))
        
        # Analyze JavaScript files
        for file_path in js_files:
            full_path = Path(repo_path) / file_path
            issues.extend(self._analyze_js_file(str(full_path), file_path))
        
        execution_time = (time.time() - start_time) * 1000
        self.log_analysis_complete(len(issues), execution_time)
        
        # Calculate metrics
        metrics = self._calculate_metrics(issues, python_files + js_files)
        summary = self._generate_summary(issues, metrics)
        
        return AgentResult(
            agent_type=self.agent_type,
            issues=issues,
            metrics=metrics,
            summary=summary,
            execution_time_ms=execution_time
        )
    
    def _analyze_python_file(self, full_path: str, relative_path: str) -> List[AgentIssue]:
        """Analyze a Python file for security issues."""
        issues = []
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Pattern-based analysis
            for pattern_name in self.patterns_enabled:
                if pattern_name not in self.SECURITY_PATTERNS:
                    continue
                
                pattern_info = self.SECURITY_PATTERNS[pattern_name]
                pattern = pattern_info['pattern']
                
                for line_num, line in enumerate(lines, 1):
                    if re.search(pattern, line, re.IGNORECASE):
                        issue = AgentIssue(
                            file_path=relative_path,
                            line_number=line_num,
                            issue_type=f"SEC_{pattern_name.upper()}",
                            severity=pattern_info['severity'],
                            title=pattern_info['title'],
                            description=pattern_info['description'],
                            recommendation=pattern_info['recommendation'],
                            code_snippet=line.strip(),
                            tags=['security', pattern_name],
                            confidence=0.8,
                        )
                        issues.append(issue)
            
            # AST-based analysis for more complex patterns
            try:
                tree = ast.parse(content)
                issues.extend(self._analyze_python_ast(tree, relative_path))
            except SyntaxError:
                pass  # Skip files with syntax errors
                
        except Exception as e:
            self.logger.warning(f"Error analyzing {relative_path}: {e}")
        
        return issues
    
    def _analyze_python_ast(self, tree: ast.AST, file_path: str) -> List[AgentIssue]:
        """Analyze Python AST for security issues."""
        issues = []
        
        for node in ast.walk(tree):
            # Check for assert statements (should not be used for security)
            if isinstance(node, ast.Assert):
                issues.append(AgentIssue(
                    file_path=file_path,
                    line_number=node.lineno,
                    issue_type="SEC_ASSERT_SECURITY",
                    severity=IssueSeverity.MEDIUM,
                    title="Assert Used for Security Check",
                    description="Assert statements can be optimized away with -O flag",
                    recommendation="Use explicit if statements for security checks",
                    tags=['security', 'assert'],
                    confidence=0.9,
                ))
            
            # Check for requests without timeout
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if (node.func.attr in ['get', 'post', 'put', 'delete', 'patch'] and
                        isinstance(node.func.value, ast.Name) and 
                        node.func.value.id == 'requests'):
                        # Check if timeout is provided
                        has_timeout = any(
                            kw.arg == 'timeout' for kw in node.keywords
                        )
                        if not has_timeout:
                            issues.append(AgentIssue(
                                file_path=file_path,
                                line_number=node.lineno,
                                issue_type="SEC_NO_TIMEOUT",
                                severity=IssueSeverity.LOW,
                                title="HTTP Request Without Timeout",
                                description="Requests without timeout can hang indefinitely",
                                recommendation="Add timeout parameter: requests.get(url, timeout=30)",
                                tags=['security', 'timeout'],
                                confidence=0.95,
                            ))
        
        return issues
    
    def _analyze_js_file(self, full_path: str, relative_path: str) -> List[AgentIssue]:
        """Analyze a JavaScript file for security issues."""
        issues = []
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                # Check for eval usage
                if re.search(r'\beval\s*\(', line):
                    issues.append(AgentIssue(
                        file_path=relative_path,
                        line_number=line_num,
                        issue_type="SEC_JS_EVAL",
                        severity=IssueSeverity.HIGH,
                        title="Dangerous eval() in JavaScript",
                        description="eval() can execute arbitrary code",
                        recommendation="Avoid eval(), use JSON.parse() or safe alternatives",
                        code_snippet=line.strip(),
                        tags=['security', 'javascript', 'eval'],
                        confidence=0.9,
                    ))
                
                # Check for innerHTML usage
                if re.search(r'\.innerHTML\s*=', line):
                    issues.append(AgentIssue(
                        file_path=relative_path,
                        line_number=line_num,
                        issue_type="SEC_XSS_INNERHTML",
                        severity=IssueSeverity.MEDIUM,
                        title="Potential XSS via innerHTML",
                        description="Setting innerHTML with user data can lead to XSS",
                        recommendation="Use textContent or sanitize user input with DOMPurify",
                        code_snippet=line.strip(),
                        tags=['security', 'xss', 'javascript'],
                        confidence=0.7,
                    ))
                
                # Check for console.log in production
                if re.search(r'console\.(log|debug|info)', line):
                    issues.append(AgentIssue(
                        file_path=relative_path,
                        line_number=line_num,
                        issue_type="SEC_CONSOLE_LOG",
                        severity=IssueSeverity.LOW,
                        title="Console Logging in Production",
                        description="Console logs may expose sensitive data",
                        recommendation="Remove console.log or use proper logging library",
                        code_snippet=line.strip(),
                        tags=['security', 'logging'],
                        confidence=0.6,
                    ))
                    
        except Exception as e:
            self.logger.warning(f"Error analyzing {relative_path}: {e}")
        
        return issues
    
    def _calculate_metrics(self, issues: List[AgentIssue], files: List[str]) -> Dict[str, Any]:
        """Calculate security metrics."""
        severity_counts = {}
        for issue in issues:
            severity = issue.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        issue_types = {}
        for issue in issues:
            issue_types[issue.issue_type] = issue_types.get(issue.issue_type, 0) + 1
        
        # Calculate security score (0-100, higher is better)
        critical_count = severity_counts.get('critical', 0)
        high_count = severity_counts.get('high', 0)
        medium_count = severity_counts.get('medium', 0)
        
        security_score = max(0, 100 - (critical_count * 20) - (high_count * 10) - (medium_count * 5))
        
        return {
            'files_analyzed': len(files),
            'total_issues': len(issues),
            'severity_breakdown': severity_counts,
            'issue_types': issue_types,
            'security_score': security_score,
            'critical_issues': critical_count,
            'high_priority_issues': high_count,
        }
    
    def _generate_summary(self, issues: List[AgentIssue], metrics: Dict[str, Any]) -> str:
        """Generate human-readable summary."""
        total = len(issues)
        critical = metrics['critical_issues']
        high = metrics['high_priority_issues']
        score = metrics['security_score']
        
        if total == 0:
            return "✅ No security issues detected. Security score: 100/100"
        
        summary_parts = [
            f"Found {total} security issue{'s' if total != 1 else ''}."
        ]
        
        if critical > 0:
            summary_parts.append(f"⚠️ {critical} CRITICAL issue{'s' if critical != 1 else ''} require immediate attention!")
        
        if high > 0:
            summary_parts.append(f"🔴 {high} HIGH priority issue{'s' if high != 1 else ''} should be fixed soon.")
        
        summary_parts.append(f"Security score: {score}/100")
        
        return " ".join(summary_parts)
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get agent capabilities."""
        return {
            'name': 'Security Agent',
            'description': 'Detects security vulnerabilities and potential threats',
            'supported_languages': ['Python', 'JavaScript', 'TypeScript'],
            'checks': [
                'Hardcoded credentials detection',
                'SQL injection vulnerabilities',
                'Command injection risks',
                'Weak cryptography usage',
                'Unsafe deserialization',
                'XSS vulnerabilities',
                'Debug mode detection',
                'Missing request timeouts',
            ],
            'severity_levels': ['critical', 'high', 'medium', 'low', 'info'],
        }
