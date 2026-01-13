"""
Abstraction leakage analyzer.

Detects exposed implementation details, broken encapsulation, and abstraction violations.
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


class AbstractionLeakageAnalyzer(BaseAnalyzer):
    """Detect abstraction leakage."""
    
    @property
    def bug_class(self) -> BugClass:
        return BugClass.ABSTRACTION_LEAKAGE
    
    def analyze(
        self,
        repository_path: str,
        repository_url: str,
        branch: str = "main",
    ) -> List[IntelligenceProposal]:
        """Analyze repository for abstraction leakage."""
        self.start_timing()
        self._reset_metrics()
        
        proposals = []
        
        # 1. Detect exposed private attributes
        exposed = self._detect_exposed_privates(repository_path)
        proposals.extend(exposed)
        
        # 2. Detect direct data structure access
        direct_access = self._detect_direct_access(repository_path)
        proposals.extend(direct_access)
        
        # 3. Detect implementation-specific types
        impl_types = self._detect_implementation_types(repository_path)
        proposals.extend(impl_types)
        
        # Finalize all proposals
        finalized = []
        for proposal in proposals:
            proposal.repository_url = repository_url
            proposal.branch = branch
            finalized.append(self._finalize_proposal(proposal))
        
        return finalized
    
    def _detect_exposed_privates(
        self,
        repository_path: str,
    ) -> List[IntelligenceProposal]:
        """Detect exposed private attributes."""
        proposals = []
        
        issues = self._scan_for_private_access(repository_path)
        
        if issues:
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.ABSTRACTION_LEAKAGE
            proposal.severity = Severity.MEDIUM
            
            issue_count = len(issues)
            
            proposal.problem_statement = (
                f"Found {issue_count} accesses to private attributes (starting with _). "
                f"Exposes internal implementation details that should be hidden."
            )
            
            proposal.risk_explanation = (
                f"Code accessing private attributes depends on implementation. If internal "
                f"structure changes, all accessing code breaks. Makes refactoring harder. "
                f"Violates encapsulation principle."
            )
            
            proposal.root_cause_hypothesis = (
                f"Developers took shortcut to access private attributes instead of using "
                f"public interface. Or public interface doesn't provide needed access."
            )
            
            # Add affected files
            for file_path, line_num in issues:
                proposal.affected_files.append(
                    AffectedFile(path=file_path, severity=Severity.MEDIUM)
                )
            
            # Strategies
            proposal.suggested_strategies = [
                FixStrategy(
                    name="Create public accessors",
                    description=(
                        f"Create public methods/properties to provide access to private data "
                        f"in controlled way."
                    ),
                    effort_estimate=EffortEstimate.SMALL,
                    prerequisite_actions=[
                        "Identify accessed private attributes",
                        "Design public accessors",
                        "Implement getter/setter or properties",
                        "Update all accessing code",
                        "Remove direct private access",
                    ],
                    assumptions=[
                        "Public interface can be designed",
                        "Data can be safely exposed via getters",
                    ],
                    risks=[
                        "Accessors may have performance impact",
                        "May expose too much data",
                    ],
                ),
                FixStrategy(
                    name="Restructure data with composition",
                    description=(
                        f"Restructure class to expose data through proper public interface. "
                        f"May require composition or redesign."
                    ),
                    effort_estimate=EffortEstimate.LARGE,
                    prerequisite_actions=[
                        "Assess if current structure is necessary",
                        "Design new public interface",
                        "Restructure class hierarchy",
                        "Update all client code",
                        "Test new structure",
                    ],
                    assumptions=[
                        "Restructuring is feasible",
                        "Client code can be updated",
                    ],
                    risks=[
                        "Major refactoring",
                        "May change semantics",
                    ],
                ),
            ]
            
            proposal.confidence_level = 90
            proposal.confidence_explanation = (
                "Private attribute access is easily detectable. Confidence high that "
                "these violate encapsulation."
            )
            proposal.requires_human_decision = True
            proposal.decision_required_for = (
                "Design public interface; determine which data should be exposed."
            )
            
            self.patterns_matched.append(f"exposed_privates:{issue_count}")
            proposals.append(proposal)
        
        return proposals
    
    def _detect_direct_access(
        self,
        repository_path: str,
    ) -> List[IntelligenceProposal]:
        """Detect direct access to data structures."""
        proposals = []
        
        issues = self._scan_for_direct_structure_access(repository_path)
        
        if issues:
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.ABSTRACTION_LEAKAGE
            proposal.severity = Severity.MEDIUM
            
            issue_count = len(issues)
            
            proposal.problem_statement = (
                f"Found {issue_count} direct accesses to internal data structures "
                f"(dict, list, set). Should use public API instead."
            )
            
            proposal.risk_explanation = (
                f"Direct structure access bypasses encapsulation. Code depends on specific "
                f"data structure choices. Changes to internal structure break all accessing code. "
                f"No invariant enforcement."
            )
            
            proposal.root_cause_hypothesis = (
                f"Objects expose raw data structures instead of providing methods. "
                f"Easier to directly access than write getters."
            )
            
            # Add affected files
            for file_path, line_num in issues:
                proposal.affected_files.append(
                    AffectedFile(path=file_path, severity=Severity.MEDIUM)
                )
            
            # Strategies
            proposal.suggested_strategies = [
                FixStrategy(
                    name="Provide methods instead of direct access",
                    description=(
                        f"Replace direct structure access with methods. Hide data structure "
                        f"behind public methods."
                    ),
                    effort_estimate=EffortEstimate.SMALL,
                    prerequisite_actions=[
                        "Identify data structures being directly accessed",
                        "Create methods for operations",
                        "Update all accessing code",
                        "Make structures private",
                    ],
                    assumptions=[
                        "All access patterns can be captured in methods",
                        "Method-based access is sufficient",
                    ],
                    risks=[
                        "Method interface may be limited",
                        "Performance impact from method calls",
                    ],
                ),
                FixStrategy(
                    name="Use dataclass or named tuple",
                    description=(
                        f"If data is just data holder, use @dataclass or namedtuple "
                        f"with explicit public fields."
                    ),
                    effort_estimate=EffortEstimate.SMALL,
                    prerequisite_actions=[
                        "Convert to dataclass",
                        "Add type hints",
                        "Define frozen=True if immutable",
                        "Update accessing code if needed",
                    ],
                    assumptions=[
                        "Object is purely data holder",
                        "Fields are well-defined",
                    ],
                    risks=[
                        "Dataclass is less flexible",
                        "May expose internals",
                    ],
                ),
            ]
            
            proposal.confidence_level = 85
            proposal.confidence_explanation = (
                "Direct structure access is detectable. Confidence high that "
                "these should use public API."
            )
            proposal.requires_human_decision = True
            proposal.decision_required_for = (
                "Design public API; methods vs dataclass."
            )
            
            self.patterns_matched.append(f"direct_access:{issue_count}")
            proposals.append(proposal)
        
        return proposals
    
    def _detect_implementation_types(
        self,
        repository_path: str,
    ) -> List[IntelligenceProposal]:
        """Detect function signatures exposing implementation types."""
        proposals = []
        
        issues = self._scan_for_impl_type_leakage(repository_path)
        
        if issues:
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.ABSTRACTION_LEAKAGE
            proposal.severity = Severity.LOW
            
            issue_count = len(issues)
            
            proposal.problem_statement = (
                f"Found {issue_count} function signatures exposing implementation types "
                f"(dict, list, etc.) instead of abstract types or protocols."
            )
            
            proposal.risk_explanation = (
                f"Functions returning concrete types make it hard to change implementation. "
                f"Callers depend on specific type. Should return abstract type (protocol, interface). "
                f"Makes code less flexible."
            )
            
            proposal.root_cause_hypothesis = (
                f"Quick implementation without thinking about abstraction. Python's "
                f"duck typing makes specific types visible in signatures."
            )
            
            # Add affected files
            for file_path, line_num in issues:
                proposal.affected_files.append(
                    AffectedFile(path=file_path, severity=Severity.LOW)
                )
            
            # Strategies
            proposal.suggested_strategies = [
                FixStrategy(
                    name="Use abstract return types",
                    description=(
                        f"Change return types to abstract types (Sequence, Mapping, Iterable) "
                        f"instead of list, dict."
                    ),
                    effort_estimate=EffortEstimate.SMALL,
                    prerequisite_actions=[
                        "Review function signatures",
                        "Change return types to collections.abc types",
                        "Update type hints",
                        "Test return values",
                    ],
                    assumptions=[
                        "Abstract types are compatible",
                        "Callers use abstract interface",
                    ],
                    risks=[
                        "May break code using specific methods",
                        "Performance impact",
                    ],
                ),
                FixStrategy(
                    name="Define protocols/abstract base classes",
                    description=(
                        f"Define protocols (typing.Protocol) or abstract base classes that "
                        f"specify expected interface without exposing implementation."
                    ),
                    effort_estimate=EffortEstimate.SMALL,
                    prerequisite_actions=[
                        "Define protocol/ABC",
                        "Update function signatures",
                        "Implement protocol in return objects",
                        "Update type hints",
                    ],
                    assumptions=[
                        "Protocol/ABC can be designed",
                        "Return objects can implement protocol",
                    ],
                    risks=[
                        "Over-engineering for simple cases",
                        "Complexity overhead",
                    ],
                ),
            ]
            
            proposal.confidence_level = 75
            proposal.confidence_explanation = (
                "Type leakage requires analyzing type hints. Confidence moderate; "
                "some concrete types may be intentional."
            )
            proposal.requires_human_decision = True
            proposal.decision_required_for = (
                "Decide which types should be abstracted; cost-benefit of abstraction."
            )
            
            self.patterns_matched.append(f"impl_type_leakage:{issue_count}")
            proposals.append(proposal)
        
        return proposals
    
    def _scan_for_private_access(self, repository_path: str) -> List[Tuple]:
        """Scan for accesses to private attributes."""
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
                            
                            # Look for obj._private or obj.__dunder
                            if re.search(r'\.\s*_[a-zA-Z_]\w*', line):
                                # Skip if it's self._private within class definition
                                if not re.search(r'self\._', line):
                                    issues.append((file_path, line_num))
                except Exception:
                    pass
        
        return issues
    
    def _scan_for_direct_structure_access(self, repository_path: str) -> List[Tuple]:
        """Scan for direct structure access."""
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
                            
                            # Look for .[...] or .['...']
                            if re.search(r'\.\s*\[|\.get\(|\.keys\(|\.values\(', line):
                                issues.append((file_path, line_num))
                except Exception:
                    pass
        
        return issues
    
    def _scan_for_impl_type_leakage(self, repository_path: str) -> List[Tuple]:
        """Scan for implementation types in function signatures."""
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
                            
                            # Look for -> dict, -> list, -> set
                            if re.search(r'->\s*(dict|list|set|tuple)\b', line):
                                issues.append((file_path, line_num))
                except Exception:
                    pass
        
        return issues
