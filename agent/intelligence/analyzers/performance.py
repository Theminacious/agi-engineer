"""
Performance anti-patterns analyzer.

Detects N+1 queries, unbounded growth, blocking I/O, and other performance issues.
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


class PerformanceAnalyzer(BaseAnalyzer):
    """Detect performance anti-patterns."""
    
    @property
    def bug_class(self) -> BugClass:
        return BugClass.PERFORMANCE_ANTI_PATTERNS
    
    # Patterns for performance issues
    PERFORMANCE_PATTERNS = {
        'nplus1': r'for\s+\w+\s+in\s+\w+.*:.*(?:\.query|\.filter|\.get|\.all)',
        'unbounded_loop': r'while\s+(True|1)',
        'blocking_io': r'\.read\(\)|\.readline\(\)|\.readlines\(\)|open\(',
        'sleep_in_loop': r'for\s+\w+.*:.*time\.sleep',
        'recursive_query': r'def\s+\w+.*:.*(?:\.query|\.get).*return\s+\w+',
    }
    
    def analyze(
        self,
        repository_path: str,
        repository_url: str,
        branch: str = "main",
    ) -> List[IntelligenceProposal]:
        """Analyze repository for performance issues."""
        self.start_timing()
        self._reset_metrics()
        
        proposals = []
        
        # 1. Detect N+1 queries
        nplus1 = self._detect_nplus1_queries(repository_path)
        proposals.extend(nplus1)
        
        # 2. Detect unbounded loops
        unbounded = self._detect_unbounded_loops(repository_path)
        proposals.extend(unbounded)
        
        # 3. Detect blocking I/O in hot paths
        blocking = self._detect_blocking_io(repository_path)
        proposals.extend(blocking)
        
        # Finalize all proposals
        finalized = []
        for proposal in proposals:
            proposal.repository_url = repository_url
            proposal.branch = branch
            finalized.append(self._finalize_proposal(proposal))
        
        return finalized
    
    def _detect_nplus1_queries(
        self,
        repository_path: str,
    ) -> List[IntelligenceProposal]:
        """Detect N+1 query patterns."""
        proposals = []
        
        issues = self._scan_for_nplus1(repository_path)
        
        if issues:
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.PERFORMANCE_ANTI_PATTERNS
            proposal.severity = Severity.HIGH
            
            issue_count = len(issues)
            
            proposal.problem_statement = (
                f"Found {issue_count} potential N+1 query patterns. "
                f"Queries executed in loops can cause exponential database traffic."
            )
            
            proposal.risk_explanation = (
                f"N+1 queries execute one query to fetch N records, then N additional queries "
                f"to fetch related data. Results in O(N) database calls instead of O(1). "
                f"Causes: slow page loads, database overload, timeout errors, poor user experience."
            )
            
            proposal.root_cause_hypothesis = (
                f"Eager loading not configured; relationships fetched lazily inside loops. "
                f"This is a common pattern in ORMs like SQLAlchemy and Django."
            )
            
            # Add affected files
            for file_path, line_num in issues:
                proposal.affected_files.append(
                    AffectedFile(path=file_path, severity=Severity.HIGH)
                )
            
            # Strategies
            proposal.suggested_strategies = [
                FixStrategy(
                    name="Use eager loading",
                    description=(
                        f"Configure eager loading via prefetch_related() (Django) or "
                        f"joinedload() (SQLAlchemy) to fetch related data in a single query."
                    ),
                    effort_estimate=EffortEstimate.SMALL,
                    prerequisite_actions=[
                        "Identify the ORM being used",
                        "Audit all N+1 patterns",
                        "Apply eager loading configuration",
                        "Measure improvement with profiling",
                        "Test query performance",
                    ],
                    assumptions=[
                        "ORM supports eager loading",
                        "Relationships are well-defined",
                    ],
                    risks=[
                        "May fetch unnecessary data",
                        "Can cause memory issues with large result sets",
                        "May introduce SQL join complexity",
                    ],
                ),
                FixStrategy(
                    name="Refactor to use select_related or joins",
                    description=(
                        f"Restructure queries to use single JOIN or select_related() "
                        f"to fetch all needed data in one query."
                    ),
                    effort_estimate=EffortEstimate.MEDIUM,
                    prerequisite_actions=[
                        "Understand relationship structure",
                        "Design optimal query strategy",
                        "Refactor all affected queries",
                        "Add query profiling",
                        "Benchmark improvements",
                    ],
                    assumptions=[
                        "Join is semantically correct",
                        "Result structure can accommodate joined data",
                    ],
                    risks=[
                        "May change query semantics",
                        "Can affect pagination logic",
                        "Requires database schema understanding",
                    ],
                ),
            ]
            
            proposal.confidence_level = 70
            proposal.confidence_explanation = (
                f"Pattern matching detects loops with queries, but requires code flow "
                f"analysis to confirm N+1. Recommend profiling to verify."
            )
            proposal.requires_human_decision = True
            proposal.decision_required_for = (
                "Eager loading strategy; requires understanding of data flow and ORM."
            )
            
            self.patterns_matched.append(f"nplus1_queries:{issue_count}")
            proposals.append(proposal)
        
        return proposals
    
    def _detect_unbounded_loops(
        self,
        repository_path: str,
    ) -> List[IntelligenceProposal]:
        """Detect unbounded loops."""
        proposals = []
        
        issues = self._scan_for_unbounded_loops(repository_path)
        
        if issues:
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.PERFORMANCE_ANTI_PATTERNS
            proposal.severity = Severity.MEDIUM
            
            issue_count = len(issues)
            
            proposal.problem_statement = (
                f"Found {issue_count} unbounded loops (while True). "
                f"Can cause infinite loops or high CPU usage if not properly controlled."
            )
            
            proposal.risk_explanation = (
                f"Unbounded loops without proper exit conditions risk infinite loops, "
                f"high CPU usage, memory leaks, and denial of service. "
                f"Must verify exit conditions are present and reachable."
            )
            
            proposal.root_cause_hypothesis = (
                f"Loop control flow is complex or relies on external conditions "
                f"that may not be met."
            )
            
            # Add affected files
            for file_path, line_num in issues:
                proposal.affected_files.append(
                    AffectedFile(path=file_path, severity=Severity.MEDIUM)
                )
            
            # Strategies
            proposal.suggested_strategies = [
                FixStrategy(
                    name="Add explicit exit conditions",
                    description=(
                        f"Add timeout, max iteration count, or explicit break conditions "
                        f"to all unbounded loops."
                    ),
                    effort_estimate=EffortEstimate.SMALL,
                    prerequisite_actions=[
                        "Review each unbounded loop",
                        "Identify intended exit condition",
                        "Add timeout or iteration limit",
                        "Test exit paths",
                    ],
                    assumptions=[
                        "Safe exit condition exists",
                        "Timeout is appropriate for use case",
                    ],
                    risks=[
                        "May prematurely exit if timeout too short",
                        "Requires careful testing",
                    ],
                ),
                FixStrategy(
                    name="Convert to for loop or generator",
                    description=(
                        f"Replace unbounded while loops with for loops over "
                        f"explicit iterables or generators with known bounds."
                    ),
                    effort_estimate=EffortEstimate.SMALL,
                    prerequisite_actions=[
                        "Understand loop iteration pattern",
                        "Design replacement loop structure",
                        "Refactor to for loop or generator",
                        "Test behavior",
                    ],
                    assumptions=[
                        "Iteration bounds can be determined",
                        "For loop semantics match while loop",
                    ],
                    risks=[
                        "May change behavior if not careful",
                        "Requires careful refactoring",
                    ],
                ),
            ]
            
            proposal.confidence_level = 90
            proposal.confidence_explanation = (
                "while True is easily detectable; confidence high that these are actual "
                "unbounded loops. However, exit conditions may be valid (e.g., daemon threads)."
            )
            proposal.requires_human_decision = True
            proposal.decision_required_for = (
                "Assess whether unbounded loops are intentional (e.g., servers, daemons)."
            )
            
            self.patterns_matched.append(f"unbounded_loops:{issue_count}")
            proposals.append(proposal)
        
        return proposals
    
    def _detect_blocking_io(
        self,
        repository_path: str,
    ) -> List[IntelligenceProposal]:
        """Detect blocking I/O in performance-critical code."""
        proposals = []
        
        issues = self._scan_for_blocking_io(repository_path)
        
        if issues:
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.PERFORMANCE_ANTI_PATTERNS
            proposal.severity = Severity.MEDIUM
            
            issue_count = len(issues)
            
            proposal.problem_statement = (
                f"Found {issue_count} blocking I/O operations. "
                f"Can cause thread blocking, slow responses, or reduced throughput."
            )
            
            proposal.risk_explanation = (
                f"Blocking I/O (file reads, network calls, database queries) without "
                f"proper timeout or async handling can block entire thread pools, "
                f"reduce application throughput, and cause cascading failures."
            )
            
            proposal.root_cause_hypothesis = (
                f"Code uses synchronous I/O without considering performance impact. "
                f"May be appropriate for batch jobs but problematic for request handlers."
            )
            
            # Add affected files
            for file_path, line_num in issues:
                proposal.affected_files.append(
                    AffectedFile(path=file_path, severity=Severity.MEDIUM)
                )
            
            # Strategies
            proposal.suggested_strategies = [
                FixStrategy(
                    name="Use async/await patterns",
                    description=(
                        f"Convert blocking I/O to async/await for {issue_count} locations "
                        f"using asyncio, aiohttp, or async ORM."
                    ),
                    effort_estimate=EffortEstimate.LARGE,
                    prerequisite_actions=[
                        "Choose async framework",
                        "Refactor to async/await",
                        "Add timeout handling",
                        "Test concurrent behavior",
                        "Measure improvement",
                    ],
                    assumptions=[
                        "Async is compatible with application design",
                        "Dependencies support async",
                    ],
                    risks=[
                        "Significant refactoring required",
                        "Async introduces complexity",
                        "May break existing synchronous code",
                    ],
                ),
                FixStrategy(
                    name="Add timeouts and thread pooling",
                    description=(
                        f"Add timeout parameters to all I/O operations and use thread "
                        f"pools or process pools to limit blocking impact."
                    ),
                    effort_estimate=EffortEstimate.MEDIUM,
                    prerequisite_actions=[
                        "Identify appropriate timeout values",
                        "Add timeout to all I/O calls",
                        "Configure thread pool size",
                        "Implement proper error handling",
                        "Test under load",
                    ],
                    assumptions=[
                        "Timeout values are appropriate",
                        "Thread pool is large enough",
                    ],
                    risks=[
                        "May introduce thread contention",
                        "Timeout errors require handling",
                    ],
                ),
            ]
            
            proposal.confidence_level = 80
            proposal.confidence_explanation = (
                "Blocking I/O patterns are detectable; however, context matters "
                "(batch jobs may be fine with blocking I/O)."
            )
            proposal.requires_human_decision = True
            proposal.decision_required_for = (
                "Assess whether code path needs async; depends on performance requirements."
            )
            
            self.patterns_matched.append(f"blocking_io:{issue_count}")
            proposals.append(proposal)
        
        return proposals
    
    def _scan_for_nplus1(self, repository_path: str) -> List[Tuple]:
        """Scan for N+1 query patterns."""
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
                            
                            # Look for loop followed by query
                            if re.search(r'for\s+\w+\s+in', line):
                                # Check next few lines for database query
                                if re.search(
                                    r'\.query\(|\.filter\(|\.get\(|\.all\(|db\.session',
                                    line
                                ):
                                    issues.append((file_path, line_num))
                except Exception:
                    pass
        
        return issues
    
    def _scan_for_unbounded_loops(self, repository_path: str) -> List[Tuple]:
        """Scan for unbounded loops."""
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
                            
                            if re.search(r'while\s+(True|1)\s*:', line):
                                issues.append((file_path, line_num))
                except Exception:
                    pass
        
        return issues
    
    def _scan_for_blocking_io(self, repository_path: str) -> List[Tuple]:
        """Scan for blocking I/O."""
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
                            
                            if re.search(r'\.read\(|\.readlines\(|open\(', line):
                                issues.append((file_path, line_num))
                except Exception:
                    pass
        
        return issues
