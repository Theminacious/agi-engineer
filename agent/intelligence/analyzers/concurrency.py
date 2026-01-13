"""
Concurrency hazards analyzer.

Detects shared mutable state, race conditions, deadlocks, and synchronization issues.
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


class ConcurrencyAnalyzer(BaseAnalyzer):
    """Detect concurrency hazards."""
    
    @property
    def bug_class(self) -> BugClass:
        return BugClass.CONCURRENCY_HAZARDS
    
    # Patterns for concurrency issues
    CONCURRENCY_PATTERNS = {
        'shared_mutable_list': r'self\.\w+\s*=\s*\[\]',
        'shared_mutable_dict': r'self\.\w+\s*=\s*\{\}',
        'global_mutable': r'global\s+\w+\s+\w+=',
        'lock_not_used': r'threading\.Lock\(\)|Lock\(\)(?!.*with)',
        'double_lock': r'acquire.*acquire|lock.*lock',
    }
    
    def analyze(
        self,
        repository_path: str,
        repository_url: str,
        branch: str = "main",
    ) -> List[IntelligenceProposal]:
        """Analyze repository for concurrency issues."""
        self.start_timing()
        self._reset_metrics()
        
        proposals = []
        
        # 1. Detect shared mutable state
        shared = self._detect_shared_mutable_state(repository_path)
        proposals.extend(shared)
        
        # 2. Detect missing synchronization
        unsync = self._detect_missing_synchronization(repository_path)
        proposals.extend(unsync)
        
        # 3. Detect potential deadlocks
        deadlocks = self._detect_potential_deadlocks(repository_path)
        proposals.extend(deadlocks)
        
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
        """Detect shared mutable state."""
        proposals = []
        
        issues = self._scan_for_shared_mutable(repository_path)
        
        if issues:
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.CONCURRENCY_HAZARDS
            proposal.severity = Severity.HIGH
            
            issue_count = len(issues)
            
            proposal.problem_statement = (
                f"Found {issue_count} potential shared mutable state issues. "
                f"Mutable containers (lists, dicts) shared across threads without synchronization "
                f"can cause data corruption and race conditions."
            )
            
            proposal.risk_explanation = (
                f"Shared mutable state without proper synchronization causes race conditions: "
                f"data corruption, lost updates, memory inconsistency. Multiple threads reading/writing "
                f"the same list/dict can see inconsistent state. Data structure operations are not atomic."
            )
            
            proposal.root_cause_hypothesis = (
                f"Mutable containers created in class __init__ (or at module level) and accessed "
                f"by multiple threads without locks. Common pattern in multi-threaded servers."
            )
            
            # Add affected files
            for file_path, line_num in issues:
                proposal.affected_files.append(
                    AffectedFile(path=file_path, severity=Severity.HIGH)
                )
            
            # Strategies
            proposal.suggested_strategies = [
                FixStrategy(
                    name="Use thread-safe containers",
                    description=(
                        f"Replace mutable lists/dicts with thread-safe alternatives: "
                        f"queue.Queue, threading.RLock for dicts, or immutable data structures."
                    ),
                    effort_estimate=EffortEstimate.MEDIUM,
                    prerequisite_actions=[
                        "Identify all shared mutable containers",
                        "Choose thread-safe replacement (Queue, RLock, immutable)",
                        "Refactor all access patterns",
                        "Add synchronization tests",
                        "Load test with concurrent access",
                    ],
                    assumptions=[
                        "Thread-safe container API is compatible",
                        "Performance impact is acceptable",
                    ],
                    risks=[
                        "May reduce performance",
                        "Queue has different API than list/dict",
                        "Immutable requires different code patterns",
                    ],
                ),
                FixStrategy(
                    name="Add explicit locking",
                    description=(
                        f"Wrap all access to shared mutable state with locks. "
                        f"Use with statement for proper lock management."
                    ),
                    effort_estimate=EffortEstimate.MEDIUM,
                    prerequisite_actions=[
                        "Create lock for each shared container",
                        "Identify all access points",
                        "Wrap with 'with lock' pattern",
                        "Add synchronization tests",
                        "Profile lock contention",
                    ],
                    assumptions=[
                        "Lock acquisition order prevents deadlock",
                        "Lock granularity is appropriate",
                    ],
                    risks=[
                        "Deadlock if locks acquired in inconsistent order",
                        "Lock contention reduces concurrency",
                        "Easy to forget lock in some paths",
                    ],
                ),
            ]
            
            proposal.confidence_level = 70
            proposal.confidence_explanation = (
                f"Detection finds mutable container creation; however, requires "
                f"control flow analysis to confirm shared across threads. "
                f"Static analysis may have false positives."
            )
            proposal.requires_human_decision = True
            proposal.decision_required_for = (
                "Verify containers are actually shared; choose synchronization strategy."
            )
            
            self.patterns_matched.append(f"shared_mutable:{issue_count}")
            proposals.append(proposal)
        
        return proposals
    
    def _detect_missing_synchronization(
        self,
        repository_path: str,
    ) -> List[IntelligenceProposal]:
        """Detect missing synchronization around critical sections."""
        proposals = []
        
        issues = self._scan_for_missing_synchronization(repository_path)
        
        if issues:
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.CONCURRENCY_HAZARDS
            proposal.severity = Severity.HIGH
            
            issue_count = len(issues)
            
            proposal.problem_statement = (
                f"Found {issue_count} locations with potential unsynchronized access. "
                f"Multi-threaded code accessing shared state without locks risks data corruption."
            )
            
            proposal.risk_explanation = (
                f"Operations on shared state must be atomic. Without locks, thread preemption "
                f"between operations causes race conditions. Example: checking then modifying "
                f"a counter is not atomic without synchronization."
            )
            
            proposal.root_cause_hypothesis = (
                f"Code assumes single-threaded execution or relies on GIL (which doesn't protect "
                f"against all races). Multiple threads access shared state without coordination."
            )
            
            # Add affected files
            for file_path, line_num in issues:
                proposal.affected_files.append(
                    AffectedFile(path=file_path, severity=Severity.HIGH)
                )
            
            # Strategies
            proposal.suggested_strategies = [
                FixStrategy(
                    name="Identify critical sections and add locks",
                    description=(
                        f"Code review to identify all critical sections. "
                        f"Add locks around shared state access using 'with lock' pattern."
                    ),
                    effort_estimate=EffortEstimate.LARGE,
                    prerequisite_actions=[
                        "Identify all shared state",
                        "Map which code accesses shared state",
                        "Define critical sections",
                        "Add appropriate locks",
                        "Test for race conditions",
                    ],
                    assumptions=[
                        "All shared state is identifiable",
                        "Critical sections can be clearly defined",
                    ],
                    risks=[
                        "Easy to miss some access paths",
                        "Deadlock if lock order is inconsistent",
                        "May reduce concurrency",
                    ],
                ),
                FixStrategy(
                    name="Use concurrent data structures or message passing",
                    description=(
                        f"Replace shared state with concurrent data structures "
                        f"or use message passing (queues) for inter-thread communication."
                    ),
                    effort_estimate=EffortEstimate.VERY_LARGE,
                    prerequisite_actions=[
                        "Redesign architecture for message passing",
                        "Use queue.Queue or similar",
                        "Refactor thread communication",
                        "Update all shared state patterns",
                        "Extensive testing",
                    ],
                    assumptions=[
                        "Message passing is compatible with design",
                        "No critical shared state is required",
                    ],
                    risks=[
                        "Major architectural change",
                        "May reduce performance",
                        "Requires significant refactoring",
                    ],
                ),
            ]
            
            proposal.confidence_level = 65
            proposal.confidence_explanation = (
                f"Detecting unsynchronized access requires precise control flow analysis. "
                f"Pattern matching has moderate confidence; recommend code review to verify."
            )
            proposal.requires_human_decision = True
            proposal.decision_required_for = (
                "Architecture review to determine best synchronization approach."
            )
            
            self.patterns_matched.append(f"missing_sync:{issue_count}")
            proposals.append(proposal)
        
        return proposals
    
    def _detect_potential_deadlocks(
        self,
        repository_path: str,
    ) -> List[IntelligenceProposal]:
        """Detect potential deadlock patterns."""
        proposals = []
        
        issues = self._scan_for_deadlock_patterns(repository_path)
        
        if issues:
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.CONCURRENCY_HAZARDS
            proposal.severity = Severity.MEDIUM
            
            issue_count = len(issues)
            
            proposal.problem_statement = (
                f"Found {issue_count} potential deadlock patterns. "
                f"Nested lock acquisitions or multiple locks without consistent ordering "
                f"can deadlock."
            )
            
            proposal.risk_explanation = (
                f"Deadlock occurs when: Thread A holds lock1, waits for lock2; "
                f"Thread B holds lock2, waits for lock1. Threads are forever blocked. "
                f"Application becomes unresponsive, hangs, or crashes."
            )
            
            proposal.root_cause_hypothesis = (
                f"Multiple locks acquired in different orders in different code paths. "
                f"Nested lock acquisition without clear ordering discipline."
            )
            
            # Add affected files
            for file_path, line_num in issues:
                proposal.affected_files.append(
                    AffectedFile(path=file_path, severity=Severity.MEDIUM)
                )
            
            # Strategies
            proposal.suggested_strategies = [
                FixStrategy(
                    name="Establish lock ordering discipline",
                    description=(
                        f"Define a global lock order (e.g., always lock A before B). "
                        f"Enforce this across all code paths to prevent circular waits."
                    ),
                    effort_estimate=EffortEstimate.MEDIUM,
                    prerequisite_actions=[
                        "Identify all locks",
                        "Define lock ordering (document)",
                        "Audit all code for violations",
                        "Add comments enforcing order",
                        "Test with stress tests",
                    ],
                    assumptions=[
                        "Lock order can be globally defined",
                        "No circular dependencies",
                    ],
                    risks=[
                        "Discipline is hard to maintain",
                        "New developers may not follow order",
                        "May require refactoring",
                    ],
                ),
                FixStrategy(
                    name="Timeout-based deadlock detection",
                    description=(
                        f"Add timeout to all lock acquisitions. "
                        f"If timeout occurs, release locks and retry (exponential backoff)."
                    ),
                    effort_estimate=EffortEstimate.SMALL,
                    prerequisite_actions=[
                        "Add timeout to lock acquisitions",
                        "Implement retry logic",
                        "Add deadlock detection monitoring",
                        "Log deadlock events",
                        "Test retry mechanism",
                    ],
                    assumptions=[
                        "Timeout values are reasonable",
                        "Retry can succeed",
                    ],
                    risks=[
                        "Timeout may be too short",
                        "Retry may cause livelock",
                        "May hide real deadlock",
                    ],
                ),
            ]
            
            proposal.confidence_level = 60
            proposal.confidence_explanation = (
                f"Detecting deadlock patterns requires precise control flow analysis. "
                f"Pattern matching has low-to-moderate confidence; may miss or over-report."
            )
            proposal.requires_human_decision = True
            proposal.decision_required_for = (
                "Code review to verify deadlock potential; establish lock ordering discipline."
            )
            
            self.patterns_matched.append(f"deadlock_patterns:{issue_count}")
            proposals.append(proposal)
        
        return proposals
    
    def _scan_for_shared_mutable(self, repository_path: str) -> List[Tuple]:
        """Scan for shared mutable state."""
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
                            
                            # Look for self.x = [] or self.x = {}
                            if re.search(r'self\.\w+\s*=\s*(\[|\{)', line):
                                # Skip if followed by immutable
                                if 'Lock' not in line and 'Queue' not in line:
                                    issues.append((file_path, line_num))
                except Exception:
                    pass
        
        return issues
    
    def _scan_for_missing_synchronization(self, repository_path: str) -> List[Tuple]:
        """Scan for potential missing synchronization."""
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
                            
                            # Look for threading.Thread without clear sync
                            if 'Thread(' in line or 'threading.Thread' in line:
                                issues.append((file_path, line_num))
                except Exception:
                    pass
        
        return issues
    
    def _scan_for_deadlock_patterns(self, repository_path: str) -> List[Tuple]:
        """Scan for deadlock patterns."""
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
                        
                        # Look for multiple lock acquisitions
                        lock_count = len(re.findall(r'\.acquire\(|with.*lock', content))
                        if lock_count > 2:  # Multiple locks in same file
                            for line_num, line in enumerate(content.split('\n'), 1):
                                if re.search(r'\.acquire\(|with.*lock', line):
                                    issues.append((file_path, line_num))
                except Exception:
                    pass
        
        return issues
