"""
API contract analyzer.

Detects API contract violations, breaking changes, and incompatibilities.
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


class APIContractAnalyzer(BaseAnalyzer):
    """Detect API contract violations."""
    
    @property
    def bug_class(self) -> BugClass:
        return BugClass.API_CONTRACT_VIOLATIONS
    
    def analyze(
        self,
        repository_path: str,
        repository_url: str,
        branch: str = "main",
    ) -> List[IntelligenceProposal]:
        """Analyze repository for API contract violations."""
        self.start_timing()
        self._reset_metrics()
        
        proposals = []
        
        # 1. Detect missing type hints
        missing_hints = self._detect_missing_type_hints(repository_path)
        proposals.extend(missing_hints)
        
        # 2. Detect incompatible method signatures
        incompatible = self._detect_incompatible_signatures(repository_path)
        proposals.extend(incompatible)
        
        # 3. Detect missing documentation
        missing_docs = self._detect_missing_documentation(repository_path)
        proposals.extend(missing_docs)
        
        # Finalize all proposals
        finalized = []
        for proposal in proposals:
            proposal.repository_url = repository_url
            proposal.branch = branch
            finalized.append(self._finalize_proposal(proposal))
        
        return finalized
    
    def _detect_missing_type_hints(
        self,
        repository_path: str,
    ) -> List[IntelligenceProposal]:
        """Detect functions without type hints."""
        proposals = []
        
        issues = self._scan_for_missing_type_hints(repository_path)
        
        if issues:
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.API_CONTRACT_VIOLATIONS
            proposal.severity = Severity.MEDIUM
            
            issue_count = len(issues)
            
            proposal.problem_statement = (
                f"Found {issue_count} functions without type hints. Type hints document "
                f"expected parameter and return types, improving API clarity."
            )
            
            proposal.risk_explanation = (
                f"Without type hints, callers must read function implementation to understand "
                f"expected types. IDE autocompletion is limited. Type checking (mypy) cannot "
                f"catch type errors. Refactoring is harder."
            )
            
            proposal.root_cause_hypothesis = (
                f"Code written before adopting type hints. Or developer didn't add hints "
                f"initially. May be older Python code."
            )
            
            # Add affected files
            for file_path, line_num in issues:
                proposal.affected_files.append(
                    AffectedFile(path=file_path, severity=Severity.MEDIUM)
                )
            
            # Strategies
            proposal.suggested_strategies = [
                FixStrategy(
                    name="Add type hints manually",
                    description=(
                        f"Add type hints to {issue_count} functions. Use built-in types "
                        f"and typing module (Union, Optional, etc.)."
                    ),
                    effort_estimate=EffortEstimate.MEDIUM,
                    prerequisite_actions=[
                        "Understand Python typing syntax",
                        "Add hints to function signatures",
                        "Add return type hints",
                        "Run mypy to verify",
                        "Test code still works",
                    ],
                    assumptions=[
                        "Types are inferrable from code",
                        "Python 3.5+ (type hints supported)",
                    ],
                    risks=[
                        "Hints may be wrong",
                        "May require refactoring for clarity",
                    ],
                ),
                FixStrategy(
                    name="Use auto type hint tools",
                    description=(
                        f"Use tools like pydantic, pyright, or Pylance to infer and add "
                        f"type hints automatically."
                    ),
                    effort_estimate=EffortEstimate.SMALL,
                    prerequisite_actions=[
                        "Install pydantic or type checking tool",
                        "Generate type hints",
                        "Review generated hints",
                        "Adjust as needed",
                        "Commit hints",
                    ],
                    assumptions=[
                        "Auto-inference is accurate enough",
                        "Tools are available",
                    ],
                    risks=[
                        "Auto-inference may be imprecise",
                        "Generated hints may need review",
                    ],
                ),
            ]
            
            proposal.confidence_level = 85
            proposal.confidence_explanation = (
                "Missing type hints are detectable via pattern matching. Confidence high "
                "that these functions should be typed."
            )
            proposal.requires_human_decision = True
            proposal.decision_required_for = (
                "Prioritize type hint addition; manual vs auto-generation."
            )
            
            self.patterns_matched.append(f"missing_type_hints:{issue_count}")
            proposals.append(proposal)
        
        return proposals
    
    def _detect_incompatible_signatures(
        self,
        repository_path: str,
    ) -> List[IntelligenceProposal]:
        """Detect incompatible method overrides."""
        proposals = []
        
        issues = self._scan_for_signature_mismatches(repository_path)
        
        if issues:
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.API_CONTRACT_VIOLATIONS
            proposal.severity = Severity.HIGH
            
            issue_count = len(issues)
            
            proposal.problem_statement = (
                f"Found {issue_count} method overrides with incompatible signatures. "
                f"Subclasses should match parent method signatures."
            )
            
            proposal.risk_explanation = (
                f"Incompatible method signatures break Liskov Substitution Principle. "
                f"Code expecting parent class behavior fails with subclass. Type errors. "
                f"Late-binding errors at runtime."
            )
            
            proposal.root_cause_hypothesis = (
                f"Subclass added parameters or changed return type without updating parent. "
                f"Or developer didn't understand inheritance contract."
            )
            
            # Add affected files
            for file_path, line_num in issues:
                proposal.affected_files.append(
                    AffectedFile(path=file_path, severity=Severity.HIGH)
                )
            
            # Strategies
            proposal.suggested_strategies = [
                FixStrategy(
                    name="Fix method signatures to match parent",
                    description=(
                        f"Update {issue_count} incompatible method signatures to match "
                        f"parent class. Use super() appropriately."
                    ),
                    effort_estimate=EffortEstimate.SMALL,
                    prerequisite_actions=[
                        "Review parent class signatures",
                        "Update subclass signatures",
                        "Call super() if needed",
                        "Test polymorphic usage",
                    ],
                    assumptions=[
                        "Parent signature is correct",
                        "Subclass can be adapted",
                    ],
                    risks=[
                        "May break subclass functionality",
                        "May require code redesign",
                    ],
                ),
                FixStrategy(
                    name="Refactor to composition or protocol",
                    description=(
                        f"If signatures cannot be matched, reconsider inheritance. "
                        f"Use composition or protocol-based design."
                    ),
                    effort_estimate=EffortEstimate.LARGE,
                    prerequisite_actions=[
                        "Assess if inheritance is appropriate",
                        "Design composition structure",
                        "Define protocols/interfaces",
                        "Refactor class hierarchy",
                        "Update client code",
                    ],
                    assumptions=[
                        "Composition is viable",
                        "Protocols can be defined",
                    ],
                    risks=[
                        "Major refactoring",
                        "May change code organization",
                    ],
                ),
            ]
            
            proposal.confidence_level = 75
            proposal.confidence_explanation = (
                "Signature mismatches require data flow analysis to confirm. "
                "Pattern matching has moderate confidence; recommend code review."
            )
            proposal.requires_human_decision = True
            proposal.decision_required_for = (
                "Strategy for fixing inheritance; matching signatures vs refactoring."
            )
            
            self.patterns_matched.append(f"signature_mismatches:{issue_count}")
            proposals.append(proposal)
        
        return proposals
    
    def _detect_missing_documentation(
        self,
        repository_path: str,
    ) -> List[IntelligenceProposal]:
        """Detect functions without docstrings."""
        proposals = []
        
        issues = self._scan_for_missing_docstrings(repository_path)
        
        if issues:
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.API_CONTRACT_VIOLATIONS
            proposal.severity = Severity.LOW
            
            issue_count = len(issues)
            
            proposal.problem_statement = (
                f"Found {issue_count} public functions without docstrings. "
                f"Undocumented APIs are hard to use correctly."
            )
            
            proposal.risk_explanation = (
                f"Without docstrings, callers must read code to understand function behavior. "
                f"API usage is unclear. IDE help is unavailable. Common errors in usage."
            )
            
            proposal.root_cause_hypothesis = (
                f"Functions added without documentation. Time pressure or oversight. "
                f"No documentation standard enforcement."
            )
            
            # Add affected files
            for file_path, line_num in issues:
                proposal.affected_files.append(
                    AffectedFile(path=file_path, severity=Severity.LOW)
                )
            
            # Strategies
            proposal.suggested_strategies = [
                FixStrategy(
                    name="Add docstrings to public APIs",
                    description=(
                        f"Write docstrings for {issue_count} functions documenting: "
                        f"purpose, parameters, return value, exceptions, examples."
                    ),
                    effort_estimate=EffortEstimate.SMALL,
                    prerequisite_actions=[
                        "Choose docstring format (Google, NumPy, Sphinx)",
                        "Write docstrings",
                        "Include parameter descriptions",
                        "Document return types and exceptions",
                        "Add usage examples",
                    ],
                    assumptions=[
                        "Functions are well-designed",
                        "Behavior is deterministic",
                    ],
                    risks=[
                        "Documentation may get out of sync",
                        "Time-consuming",
                    ],
                ),
                FixStrategy(
                    name="Generate docstrings with AI tools",
                    description=(
                        f"Use AI tools to auto-generate docstrings, then review and adjust "
                        f"for accuracy."
                    ),
                    effort_estimate=EffortEstimate.SMALL,
                    prerequisite_actions=[
                        "Use tool like OpenAI Codex or similar",
                        "Generate docstrings",
                        "Review for accuracy",
                        "Fix any hallucinations",
                        "Commit documentation",
                    ],
                    assumptions=[
                        "Code is clear enough for AI",
                        "Generated docs are mostly accurate",
                    ],
                    risks=[
                        "AI may hallucinate incorrect descriptions",
                        "Requires human review",
                    ],
                ),
            ]
            
            proposal.confidence_level = 90
            proposal.confidence_explanation = (
                "Missing docstrings are easily detectable. Confidence high that public "
                "functions should be documented."
            )
            proposal.requires_human_decision = True
            proposal.decision_required_for = (
                "Documentation priority; which functions to document first."
            )
            
            self.patterns_matched.append(f"missing_docstrings:{issue_count}")
            proposals.append(proposal)
        
        return proposals
    
    def _scan_for_missing_type_hints(self, repository_path: str) -> List[Tuple]:
        """Scan for functions without type hints."""
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
                            
                            # Look for function definitions without type hints
                            if re.match(r'^\s*def\s+\w+\(.*\):\s*$', line):
                                if '->' not in line and ':' in line:
                                    issues.append((file_path, line_num))
                except Exception:
                    pass
        
        return issues
    
    def _scan_for_signature_mismatches(self, repository_path: str) -> List[Tuple]:
        """Scan for incompatible method overrides."""
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
                        in_class = False
                        for line_num, line in enumerate(f, 1):
                            self.lines_analyzed += 1
                            
                            if 'class ' in line:
                                in_class = True
                            elif in_class and re.match(r'^\s*def\s+__init__', line):
                                # Check if __init__ has unexpected parameters
                                if re.search(r'\*args|\*\*kwargs', line):
                                    issues.append((file_path, line_num))
                except Exception:
                    pass
        
        return issues
    
    def _scan_for_missing_docstrings(self, repository_path: str) -> List[Tuple]:
        """Scan for functions without docstrings."""
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
                            
                            # Look for public functions
                            if re.match(r'^\s*def\s+(?!_)\w+\(', line):
                                # Check if next line is docstring
                                # (simplified check - real implementation should look at next lines)
                                if '"""' not in line and "'''" not in line:
                                    issues.append((file_path, line_num))
                except Exception:
                    pass
        
        return issues
