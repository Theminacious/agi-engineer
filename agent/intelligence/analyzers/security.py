"""
Security misconfigurations analyzer.

Detects hardcoded secrets, insecure patterns, and security anti-patterns.
"""

from typing import List, Tuple
import os
import re
from agent.intelligence.analyzer import BaseAnalyzer
from agent.intelligence.proposal import (
    IntelligenceProposal,
    BugClass,
    Severity,
    AffectedFile,
    FixStrategy,
    EffortEstimate,
)


class SecurityAnalyzer(BaseAnalyzer):
    """Detect security misconfigurations and vulnerabilities."""
    
    @property
    def bug_class(self) -> BugClass:
        return BugClass.SECURITY_MISCONFIGURATIONS
    
    # Patterns for common secrets
    SECRET_PATTERNS = {
        'api_key': r'["\']?api[_-]?key["\']?\s*[=:]\s*["\']([^"\']+)["\']',
        'password': r'["\']?password["\']?\s*[=:]\s*["\']([^"\']+)["\']',
        'token': r'["\']?token["\']?\s*[=:]\s*["\']([^"\']+)["\']',
        'secret': r'["\']?secret["\']?\s*[=:]\s*["\']([^"\']+)["\']',
        'aws_key': r'AKIA[0-9A-Z]{16}',
        'private_key': r'-----BEGIN PRIVATE KEY-----',
    }
    
    # Insecure patterns
    INSECURE_PATTERNS = {
        'sql_concat': r'query\s*[+=]\s*["\'].*\'\s*\+',  # SQL concatenation
        'disabled_auth': r'auth\s*[=:]\s*(False|false|None)',
        'permissive_cors': r'CORS.*\*|allow_origin\s*[=:]\s*["\']\*["\']',
        'debug_mode': r'DEBUG\s*[=:]\s*(True|true)',
    }
    
    def analyze(
        self,
        repository_path: str,
        repository_url: str,
        branch: str = "main",
    ) -> List[IntelligenceProposal]:
        """Analyze repository for security issues."""
        self.start_timing()
        self._reset_metrics()
        
        proposals = []
        
        # 1. Detect hardcoded secrets
        secrets = self._detect_hardcoded_secrets(repository_path)
        proposals.extend(secrets)
        
        # 2. Detect insecure patterns
        insecure = self._detect_insecure_patterns(repository_path)
        proposals.extend(insecure)
        
        # Finalize all proposals
        finalized = []
        for proposal in proposals:
            proposal.repository_url = repository_url
            proposal.branch = branch
            finalized.append(self._finalize_proposal(proposal))
        
        return finalized
    
    def _detect_hardcoded_secrets(
        self,
        repository_path: str,
    ) -> List[IntelligenceProposal]:
        """Detect hardcoded secrets and credentials."""
        proposals = []
        
        found_secrets = self._scan_for_secrets(repository_path)
        
        if found_secrets:
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.SECURITY_MISCONFIGURATIONS
            proposal.severity = Severity.CRITICAL
            
            secret_count = len(found_secrets)
            secret_types = set(s[1] for s in found_secrets)
            
            proposal.problem_statement = (
                f"Found {secret_count} hardcoded secrets ({', '.join(secret_types)}) "
                f"in source code. Credentials must be stored in environment variables."
            )
            
            proposal.risk_explanation = (
                f"Hardcoded secrets in source code are exposed in: version control history, "
                f"build logs, deployed containers, crash reports. Anyone with repo access "
                f"can steal credentials. High probability of breach."
            )
            
            proposal.root_cause_hypothesis = (
                f"Credentials were added directly to code for convenience during development "
                f"and were never migrated to environment variables."
            )
            
            # Add affected files
            for file_path, secret_type, _ in found_secrets:
                proposal.affected_files.append(
                    AffectedFile(path=file_path, severity=Severity.CRITICAL)
                )
            
            # Strategies
            proposal.suggested_strategies = [
                FixStrategy(
                    name="Migrate to environment variables",
                    description=(
                        f"Move {secret_count} secrets to environment variables. "
                        f"Update code to read from environment. Rotate all exposed credentials."
                    ),
                    effort_estimate=EffortEstimate.MEDIUM,
                    prerequisite_actions=[
                        "Audit all secret types used",
                        "Set up environment variable management",
                        "Update code to read from environment",
                        "Rotate all exposed credentials immediately",
                        "Remove secrets from version control history",
                    ],
                    assumptions=[
                        "Environment variables are protected in deployment",
                        "All copies of repo are cleaned",
                    ],
                    risks=[
                        "Must rotate credentials (expensive)",
                        "Environment setup may be complex",
                        "Requires deployment infrastructure changes",
                    ],
                ),
                FixStrategy(
                    name="Use secrets management service",
                    description=(
                        f"Integrate with AWS Secrets Manager, HashiCorp Vault, or similar. "
                        f"Retrieve secrets at runtime, never store in code."
                    ),
                    effort_estimate=EffortEstimate.LARGE,
                    prerequisite_actions=[
                        "Choose secrets management service",
                        "Set up service credentials",
                        "Implement client library integration",
                        "Update all secret access code",
                        "Test in dev, staging, production",
                        "Rotate old credentials",
                    ],
                    assumptions=[
                        "Service is available in all environments",
                        "Network access is reliable",
                    ],
                    risks=[
                        "Additional service dependency",
                        "Network latency for secret retrieval",
                        "Service outage blocks deployment",
                    ],
                ),
            ]
            
            proposal.confidence_level = 100
            proposal.confidence_explanation = (
                "Hardcoded secrets are detectable via pattern matching with 100% confidence "
                "when found. However, some obfuscated secrets may be missed."
            )
            proposal.requires_human_decision = True
            proposal.decision_required_for = (
                "Which secrets management approach to use; immediate credential rotation is CRITICAL."
            )
            
            self.patterns_matched.append(f"hardcoded_secrets:{secret_count}")
            proposals.append(proposal)
        
        return proposals
    
    def _detect_insecure_patterns(
        self,
        repository_path: str,
    ) -> List[IntelligenceProposal]:
        """Detect insecure coding patterns."""
        proposals = []
        
        issues = self._scan_for_insecure_patterns(repository_path)
        
        for pattern_name, affected_files in issues.items():
            if not affected_files:
                continue
            
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.SECURITY_MISCONFIGURATIONS
            
            # Map pattern to severity
            severity_map = {
                'sql_concat': Severity.CRITICAL,
                'disabled_auth': Severity.HIGH,
                'permissive_cors': Severity.HIGH,
                'debug_mode': Severity.MEDIUM,
            }
            proposal.severity = severity_map.get(pattern_name, Severity.MEDIUM)
            
            # Problem statement
            problem_map = {
                'sql_concat': (
                    f"SQL injection vulnerability: queries built via string concatenation "
                    f"in {len(affected_files)} locations. Use parameterized queries."
                ),
                'disabled_auth': (
                    f"Authentication disabled in {len(affected_files)} locations. "
                    f"May be debug code left in production."
                ),
                'permissive_cors': (
                    f"CORS allows all origins (*) in {len(affected_files)} locations. "
                    f"Should restrict to trusted origins."
                ),
                'debug_mode': (
                    f"Debug mode enabled in {len(affected_files)} locations. "
                    f"Should be disabled in production."
                ),
            }
            proposal.problem_statement = problem_map.get(pattern_name, f"Insecure pattern: {pattern_name}")
            
            # Risk explanation
            risk_map = {
                'sql_concat': "SQL injection allows attackers to read/modify/delete data.",
                'disabled_auth': "Unauthenticated access to protected resources.",
                'permissive_cors': "Allows any website to access resources on behalf of users.",
                'debug_mode': "Exposes internal state, error details, and stack traces to attackers.",
            }
            proposal.risk_explanation = risk_map.get(pattern_name, "Security risk from insecure pattern.")
            
            # Root cause
            cause_map = {
                'sql_concat': "Dynamic query building without parameterization.",
                'disabled_auth': "Debug code not removed before deployment.",
                'permissive_cors': "Overly permissive configuration for development convenience.",
                'debug_mode': "Development settings not changed for production.",
            }
            proposal.root_cause_hypothesis = cause_map.get(pattern_name, "Insecure design choice.")
            
            # Affected files
            for file_path in affected_files[:5]:  # Limit to first 5
                proposal.affected_files.append(
                    AffectedFile(path=file_path, severity=proposal.severity)
                )
            
            if len(affected_files) > 5:
                proposal.affected_files.append(
                    AffectedFile(
                        path=f"... and {len(affected_files) - 5} more files",
                        severity=proposal.severity
                    )
                )
            
            # Generic strategies
            proposal.suggested_strategies = [
                FixStrategy(
                    name="Apply security fix",
                    description=f"Fix the {pattern_name} issue in all {len(affected_files)} locations.",
                    effort_estimate=EffortEstimate.MEDIUM,
                    prerequisite_actions=[
                        f"Audit all {pattern_name} occurrences",
                        "Apply security fix pattern",
                        "Test fixes thoroughly",
                        "Deploy to production",
                    ],
                    assumptions=[
                        "Fix pattern is known for this issue",
                        "Fixes do not break functionality",
                    ],
                    risks=[
                        "May introduce subtle bugs if not careful",
                        "Testing must be thorough",
                    ],
                ),
                FixStrategy(
                    name="Security code review",
                    description=(
                        f"Conduct security-focused code review of {pattern_name} "
                        f"to understand root cause and design comprehensive fix."
                    ),
                    effort_estimate=EffortEstimate.SMALL,
                    prerequisite_actions=[
                        "Engage security specialist",
                        "Review code with security lens",
                        "Design fix strategy",
                        "Plan rollout",
                    ],
                    assumptions=[
                        "Security expertise available",
                    ],
                    risks=[
                        "Takes time to schedule review",
                        "May discover more issues",
                    ],
                ),
            ]
            
            proposal.confidence_level = 85
            proposal.confidence_explanation = (
                f"Pattern matching for {pattern_name} may have false positives; "
                "recommend security code review to confirm."
            )
            proposal.requires_human_decision = True
            proposal.decision_required_for = (
                "Security fix strategy; may require specialist involvement."
            )
            
            self.patterns_matched.append(f"insecure_{pattern_name}:{len(affected_files)}")
            proposals.append(proposal)
        
        return proposals
    
    def _scan_for_secrets(self, repository_path: str) -> List[Tuple]:
        """
        Scan for hardcoded secrets.
        Returns: [(file_path, secret_type, line_num), ...]
        """
        secrets = []
        
        for root, dirs, files in os.walk(repository_path):
            dirs[:] = [d for d in dirs if d not in {
                '__pycache__', '.git', 'venv', 'build', 'dist'
            }]
            
            for file in files:
                # Skip binary files
                if file.endswith(('.pyc', '.exe', '.dll', '.so')):
                    continue
                
                file_path = os.path.join(root, file)
                self.files_scanned += 1
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            self.lines_analyzed += 1
                            
                            for secret_type, pattern in self.SECRET_PATTERNS.items():
                                if re.search(pattern, line, re.IGNORECASE):
                                    secrets.append((file_path, secret_type, line_num))
                except Exception:
                    pass
        
        return secrets
    
    def _scan_for_insecure_patterns(self, repository_path: str) -> dict:
        """
        Scan for insecure patterns.
        Returns: {pattern_name: [file_paths], ...}
        """
        issues = {k: [] for k in self.INSECURE_PATTERNS.keys()}
        
        for root, dirs, files in os.walk(repository_path):
            dirs[:] = [d for d in dirs if d not in {
                '__pycache__', '.git', 'venv', 'build', 'dist'
            }]
            
            for file in files:
                if not file.endswith(('.py', '.js', '.ts', '.sql', '.yml', '.yaml')):
                    continue
                
                file_path = os.path.join(root, file)
                self.files_scanned += 1
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        self.lines_analyzed += len(content.split('\n'))
                        
                        for pattern_name, pattern in self.INSECURE_PATTERNS.items():
                            if re.search(pattern, content, re.IGNORECASE):
                                issues[pattern_name].append(file_path)
                except Exception:
                    pass
        
        return issues
