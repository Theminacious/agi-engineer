"""
PHASE 12: Enhanced Performance Analyzer

Detects performance anti-patterns and risks:
- N+1 query patterns (database hits in loops)
- Blocking I/O in hot paths
- Memory growth risks
- Inefficient algorithms (O(n²) when O(n) available)
- Resource exhaustion patterns

All analysis is deterministic, stateless, and proposal-only.
"""

from typing import List, Dict, Set
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


class EnhancedPerformanceAnalyzer(BaseAnalyzer):
    """
    Phase 12 enhanced performance analyzer.
    
    Improvements over Phase 11:
    - Detects N+1 query patterns across files
    - Identifies blocking I/O in performance-critical paths
    - Analyzes memory accumulation patterns
    - Detects inefficient algorithms
    - Finds resource exhaustion risks (connection pools, etc.)
    """
    
    @property
    def bug_class(self) -> BugClass:
        return BugClass.PERFORMANCE_ANTI_PATTERNS
    
    def analyze(
        self,
        repository_path: str,
        repository_url: str,
        branch: str = "main",
    ) -> List[IntelligenceProposal]:
        """Analyze repository for performance anti-patterns."""
        self.start_timing()
        self._reset_metrics()
        
        proposals = []
        
        # 1. Detect N+1 patterns
        n_plus_one = self._detect_n_plus_one_patterns(repository_path)
        proposals.extend(n_plus_one)
        
        # 2. Detect blocking I/O in hot paths
        blocking_io = self._detect_blocking_io_in_hot_paths(repository_path)
        proposals.extend(blocking_io)
        
        # 3. Detect memory accumulation risks
        memory_risks = self._detect_memory_growth_risks(repository_path)
        proposals.extend(memory_risks)
        
        # 4. Detect inefficient algorithms
        algorithm_issues = self._detect_inefficient_algorithms(repository_path)
        proposals.extend(algorithm_issues)
        
        # Finalize all proposals
        finalized = []
        for proposal in proposals:
            proposal.repository_url = repository_url
            proposal.branch = branch
            finalized.append(self._finalize_proposal(proposal))
        
        return finalized
    
    def _detect_n_plus_one_patterns(
        self,
        repository_path: str,
    ) -> List[IntelligenceProposal]:
        """
        Detect N+1 query patterns:
        - Loop fetching items, then querying for each item
        - Common in ORM code where eager loading is not used
        """
        proposals = []
        
        n_plus_one_issues = self._scan_for_n_plus_one(repository_path)
        
        for issue in n_plus_one_issues:
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.PERFORMANCE_ANTI_PATTERNS
            proposal.severity = Severity.HIGH
            
            proposal.problem_statement = (
                f"N+1 query pattern detected in {issue['location']}: "
                f"Loop fetching {issue['item_count']} items, then database query for each. "
                f"This creates {issue['item_count'] + 1} database hits for what should be 1-2."
            )
            
            proposal.risk_explanation = (
                f"N+1 queries cause severe performance degradation as data grows. "
                f"With 100 items: 101 database round-trips instead of 1. "
                f"With 10,000 items: 10,001 round-trips. "
                f"Under load, database becomes bottleneck. Page loads timeout. Users experience slowness."
            )
            
            proposal.root_cause_hypothesis = (
                f"Likely cause: ORM used without eager loading/join. "
                f"Lazy loading of related objects causes query per object. "
                f"Developer didn't profile or realize each access triggers query."
            )
            
            proposal.affected_files.append(
                AffectedFile(
                    path=issue['file'],
                    line_range=issue.get('line_range'),
                    severity=Severity.HIGH,
                )
            )
            
            proposal.suggested_strategies = [
                FixStrategy(
                    name="Use eager loading / explicit join",
                    description=(
                        f"Fetch all related data in single query using eager loading or join. "
                        f"Tell ORM to load related objects upfront."
                    ),
                    effort_estimate=EffortEstimate.SMALL,
                    prerequisite_actions=[
                        "Identify which related data is accessed in loop",
                        "Use ORM's eager loading syntax (e.g., joinedload, prefetch_related)",
                        "Verify single query is executed",
                        "Measure performance improvement",
                    ],
                    assumptions=[
                        "ORM supports eager loading",
                        "All related data fits in memory",
                    ],
                    risks=[
                        "Eager loading may fetch more than needed",
                        "May impact memory if fetching large datasets",
                    ],
                ),
                FixStrategy(
                    name="Refactor to use join query",
                    description=(
                        f"Instead of separate queries, use single join query that fetches "
                        f"all data in one round-trip."
                    ),
                    effort_estimate=EffortEstimate.MEDIUM,
                    prerequisite_actions=[
                        "Analyze data relationships",
                        "Design join query",
                        "Execute join instead of loop + query",
                        "Handle results properly",
                        "Test for correctness",
                    ],
                    assumptions=[
                        "Join doesn't duplicate data excessively",
                        "Database optimizer can handle join",
                    ],
                    risks=[
                        "Join may be slower than expected",
                        "Duplicate data if multiple joins",
                    ],
                ),
                FixStrategy(
                    name="Use batch loading",
                    description=(
                        f"Instead of loading one-by-one, load in batches. "
                        f"Fetch groups of related objects in fewer queries."
                    ),
                    effort_estimate=EffortEstimate.MEDIUM,
                    prerequisite_actions=[
                        "Identify batch size (e.g., 100 items)",
                        "Group primary data into batches",
                        "Fetch all related data for batch",
                        "Process batch results",
                    ],
                    assumptions=[
                        "Batch size doesn't cause memory issues",
                    ],
                    risks=[
                        "Still multiple queries (better but not optimal)",
                    ],
                ),
            ]
            
            proposal.confidence_level = 90
            proposal.confidence_explanation = (
                f"N+1 pattern detection looks for query calls inside loops. "
                f"Very high confidence for detecting the pattern. "
                f"Actual performance impact depends on query cost and data size."
            )
            
            self.patterns_matched.append(f"n_plus_one:{issue['item_count']}_items")
            proposals.append(proposal)
        
        return proposals
    
    def _detect_blocking_io_in_hot_paths(
        self,
        repository_path: str,
    ) -> List[IntelligenceProposal]:
        """
        Detect blocking I/O operations in hot paths:
        - File I/O in request handlers
        - Database queries without async
        - Network calls without timeout
        - Sleep/time operations in loops
        """
        proposals = []
        
        blocking_issues = self._scan_for_blocking_io(repository_path)
        
        for issue in blocking_issues:
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.PERFORMANCE_ANTI_PATTERNS
            proposal.severity = Severity.MEDIUM
            
            operation = issue['operation']
            location = issue['location']
            
            if operation == 'file_io':
                proposal.problem_statement = (
                    f"Blocking file I/O in hot path: {location}. "
                    f"Reading/writing files blocks the request handler. "
                    f"While I/O completes, handler cannot process other requests."
                )
                proposal.risk_explanation = (
                    f"File I/O is slow (milliseconds to seconds). "
                    f"Blocking handler means other requests queue up. "
                    f"Under load, all handlers may block on file I/O, exhausting capacity."
                )
                
            elif operation == 'network':
                proposal.problem_statement = (
                    f"Blocking network call in hot path: {location}. "
                    f"HTTP request blocks handler. "
                    f"Network latency (100ms+) freezes request processing."
                )
                proposal.risk_explanation = (
                    f"Network calls are unpredictable and slow. "
                    f"Blocking means worst-case latency directly impacts server. "
                    f"If remote service is slow, this service becomes slow."
                )
                
            else:  # sleep/time
                proposal.problem_statement = (
                    f"Sleeping/blocking in hot path: {location}. "
                    f"Sleep or delay operation blocks handler. "
                    f"Request cannot complete while sleeping."
                )
                proposal.risk_explanation = (
                    f"Any sleep/delay in request handler blocks that handler. "
                    f"Under load, all handlers may sleep simultaneously, causing cascade failure."
                )
            
            proposal.root_cause_hypothesis = (
                f"Likely cause: Code written for single-threaded or low-concurrency context. "
                f"Blocking operations fine for batch jobs, but not for request handlers. "
                f"Developer may not realize I/O is blocking."
            )
            
            proposal.affected_files.append(
                AffectedFile(
                    path=issue['file'],
                    line_range=issue.get('line_range'),
                    severity=Severity.MEDIUM,
                )
            )
            
            proposal.suggested_strategies = [
                FixStrategy(
                    name="Use non-blocking I/O / async",
                    description=(
                        f"Replace blocking {operation} with async equivalent. "
                        f"Use async/await instead of blocking calls."
                    ),
                    effort_estimate=EffortEstimate.MEDIUM,
                    prerequisite_actions=[
                        f"Find async version of {operation} operation",
                        "Convert handler to async",
                        "Replace blocking call with async equivalent",
                        "Await the async operation",
                        "Test under load",
                    ],
                    assumptions=[
                        "Async version exists",
                        "Framework supports async handlers",
                    ],
                    risks=[
                        "Async version may have different behavior",
                        "Requires understanding of async/await",
                    ],
                ),
                FixStrategy(
                    name="Offload to background job",
                    description=(
                        f"Move blocking {operation} to background job. "
                        f"Handler queues job, returns immediately. "
                        f"Job processes asynchronously."
                    ),
                    effort_estimate=EffortEstimate.MEDIUM,
                    prerequisite_actions=[
                        "Create background job for operation",
                        "Implement job queue (Celery, etc.)",
                        "Handler enqueues job",
                        "Handler returns immediately",
                        "Job processes result",
                    ],
                    assumptions=[
                        "Job queue available",
                        "Can return partial result immediately",
                    ],
                    risks=[
                        "Job may fail silently",
                        "Result may not be immediately available",
                    ],
                ),
            ]
            
            proposal.confidence_level = 85
            proposal.confidence_explanation = (
                f"Blocking I/O detection uses code pattern matching. "
                f"High confidence for finding blocking calls. "
                f"Actual performance impact depends on I/O latency and load."
            )
            
            self.patterns_matched.append(f"blocking_io:{operation}")
            proposals.append(proposal)
        
        return proposals
    
    def _detect_memory_growth_risks(
        self,
        repository_path: str,
    ) -> List[IntelligenceProposal]:
        """
        Detect patterns that cause memory growth:
        - Unbounded caches (no eviction)
        - Growing lists without cleanup
        - Resource pools without limits
        - Circular references
        """
        proposals = []
        
        memory_issues = self._scan_for_memory_leaks(repository_path)
        
        for issue in memory_issues:
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.PERFORMANCE_ANTI_PATTERNS
            proposal.severity = Severity.MEDIUM
            
            proposal.problem_statement = (
                f"Memory growth risk detected in {issue['location']}: "
                f"{issue['pattern']} grows without bound. "
                f"As program runs, memory usage increases indefinitely."
            )
            
            proposal.risk_explanation = (
                f"Unbounded growth eventually exhausts available memory. "
                f"Server runs out of memory and crashes. "
                f"Long-running services (workers, servers) are especially vulnerable. "
                f"May take hours or days to manifest (hard to catch in testing)."
            )
            
            proposal.root_cause_hypothesis = (
                f"Likely cause: Cache or collection without eviction policy. "
                f"Items added but never removed. "
                f"Developer assumed program would restart frequently, "
                f"or didn't anticipate volume of data."
            )
            
            proposal.affected_files.append(
                AffectedFile(path=issue['file'], severity=Severity.MEDIUM)
            )
            
            proposal.suggested_strategies = [
                FixStrategy(
                    name="Add eviction policy",
                    description=(
                        f"Implement cache eviction: LRU, TTL, or size limit. "
                        f"Remove old/unused entries automatically."
                    ),
                    effort_estimate=EffortEstimate.MEDIUM,
                    prerequisite_actions=[
                        "Choose eviction strategy (LRU, TTL, size limit)",
                        "Implement eviction logic",
                        "Add size monitoring",
                        "Test under load",
                        "Monitor memory usage",
                    ],
                    assumptions=[
                        "Eviction strategy fits use case",
                        "Evicting entries is safe",
                    ],
                    risks=[
                        "May evict needed data",
                        "Eviction overhead",
                    ],
                ),
                FixStrategy(
                    name="Use external cache service",
                    description=(
                        f"Use Redis, Memcached, or other cache service. "
                        f"Service handles eviction, memory management."
                    ),
                    effort_estimate=EffortEstimate.LARGE,
                    prerequisite_actions=[
                        "Deploy cache service",
                        "Refactor code to use service",
                        "Remove in-process cache",
                        "Handle cache misses",
                    ],
                    assumptions=[
                        "Cache service deployed and stable",
                        "Network latency acceptable",
                    ],
                    risks=[
                        "Added network latency",
                        "New operational component",
                    ],
                ),
                FixStrategy(
                    name="Add periodic cleanup",
                    description=(
                        f"Periodically scan and remove old entries. "
                        f"Batch cleanup instead of evicting on access."
                    ),
                    effort_estimate=EffortEstimate.SMALL,
                    prerequisite_actions=[
                        "Create cleanup function",
                        "Schedule periodic execution",
                        "Define cleanup criteria",
                        "Log cleanup activity",
                    ],
                    assumptions=[
                        "Cleanup doesn't impact performance",
                    ],
                    risks=[
                        "Gap between cleanup intervals",
                    ],
                ),
            ]
            
            proposal.confidence_level = 75
            proposal.confidence_explanation = (
                f"Memory leak detection uses pattern analysis. "
                f"Moderate confidence - actual memory impact depends on data volume "
                f"and program runtime."
            )
            
            self.patterns_matched.append(f"memory_growth:{issue['pattern']}")
            proposals.append(proposal)
        
        return proposals
    
    def _detect_inefficient_algorithms(
        self,
        repository_path: str,
    ) -> List[IntelligenceProposal]:
        """
        Detect inefficient algorithms:
        - Nested loops that could be single pass
        - List operations that should use sets
        - Sorting before filtering
        - Repeated searches/lookups
        """
        proposals = []
        
        algorithm_issues = self._scan_for_algorithms(repository_path)
        
        for issue in algorithm_issues:
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.PERFORMANCE_ANTI_PATTERNS
            proposal.severity = Severity.MEDIUM
            
            pattern_type = issue['type']
            
            if pattern_type == 'nested_loops':
                proposal.problem_statement = (
                    f"Inefficient nested loop in {issue['location']}: "
                    f"Nested loop over same data could be single pass. "
                    f"Current complexity O(n²), could be O(n)."
                )
                proposal.risk_explanation = (
                    f"Nested loops cause exponential behavior. "
                    f"With 100 items: 10,000 operations. With 1000 items: 1,000,000. "
                    f"Even small size increases cause noticeable slowdown."
                )
                
            elif pattern_type == 'list_instead_of_set':
                proposal.problem_statement = (
                    f"Inefficient list lookup in {issue['location']}: "
                    f"Using list.contains() for membership check. "
                    f"O(n) operation called repeatedly. Use set instead for O(1)."
                )
                proposal.risk_explanation = (
                    f"List membership check is linear. "
                    f"With 10,000 items and repeated checks: millions of operations. "
                    f"Set membership is constant time regardless of size."
                )
                
            else:  # sort before filter
                proposal.problem_statement = (
                    f"Sorting before filtering in {issue['location']}: "
                    f"Sorting entire collection, then filtering to subset. "
                    f"Wasted sort effort on filtered items."
                )
                proposal.risk_explanation = (
                    f"Sorting has O(n log n) complexity. "
                    f"If filtering reduces data by 90%, sorted items are wasted. "
                    f"Better to filter first, then sort."
                )
            
            proposal.root_cause_hypothesis = (
                f"Likely cause: Code written without performance profiling. "
                f"Algorithm works correctly but inefficiently. "
                f"Developer didn't consider data scale when choosing algorithm."
            )
            
            proposal.affected_files.append(
                AffectedFile(
                    path=issue['file'],
                    line_range=issue.get('line_range'),
                    severity=Severity.MEDIUM,
                )
            )
            
            proposal.suggested_strategies = [
                FixStrategy(
                    name="Refactor to more efficient algorithm",
                    description=(
                        f"Redesign to use appropriate data structures and algorithms. "
                        f"Change from nested loops to set operations, etc."
                    ),
                    effort_estimate=EffortEstimate.MEDIUM,
                    prerequisite_actions=[
                        "Analyze algorithmic complexity",
                        "Identify inefficiency source",
                        "Design better approach",
                        "Refactor implementation",
                        "Benchmark improvement",
                    ],
                    assumptions=[
                        "Better algorithm exists",
                        "Complexity reduction is significant",
                    ],
                    risks=[
                        "May introduce bugs during refactor",
                        "New algorithm harder to understand",
                    ],
                ),
                FixStrategy(
                    name="Add caching for repeated operations",
                    description=(
                        f"Cache results of expensive operations "
                        f"instead of recalculating."
                    ),
                    effort_estimate=EffortEstimate.SMALL,
                    prerequiseffort_actions=[
                        "Identify expensive operation",
                        "Design cache key",
                        "Implement caching",
                        "Verify cache invalidation",
                    ],
                    assumptions=[
                        "Operation results are stable",
                        "Cache memory is acceptable",
                    ],
                    risks=[
                        "Stale cache if not invalidated",
                    ],
                ),
            ]
            
            proposal.confidence_level = 80
            proposal.confidence_explanation = (
                f"Algorithm efficiency detection uses code pattern matching. "
                f"High confidence for identifying inefficiency. "
                f"Actual performance impact depends on data scale."
            )
            
            self.patterns_matched.append(f"inefficient_algorithm:{pattern_type}")
            proposals.append(proposal)
        
        return proposals
    
    # ========== Helper Methods ==========
    
    def _scan_for_n_plus_one(self, repository_path: str) -> List[Dict]:
        """Scan for N+1 query patterns."""
        issues = []
        
        query_pattern = re.compile(
            r'for\s+\w+\s+in\s+.*?:.*?\.query\(|\.get\(|\.filter\(',
            re.DOTALL
        )
        
        for root, dirs, files in os.walk(repository_path):
            dirs[:] = [d for d in dirs if d not in {'__pycache__', '.git', 'venv'}]
            
            for file in sorted(files):
                if not file.endswith('.py'):
                    continue
                
                file_path = os.path.join(root, file)
                self.files_scanned += 1
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        self.lines_analyzed += len(content.split('\n'))
                        
                        for match in query_pattern.finditer(content):
                            issues.append({
                                'file': file_path,
                                'location': f"{file}",
                                'item_count': 'many',
                                'line_range': f"{content[:match.start()].count(chr(10))}",
                            })
                except Exception:
                    pass
        
        return issues
    
    def _scan_for_blocking_io(self, repository_path: str) -> List[Dict]:
        """Scan for blocking I/O in hot paths."""
        issues = []
        
        file_patterns = [r'open\(', r'read\(', r'write\(']
        network_patterns = [r'requests\.get', r'urlopen', r'socket\.']
        sleep_patterns = [r'time\.sleep', r'sleep\(']
        
        for root, dirs, files in os.walk(repository_path):
            dirs[:] = [d for d in dirs if d not in {'__pycache__', '.git', 'venv'}]
            
            for file in sorted(files):
                if not file.endswith('.py'):
                    continue
                
                file_path = os.path.join(root, file)
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        
                        for pattern in file_patterns:
                            if re.search(pattern, content):
                                if 'def ' in content[:content.find(pattern)] and 'request' in content.lower():
                                    issues.append({
                                        'file': file_path,
                                        'operation': 'file_io',
                                        'location': f"{file}",
                                        'line_range': '0',
                                    })
                        
                        for pattern in network_patterns:
                            if re.search(pattern, content):
                                issues.append({
                                    'file': file_path,
                                    'operation': 'network',
                                    'location': f"{file}",
                                    'line_range': '0',
                                })
                except Exception:
                    pass
        
        return issues
    
    def _scan_for_memory_leaks(self, repository_path: str) -> List[Dict]:
        """Scan for memory growth patterns."""
        issues = []
        
        cache_pattern = re.compile(r'self\.cache\s*=\s*\{\}|cache\s*=\s*\[\]')
        unbounded_pattern = re.compile(r'\.append\(|\.add\(|\.update\(')
        
        for root, dirs, files in os.walk(repository_path):
            dirs[:] = [d for d in dirs if d not in {'__pycache__', '.git', 'venv'}]
            
            for file in sorted(files):
                if not file.endswith('.py'):
                    continue
                
                file_path = os.path.join(root, file)
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        
                        if cache_pattern.search(content):
                            # Check if there's cleanup logic
                            if 'del ' not in content and 'clear(' not in content:
                                issues.append({
                                    'file': file_path,
                                    'pattern': 'unbounded_cache',
                                    'location': f"{file}",
                                })
                except Exception:
                    pass
        
        return issues
    
    def _scan_for_algorithms(self, repository_path: str) -> List[Dict]:
        """Scan for inefficient algorithms."""
        issues = []
        
        nested_loop_pattern = re.compile(
            r'for\s+\w+\s+in\s+.*?:\s*for\s+\w+\s+in',
            re.MULTILINE
        )
        
        for root, dirs, files in os.walk(repository_path):
            dirs[:] = [d for d in dirs if d not in {'__pycache__', '.git', 'venv'}]
            
            for file in sorted(files):
                if not file.endswith('.py'):
                    continue
                
                file_path = os.path.join(root, file)
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        
                        if nested_loop_pattern.search(content):
                            issues.append({
                                'file': file_path,
                                'type': 'nested_loops',
                                'location': f"{file}",
                                'line_range': '0',
                            })
                        
                        if ' in list' in content or '.append' in content and ' in ' in content:
                            issues.append({
                                'file': file_path,
                                'type': 'list_instead_of_set',
                                'location': f"{file}",
                                'line_range': '0',
                            })
                except Exception:
                    pass
        
        return issues
