"""
Test coverage analyzer.

Detects code paths with insufficient test coverage and untested critical paths.
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


class TestCoverageAnalyzer(BaseAnalyzer):
    """Detect test coverage gaps."""
    
    @property
    def bug_class(self) -> BugClass:
        return BugClass.TEST_COVERAGE_BLIND_SPOTS
    
    def analyze(
        self,
        repository_path: str,
        repository_url: str,
        branch: str = "main",
    ) -> List[IntelligenceProposal]:
        """Analyze repository for test coverage gaps."""
        self.start_timing()
        self._reset_metrics()
        
        proposals = []
        
        # 1. Detect critical code without tests
        critical = self._detect_critical_without_tests(repository_path)
        proposals.extend(critical)
        
        # 2. Detect error handling without tests
        untested_errors = self._detect_untested_error_handling(repository_path)
        proposals.extend(untested_errors)
        
        # 3. Detect complex logic without tests
        complex_code = self._detect_complex_untested_code(repository_path)
        proposals.extend(complex_code)
        
        # Finalize all proposals
        finalized = []
        for proposal in proposals:
            proposal.repository_url = repository_url
            proposal.branch = branch
            finalized.append(self._finalize_proposal(proposal))
        
        return finalized
    
    def _detect_critical_without_tests(
        self,
        repository_path: str,
    ) -> List[IntelligenceProposal]:
        """Detect critical code paths without test coverage."""
        proposals = []
        
        issues = self._scan_for_critical_code(repository_path)
        
        if issues:
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.TEST_COVERAGE_BLIND_SPOTS
            proposal.severity = Severity.HIGH
            
            issue_count = len(issues)
            
            proposal.problem_statement = (
                f"Found {issue_count} critical code paths (security, payment, data) "
                f"without test coverage. Bugs in critical code have highest impact."
            )
            
            proposal.risk_explanation = (
                f"Critical code (payment processing, authentication, data persistence) "
                f"must be thoroughly tested. Untested critical code risks data loss, "
                f"security breaches, or financial loss."
            )
            
            proposal.root_cause_hypothesis = (
                f"Critical code was added without accompanying tests. Tests may have been "
                f"skipped due to time pressure or complexity."
            )
            
            # Add affected files
            for file_path, line_num in issues:
                proposal.affected_files.append(
                    AffectedFile(path=file_path, severity=Severity.CRITICAL)
                )
            
            # Strategies
            proposal.suggested_strategies = [
                FixStrategy(
                    name="Add unit tests for critical paths",
                    description=(
                        f"Write unit tests covering happy path and error cases for "
                        f"{issue_count} critical functions."
                    ),
                    effort_estimate=EffortEstimate.LARGE,
                    prerequisite_actions=[
                        "Identify critical functions",
                        "Write happy path tests",
                        "Write error case tests",
                        "Aim for 100% branch coverage",
                        "Add regression tests",
                    ],
                    assumptions=[
                        "Code is testable (can inject dependencies)",
                        "Tests can be automated",
                    ],
                    risks=[
                        "Tests may miss edge cases",
                        "High test maintenance burden",
                    ],
                ),
                FixStrategy(
                    name="Add integration/E2E tests",
                    description=(
                        f"Add integration tests that exercise critical code in realistic scenarios. "
                        f"Use test database and mocked external services."
                    ),
                    effort_estimate=EffortEstimate.VERY_LARGE,
                    prerequisite_actions=[
                        "Set up test environment",
                        "Create test database fixtures",
                        "Write integration test scenarios",
                        "Mock external services",
                        "Automate test execution",
                    ],
                    assumptions=[
                        "Integration testing environment can be set up",
                        "External services can be mocked",
                    ],
                    risks=[
                        "Integration tests are slow",
                        "Flaky tests from external dependencies",
                        "High maintenance burden",
                    ],
                ),
            ]
            
            proposal.confidence_level = 85
            proposal.confidence_explanation = (
                f"Detection identifies code related to security/payment/data. Confidence "
                f"high that these are critical. Recommend code review to confirm."
            )
            proposal.requires_human_decision = True
            proposal.decision_required_for = (
                "Prioritize which critical paths to test first; allocate test resources."
            )
            
            self.patterns_matched.append(f"critical_untested:{issue_count}")
            proposals.append(proposal)
        
        return proposals
    
    def _detect_untested_error_handling(
        self,
        repository_path: str,
    ) -> List[IntelligenceProposal]:
        """Detect error handling without test coverage."""
        proposals = []
        
        issues = self._scan_for_untested_errors(repository_path)
        
        if issues:
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.TEST_COVERAGE_BLIND_SPOTS
            proposal.severity = Severity.MEDIUM
            
            issue_count = len(issues)
            
            proposal.problem_statement = (
                f"Found {issue_count} error handling paths (try/except, raise) "
                f"without test coverage. Error paths are often untested."
            )
            
            proposal.risk_explanation = (
                f"Error handling code is executed rarely but critically. Untested "
                f"error paths often contain bugs that only surface in production during "
                f"actual failures."
            )
            
            proposal.root_cause_hypothesis = (
                f"Focus on happy path testing. Error cases overlooked. Error handling "
                f"is harder to test (requires error injection)."
            )
            
            # Add affected files
            for file_path, line_num in issues:
                proposal.affected_files.append(
                    AffectedFile(path=file_path, severity=Severity.MEDIUM)
                )
            
            # Strategies
            proposal.suggested_strategies = [
                FixStrategy(
                    name="Add error case tests",
                    description=(
                        f"Write tests that trigger error conditions. Use mocks to raise "
                        f"exceptions. Test error recovery and cleanup."
                    ),
                    effort_estimate=EffortEstimate.MEDIUM,
                    prerequisite_actions=[
                        "Identify error conditions",
                        "Use mock/patch to trigger errors",
                        "Test error message and logging",
                        "Verify cleanup/rollback",
                        "Test error propagation",
                    ],
                    assumptions=[
                        "Code is mockable",
                        "Errors are deterministic",
                    ],
                    risks=[
                        "Error triggering may be complex",
                        "Mocks may not reflect real errors",
                    ],
                ),
                FixStrategy(
                    name="Use pytest-raising and hypothesis",
                    description=(
                        f"Use pytest-raises to test exceptions and hypothesis property-based "
                        f"testing to generate error conditions automatically."
                    ),
                    effort_estimate=EffortEstimate.SMALL,
                    prerequisite_actions=[
                        "Install pytest-raises, hypothesis",
                        "Learn hypothesis API",
                        "Write property-based tests",
                        "Generate edge cases",
                        "Verify error handling",
                    ],
                    assumptions=[
                        "Code is deterministic",
                        "Properties can be expressed",
                    ],
                    risks=[
                        "Hypothesis may be overkill for simple cases",
                        "Learning curve",
                    ],
                ),
            ]
            
            proposal.confidence_level = 75
            proposal.confidence_explanation = (
                f"Detection finds try/except blocks but cannot easily determine if tested. "
                f"Pattern matching has moderate confidence; recommend coverage measurement."
            )
            proposal.requires_human_decision = True
            proposal.decision_required_for = (
                "Prioritize error cases for testing; allocate test resources."
            )
            
            self.patterns_matched.append(f"untested_errors:{issue_count}")
            proposals.append(proposal)
        
        return proposals
    
    def _detect_complex_untested_code(
        self,
        repository_path: str,
    ) -> List[IntelligenceProposal]:
        """Detect complex code without test coverage."""
        proposals = []
        
        issues = self._scan_for_complex_code(repository_path)
        
        if issues:
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.TEST_COVERAGE_BLIND_SPOTS
            proposal.severity = Severity.MEDIUM
            
            issue_count = len(issues)
            
            proposal.problem_statement = (
                f"Found {issue_count} complex functions (nested conditionals, loops, branching) "
                f"without comprehensive test coverage. Complex code has higher bug probability."
            )
            
            proposal.risk_explanation = (
                f"Complex code with many branches is hard to reason about and test. "
                f"Each branch combination must be tested. Untested combinations hide bugs."
            )
            
            proposal.root_cause_hypothesis = (
                f"Complex code written without accompanying tests. High cyclomatic complexity "
                f"makes comprehensive testing difficult."
            )
            
            # Add affected files
            for file_path, line_num in issues:
                proposal.affected_files.append(
                    AffectedFile(path=file_path, severity=Severity.MEDIUM)
                )
            
            # Strategies
            proposal.suggested_strategies = [
                FixStrategy(
                    name="Simplify complex functions",
                    description=(
                        f"Refactor {issue_count} complex functions to reduce cyclomatic complexity. "
                        f"Split into smaller functions with single responsibility."
                    ),
                    effort_estimate=EffortEstimate.LARGE,
                    prerequisite_actions=[
                        "Measure cyclomatic complexity",
                        "Identify complex branches",
                        "Extract helper functions",
                        "Reduce nesting",
                        "Test refactored code",
                    ],
                    assumptions=[
                        "Refactoring doesn't change behavior",
                        "Code can be split meaningfully",
                    ],
                    risks=[
                        "Refactoring may introduce bugs",
                        "More functions to maintain",
                    ],
                ),
                FixStrategy(
                    name="Add comprehensive branch coverage tests",
                    description=(
                        f"Write tests covering all branches and combinations. "
                        f"Aim for 100% branch coverage for complex code."
                    ),
                    effort_estimate=EffortEstimate.LARGE,
                    prerequisiate_actions=[
                        "Enumerate all branches",
                        "Create test cases for each combination",
                        "Use coverage.py to measure",
                        "Add edge case tests",
                        "Run mutation testing",
                    ],
                    assumptions=[
                        "All branches are testable",
                        "Combinations are manageable",
                    ],
                    risks=[
                        "Test explosion with many branches",
                        "High test maintenance burden",
                    ],
                ),
            ]
            
            proposal.confidence_level = 70
            proposal.confidence_explanation = (
                f"Detection identifies code with high branching. Confidence moderate "
                f"that this code lacks tests; recommend coverage measurement."
            )
            proposal.requires_human_decision = True
            proposal.decision_required_for = (
                "Choose refactoring vs testing strategy for complex code."
            )
            
            self.patterns_matched.append(f"complex_untested:{issue_count}")
            proposals.append(proposal)
        
        return proposals
    
    def _scan_for_critical_code(self, repository_path: str) -> List[Tuple]:
        """Scan for critical code paths."""
        issues = []
        
        critical_keywords = ['payment', 'transaction', 'security', 'password', 'token', 'auth', 'encrypt']
        
        for root, dirs, files in os.walk(repository_path):
            dirs[:] = [d for d in dirs if d not in {
                '__pycache__', '.git', 'venv', 'build', 'dist', 'tests'
            }]
            
            for file in files:
                if not file.endswith('.py') or file.startswith('test_'):
                    continue
                
                file_path = os.path.join(root, file)
                self.files_scanned += 1
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            self.lines_analyzed += 1
                            
                            for keyword in critical_keywords:
                                if keyword in line.lower():
                                    issues.append((file_path, line_num))
                                    break
                except Exception:
                    pass
        
        return issues
    
    def _scan_for_untested_errors(self, repository_path: str) -> List[Tuple]:
        """Scan for error handling without tests."""
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
                            
                            if re.search(r'except\s+\w+|raise\s+\w+', line):
                                issues.append((file_path, line_num))
                except Exception:
                    pass
        
        return issues
    
    def _scan_for_complex_code(self, repository_path: str) -> List[Tuple]:
        """Scan for complex functions (high branching)."""
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
                        content = f.read()
                        self.lines_analyzed += len(content.split('\n'))
                        
                        # Find functions with high complexity (many if/for/while)
                        functions = re.finditer(r'def\s+\w+.*?:\n(.*?)(?=\ndef |\Z)', content, re.DOTALL)
                        for match in functions:
                            func_body = match.group(1)
                            # Count branching statements
                            branch_count = len(re.findall(
                                r'\bif\b|\belif\b|\belse\b|\bfor\b|\bwhile\b',
                                func_body
                            ))
                            
                            # If high branching, flag it
                            if branch_count >= 5:
                                for line_num, line in enumerate(content.split('\n'), 1):
                                    if 'def ' in line and match.group(0) in content[content.find(line):]:
                                        issues.append((file_path, line_num))
                                        break
                except Exception:
                    pass
        
        return issues
