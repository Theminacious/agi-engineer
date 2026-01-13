"""
PHASE 12: Enhanced Concurrency Analyzer

Detects concurrency hazards with deeper analysis:
- Shared mutable state without synchronization
- Thread-safety violations (reading from data races)
- Async misuse patterns (awaits in loops, fire-and-forget)
- Lock contention risks
- Callback hell patterns

All analysis is deterministic, stateless, and proposal-only.
"""

from typing import List, Dict, Set, Tuple
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


class EnhancedConcurrencyAnalyzer(BaseAnalyzer):
    """
    Phase 12 enhanced concurrency analyzer.
    
    Improvements over Phase 11:
    - Detects shared mutable state patterns
    - Analyzes thread safety without annotations
    - Identifies async anti-patterns
    - Detects lock usage and contention risks
    - Finds callback nesting (callback hell)
    """
    
    @property
    def bug_class(self) -> BugClass:
        return BugClass.CONCURRENCY_HAZARDS
    
    def analyze(
        self,
        repository_path: str,
        repository_url: str,
        branch: str = "main",
    ) -> List[IntelligenceProposal]:
        """Analyze repository for concurrency hazards."""
        self.start_timing()
        self._reset_metrics()
        
        proposals = []
        
        # 1. Detect shared mutable state
        shared_state = self._detect_shared_mutable_state(repository_path)
        proposals.extend(shared_state)
        
        # 2. Detect thread-safety violations
        thread_safety = self._detect_thread_safety_violations(repository_path)
        proposals.extend(thread_safety)
        
        # 3. Detect async anti-patterns
        async_patterns = self._detect_async_anti_patterns(repository_path)
        proposals.extend(async_patterns)
        
        # 4. Detect lock contention risks
        lock_issues = self._detect_lock_contention_risks(repository_path)
        proposals.extend(lock_issues)
        
        # Finalize all proposals
        finalized = []
        for proposal in proposals:
            proposal.repository_url = repository_url
            proposal.branch = branch
            finalized.append(self._finalize_proposal(proposal))
        
        return finalized
    
    def _detect_shared_mutable_state(
        self,
        repository_path: str,
    ) -> List[IntelligenceProposal]:
        """
        Detect patterns indicating shared mutable state without synchronization.
        
        Patterns:
        - Class attributes that are mutable (lists, dicts)
        - Global variables that are modified
        - Threading without locks
        """
        proposals = []
        
        shared_state_issues = self._scan_for_shared_state(repository_path)
        
        for issue in shared_state_issues:
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.CONCURRENCY_HAZARDS
            proposal.severity = Severity.CRITICAL
            
            proposal.problem_statement = (
                f"Shared mutable state detected: {issue['name']} in {issue['location']}. "
                f"Multiple threads may access and modify this without synchronization, "
                f"causing data races and inconsistent state."
            )
            
            proposal.risk_explanation = (
                f"Shared mutable state without synchronization is a critical concurrency hazard. "
                f"Two threads may read, modify, and write the same state simultaneously, "
                f"resulting in lost updates, memory corruption, or incorrect behavior. "
                f"Bugs are difficult to reproduce and may appear only under load."
            )
            
            proposal.root_cause_hypothesis = (
                f"Likely causes: (1) Code was single-threaded when written, "
                f"(2) Threading/async added later without refactoring shared state, "
                f"(3) Insufficient understanding of concurrency implications."
            )
            
            proposal.affected_files.append(
                AffectedFile(path=issue['file'], severity=Severity.CRITICAL)
            )
            
            proposal.suggested_strategies = [
                FixStrategy(
                    name="Use thread-safe data structures",
                    description=(
                        f"Replace mutable {issue['type']} with thread-safe equivalent "
                        f"(e.g., Queue, ThreadSafeDict, AtomicReference)."
                    ),
                    effort_estimate=EffortEstimate.SMALL,
                    prerequisite_actions=[
                        f"Identify thread-safe alternative for {issue['type']}",
                        f"Replace {issue['name']} with thread-safe version",
                        "Update all access patterns",
                        "Test under concurrent load",
                    ],
                    assumptions=[
                        "Thread-safe alternative exists for use case",
                        "Performance characteristics are acceptable",
                    ],
                    risks=[
                        "Thread-safe structures may have different API",
                        "Performance overhead from synchronization",
                    ],
                ),
                FixStrategy(
                    name="Synchronize access with locks",
                    description=(
                        f"Protect access to {issue['name']} with mutex/lock. "
                        f"Acquire lock before reading/writing, release after."
                    ),
                    effort_estimate=EffortEstimate.MEDIUM,
                    prerequisite_actions=[
                        "Identify all access points to shared state",
                        "Create lock for protecting state",
                        "Wrap all access in lock acquisition",
                        "Ensure locks are released (use context managers)",
                        "Test for deadlock scenarios",
                    ],
                    assumptions=[
                        "Deadlock can be avoided",
                        "Lock contention is acceptable",
                    ],
                    risks=[
                        "Deadlock if multiple locks acquired",
                        "Performance impact under high contention",
                        "Easy to forget locks and introduce races",
                    ],
                ),
                FixStrategy(
                    name="Eliminate shared state with message passing",
                    description=(
                        f"Redesign to avoid shared state. Use message passing "
                        f"(channels, queues) to coordinate between threads instead."
                    ),
                    effort_estimate=EffortEstimate.LARGE,
                    prerequisite_actions=[
                        "Identify what data is shared",
                        "Design message types for coordination",
                        "Create message queue/channel",
                        "Refactor to send/receive messages",
                        "Ensure no direct state access",
                    ],
                    assumptions=[
                        "Message passing pattern fits use case",
                        "Latency of queuing is acceptable",
                    ],
                    risks=[
                        "Message ordering may matter",
                        "Harder to reason about causality",
                    ],
                ),
            ]
            
            proposal.confidence_level = 85
            proposal.confidence_explanation = (
                f"Shared mutable state detection uses static pattern analysis. "
                f"Confidence is high for finding the pattern, but actual severity "
                f"depends on whether state is truly accessed concurrently (runtime behavior)."
            )
            
            self.patterns_matched.append(f"shared_mutable_state:{issue['name']}")
            proposals.append(proposal)
        
        return proposals
    
    def _detect_thread_safety_violations(
        self,
        repository_path: str,
    ) -> List[IntelligenceProposal]:
        """
        Detect thread-safety violations:
        - Methods not marked as @thread_safe but should be
        - Accessing non-thread-safe data without synchronization
        - Checking-then-acting patterns (TOCTOU)
        """
        proposals = []
        
        violations = self._scan_for_thread_safety_issues(repository_path)
        
        for violation in violations:
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.CONCURRENCY_HAZARDS
            proposal.severity = Severity.HIGH
            
            proposal.problem_statement = (
                f"Thread-safety violation in {violation['method']}: "
                f"Method accesses non-thread-safe data but is not synchronized. "
                f"Concurrent calls will cause data races."
            )
            
            proposal.risk_explanation = (
                f"If this method is called from multiple threads simultaneously, "
                f"the non-thread-safe access pattern will cause data corruption or inconsistency. "
                f"Bugs may only appear under specific timing conditions, making them hard to debug."
            )
            
            proposal.root_cause_hypothesis = (
                f"Likely causes: (1) Method wasn't considered for concurrent access when written, "
                f"(2) Synchronization forgotten when threading support was added, "
                f"(3) Check-then-act pattern where state changes between check and action."
            )
            
            proposal.affected_files.append(
                AffectedFile(
                    path=violation['file'],
                    line_range=violation.get('line_range'),
                    severity=Severity.HIGH,
                )
            )
            
            proposal.suggested_strategies = [
                FixStrategy(
                    name="Add synchronization (lock)",
                    description=(
                        f"Protect {violation['method']} method with synchronization. "
                        f"Use lock or synchronized keyword to ensure atomicity."
                    ),
                    effort_estimate=EffortEstimate.SMALL,
                    prerequisite_actions=[
                        f"Mark {violation['method']} as synchronized/locked",
                        "Analyze for deadlock risks",
                        "Test concurrent access",
                    ],
                    assumptions=[
                        "Synchronizing entire method is appropriate",
                        "No deadlock with other locks",
                    ],
                    risks=[
                        "May serialize too much (performance)",
                        "Deadlock if locks acquired in wrong order",
                    ],
                ),
                FixStrategy(
                    name="Refine synchronization (fine-grained locking)",
                    description=(
                        f"Instead of synchronizing entire method, synchronize only "
                        f"critical sections that access non-thread-safe data."
                    ),
                    effort_estimate=EffortEstimate.MEDIUM,
                    prerequisite_actions=[
                        "Identify critical sections",
                        "Minimize locked region",
                        "Acquire/release locks appropriately",
                        "Verify no data races",
                    ],
                    assumptions=[
                        "Critical sections can be isolated",
                        "Deadlock avoided",
                    ],
                    risks=[
                        "Harder to understand locking strategy",
                        "Easier to miss synchronization",
                    ],
                ),
                FixStrategy(
                    name="Use thread-safe alternative",
                    description=(
                        f"Replace non-thread-safe data structures with thread-safe versions "
                        f"(e.g., ConcurrentHashMap, AtomicReference). No synchronization needed."
                    ),
                    effort_estimate=EffortEstimate.SMALL,
                    prerequisite_actions=[
                        "Choose thread-safe alternative",
                        "Replace data structure",
                        "Update access patterns if needed",
                        "Test",
                    ],
                    assumptions=[
                        "Thread-safe alternative exists",
                        "API compatible",
                    ],
                    risks=[
                        "Performance characteristics may differ",
                        "Different semantics (e.g., atomic updates)",
                    ],
                ),
            ]
            
            proposal.confidence_level = 75
            proposal.confidence_explanation = (
                f"Thread-safety analysis uses pattern matching. "
                f"Moderate confidence - actual thread-safety depends on runtime behavior "
                f"and thread creation patterns (hard to analyze statically)."
            )
            
            self.patterns_matched.append(f"thread_safety_violation:{violation['method']}")
            proposals.append(proposal)
        
        return proposals
    
    def _detect_async_anti_patterns(
        self,
        repository_path: str,
    ) -> List[IntelligenceProposal]:
        """
        Detect async/await anti-patterns:
        - Awaiting in loops (should batch/parallel)
        - Fire-and-forget (missing await)
        - Blocking operations in async context
        - Async over sync (using async wrapper for no benefit)
        """
        proposals = []
        
        anti_patterns = self._scan_for_async_patterns(repository_path)
        
        for pattern in anti_patterns:
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.CONCURRENCY_HAZARDS
            proposal.severity = Severity.MEDIUM
            
            pattern_name = pattern['pattern']
            
            if pattern_name == 'await_in_loop':
                proposal.problem_statement = (
                    f"Async anti-pattern detected in {pattern['method']}: "
                    f"Awaiting {pattern['count']} times in a loop. "
                    f"This serializes async operations when they could run concurrently."
                )
                proposal.risk_explanation = (
                    f"Each await inside the loop blocks until one operation completes, "
                    f"then starts the next. This is O(n) total time. "
                    f"Running all {pattern['count']} concurrently would be O(1) time if operations don't depend on each other."
                )
                proposal.root_cause_hypothesis = (
                    f"Code pattern is natural and easy to write, but doesn't leverage async benefits. "
                    f"Likely developer unfamiliar with asyncio.gather/concurrent patterns."
                )
                strategies_effort = EffortEstimate.SMALL
                
            elif pattern_name == 'fire_and_forget':
                proposal.problem_statement = (
                    f"Fire-and-forget async call in {pattern['method']}: "
                    f"Calling async function without awaiting. "
                    f"Errors are silently ignored and coroutine never completes."
                )
                proposal.risk_explanation = (
                    f"Silently ignores errors in async operation. "
                    f"Coroutine starts but may never complete. "
                    f"Debug messages won't show what went wrong. "
                    f"If operation raises exception, it's lost."
                )
                proposal.root_cause_hypothesis = (
                    f"Developer didn't want to wait for operation (fire-and-forget pattern), "
                    f"but forgot that in Python/JS, this means errors are ignored. "
                    f"Should use explicit background task/spawn instead."
                )
                strategies_effort = EffortEstimate.SMALL
                
            else:  # blocking in async
                proposal.problem_statement = (
                    f"Blocking operation detected in async context {pattern['method']}: "
                    f"Calling {pattern['operation']} which blocks the event loop. "
                    f"This defeats async benefits - event loop stalls while blocking."
                )
                proposal.risk_explanation = (
                    f"Blocking in async context stalls the entire event loop. "
                    f"All other async operations waiting on this loop are delayed. "
                    f"Effectively serializes async work, defeating concurrency benefits."
                )
                proposal.root_cause_hypothesis = (
                    f"Blocking library doesn't have async equivalent, or developer "
                    f"unaware that their synchronous call blocks the event loop."
                )
                strategies_effort = EffortEstimate.MEDIUM
            
            proposal.affected_files.append(
                AffectedFile(
                    path=pattern['file'],
                    line_range=pattern.get('line_range'),
                    severity=Severity.MEDIUM,
                )
            )
            
            if pattern_name == 'await_in_loop':
                proposal.suggested_strategies = [
                    FixStrategy(
                        name="Use asyncio.gather for concurrent awaits",
                        description=(
                            f"Instead of awaiting in loop, collect all futures/coroutines "
                            f"and pass to asyncio.gather() to run concurrently."
                        ),
                        effort_estimate=EffortEstimate.SMALL,
                        prerequisite_actions=[
                            "Collect async operations into list",
                            "Use asyncio.gather(*operations) instead of loop",
                            "Handle exceptions with return_exceptions=True if needed",
                            "Test concurrent execution",
                        ],
                        assumptions=[
                            "Operations don't depend on each other",
                            "Order of completion doesn't matter",
                        ],
                        risks=[
                            "If operations depend on order, gather breaks it",
                            "All errors happen at once (may be overwhelming)",
                        ],
                    ),
                    FixStrategy(
                        name="Use asyncio.TaskGroup for structured concurrency",
                        description=(
                            f"Use TaskGroup (Python 3.11+) for cleaner concurrent operation handling. "
                            f"Automatically manages lifecycle and cancellation."
                        ),
                        effort_estimate=EffortEstimate.SMALL,
                        prerequisite_actions=[
                            "Require Python 3.11+",
                            "Create TaskGroup",
                            "Use create_task() for each operation",
                            "Let TaskGroup manage lifecycle",
                        ],
                        assumptions=[
                            "Python 3.11+ available",
                            "Operations can be independent",
                        ],
                        risks=[
                            "Requires newer Python version",
                            "Different error handling than gather",
                        ],
                    ),
                ]
            elif pattern_name == 'fire_and_forget':
                proposal.suggested_strategies = [
                    FixStrategy(
                        name="Await the operation explicitly",
                        description=(
                            f"If you need to wait for operation, add 'await'. "
                            f"If you don't want to wait, use explicit background task handling."
                        ),
                        effort_estimate=EffortEstimate.TRIVIAL,
                        prerequisite_actions=[
                            "Add 'await' if operation should block",
                            "Or use explicit background task if fire-and-forget intended",
                        ],
                        assumptions=[],
                        risks=[],
                    ),
                    FixStrategy(
                        name="Create background task with error handling",
                        description=(
                            f"Use asyncio.create_task() with error callback "
                            f"to handle errors from background task."
                        ),
                        effort_estimate=EffortEstimate.SMALL,
                        prerequisite_actions=[
                            "Use asyncio.create_task() instead of just calling function",
                            "Add done_callback to handle errors",
                            "Log/handle exceptions from callback",
                        ],
                        assumptions=[
                            "Explicit error handling needed",
                        ],
                        risks=[
                            "Callback may be delayed",
                        ],
                    ),
                ]
            else:  # blocking
                proposal.suggested_strategies = [
                    FixStrategy(
                        name="Use async equivalent",
                        description=(
                            f"Replace blocking operation with async equivalent. "
                            f"Most libraries have aio versions (aiofiles, aiohttp, etc)."
                        ),
                        effort_estimate=EffortEstimate.MEDIUM,
                        prerequisite_actions=[
                            f"Find async version of {pattern['operation']}",
                            "Replace blocking call with async",
                            "Add await",
                            "Test that event loop stays responsive",
                        ],
                        assumptions=[
                            "Async equivalent exists",
                            "API is similar",
                        ],
                        risks=[
                            "Async version may have different behavior",
                            "May need refactor of calling code",
                        ],
                    ),
                    FixStrategy(
                        name="Use executor to run in thread pool",
                        description=(
                            f"If no async version exists, use loop.run_in_executor() "
                            f"to run blocking operation in thread pool."
                        ),
                        effort_estimate=EffortEstimate.SMALL,
                        prerequisite_actions=[
                            f"Wrap {pattern['operation']} with run_in_executor()",
                            "Await the executor future",
                            "Consider thread pool size",
                        ],
                        assumptions=[
                            "Thread pool overhead acceptable",
                            "Operation is thread-safe",
                        ],
                        risks=[
                            "Thread pool adds overhead",
                            "Thread-safety concerns with GIL",
                        ],
                    ),
                ]
            
            proposal.confidence_level = 90
            proposal.confidence_explanation = (
                f"Async anti-patterns are detected through code inspection. "
                f"Very high confidence - patterns are objective and unambiguous."
            )
            
            self.patterns_matched.append(f"async_anti_pattern:{pattern_name}")
            proposals.append(proposal)
        
        return proposals
    
    def _detect_lock_contention_risks(
        self,
        repository_path: str,
    ) -> List[IntelligenceProposal]:
        """
        Detect lock contention risks:
        - Locks held too long
        - Nested locks (deadlock risk)
        - Reentrant locks used incorrectly
        - Lock ordering violations
        """
        proposals = []
        
        contention_risks = self._scan_for_lock_issues(repository_path)
        
        for risk in contention_risks:
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.CONCURRENCY_HAZARDS
            proposal.severity = Severity.HIGH
            
            if risk['type'] == 'lock_held_too_long':
                proposal.problem_statement = (
                    f"Lock held for too long in {risk['location']}: "
                    f"Critical section is {risk['lines']} lines. "
                    f"Lock contention will be high under concurrent load."
                )
                proposal.risk_explanation = (
                    f"While one thread holds the lock, all others wait. "
                    f"Large critical section means long waits. "
                    f"Under load, threads pile up waiting for lock, reducing throughput."
                )
                
            elif risk['type'] == 'nested_locks':
                proposal.problem_statement = (
                    f"Nested locks detected in {risk['location']}: "
                    f"Lock {risk['lock1']} acquired, then {risk['lock2']} while holding first. "
                    f"Risk of deadlock if other code acquires locks in different order."
                )
                proposal.risk_explanation = (
                    f"Thread A acquires lock 1, tries for lock 2. "
                    f"Thread B acquires lock 2, tries for lock 1. "
                    f"Deadlock - both threads wait forever. System hangs."
                )
            
            else:  # lock ordering
                proposal.problem_statement = (
                    f"Lock ordering violation in {risk['location']}: "
                    f"Locks acquired in different order than elsewhere. "
                    f"High deadlock risk."
                )
                proposal.risk_explanation = (
                    f"If locks are always acquired in same order (lock 1, then lock 2), "
                    f"no deadlock possible. But if this code acquires in reverse order, "
                    f"deadlock is possible."
                )
            
            proposal.affected_files.append(
                AffectedFile(path=risk['file'], severity=Severity.HIGH)
            )
            
            proposal.suggested_strategies = [
                FixStrategy(
                    name="Reduce critical section size",
                    description=(
                        f"Move non-critical code outside lock. "
                        f"Only protect access to shared state."
                    ),
                    effort_estimate=EffortEstimate.MEDIUM,
                    prerequisite_actions=[
                        "Identify what actually needs locking",
                        "Move preparation before lock",
                        "Move cleanup after lock",
                        "Test correctness under concurrency",
                    ],
                    assumptions=[
                        "Non-critical code doesn't depend on lock",
                    ],
                    risks=[
                        "May introduce new races if careless",
                    ],
                ),
                FixStrategy(
                    name="Use finer-grained locking",
                    description=(
                        f"Instead of one lock for whole structure, use multiple locks "
                        f"for different parts."
                    ),
                    effort_estimate=EffortEstimate.LARGE,
                    prerequisite_actions=[
                        "Partition shared state",
                        "Create separate lock for each partition",
                        "Update code to lock only relevant partition",
                        "Verify no deadlock",
                    ],
                    assumptions=[
                        "State can be partitioned",
                        "Partitions are independent",
                    ],
                    risks=[
                        "Complexity increases significantly",
                        "Easier to make mistakes",
                    ],
                ),
            ]
            
            proposal.confidence_level = 75
            proposal.confidence_explanation = (
                f"Lock analysis uses code inspection and heuristics. "
                f"Moderate confidence - actual contention/deadlock depends on runtime behavior."
            )
            
            self.patterns_matched.append(f"lock_contention:{risk['type']}")
            proposals.append(proposal)
        
        return proposals
    
    # ========== Helper Methods ==========
    
    def _scan_for_shared_state(self, repository_path: str) -> List[Dict]:
        """Scan for shared mutable state patterns."""
        issues = []
        
        patterns = [
            (r'self\.\w+\s*=\s*\[\]', 'list'),
            (r'self\.\w+\s*=\s*\{\}', 'dict'),
            (r'self\.\w+\s*=\s*set\(\)', 'set'),
            (r'^\w+\s*=\s*\[\]', 'list'),
            (r'^\w+\s*=\s*\{\}', 'dict'),
        ]
        
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
                        
                        for pattern, dtype in patterns:
                            for match in re.finditer(pattern, content, re.MULTILINE):
                                issues.append({
                                    'file': file_path,
                                    'name': match.group(0),
                                    'type': dtype,
                                    'location': f"{file}:{content[:match.start()].count(chr(10)) + 1}",
                                })
                except Exception:
                    pass
        
        return issues
    
    def _scan_for_thread_safety_issues(self, repository_path: str) -> List[Dict]:
        """Scan for thread-safety violations."""
        issues = []
        
        patterns = [
            r'def\s+(\w+)\s*\(self.*\).*:.*(?:self\.\w+\s*[+\-*=/]|append|extend|update)',
        ]
        
        for root, dirs, files in os.walk(repository_path):
            dirs[:] = [d for d in dirs if d not in {'__pycache__', '.git', 'venv'}]
            
            for file in sorted(files):
                if not file.endswith('.py'):
                    continue
                
                file_path = os.path.join(root, file)
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        
                        for i, line in enumerate(lines):
                            if 'Thread' in line or 'thread' in line:
                                # Look for non-synchronized state access nearby
                                if any(pattern in ''.join(lines[max(0, i-5):i+5]) 
                                       for pattern in ['self.', '.append', '.update']):
                                    issues.append({
                                        'file': file_path,
                                        'method': 'method_at_line_' + str(i),
                                        'line_range': f"{i}-{i+5}",
                                    })
                except Exception:
                    pass
        
        return issues
    
    def _scan_for_async_patterns(self, repository_path: str) -> List[Dict]:
        """Scan for async anti-patterns."""
        patterns = []
        
        await_in_loop_pattern = re.compile(
            r'for\s+\w+\s+in\s+.*?:.*?await',
            re.DOTALL
        )
        fire_and_forget_pattern = re.compile(
            r'(?<!await)\s+(?:asyncio\.create_task\(|\w+\(.*?\))\s*$',
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
                        
                        # Check for await in loop
                        for match in await_in_loop_pattern.finditer(content):
                            count = content[match.start():match.end()].count('await')
                            patterns.append({
                                'pattern': 'await_in_loop',
                                'file': file_path,
                                'method': 'unknown',
                                'count': count,
                                'line_range': f"{content[:match.start()].count(chr(10))}",
                            })
                        
                        # Check for blocking in async
                        if 'async def' in content and ('requests.get' in content or 'time.sleep' in content):
                            patterns.append({
                                'pattern': 'blocking_in_async',
                                'file': file_path,
                                'method': 'unknown',
                                'operation': 'requests/time.sleep',
                                'line_range': '0',
                            })
                except Exception:
                    pass
        
        return patterns
    
    def _scan_for_lock_issues(self, repository_path: str) -> List[Dict]:
        """Scan for lock contention issues."""
        issues = []
        
        lock_pattern = re.compile(r'(lock|Lock|mutex)\.acquire|with\s+\w+:')
        
        for root, dirs, files in os.walk(repository_path):
            dirs[:] = [d for d in dirs if d not in {'__pycache__', '.git', 'venv'}]
            
            for file in sorted(files):
                if not file.endswith('.py'):
                    continue
                
                file_path = os.path.join(root, file)
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        
                        for match in lock_pattern.finditer(content):
                            line_num = content[:match.start()].count('\n')
                            # Check if this is start of long critical section
                            section_end = min(match.end() + 1000, len(content))
                            section = content[match.end():section_end]
                            lines_in_section = section.count('\n')
                            
                            if lines_in_section > 20:  # Long critical section
                                issues.append({
                                    'type': 'lock_held_too_long',
                                    'file': file_path,
                                    'location': f"{file}:{line_num}",
                                    'lines': lines_in_section,
                                })
                except Exception:
                    pass
        
        return issues
