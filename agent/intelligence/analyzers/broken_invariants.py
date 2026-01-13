"""
Broken invariants analyzer.

Detects violations of object invariants, constructor failures, and missing error handling.
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


class BrokenInvariantsAnalyzer(BaseAnalyzer):
    """Detect broken object invariants."""
    
    @property
    def bug_class(self) -> BugClass:
        return BugClass.BROKEN_INVARIANTS
    
    def analyze(
        self,
        repository_path: str,
        repository_url: str,
        branch: str = "main",
    ) -> List[IntelligenceProposal]:
        """Analyze repository for broken invariants."""
        self.start_timing()
        self._reset_metrics()
        
        proposals = []
        
        # 1. Detect constructors with unhandled exceptions
        uncaught = self._detect_unhandled_exceptions(repository_path)
        proposals.extend(uncaught)
        
        # 2. Detect missing error handling
        missing = self._detect_missing_error_handling(repository_path)
        proposals.extend(missing)
        
        # 3. Detect incomplete initialization
        incomplete = self._detect_incomplete_initialization(repository_path)
        proposals.extend(incomplete)
        
        # Finalize all proposals
        finalized = []
        for proposal in proposals:
            proposal.repository_url = repository_url
            proposal.branch = branch
            finalized.append(self._finalize_proposal(proposal))
        
        return finalized
    
    def _detect_unhandled_exceptions(
        self,
        repository_path: str,
    ) -> List[IntelligenceProposal]:
        """Detect constructors that may raise unhandled exceptions."""
        proposals = []
        
        issues = self._scan_for_unhandled_exceptions(repository_path)
        
        if issues:
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.BROKEN_INVARIANTS
            proposal.severity = Severity.HIGH
            
            issue_count = len(issues)
            
            proposal.problem_statement = (
                f"Found {issue_count} constructors or initialization code paths that may raise "
                f"exceptions without proper handling. Objects may be left in partial state."
            )
            
            proposal.risk_explanation = (
                f"If __init__ or initialization method raises exception, object may be partially "
                f"initialized. Subsequent method calls may fail unexpectedly. Invariants are broken. "
                f"Can cause cascading failures in code that assumes initialization succeeded."
            )
            
            proposal.root_cause_hypothesis = (
                f"Code calls operations that may fail (file I/O, network, parsing) in __init__ "
                f"without try/except or proper error handling."
            )
            
            # Add affected files
            for file_path, line_num in issues:
                proposal.affected_files.append(
                    AffectedFile(path=file_path, severity=Severity.HIGH)
                )
            
            # Strategies
            proposal.suggested_strategies = [
                FixStrategy(
                    name="Move risky operations to lazy initialization",
                    description=(
                        f"Move operations that may fail out of __init__. Use lazy initialization "
                        f"or factory pattern. Initialize only essential data in __init__."
                    ),
                    effort_estimate=EffortEstimate.MEDIUM,
                    prerequisite_actions=[
                        "Identify operations in __init__ that may fail",
                        "Move to separate initialization method or property",
                        "Call lazy init on first access",
                        "Add state tracking (initialized, uninitialized)",
                        "Test lazy init behavior",
                    ],
                    assumptions=[
                        "Lazy init is compatible with usage patterns",
                        "Callers check initialization before use",
                    ],
                    risks=[
                        "May defer errors until runtime",
                        "Adds complexity to state management",
                        "Requires caller awareness",
                    ],
                ),
                FixStrategy(
                    name="Add proper exception handling",
                    description=(
                        f"Add try/except in __init__ to catch and handle potential exceptions. "
                        f"Ensure object is left in valid state even if exception occurs."
                    ),
                    effort_estimate=EffortEstimate.SMALL,
                    prerequisite_actions=[
                        "Identify all operations that may fail",
                        "Add try/except around each",
                        "Define valid error states",
                        "Add logging/telemetry",
                        "Test error paths",
                    ],
                    assumptions=[
                        "Errors are recoverable or detectable",
                        "Exception handling doesn't hide problems",
                    ],
                    risks=[
                        "May hide exceptions",
                        "Requires careful exception handling design",
                    ],
                ),
            ]
            
            proposal.confidence_level = 75
            proposal.confidence_explanation = (
                f"Detection finds operations in __init__ that may fail; however, "
                f"requires semantic analysis to verify actual risk. Pattern matching has moderate confidence."
            )
            proposal.requires_human_decision = True
            proposal.decision_required_for = (
                "Assess initialization strategy; lazy init vs exception handling."
            )
            
            self.patterns_matched.append(f"unhandled_init:{issue_count}")
            proposals.append(proposal)
        
        return proposals
    
    def _detect_missing_error_handling(
        self,
        repository_path: str,
    ) -> List[IntelligenceProposal]:
        """Detect code paths without error handling."""
        proposals = []
        
        issues = self._scan_for_missing_error_handling(repository_path)
        
        if issues:
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.BROKEN_INVARIANTS
            proposal.severity = Severity.MEDIUM
            
            issue_count = len(issues)
            
            proposal.problem_statement = (
                f"Found {issue_count} risky operations (I/O, parsing, network) without "
                f"proper error handling. Unhandled exceptions can crash application."
            )
            
            proposal.risk_explanation = (
                f"Operations like file access, JSON parsing, HTTP requests can fail. "
                f"Without try/except, exceptions propagate and may crash application. "
                f"Application reliability is compromised."
            )
            
            proposal.root_cause_hypothesis = (
                f"Code assumes operations succeed. Defensive programming practices not applied. "
                f"May be prototypical code not hardened for production."
            )
            
            # Add affected files
            for file_path, line_num in issues:
                proposal.affected_files.append(
                    AffectedFile(path=file_path, severity=Severity.MEDIUM)
                )
            
            # Strategies
            proposal.suggested_strategies = [
                FixStrategy(
                    name="Add try/except blocks",
                    description=(
                        f"Wrap risky operations in try/except. Log errors, return sensible defaults, "
                        f"or propagate with context."
                    ),
                    effort_estimate=EffortEstimate.SMALL,
                    prerequisite_actions=[
                        "Identify all risky operations",
                        "Add try/except around each",
                        "Define error handling (log, retry, default)",
                        "Test error paths",
                        "Add monitoring/alerting",
                    ],
                    assumptions=[
                        "Error recovery is possible",
                        "Sensible default values exist",
                    ],
                    risks=[
                        "May hide real errors",
                        "Over-broad except can hide bugs",
                    ],
                ),
                FixStrategy(
                    name="Use context managers and cleanup",
                    description=(
                        f"Use 'with' statements and context managers to ensure cleanup "
                        f"even if exception occurs (e.g., file close, connection close)."
                    ),
                    effort_estimate=EffortEstimate.SMALL,
                    prerequisite_actions=[
                        "Identify resources needing cleanup",
                        "Use 'with' statements",
                        "Implement __enter__ and __exit__ if custom",
                        "Test exception cleanup",
                    ],
                    assumptions=[
                        "Resources support context managers",
                        "Cleanup is deterministic",
                    ],
                    risks=[
                        "Cleanup may raise exceptions",
                        "Complex nested context managers",
                    ],
                ),
            ]
            
            proposal.confidence_level = 80
            proposal.confidence_explanation = (
                f"Pattern matching for risky operations is reliable. Confidence high "
                f"that these operations need error handling."
            )
            proposal.requires_human_decision = True
            proposal.decision_required_for = (
                "Determine error handling strategy for each operation type."
            )
            
            self.patterns_matched.append(f"missing_error_handling:{issue_count}")
            proposals.append(proposal)
        
        return proposals
    
    def _detect_incomplete_initialization(
        self,
        repository_path: str,
    ) -> List[IntelligenceProposal]:
        """Detect incomplete initialization patterns."""
        proposals = []
        
        issues = self._scan_for_incomplete_init(repository_path)
        
        if issues:
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.BROKEN_INVARIANTS
            proposal.severity = Severity.MEDIUM
            
            issue_count = len(issues)
            
            proposal.problem_statement = (
                f"Found {issue_count} classes where attributes may not be initialized. "
                f"Methods may access uninitialized attributes, causing AttributeError."
            )
            
            proposal.risk_explanation = (
                f"If __init__ doesn't initialize all attributes, and methods are called "
                f"before initialization, AttributeError occurs. Hard to debug. May happen "
                f"only in certain execution paths."
            )
            
            proposal.root_cause_hypothesis = (
                f"Attributes initialized conditionally or in separate methods. "
                f"Some code paths skip initialization. No invariant enforcement."
            )
            
            # Add affected files
            for file_path, line_num in issues:
                proposal.affected_files.append(
                    AffectedFile(path=file_path, severity=Severity.MEDIUM)
                )
            
            # Strategies
            proposal.suggested_strategies = [
                FixStrategy(
                    name="Initialize all attributes in __init__",
                    description=(
                        f"Ensure every attribute accessed in methods is initialized in __init__, "
                        f"even if to None. Add type hints to document expected types."
                    ),
                    effort_estimate=EffortEstimate.SMALL,
                    prerequisite_actions=[
                        "List all attributes used in class",
                        "Ensure all are initialized in __init__",
                        "Add type hints in class docstring or annotations",
                        "Run static analysis to find uninitialized access",
                        "Test all code paths",
                    ],
                    assumptions=[
                        "All attributes can be initialized upfront",
                        "Default values are sensible",
                    ],
                    risks=[
                        "May require restructuring",
                        "Default values may be wrong",
                    ],
                ),
                FixStrategy(
                    name="Add property decorators with lazy init",
                    description=(
                        f"Use @property decorators to lazily initialize attributes on first access, "
                        f"or check and initialize on demand."
                    ),
                    effort_estimate=EffortEstimate.SMALL,
                    prerequisite_actions=[
                        "Identify which attributes are lazily initialized",
                        "Create properties with lazy init logic",
                        "Test lazy init behavior",
                        "Document lazy initialization",
                    ],
                    assumptions=[
                        "Lazy init is appropriate for attributes",
                        "No initialization order dependencies",
                    ],
                    risks=[
                        "Property access may be slower",
                        "First access may be expensive",
                    ],
                ),
            ]
            
            proposal.confidence_level = 70
            proposal.confidence_explanation = (
                f"Detecting uninitialized attributes requires data flow analysis. "
                f"Pattern matching has moderate confidence; recommend static analysis."
            )
            proposal.requires_human_decision = True
            proposal.decision_required_for = (
                "Choose initialization strategy; eager vs lazy initialization."
            )
            
            self.patterns_matched.append(f"incomplete_init:{issue_count}")
            proposals.append(proposal)
        
        return proposals
    
    def _scan_for_unhandled_exceptions(self, repository_path: str) -> List[Tuple]:
        """Scan for unhandled exceptions in __init__."""
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
                        in_init = False
                        for line_num, line in enumerate(f, 1):
                            self.lines_analyzed += 1
                            
                            if 'def __init__' in line:
                                in_init = True
                            elif in_init and line.strip().startswith('def '):
                                in_init = False
                            
                            if in_init:
                                # Look for risky operations in __init__
                                if re.search(r'open\(|\.parse|\.get|json\.load|requests\.', line):
                                    if 'try' not in line and 'except' not in line:
                                        issues.append((file_path, line_num))
                except Exception:
                    pass
        
        return issues
    
    def _scan_for_missing_error_handling(self, repository_path: str) -> List[Tuple]:
        """Scan for missing error handling."""
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
                            
                            # Look for risky operations without try/except
                            if re.search(r'\.read\(|\.parse|json\.load|requests\.', line):
                                # Check if it's in a try block (simple heuristic)
                                if 'try' not in line and '.get(' not in line:
                                    issues.append((file_path, line_num))
                except Exception:
                    pass
        
        return issues
    
    def _scan_for_incomplete_init(self, repository_path: str) -> List[Tuple]:
        """Scan for incomplete initialization."""
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
                        
                        # Look for classes with many attributes
                        classes = re.finditer(r'class\s+(\w+).*?:\n(.*?)(?=\nclass |\Z)', content, re.DOTALL)
                        for match in classes:
                            class_def = match.group(2)
                            # Count self.x assignments in methods
                            method_attrs = len(re.findall(r'self\.\w+\s*=', class_def))
                            # Count self.x accesses (likely use)
                            method_uses = len(re.findall(r'self\.\w+(?!\s*=)', class_def))
                            
                            # If more uses than sets, likely incomplete init
                            if method_uses > method_attrs * 2:
                                for line_num, line in enumerate(content.split('\n'), 1):
                                    if f'class {match.group(1)}' in line:
                                        issues.append((file_path, line_num))
                except Exception:
                    pass
        
        return issues
