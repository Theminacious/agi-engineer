"""
Configuration drift analyzer.

Detects environment-specific configuration issues, inconsistent settings, and drift between environments.
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


class ConfigurationDriftAnalyzer(BaseAnalyzer):
    """Detect configuration drift and inconsistencies."""
    
    @property
    def bug_class(self) -> BugClass:
        return BugClass.CONFIGURATION_DRIFT
    
    def analyze(
        self,
        repository_path: str,
        repository_url: str,
        branch: str = "main",
    ) -> List[IntelligenceProposal]:
        """Analyze repository for configuration drift."""
        self.start_timing()
        self._reset_metrics()
        
        proposals = []
        
        # 1. Detect missing environment variables
        missing_env = self._detect_missing_env_vars(repository_path)
        proposals.extend(missing_env)
        
        # 2. Detect hardcoded configuration
        hardcoded = self._detect_hardcoded_config(repository_path)
        proposals.extend(hardcoded)
        
        # 3. Detect environment-specific code
        env_specific = self._detect_environment_specific_code(repository_path)
        proposals.extend(env_specific)
        
        # Finalize all proposals
        finalized = []
        for proposal in proposals:
            proposal.repository_url = repository_url
            proposal.branch = branch
            finalized.append(self._finalize_proposal(proposal))
        
        return finalized
    
    def _detect_missing_env_vars(
        self,
        repository_path: str,
    ) -> List[IntelligenceProposal]:
        """Detect missing environment variable documentation."""
        proposals = []
        
        issues = self._scan_for_env_usage(repository_path)
        
        if issues:
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.CONFIGURATION_DRIFT
            proposal.severity = Severity.MEDIUM
            
            issue_count = len(issues)
            
            proposal.problem_statement = (
                f"Found {issue_count} environment variables used in code "
                f"but not documented. Missing documentation causes deployment errors."
            )
            
            proposal.risk_explanation = (
                f"Without documentation of required environment variables, developers "
                f"deploying to new environments forget to set them. Application crashes "
                f"with 'KeyError' or uses wrong defaults."
            )
            
            proposal.root_cause_hypothesis = (
                f"Environment variables added over time without maintaining documentation. "
                f"No single source of truth for required configuration."
            )
            
            # Add affected files
            for file_path, line_num in issues:
                proposal.affected_files.append(
                    AffectedFile(path=file_path, severity=Severity.MEDIUM)
                )
            
            # Strategies
            proposal.suggested_strategies = [
                FixStrategy(
                    name="Create .env.example file",
                    description=(
                        f"Create .env.example documenting all required environment variables "
                        f"with descriptions and example values."
                    ),
                    effort_estimate=EffortEstimate.SMALL,
                    prerequisite_actions=[
                        "Audit all os.environ and os.getenv calls",
                        "Create .env.example",
                        "Document each variable: name, description, default",
                        "Include examples for each environment (dev, staging, prod)",
                        "Add to README",
                    ],
                    assumptions=[
                        "All variables are documented",
                        "Example values are safe to share",
                    ],
                    risks=[
                        "May accidentally include sensitive values",
                        "Documentation gets out of sync",
                    ],
                ),
                FixStrategy(
                    name="Use configuration schema validation",
                    description=(
                        f"Create schema (pydantic, marshmallow) that validates required "
                        f"environment variables at startup."
                    ),
                    effort_estimate=EffortEstimate.MEDIUM,
                    prerequisite_actions=[
                        "Choose schema library (pydantic recommended)",
                        "Define config schema with all vars",
                        "Add validation at application startup",
                        "Provide helpful error messages",
                        "Test missing var error handling",
                    ],
                    assumptions=[
                        "Schema library is compatible",
                        "Validation can run at startup",
                    ],
                    risks=[
                        "Schema library adds dependency",
                        "Validation may be verbose",
                    ],
                ),
            ]
            
            proposal.confidence_level = 80
            proposal.confidence_explanation = (
                f"Detection finds environment variable usage. Confidence high that "
                f"these should be documented."
            )
            proposal.requires_human_decision = True
            proposal.decision_required_for = (
                "Choose documentation strategy; schema validation vs .env.example."
            )
            
            self.patterns_matched.append(f"missing_env_vars:{issue_count}")
            proposals.append(proposal)
        
        return proposals
    
    def _detect_hardcoded_config(
        self,
        repository_path: str,
    ) -> List[IntelligenceProposal]:
        """Detect hardcoded configuration values."""
        proposals = []
        
        issues = self._scan_for_hardcoded_values(repository_path)
        
        if issues:
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.CONFIGURATION_DRIFT
            proposal.severity = Severity.MEDIUM
            
            issue_count = len(issues)
            
            proposal.problem_statement = (
                f"Found {issue_count} hardcoded configuration values (URLs, timeouts, limits). "
                f"Should be in environment variables for environment-specific values."
            )
            
            proposal.risk_explanation = (
                f"Hardcoded values prevent adapting to different environments. Changing "
                f"configuration requires code change and redeploy. Limits, URLs, timeouts "
                f"may need different values for dev/staging/prod."
            )
            
            proposal.root_cause_hypothesis = (
                f"Configuration extracted during development but never externalized. "
                f"Developers prioritize getting things working over making configurable."
            )
            
            # Add affected files
            for file_path, line_num in issues:
                proposal.affected_files.append(
                    AffectedFile(path=file_path, severity=Severity.MEDIUM)
                )
            
            # Strategies
            proposal.suggested_strategies = [
                FixStrategy(
                    name="Externalize configuration to environment variables",
                    description=(
                        f"Replace {issue_count} hardcoded values with environment variables. "
                        f"Provide sensible defaults."
                    ),
                    effort_estimate=EffortEstimate.SMALL,
                    prerequisite_actions=[
                        "Identify all hardcoded values",
                        "Determine which should be configurable",
                        "Add environment variable reads",
                        "Provide defaults",
                        "Document in .env.example",
                        "Test with different values",
                    ],
                    assumptions=[
                        "Values differ between environments",
                        "Defaults are sensible",
                    ],
                    risks=[
                        "May introduce new bugs if defaults wrong",
                        "Requires deployment changes",
                    ],
                ),
                FixStrategy(
                    name="Create configuration management module",
                    description=(
                        f"Create centralized config module that reads and validates "
                        f"all configuration in one place."
                    ),
                    effort_estimate=EffortEstimate.MEDIUM,
                    prerequisite_actions=[
                        "Create config.py module",
                        "Define all configurable values",
                        "Add validation and defaults",
                        "Import from single location",
                        "Remove scattered config reads",
                    ],
                    assumptions=[
                        "Config module can be imported early",
                        "Single location is maintainable",
                    ],
                    risks=[
                        "Config module becomes large",
                        "Changes require module reload",
                    ],
                ),
            ]
            
            proposal.confidence_level = 85
            proposal.confidence_explanation = (
                f"Detection finds hardcoded numeric and string values. Confidence high "
                f"that these are configuration."
            )
            proposal.requires_human_decision = True
            proposal.decision_required_for = (
                "Determine which values should be configurable for each environment."
            )
            
            self.patterns_matched.append(f"hardcoded_config:{issue_count}")
            proposals.append(proposal)
        
        return proposals
    
    def _detect_environment_specific_code(
        self,
        repository_path: str,
    ) -> List[IntelligenceProposal]:
        """Detect environment-specific code branches."""
        proposals = []
        
        issues = self._scan_for_env_specific_code(repository_path)
        
        if issues:
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.CONFIGURATION_DRIFT
            proposal.severity = Severity.MEDIUM
            
            issue_count = len(issues)
            
            proposal.problem_statement = (
                f"Found {issue_count} environment-specific code branches (if ENVIRONMENT == 'prod'). "
                f"Different code paths for different environments cause drift and bugs."
            )
            
            proposal.risk_explanation = (
                f"Code that behaves differently in different environments is untestable "
                f"(can't test prod code in dev). Bugs only appear in specific environments. "
                f"Complex conditional logic is hard to maintain."
            )
            
            proposal.root_cause_hypothesis = (
                f"Quick hacks to work around environment differences. Should use "
                f"configuration instead of conditional code."
            )
            
            # Add affected files
            for file_path, line_num in issues:
                proposal.affected_files.append(
                    AffectedFile(path=file_path, severity=Severity.MEDIUM)
                )
            
            # Strategies
            proposal.suggested_strategies = [
                FixStrategy(
                    name="Replace conditionals with configuration",
                    description=(
                        f"Remove 'if ENVIRONMENT' conditionals. Replace with configuration "
                        f"values that differ per environment."
                    ),
                    effort_estimate=EffortEstimate.SMALL,
                    prerequisite_actions=[
                        "Identify all environment conditionals",
                        "Convert to configuration values",
                        "Create environment-specific config files",
                        "Test with different configs",
                    ],
                    assumptions=[
                        "Code differences are configuration-driven",
                        "No fundamental behavior changes needed",
                    ],
                    risks=[
                        "May expose differences that need to stay hidden",
                        "Requires config file management",
                    ],
                ),
                FixStrategy(
                    name="Use dependency injection for environment adapters",
                    description=(
                        f"Inject environment-specific adapters/implementations. "
                        f"Use same code path with different implementations."
                    ),
                    effort_estimate=EffortEstimate.MEDIUM,
                    prerequisite_actions=[
                        "Identify abstraction boundaries",
                        "Create environment-specific implementations",
                        "Use DI to inject correct implementation",
                        "Test with different implementations",
                    ],
                    assumptions=[
                        "Differences can be abstracted as implementations",
                        "DI framework available",
                    ],
                    risks=[
                        "May add complexity",
                        "Requires refactoring",
                    ],
                ),
            ]
            
            proposal.confidence_level = 90
            proposal.confidence_explanation = (
                f"Environment-specific conditionals are easily detectable. Confidence high "
                f"that these should be removed."
            )
            proposal.requires_human_decision = True
            proposal.decision_required_for = (
                "Strategy for removing environment-specific code; refactor vs configuration."
            )
            
            self.patterns_matched.append(f"env_specific_code:{issue_count}")
            proposals.append(proposal)
        
        return proposals
    
    def _scan_for_env_usage(self, repository_path: str) -> List[Tuple]:
        """Scan for environment variable usage."""
        issues = []
        
        for root, dirs, files in os.walk(repository_path):
            dirs[:] = [d for d in dirs if d not in {
                '__pycache__', '.git', 'venv', 'build', 'dist'
            }]
            
            for file in files:
                if not file.endswith('.py'):
                    continue
                
                file_path = os.path.join(root, file)
                self.files_scanned += 1
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            self.lines_analyzed += 1
                            
                            if re.search(r'os\.environ|os\.getenv', line):
                                issues.append((file_path, line_num))
                except Exception:
                    pass
        
        return issues
    
    def _scan_for_hardcoded_values(self, repository_path: str) -> List[Tuple]:
        """Scan for hardcoded configuration values."""
        issues = []
        
        # Patterns that suggest configuration
        config_patterns = [
            r'timeout\s*=\s*\d+',
            r'max_\w+\s*=\s*\d+',
            r'url\s*=\s*["\']http',
            r'host\s*=\s*["\']localhost["\']',
            r'port\s*=\s*\d+',
        ]
        
        for root, dirs, files in os.walk(repository_path):
            dirs[:] = [d for d in dirs if d not in {
                '__pycache__', '.git', 'venv', 'build', 'dist'
            }]
            
            for file in files:
                if not file.endswith('.py'):
                    continue
                
                file_path = os.path.join(root, file)
                self.files_scanned += 1
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            self.lines_analyzed += 1
                            
                            for pattern in config_patterns:
                                if re.search(pattern, line, re.IGNORECASE):
                                    issues.append((file_path, line_num))
                                    break
                except Exception:
                    pass
        
        return issues
    
    def _scan_for_env_specific_code(self, repository_path: str) -> List[Tuple]:
        """Scan for environment-specific code."""
        issues = []
        
        for root, dirs, files in os.walk(repository_path):
            dirs[:] = [d for d in dirs if d not in {
                '__pycache__', '.git', 'venv', 'build', 'dist'
            }]
            
            for file in files:
                if not file.endswith('.py'):
                    continue
                
                file_path = os.path.join(root, file)
                self.files_scanned += 1
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            self.lines_analyzed += 1
                            
                            if re.search(
                                r"if\s+.*ENVIRONMENT|if\s+.*ENV|if\s+.*=='prod'|if\s+.*=='dev'",
                                line,
                                re.IGNORECASE
                            ):
                                issues.append((file_path, line_num))
                except Exception:
                    pass
        
        return issues
