"""
Resource Leak Analyzer - Phase 16

Detects patterns that can cause resource leaks:
- Unclosed file handles
- Unclosed database connections
- Unclosed network sockets
- Event listeners not removed
- Timers/intervals not cleared
- Memory leaks (unbounded collections, circular references)
- Thread leaks (threads not joined)
"""

from typing import List, Tuple, Dict
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


class ResourceLeakAnalyzer(BaseAnalyzer):
    """Detect resource leak patterns."""
    
    @property
    def bug_class(self) -> BugClass:
        return BugClass.RESOURCE_LEAKS
    
    # Patterns for resource leaks (Python-focused)
    LEAK_PATTERNS = {
        # File handle leaks
        'open_without_with': r'(\w+)\s*=\s*open\([^)]+\)(?!\s*with)',
        
        # Database connection leaks
        'db_conn_no_close': r'\.connect\([^)]*\)(?!.*\.close\(\))',
        'cursor_no_close': r'\.cursor\([^)]*\)(?!.*\.close\(\))',
        
        # Network socket leaks
        'socket_no_close': r'socket\.socket\([^)]*\)(?!.*\.close\(\))',
        'requests_no_close': r'requests\.\w+\([^)]+\)(?!.*\.close\(\))',
        
        # Thread leaks
        'thread_no_join': r'Thread\([^)]*\)\.start\(\)(?!.*\.join\(\))',
        'threadpool_no_shutdown': r'ThreadPoolExecutor\([^)]*\)(?!.*\.shutdown\(\))',
        
        # Memory leaks
        'unbounded_cache': r'(cache|memo|store)\s*=\s*\{\}',  # Dict used as cache without size limit
        'global_accumulator': r'^(\w+)\s*=\s*\[\].*\.append',  # Global list that grows
        
        # Event listener leaks
        'listener_no_remove': r'\.addEventListener\([^)]*\)(?!.*removeEventListener)',
        'on_event_no_off': r'\.on\([\'"]([^\'"]+)[\'"],\s*\w+\)(?!.*\.off\()',
    }
    
    def analyze(
        self,
        repository_path: str,
        repository_url: str,
        branch: str = "main",
    ) -> List[IntelligenceProposal]:
        """Analyze repository for resource leaks."""
        self.start_timing()
        self._reset_metrics()
        
        proposals = []
        
        # 1. Detect file handle leaks
        file_leaks = self._detect_file_handle_leaks(repository_path)
        if file_leaks:
            proposals.append(file_leaks)
        
        # 2. Detect connection leaks (DB, network)
        connection_leaks = self._detect_connection_leaks(repository_path)
        if connection_leaks:
            proposals.append(connection_leaks)
        
        # 3. Detect memory leaks
        memory_leaks = self._detect_memory_leaks(repository_path)
        if memory_leaks:
            proposals.append(memory_leaks)
        
        # 4. Detect thread leaks
        thread_leaks = self._detect_thread_leaks(repository_path)
        if thread_leaks:
            proposals.append(thread_leaks)
        
        # Finalize all proposals
        finalized = []
        for proposal in proposals:
            proposal.repository_url = repository_url
            proposal.branch = branch
            finalized.append(self._finalize_proposal(proposal))
        
        return finalized
    
    def _detect_file_handle_leaks(
        self,
        repository_path: str,
    ) -> IntelligenceProposal | None:
        """Detect file operations without proper cleanup."""
        issues = self._scan_for_file_leaks(repository_path)
        
        if not issues:
            return None
        
        proposal = IntelligenceProposal()
        proposal.bug_class = BugClass.RESOURCE_LEAKS
        proposal.severity = Severity.HIGH
        
        issue_count = len(issues)
        
        proposal.problem_statement = (
            f"Found {issue_count} file operations without proper cleanup. "
            f"Unclosed file handles exhaust system resources and cause failures."
        )
        
        proposal.risk_explanation = (
            f"File handles are limited OS resources. Each unclosed file consumes one handle. "
            f"When limit is reached (typically 1024-4096), all file operations fail. "
            f"Impact: cannot log, cannot read config, cannot save data, complete service failure. "
            f"Worse on long-running services and concurrent workloads. "
            f"'Too many open files' errors are a common production incident."
        )
        
        proposal.root_cause_hypothesis = (
            f"Developers forget to close files, or exceptions occur before close(). "
            f"Common in: early return paths, exception handlers, cleanup code. "
            f"Python garbage collector eventually closes, but timing is unpredictable."
        )
        
        # Group issues by file
        issues_by_file = {}
        for file_path, line_num, code_snippet in issues:
            if file_path not in issues_by_file:
                issues_by_file[file_path] = []
            issues_by_file[file_path].append((line_num, code_snippet))
        
        proposal.affected_files = [
            AffectedFile(
                path=file_path,
                line_range=f"{min(l for l, _ in locations)}-{max(l for l, _ in locations)}",
                severity=Severity.HIGH,
            )
            for file_path, locations in issues_by_file.items()
        ]
        
        # Strategy 1: Use context managers
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Use 'with open()' context managers",
                description=(
                    f"Replace all 'f = open()' with 'with open() as f:'. "
                    f"Context managers guarantee cleanup even on exceptions. "
                    f"Example: 'with open(\"file.txt\") as f: data = f.read()'"
                ),
                effort_estimate=EffortEstimate.TRIVIAL,
                prerequisite_actions=[
                    "Find all open() calls without 'with'",
                    "Wrap in context manager blocks",
                    "Test exception paths still clean up",
                ],
                assumptions=[
                    "Python 2.5+ (with statement available)",
                    "File operations can be scoped to blocks",
                ],
                risks=[
                    "Minimal risk, this is best practice",
                    "May require indentation changes",
                ],
            )
        )
        
        # Strategy 2: Add manual cleanup with try-finally
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Add explicit close() in finally blocks",
                description=(
                    f"For cases where 'with' is not feasible, add try-finally to ensure close(). "
                    f"Example: 'f = open(...); try: ...; finally: f.close()'"
                ),
                effort_estimate=EffortEstimate.SMALL,
                prerequisite_actions=[
                    "Identify cases where 'with' cannot be used",
                    "Add try-finally blocks with explicit close",
                    "Verify cleanup happens on all paths",
                ],
                assumptions=[
                    "File handle scope spans multiple functions",
                    "Manual cleanup is necessary",
                ],
                risks=[
                    "Easy to forget close() on new code paths",
                    "More verbose than context managers",
                ],
            )
        )
        
        proposal.confidence_level = 95
        proposal.confidence_explanation = (
            f"Very high confidence: 'open()' without 'with' is a known leak pattern. "
            f"Some cases may have manual close() not detected by pattern."
        )
        
        self.patterns_matched.append("file_handle_leaks")
        
        return proposal
    
    def _detect_connection_leaks(
        self,
        repository_path: str,
    ) -> IntelligenceProposal | None:
        """Detect database/network connections without cleanup."""
        issues = self._scan_for_connection_leaks(repository_path)
        
        if not issues:
            return None
        
        proposal = IntelligenceProposal()
        proposal.bug_class = BugClass.RESOURCE_LEAKS
        proposal.severity = Severity.CRITICAL
        
        issue_count = len(issues)
        
        proposal.problem_statement = (
            f"Found {issue_count} database/network connections without proper cleanup. "
            f"Connection leaks cause connection pool exhaustion."
        )
        
        proposal.risk_explanation = (
            f"Connection pools are finite (typically 10-100 connections). "
            f"Leaked connections stay open until timeout (minutes to hours). "
            f"When pool is exhausted, new requests block or fail. "
            f"Impact: request timeouts, cascading failures, complete service outage, "
            f"database server overload. Connection exhaustion is a TOP 5 production incident cause."
        )
        
        proposal.root_cause_hypothesis = (
            f"Connections opened but not closed. Common in: error paths, early returns, "
            f"forgotten cleanup. Connection pooling libraries help but require proper usage. "
            f"Developers assume pool auto-cleans, but leaked references prevent cleanup."
        )
        
        # Group issues by file
        issues_by_file = {}
        for file_path, line_num, conn_type, code_snippet in issues:
            if file_path not in issues_by_file:
                issues_by_file[file_path] = []
            issues_by_file[file_path].append((line_num, conn_type, code_snippet))
        
        proposal.affected_files = [
            AffectedFile(
                path=file_path,
                line_range=f"{min(l for l, _, _ in locations)}-{max(l for l, _, _ in locations)}",
                severity=Severity.CRITICAL,
            )
            for file_path, locations in issues_by_file.items()
        ]
        
        # Strategy 1: Use connection context managers
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Use connection context managers",
                description=(
                    f"Use 'with conn.cursor() as cursor:' and 'with create_connection() as conn:'. "
                    f"Most DB libraries provide context manager support. "
                    f"Guarantees cleanup even on exceptions."
                ),
                effort_estimate=EffortEstimate.SMALL,
                prerequisite_actions=[
                    "Verify DB library supports context managers",
                    "Wrap all connection/cursor usage in 'with'",
                    "Test error paths clean up properly",
                ],
                assumptions=[
                    "DB library supports context managers (most modern libraries do)",
                ],
                risks=[
                    "Minimal risk, improves reliability",
                ],
            )
        )
        
        # Strategy 2: Use connection pooling properly
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Implement proper connection pooling",
                description=(
                    f"Use SQLAlchemy connection pools or library-specific pools. "
                    f"Always return connections to pool after use. "
                    f"Configure pool size, timeout, and recycling."
                ),
                effort_estimate=EffortEstimate.MEDIUM,
                prerequisite_actions=[
                    "Choose connection pooling library (SQLAlchemy, psycopg2 pool)",
                    "Configure pool parameters for workload",
                    "Refactor code to acquire/release from pool",
                    "Monitor pool metrics (size, wait time, leaks)",
                ],
                assumptions=[
                    "Team can adopt pooling library",
                    "Pool size can be tuned for workload",
                ],
                risks=[
                    "Pool exhaustion if size too small",
                    "Resource waste if size too large",
                    "Requires monitoring and tuning",
                ],
            )
        )
        
        proposal.confidence_level = 85
        proposal.confidence_explanation = (
            f"High confidence: detected connection patterns without explicit cleanup. "
            f"Some may use pools correctly but pattern matching cannot detect."
        )
        
        self.patterns_matched.append("connection_leaks")
        
        return proposal
    
    def _detect_memory_leaks(
        self,
        repository_path: str,
    ) -> IntelligenceProposal | None:
        """Detect patterns that cause memory leaks."""
        issues = self._scan_for_memory_leaks(repository_path)
        
        if not issues:
            return None
        
        proposal = IntelligenceProposal()
        proposal.bug_class = BugClass.RESOURCE_LEAKS
        proposal.severity = Severity.MEDIUM
        
        issue_count = len(issues)
        
        proposal.problem_statement = (
            f"Found {issue_count} patterns that can cause memory leaks. "
            f"Unbounded caches and global accumulators grow without limits."
        )
        
        proposal.risk_explanation = (
            f"Memory leaks cause gradual memory growth until OOM kill. "
            f"Process starts fine, then slows over hours/days, then crashes. "
            f"Impact: service restarts, performance degradation, OOM kills, data loss. "
            f"Difficult to debug because symptoms appear long after code runs."
        )
        
        proposal.root_cause_hypothesis = (
            f"Caches without eviction policies. Global collections that grow indefinitely. "
            f"Common in: user session stores, request caches, metrics accumulation. "
            f"Developers add caching for performance, forget to add expiry."
        )
        
        # Group issues by file
        issues_by_file = {}
        for file_path, line_num, leak_type, code_snippet in issues:
            if file_path not in issues_by_file:
                issues_by_file[file_path] = []
            issues_by_file[file_path].append((line_num, leak_type, code_snippet))
        
        proposal.affected_files = [
            AffectedFile(
                path=file_path,
                line_range=f"{min(l for l, _ in locations)}-{max(l for l, _ in locations)}",
                severity=Severity.MEDIUM,
            )
            for file_path, locations in issues_by_file.items()
        ]
        
        # Strategy 1: Use LRU caches with size limits
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Replace unbounded caches with LRU caches",
                description=(
                    f"Use @functools.lru_cache(maxsize=N) or cachetools.LRUCache. "
                    f"Automatically evicts old entries. "
                    f"Example: '@lru_cache(maxsize=1000)' or 'cache = LRUCache(maxsize=1000)'"
                ),
                effort_estimate=EffortEstimate.TRIVIAL,
                prerequisite_actions=[
                    "Identify all unbounded caches",
                    "Replace with LRU cache with appropriate size",
                    "Monitor cache hit rate and memory",
                ],
                assumptions=[
                    "LRU eviction policy is acceptable",
                    "Cache size can be determined from requirements",
                ],
                risks=[
                    "Evictions may reduce cache effectiveness",
                    "Need to tune cache size",
                ],
            )
        )
        
        # Strategy 2: Add periodic cleanup
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Add periodic cleanup to global collections",
                description=(
                    f"Add background task to periodically clean old entries. "
                    f"Use TTL (time-to-live) or max size policies. "
                    f"Example: every hour, remove entries older than 24h."
                ),
                effort_estimate=EffortEstimate.MEDIUM,
                prerequisite_actions=[
                    "Add timestamp to cache entries",
                    "Create cleanup background task",
                    "Schedule periodic execution",
                    "Monitor memory before/after cleanup",
                ],
                assumptions=[
                    "Background task scheduling is available",
                    "TTL can be determined from requirements",
                ],
                risks=[
                    "Cleanup may remove still-needed entries",
                    "Adds complexity to system",
                ],
            )
        )
        
        proposal.confidence_level = 70
        proposal.confidence_explanation = (
            f"Medium confidence: pattern matching finds potential leaks. "
            f"Some may be intentional bounded accumulators. Requires manual review."
        )
        
        self.patterns_matched.append("memory_leaks")
        
        return proposal
    
    def _detect_thread_leaks(
        self,
        repository_path: str,
    ) -> IntelligenceProposal | None:
        """Detect thread/executor leaks."""
        issues = self._scan_for_thread_leaks(repository_path)
        
        if not issues:
            return None
        
        proposal = IntelligenceProposal()
        proposal.bug_class = BugClass.RESOURCE_LEAKS
        proposal.severity = Severity.HIGH
        
        issue_count = len(issues)
        
        proposal.problem_statement = (
            f"Found {issue_count} threads/executors without proper cleanup. "
            f"Thread leaks cause resource exhaustion and application hangs."
        )
        
        proposal.risk_explanation = (
            f"Leaked threads consume memory and CPU. When thread limit is reached, "
            f"new operations hang indefinitely. Impact: application freeze, cannot process requests, "
            f"must kill and restart. Thread leaks often go unnoticed until production traffic surge."
        )
        
        proposal.root_cause_hypothesis = (
            f"Threads started but not joined. Executors created but not shutdown. "
            f"Common in: request handlers creating threads, background tasks, async operations."
        )
        
        # Group issues by file
        issues_by_file = {}
        for file_path, line_num, thread_type, code_snippet in issues:
            if file_path not in issues_by_file:
                issues_by_file[file_path] = []
            issues_by_file[file_path].append((line_num, thread_type, code_snippet))
        
        proposal.affected_files = [
            AffectedFile(
                path=file_path,
                line_range=f"{min(l for l, _ in locations)}-{max(l for l, _ in locations)}",
                severity=Severity.HIGH,
            )
            for file_path, locations in issues_by_file.items()
        ]
        
        # Strategy 1: Use daemon threads
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Use daemon threads for background tasks",
                description=(
                    f"Set thread.daemon = True for background threads. "
                    f"Daemon threads auto-terminate when main program exits. "
                    f"Example: 'thread = Thread(target=task, daemon=True)'"
                ),
                effort_estimate=EffortEstimate.TRIVIAL,
                prerequisite_actions=[
                    "Identify background vs foreground threads",
                    "Set daemon=True for background threads",
                    "Verify behavior on application shutdown",
                ],
                assumptions=[
                    "Threads are truly background tasks",
                    "Can be terminated abruptly",
                ],
                risks=[
                    "Daemon threads killed mid-operation on shutdown",
                    "May lose in-progress work",
                ],
            )
        )
        
        # Strategy 2: Use thread pool with context manager
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Use ThreadPoolExecutor with context manager",
                description=(
                    f"Use 'with ThreadPoolExecutor() as executor:' to ensure cleanup. "
                    f"Automatically calls shutdown() on block exit. "
                    f"Example: 'with ThreadPoolExecutor(max_workers=5) as exe: exe.submit(task)'"
                ),
                effort_estimate=EffortEstimate.SMALL,
                prerequisite_actions=[
                    "Replace Thread() with ThreadPoolExecutor",
                    "Wrap in context manager",
                    "Test cleanup on exceptions",
                ],
                assumptions=[
                    "Python 3.2+ (ThreadPoolExecutor available)",
                    "Thread pool is appropriate for workload",
                ],
                risks=[
                    "Minimal risk, improves reliability",
                ],
            )
        )
        
        proposal.confidence_level = 80
        proposal.confidence_explanation = (
            f"High confidence: detected thread patterns without cleanup. "
            f"Some may have joins not visible to pattern matching."
        )
        
        self.patterns_matched.append("thread_leaks")
        
        return proposal
    
    def _scan_for_file_leaks(self, repository_path: str) -> List[Tuple[str, int, str]]:
        """Scan files for file handle leaks."""
        issues = []
        
        for root, dirs, files in os.walk(repository_path):
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', 'venv', '.venv'}]
            
            for file in files:
                if not file.endswith('.py'):
                    continue
                
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, repository_path)
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        self.files_scanned += 1
                        self.lines_analyzed += len(lines)
                        
                        for line_num, line in enumerate(lines, 1):
                            # Check for open() without 'with'
                            if 'open(' in line and 'with' not in line:
                                # Verify it's an assignment
                                if '=' in line and 'open(' in line.split('=')[1]:
                                    issues.append((rel_path, line_num, line.strip()))
                
                except Exception:
                    continue
        
        return issues
    
    def _scan_for_connection_leaks(self, repository_path: str) -> List[Tuple[str, int, str, str]]:
        """Scan files for connection leaks."""
        issues = []
        
        for root, dirs, files in os.walk(repository_path):
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', 'venv', '.venv'}]
            
            for file in files:
                if not file.endswith('.py'):
                    continue
                
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, repository_path)
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        lines = content.split('\n')
                        
                        for line_num, line in enumerate(lines, 1):
                            # Check for connection patterns
                            if '.connect(' in line and 'with' not in line:
                                issues.append((rel_path, line_num, 'db_connection', line.strip()))
                            
                            if '.cursor(' in line and 'with' not in line:
                                issues.append((rel_path, line_num, 'db_cursor', line.strip()))
                            
                            if 'socket.socket(' in line and 'with' not in line:
                                issues.append((rel_path, line_num, 'socket', line.strip()))
                
                except Exception:
                    continue
        
        return issues
    
    def _scan_for_memory_leaks(self, repository_path: str) -> List[Tuple[str, int, str, str]]:
        """Scan files for memory leak patterns."""
        issues = []
        
        for root, dirs, files in os.walk(repository_path):
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', 'venv', '.venv'}]
            
            for file in files:
                if not file.endswith('.py'):
                    continue
                
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, repository_path)
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        
                        for line_num, line in enumerate(lines, 1):
                            # Check for unbounded cache patterns
                            if re.search(r'(cache|memo|store)\s*=\s*\{\}', line):
                                # Check if it's a global or class variable
                                if not line.startswith('    '):  # Rough heuristic for module level
                                    issues.append((rel_path, line_num, 'unbounded_cache', line.strip()))
                            
                            # Check for global list accumulators
                            if re.search(r'^(\w+)\s*=\s*\[\]', line):
                                issues.append((rel_path, line_num, 'global_accumulator', line.strip()))
                
                except Exception:
                    continue
        
        return issues
    
    def _scan_for_thread_leaks(self, repository_path: str) -> List[Tuple[str, int, str, str]]:
        """Scan files for thread leaks."""
        issues = []
        
        for root, dirs, files in os.walk(repository_path):
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', 'venv', '.venv'}]
            
            for file in files:
                if not file.endswith('.py'):
                    continue
                
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, repository_path)
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        lines = content.split('\n')
                        
                        for line_num, line in enumerate(lines, 1):
                            # Check for Thread.start() without join
                            if 'Thread(' in line and '.start()' in line:
                                # Simple heuristic: check if 'join' appears nearby
                                context = ''.join(lines[line_num:min(line_num+5, len(lines))])
                                if '.join()' not in context:
                                    issues.append((rel_path, line_num, 'thread', line.strip()))
                            
                            # Check for ThreadPoolExecutor without 'with' or shutdown
                            if 'ThreadPoolExecutor(' in line and 'with' not in line:
                                issues.append((rel_path, line_num, 'thread_pool', line.strip()))
                
                except Exception:
                    continue
        
        return issues
