"""
God objects/services analyzer.

Detects classes and services with too many responsibilities.
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


class GodObjectsAnalyzer(BaseAnalyzer):
    """Detect god objects and god services (single responsibility principle violations)."""
    
    @property
    def bug_class(self) -> BugClass:
        return BugClass.GOD_OBJECTS
    
    def analyze(
        self,
        repository_path: str,
        repository_url: str,
        branch: str = "main",
    ) -> List[IntelligenceProposal]:
        """Analyze repository for god objects/services."""
        self.start_timing()
        self._reset_metrics()
        
        proposals = []
        
        # Detect classes/services with excessive methods
        god_objects = self._detect_god_objects(repository_path)
        
        for obj_info in god_objects:
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.GOD_OBJECTS
            proposal.repository_url = repository_url
            proposal.branch = branch
            
            file_path, class_name, method_count, line_count = obj_info
            
            proposal.problem_statement = (
                f"God object detected: {class_name} has {method_count} public methods "
                f"and {line_count} lines of code. Too many responsibilities."
            )
            
            proposal.severity = (
                Severity.CRITICAL if method_count > 50 else
                Severity.HIGH if method_count > 30 else
                Severity.MEDIUM
            )
            
            proposal.risk_explanation = (
                f"Classes with {method_count} methods are expensive to test, "
                f"difficult to maintain, and likely to change frequently. "
                f"High cognitive load, increased bug risk."
            )
            
            proposal.root_cause_hypothesis = (
                f"{class_name} accumulated responsibilities over time. "
                f"No clear separation of concerns; multiple reasons to change."
            )
            
            proposal.affected_files.append(
                AffectedFile(
                    path=file_path,
                    severity=proposal.severity,
                )
            )
            
            # Strategies
            proposal.suggested_strategies = [
                FixStrategy(
                    name="Split by concern",
                    description=(
                        f"Analyze {class_name}'s methods and split into 2-3 focused classes, "
                        f"each with single responsibility."
                    ),
                    effort_estimate=EffortEstimate.LARGE,
                    prerequisite_actions=[
                        "Map methods to concerns/domains",
                        "Design new class structure",
                        "Create new classes",
                        "Move methods to appropriate classes",
                        "Update all call sites",
                    ],
                    assumptions=[
                        "Clear concerns can be identified",
                        "No shared mutable state between concerns",
                        "Does not create circular dependencies",
                    ],
                    risks=[
                        "May expose previously hidden coupling",
                        "Requires comprehensive refactoring",
                        "High risk of introducing bugs without thorough testing",
                    ],
                ),
                FixStrategy(
                    name="Extract behavior into policies",
                    description=(
                        f"Use composition pattern to extract complex behaviors "
                        f"into policy objects, reducing {class_name} methods."
                    ),
                    effort_estimate=EffortEstimate.MEDIUM,
                    prerequisite_actions=[
                        "Identify behavior clusters",
                        "Design policy classes",
                        "Extract behavior into policies",
                        "Test policy integration",
                    ],
                    assumptions=[
                        "Behaviors are extractable as policies",
                        "Supports composition pattern in language",
                    ],
                    risks=[
                        "May add indirection",
                        "Policies must be cohesive",
                    ],
                ),
                FixStrategy(
                    name="Use facade pattern selectively",
                    description=(
                        f"Keep {class_name} as simplified facade while extracting "
                        f"specialized implementations behind it. Clients use facade only."
                    ),
                    effort_estimate=EffortEstimate.SMALL,
                    prerequisite_actions=[
                        "Identify core vs specialized methods",
                        "Extract specialized code",
                        "Create simplified facade",
                        "Update public interface",
                    ],
                    assumptions=[
                        "Clear facade interface can be defined",
                        "Clients only use facade, not internal details",
                    ],
                    risks=[
                        "Hides complexity; still present internally",
                        "Does not solve testing difficulty",
                    ],
                ),
            ]
            
            proposal.confidence_level = 90
            proposal.confidence_explanation = (
                f"Method count ({method_count}) is objectively measurable; "
                f"heuristic threshold may have false positives in some domains."
            )
            
            self.patterns_matched.append(f"god_object:{class_name}:{method_count}_methods")
            proposals.append(self._finalize_proposal(proposal))
        
        return proposals
    
    def _detect_god_objects(self, repository_path: str) -> List[Tuple]:
        """
        Detect classes with excessive methods/responsibilities.
        Returns: [(file_path, class_name, method_count, line_count), ...]
        """
        god_objects = []
        
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
                    
                    # Find classes and count methods
                    classes = self._extract_classes(file_path)
                    for class_name, method_count, line_range in classes:
                        # Heuristic: more than 20 public methods is suspicious
                        if method_count >= 20:
                            start_line, end_line = line_range
                            god_objects.append((
                                file_path,
                                class_name,
                                method_count,
                                end_line - start_line,
                            ))
                except Exception:
                    pass
        
        return god_objects
    
    def _extract_classes(self, file_path: str) -> List[Tuple]:
        """
        Extract class definitions and method counts.
        Returns: [(class_name, method_count, (start_line, end_line)), ...]
        """
        classes = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            current_class = None
            class_start = 0
            method_count = 0
            indent_level = 0
            
            for line_num, line in enumerate(lines):
                stripped = line.strip()
                
                # Detect class definition
                if stripped.startswith('class '):
                    # Save previous class
                    if current_class:
                        classes.append((
                            current_class,
                            method_count,
                            (class_start, line_num),
                        ))
                    
                    # Parse new class
                    match = re.match(r'class\s+(\w+)', stripped)
                    if match:
                        current_class = match.group(1)
                        class_start = line_num
                        method_count = 0
                        indent_level = len(line) - len(line.lstrip())
                
                # Count methods (within class)
                elif current_class and stripped.startswith('def '):
                    current_indent = len(line) - len(line.lstrip())
                    # Only count if indented under class
                    if current_indent > indent_level:
                        # Count public methods (not _private or __dunder)
                        match = re.match(r'def\s+([a-zA-Z_]\w*)', stripped)
                        if match and not match.group(1).startswith('_'):
                            method_count += 1
                
                # Detect end of class (dedent to class level or module level)
                elif current_class and stripped and not stripped.startswith('#'):
                    current_indent = len(line) - len(line.lstrip())
                    if current_indent <= indent_level and not stripped.startswith('def'):
                        # Class has ended
                        classes.append((
                            current_class,
                            method_count,
                            (class_start, line_num),
                        ))
                        current_class = None
            
            # Don't forget the last class
            if current_class:
                classes.append((
                    current_class,
                    method_count,
                    (class_start, len(lines)),
                ))
        
        except Exception:
            pass
        
        return classes
