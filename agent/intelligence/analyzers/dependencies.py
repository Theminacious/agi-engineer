"""
Dependency misuse analyzer.

Detects use of deprecated APIs, version conflicts, and improper dependency usage.
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


class DependencyMisuseAnalyzer(BaseAnalyzer):
    """Detect dependency misuse."""
    
    @property
    def bug_class(self) -> BugClass:
        return BugClass.DEPENDENCY_MISUSE
    
    # Known deprecated APIs
    DEPRECATED_PATTERNS = {
        'pkg_resources': (
            r'import\s+pkg_resources|from\s+pkg_resources',
            'importlib_metadata or importlib.resources'
        ),
        'imp_module': (
            r'import\s+imp\b|from\s+imp\s',
            'importlib'
        ),
        'asyncio_coroutine': (
            r'@asyncio\.coroutine|yield\s+from',
            'async/await'
        ),
        'nose_testing': (
            r'import\s+nose|from\s+nose',
            'pytest'
        ),
    }
    
    def analyze(
        self,
        repository_path: str,
        repository_url: str,
        branch: str = "main",
    ) -> List[IntelligenceProposal]:
        """Analyze repository for dependency issues."""
        self.start_timing()
        self._reset_metrics()
        
        proposals = []
        
        # 1. Detect deprecated API usage
        deprecated = self._detect_deprecated_apis(repository_path)
        proposals.extend(deprecated)
        
        # 2. Detect missing dependencies
        missing = self._detect_missing_dependencies(repository_path)
        proposals.extend(missing)
        
        # 3. Detect version conflicts
        conflicts = self._detect_version_conflicts(repository_path)
        proposals.extend(conflicts)
        
        # Finalize all proposals
        finalized = []
        for proposal in proposals:
            proposal.repository_url = repository_url
            proposal.branch = branch
            finalized.append(self._finalize_proposal(proposal))
        
        return finalized
    
    def _detect_deprecated_apis(
        self,
        repository_path: str,
    ) -> List[IntelligenceProposal]:
        """Detect use of deprecated APIs."""
        proposals = []
        
        issues = self._scan_for_deprecated_apis(repository_path)
        
        if issues:
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.DEPENDENCY_MISUSE
            proposal.severity = Severity.MEDIUM
            
            issue_count = len(issues)
            
            proposal.problem_statement = (
                f"Found {issue_count} uses of deprecated APIs. Deprecated code may be "
                f"removed in future versions, breaking the application."
            )
            
            proposal.risk_explanation = (
                f"Deprecated APIs are scheduled for removal. Continuing to use them "
                f"creates technical debt. Future dependency upgrades will break code."
            )
            
            proposal.root_cause_hypothesis = (
                f"Code uses old APIs and hasn't been updated as libraries evolved. "
                f"May be legacy code or outdated examples."
            )
            
            # Add affected files
            for file_path, line_num, deprecated_api in issues:
                proposal.affected_files.append(
                    AffectedFile(path=file_path, severity=Severity.MEDIUM)
                )
            
            # Strategies
            proposal.suggested_strategies = [
                FixStrategy(
                    name="Update to modern APIs",
                    description=(
                        f"Replace {issue_count} deprecated API calls with modern equivalents. "
                        f"Check library documentation for migration guides."
                    ),
                    effort_estimate=EffortEstimate.SMALL,
                    prerequisite_actions=[
                        "Identify all deprecated APIs",
                        "Check library migration guides",
                        "Replace with modern APIs",
                        "Test functionality",
                        "Update imports",
                    ],
                    assumptions=[
                        "Modern APIs are available",
                        "Migration is straightforward",
                    ],
                    risks=[
                        "Modern APIs may have different behavior",
                        "May require code refactoring",
                    ],
                ),
                FixStrategy(
                    name="Plan deprecation timeline",
                    description=(
                        f"Create timeline to update all deprecated APIs. Prioritize "
                        f"based on removal date and usage frequency."
                    ),
                    effort_estimate=EffortEstimate.SMALL,
                    prerequisite_actions=[
                        "Check removal dates for each deprecated API",
                        "Assess impact of removal",
                        "Create upgrade tasks",
                        "Allocate time in sprints",
                        "Monitor library releases",
                    ],
                    assumptions=[
                        "Removal dates are known",
                        "Team can allocate time",
                    ],
                    risks=[
                        "May get deprioritized",
                        "Removal dates may change",
                    ],
                ),
            ]
            
            proposal.confidence_level = 95
            proposal.confidence_explanation = (
                "Deprecated API patterns are well-known. Confidence very high that "
                "these are actual deprecated APIs."
            )
            proposal.requires_human_decision = True
            proposal.decision_required_for = (
                "Prioritize API updates; allocate engineering time."
            )
            
            self.patterns_matched.append(f"deprecated_apis:{issue_count}")
            proposals.append(proposal)
        
        return proposals
    
    def _detect_missing_dependencies(
        self,
        repository_path: str,
    ) -> List[IntelligenceProposal]:
        """Detect missing or unused dependencies."""
        proposals = []
        
        issues = self._scan_for_import_errors(repository_path)
        
        if issues:
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.DEPENDENCY_MISUSE
            proposal.severity = Severity.HIGH
            
            issue_count = len(issues)
            
            proposal.problem_statement = (
                f"Found {issue_count} imports that may fail due to missing dependencies. "
                f"Application will crash if dependencies aren't installed."
            )
            
            proposal.risk_explanation = (
                f"Missing dependencies cause ImportError at runtime. Application cannot "
                f"start. If dependency isn't in requirements.txt, new deployments fail."
            )
            
            proposal.root_cause_hypothesis = (
                f"Code added without updating requirements.txt. Or dependency was optional "
                f"and not installed in all environments."
            )
            
            # Add affected files
            for file_path, line_num in issues:
                proposal.affected_files.append(
                    AffectedFile(path=file_path, severity=Severity.HIGH)
                )
            
            # Strategies
            proposal.suggested_strategies = [
                FixStrategy(
                    name="Add missing dependencies to requirements.txt",
                    description=(
                        f"Install missing dependencies and add to requirements.txt. "
                        f"Specify exact versions."
                    ),
                    effort_estimate=EffortEstimate.SMALL,
                    prerequisite_actions=[
                        "Identify missing dependencies",
                        "Install via pip",
                        "Add to requirements.txt",
                        "Pin versions",
                        "Test imports",
                    ],
                    assumptions=[
                        "Dependencies are available on PyPI",
                        "No version conflicts",
                    ],
                    risks=[
                        "May introduce version conflicts",
                        "Pinned versions may be too restrictive",
                    ],
                ),
                FixStrategy(
                    name="Make dependency optional",
                    description=(
                        f"If dependency is optional, check if available before importing. "
                        f"Use try/except or add conditional import."
                    ),
                    effort_estimate=EffortEstimate.SMALL,
                    prerequisite_actions=[
                        "Assess if dependency is truly optional",
                        "Add try/except around import",
                        "Provide sensible error message",
                        "Document optional dependency",
                        "Test without dependency",
                    ],
                    assumptions=[
                        "Dependency is truly optional",
                        "Fallback behavior is acceptable",
                    ],
                    risks=[
                        "May mask real import errors",
                        "Code path without dependency untested",
                    ],
                ),
            ]
            
            proposal.confidence_level = 80
            proposal.confidence_explanation = (
                "Import patterns are detectable but require runtime verification. "
                "Some imports may be conditional."
            )
            proposal.requires_human_decision = True
            proposal.decision_required_for = (
                "Determine which dependencies are required vs optional."
            )
            
            self.patterns_matched.append(f"missing_deps:{issue_count}")
            proposals.append(proposal)
        
        return proposals
    
    def _detect_version_conflicts(
        self,
        repository_path: str,
    ) -> List[IntelligenceProposal]:
        """Detect potential version conflicts."""
        proposals = []
        
        # Read requirements.txt if it exists
        req_file = os.path.join(repository_path, 'requirements.txt')
        if not os.path.exists(req_file):
            return proposals
        
        try:
            with open(req_file, 'r') as f:
                reqs = f.readlines()
        except Exception:
            return proposals
        
        # Check for loose version specs
        loose_specs = []
        for line in reqs:
            if re.match(r'^[a-zA-Z0-9_-]+\s*$', line.strip()):
                loose_specs.append(line.strip())
        
        if loose_specs:
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.DEPENDENCY_MISUSE
            proposal.severity = Severity.MEDIUM
            
            issue_count = len(loose_specs)
            
            proposal.problem_statement = (
                f"Found {issue_count} dependencies without version specifications. "
                f"Always pins 'latest' which can break due to incompatible changes."
            )
            
            proposal.risk_explanation = (
                f"Unpinned dependencies may pull breaking changes automatically. "
                f"Application works in dev but breaks in production with newer versions. "
                f"Makes builds non-deterministic and unreproducible."
            )
            
            proposal.root_cause_hypothesis = (
                f"Loose version specs simplify development but create deployment risk. "
                f"No version pinning strategy was enforced."
            )
            
            proposal.affected_files = [
                AffectedFile(path='requirements.txt', severity=Severity.MEDIUM)
            ]
            
            # Strategies
            proposal.suggested_strategies = [
                FixStrategy(
                    name="Pin all dependency versions",
                    description=(
                        f"Add version specifications to all {issue_count} loose dependencies. "
                        f"Use == for exact pinning or ~= for compatible releases."
                    ),
                    effort_estimate=EffortEstimate.SMALL,
                    prerequisite_actions=[
                        "Check installed versions",
                        "Add version specs to requirements.txt",
                        "Test with exact versions",
                        "Document version pinning policy",
                    ],
                    assumptions=[
                        "Current versions are compatible",
                        "Tests pass with pinned versions",
                    ],
                    risks=[
                        "May miss security updates",
                        "Manual updates required",
                    ],
                ),
                FixStrategy(
                    name="Use ranges for flexibility",
                    description=(
                        f"Use version ranges (e.g., ~=1.2.0) to allow compatible updates "
                        f"while preventing breaking changes."
                    ),
                    effort_estimate=EffortEstimate.SMALL,
                    prerequisite_actions=[
                        "Understand semantic versioning",
                        "Define version ranges",
                        "Add to requirements.txt",
                        "Test with range versions",
                        "Monitor for breaking changes",
                    ],
                    assumptions=[
                        "Dependencies follow semantic versioning",
                        "Ranges are appropriate",
                    ],
                    risks=[
                        "Ranges may be too loose",
                        "Breaking changes may slip through",
                    ],
                ),
            ]
            
            proposal.confidence_level = 90
            proposal.confidence_explanation = (
                "Missing version specs are easily detectable in requirements.txt. "
                "Confidence high that these should be pinned."
            )
            proposal.requires_human_decision = True
            proposal.decision_required_for = (
                "Version pinning strategy; exact vs ranges."
            )
            
            self.patterns_matched.append(f"loose_versions:{issue_count}")
            proposals.append(proposal)
        
        return proposals
    
    def _scan_for_deprecated_apis(self, repository_path: str) -> List[Tuple]:
        """Scan for deprecated API usage."""
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
                            
                            for api_name, (pattern, _) in self.DEPRECATED_PATTERNS.items():
                                if re.search(pattern, line):
                                    issues.append((file_path, line_num, api_name))
                                    break
                except Exception:
                    pass
        
        return issues
    
    def _scan_for_import_errors(self, repository_path: str) -> List[Tuple]:
        """Scan for imports that may fail."""
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
                            
                            # Look for imports
                            if re.match(r'^\s*(import|from)\s+', line):
                                # Extract module name
                                match = re.match(r'^\s*(?:import|from)\s+([\w.]+)', line)
                                if match:
                                    module = match.group(1).split('.')[0]
                                    # Check if it's third-party (not stdlib)
                                    if not self._is_stdlib(module):
                                        issues.append((file_path, line_num))
                except Exception:
                    pass
        
        return issues
    
    def _is_stdlib(self, module: str) -> bool:
        """Check if module is in Python stdlib."""
        stdlib_modules = {
            'os', 'sys', 're', 'json', 'time', 'datetime', 'collections',
            'itertools', 'functools', 'operator', 'math', 'random', 'statistics',
            'decimal', 'fractions', 'cmath', 'string', 'io', 'pathlib', 'glob',
            'fnmatch', 'shutil', 'sqlite3', 'zlib', 'gzip', 'bz2', 'lzma',
            'pickle', 'configparser', 'logging', 'argparse', 'getpass', 'curses',
            'platform', 'subprocess', 'socket', 'ssl', 'select', 'selectors',
            'asyncio', 'threading', 'multiprocessing', 'concurrent', 'urllib',
            'http', 'ftplib', 'poplib', 'imaplib', 'smtplib', 'uuid', 'socketserver',
            'xmlrpc', 'json', 'csv', 'configparser', 'netrc', 'plistlib',
        }
        return module in stdlib_modules
