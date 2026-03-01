"""
Reliability Pattern Analyzer - Phase 16

Detects reliability anti-patterns:
- Retry without exponential backoff
- Missing timeout configurations
- Silent failure swallowing
- Catch-and-ignore exception patterns
- Blocking I/O in async contexts
- Missing circuit breakers
- Cascading failure risks
- Missing healthchecks/probes
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


class ReliabilityPatternAnalyzer(BaseAnalyzer):
    """Detect reliability anti-patterns that cause unstable systems."""
    
    @property
    def bug_class(self) -> BugClass:
        return BugClass.RELIABILITY_ANTI_PATTERNS
    
    # Patterns for reliability anti-patterns
    RELIABILITY_PATTERNS = {
        # Retry without backoff
        'retry_without_backoff': r'(for|while).*retry.*(?!sleep|backoff|delay)',
        'immediate_retry': r'except.*:\s*continue',  # Retry loop without delay
        
        # Missing timeouts
        'requests_no_timeout': r'requests\.\w+\([^)]*\)(?!.*timeout=)',
        'socket_no_timeout': r'socket\.socket\([^)]*\)(?!.*settimeout)',
        'db_no_timeout': r'\.connect\([^)]*\)(?!.*timeout=)',
        
        # Silent failures
        'bare_except': r'except\s*:',  # except: without type
        'pass_except': r'except[^:]*:\s*pass',  # except: pass
        'silent_except': r'except[^:]*:\s*(?!log|print|raise)',  # except without logging
        
        # Blocking in async
        'blocking_in_async': r'async\s+def.*:.*(?:time\.sleep|requests\.\w+)',
        'sync_io_in_async': r'async\s+def.*:.*open\(',
        
        # Circuit breaker missing
        'external_call_no_cb': r'requests\.\w+\(.*\)(?!.*circuit|breaker|timeout)',
        
        # Missing healthchecks
        'no_health_endpoint': r'@app\.route|@router\.',  # Has routes but check for /health
    }
    
    def analyze(
        self,
        repository_path: str,
        repository_url: str,
        branch: str = "main",
    ) -> List[IntelligenceProposal]:
        """Analyze repository for reliability anti-patterns."""
        self.start_timing()
        self._reset_metrics()
        
        proposals = []
        
        # 1. Detect retry patterns without backoff
        retry_issues = self._detect_retry_without_backoff(repository_path)
        if retry_issues:
            proposals.append(retry_issues)
        
        # 2. Detect missing timeouts
        timeout_issues = self._detect_missing_timeouts(repository_path)
        if timeout_issues:
            proposals.append(timeout_issues)
        
        # 3. Detect silent failures
        silent_failures = self._detect_silent_failures(repository_path)
        if silent_failures:
            proposals.append(silent_failures)
        
        # 4. Detect blocking operations in async code
        blocking_async = self._detect_blocking_in_async(repository_path)
        if blocking_async:
            proposals.append(blocking_async)
        
        # Finalize all proposals
        finalized = []
        for proposal in proposals:
            proposal.repository_url = repository_url
            proposal.branch = branch
            finalized.append(self._finalize_proposal(proposal))
        
        return finalized
    
    def _detect_retry_without_backoff(
        self,
        repository_path: str,
    ) -> IntelligenceProposal | None:
        """Detect retry logic without exponential backoff."""
        issues = self._scan_for_retry_patterns(repository_path)
        
        if not issues:
            return None
        
        proposal = IntelligenceProposal()
        proposal.bug_class = BugClass.RELIABILITY_ANTI_PATTERNS
        proposal.severity = Severity.HIGH
        
        issue_count = len(issues)
        
        proposal.problem_statement = (
            f"Found {issue_count} retry patterns without exponential backoff. "
            f"Immediate retries amplify failures and overload downstream services."
        )
        
        proposal.risk_explanation = (
            f"Retry without backoff creates thundering herd. When service fails, all clients "
            f"retry immediately → service cannot recover → retries amplify load → cascading failure. "
            f"Impact: complete outage, database overload, DDoS-like behavior on own infrastructure. "
            f"Proper backoff gives systems time to recover. This is CRITICAL for distributed systems."
        )
        
        proposal.root_cause_hypothesis = (
            f"Developers add retry for reliability without understanding backoff. "
            f"Common in: API clients, DB connection retry, message queue consumers. "
            f"Simple retry loop is easier to write but causes production incidents."
        )
        
        # Group issues by file
        issues_by_file = {}
        for file_path, line_num, pattern_type, code_snippet in issues:
            if file_path not in issues_by_file:
                issues_by_file[file_path] = []
            issues_by_file[file_path].append((line_num, pattern_type, code_snippet))
        
        proposal.affected_files = [
            AffectedFile(
                path=file_path,
                line_range=f"{min(l for l, _, _ in locations)}-{max(l for l, _, _ in locations)}",
                severity=Severity.HIGH,
            )
            for file_path, locations in issues_by_file.items()
        ]
        
        # Strategy 1: Add exponential backoff
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Implement exponential backoff with jitter",
                description=(
                    f"Add exponential backoff: wait 2^attempt * base_delay + random_jitter. "
                    f"Example: backoff library or tenacity library. "
                    f"Typical: 1s, 2s, 4s, 8s, 16s (max). Jitter prevents synchronized retries."
                ),
                effort_estimate=EffortEstimate.SMALL,
                prerequisite_actions=[
                    "Install backoff or tenacity library",
                    "Replace retry loops with @backoff.on_exception decorator",
                    "Configure max_tries and max_time limits",
                    "Add jitter to prevent thundering herd",
                ],
                assumptions=[
                    "Transient failures are expected",
                    "Exponential delays are acceptable",
                ],
                risks=[
                    "Increased latency on failures (by design)",
                    "May delay detection of persistent failures",
                ],
            )
        )
        
        # Strategy 2: Use circuit breaker
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Add circuit breaker pattern",
                description=(
                    f"Use pybreaker or similar. Circuit breaker stops retries when failure rate high. "
                    f"States: closed (normal) → open (failing, no retries) → half-open (testing recovery). "
                    f"Protects downstream services from overload."
                ),
                effort_estimate=EffortEstimate.MEDIUM,
                prerequisite_actions=[
                    "Install pybreaker library",
                    "Wrap external calls with circuit breaker",
                    "Configure failure threshold (e.g., 5 failures in 30s)",
                    "Configure recovery timeout (e.g., try again after 60s)",
                    "Add metrics/alerts for circuit breaker state",
                ],
                assumptions=[
                    "Circuit breaker state can be shared across requests",
                    "Half-open testing is acceptable",
                ],
                risks=[
                    "May reject valid requests during recovery",
                    "Requires tuning failure threshold",
                ],
            )
        )
        
        # Strategy 3: Rate limiting
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Add rate limiting to retries",
                description=(
                    f"Limit retry rate to prevent overwhelming downstream. "
                    f"Use token bucket or sliding window. "
                    f"Example: max 10 retries per minute per client."
                ),
                effort_estimate=EffortEstimate.MEDIUM,
                prerequisite_actions=[
                    "Implement rate limiter (ratelimit library or Redis)",
                    "Configure per-client or global limits",
                    "Add logging when rate limit hit",
                ],
                assumptions=[
                    "Rate limits can be determined from capacity",
                    "Some requests may be rejected",
                ],
                risks=[
                    "May reject legitimate retries",
                    "Requires capacity planning",
                ],
            )
        )
        
        proposal.confidence_level = 80
        proposal.confidence_explanation = (
            f"High confidence: detected retry patterns. Some may have backoff in outer scope. "
            f"Manual review recommended to confirm."
        )
        
        self.patterns_matched.append("retry_without_backoff")
        
        return proposal
    
    def _detect_missing_timeouts(
        self,
        repository_path: str,
    ) -> IntelligenceProposal | None:
        """Detect operations without timeout configuration."""
        issues = self._scan_for_missing_timeouts(repository_path)
        
        if not issues:
            return None
        
        proposal = IntelligenceProposal()
        proposal.bug_class = BugClass.RELIABILITY_ANTI_PATTERNS
        proposal.severity = Severity.CRITICAL
        
        issue_count = len(issues)
        
        proposal.problem_statement = (
            f"Found {issue_count} network/IO operations without timeouts. "
            f"Operations can hang indefinitely, exhausting resources."
        )
        
        proposal.risk_explanation = (
            f"Timeouts are MANDATORY for production reliability. Without timeout: "
            f"slow downstream hangs caller → threads/workers exhausted → complete service hang. "
            f"One slow dependency freezes entire application. "
            f"Impact: service hang, request backlog, resource exhaustion, total outage. "
            f"This is a TOP 3 cause of production incidents."
        )
        
        proposal.root_cause_hypothesis = (
            f"Developers assume network operations complete quickly. "
            f"Common in: HTTP clients, DB queries, external APIs. "
            f"Default timeout is often None (infinite). Production networks are unreliable."
        )
        
        # Group issues by file
        issues_by_file = {}
        for file_path, line_num, operation_type, code_snippet in issues:
            if file_path not in issues_by_file:
                issues_by_file[file_path] = []
            issues_by_file[file_path].append((line_num, operation_type, code_snippet))
        
        proposal.affected_files = [
            AffectedFile(
                path=file_path,
                line_range=f"{min(l for l, _, _ in locations)}-{max(l for l, _, _ in locations)}",
                severity=Severity.CRITICAL,
            )
            for file_path, locations in issues_by_file.items()
        ]
        
        # Strategy 1: Add explicit timeouts
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Add explicit timeout to all operations",
                description=(
                    f"Add timeout parameter to all network/IO operations. "
                    f"HTTP: timeout=30, DB: connect_timeout=5, Socket: settimeout(10). "
                    f"Example: 'requests.get(url, timeout=30)'"
                ),
                effort_estimate=EffortEstimate.TRIVIAL,
                prerequisite_actions=[
                    "Add timeout to all requests.* calls (e.g., timeout=30)",
                    "Add timeout to all DB connections (e.g., connect_timeout=5)",
                    "Add timeout to all socket operations",
                    "Document timeout values and rationale",
                ],
                assumptions=[
                    "Timeout values can be determined from SLAs",
                    "Timeouts are acceptable (operations may fail)",
                ],
                risks=[
                    "May fail slow-but-valid operations",
                    "Requires tuning timeout values",
                ],
            )
        )
        
        # Strategy 2: Use global timeout defaults
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Configure global timeout defaults",
                description=(
                    f"Set default timeouts in HTTP client sessions. "
                    f"Example: 'session = requests.Session(); session.timeout = 30' or "
                    f"configure http.client defaults."
                ),
                effort_estimate=EffortEstimate.SMALL,
                prerequisite_actions=[
                    "Create configured HTTP session singleton",
                    "Set default timeout on session",
                    "Replace all requests.* calls with session.* calls",
                    "Add per-endpoint overrides where needed",
                ],
                assumptions=[
                    "All HTTP calls can use same session",
                    "Single default timeout is reasonable",
                ],
                risks=[
                    "May not fit all use cases",
                    "Overrides still need manual configuration",
                ],
            )
        )
        
        proposal.confidence_level = 95
        proposal.confidence_explanation = (
            f"Very high confidence: operations without 'timeout=' parameter. "
            f"This is a known reliability anti-pattern."
        )
        
        self.patterns_matched.append("missing_timeouts")
        
        return proposal
    
    def _detect_silent_failures(
        self,
        repository_path: str,
    ) -> IntelligenceProposal | None:
        """Detect exception handling that silently swallows errors."""
        issues = self._scan_for_silent_failures(repository_path)
        
        if not issues:
            return None
        
        proposal = IntelligenceProposal()
        proposal.bug_class = BugClass.RELIABILITY_ANTI_PATTERNS
        proposal.severity = Severity.MEDIUM
        
        issue_count = len(issues)
        
        proposal.problem_statement = (
            f"Found {issue_count} exception handlers that silently swallow errors. "
            f"'except: pass' and bare except hide failures and make debugging impossible."
        )
        
        proposal.risk_explanation = (
            f"Silent failures hide critical bugs. Error occurs, gets caught, no logging, "
            f"execution continues with invalid state. Impact: data corruption, partial failures "
            f"that cascade, impossible to debug production issues. "
            f"'It works on my machine' syndrome. Users experience mysterious bugs."
        )
        
        proposal.root_cause_hypothesis = (
            f"Developers add 'except: pass' to silence errors during development. "
            f"Common in: quick fixes, prototypes, 'works for me' code. "
            f"Left in production by accident or laziness."
        )
        
        # Group issues by file
        issues_by_file = {}
        for file_path, line_num, failure_type, code_snippet in issues:
            if file_path not in issues_by_file:
                issues_by_file[file_path] = []
            issues_by_file[file_path].append((line_num, failure_type, code_snippet))
        
        proposal.affected_files = [
            AffectedFile(
                path=file_path,
                line_range=f"{min(l for l, _, _ in locations)}-{max(l for l, _, _ in locations)}",
                severity=Severity.MEDIUM,
            )
            for file_path, locations in issues_by_file.items()
        ]
        
        # Strategy 1: Add logging to exception handlers
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Add logging to all exception handlers",
                description=(
                    f"Replace 'except: pass' with 'except Exception as e: logger.exception(e)'. "
                    f"Minimum: log error with context. Better: log + metrics + alert."
                ),
                effort_estimate=EffortEstimate.TRIVIAL,
                prerequisite_actions=[
                    "Add logger.exception() to all except blocks",
                    "Include context (request ID, user ID, input)",
                    "Verify logs are aggregated and searchable",
                ],
                assumptions=[
                    "Logging infrastructure exists",
                    "Logs are monitored",
                ],
                risks=[
                    "Minimal risk, dramatically improves debuggability",
                ],
            )
        )
        
        # Strategy 2: Use specific exception types
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Replace bare except with specific types",
                description=(
                    f"Catch specific exceptions (JSONDecodeError, ConnectionError) not bare 'except:'. "
                    f"Prevents hiding unexpected errors. "
                    f"Example: 'except (JSONDecodeError, ValueError) as e: ...' not 'except:'"
                ),
                effort_estimate=EffortEstimate.SMALL,
                prerequisite_actions=[
                    "Identify what exceptions are expected",
                    "Replace 'except:' with specific exception types",
                    "Let unexpected exceptions propagate",
                ],
                assumptions=[
                    "Expected exceptions can be identified",
                    "Unexpected exceptions should crash (fail fast)",
                ],
                risks=[
                    "May allow unhandled exceptions",
                    "Requires understanding exception hierarchy",
                ],
            )
        )
        
        proposal.confidence_level = 100
        proposal.confidence_explanation = (
            f"Absolute confidence: 'except: pass' and bare except are universally bad. "
            f"No false positives."
        )
        
        self.patterns_matched.append("silent_failures")
        
        return proposal
    
    def _detect_blocking_in_async(
        self,
        repository_path: str,
    ) -> IntelligenceProposal | None:
        """Detect blocking operations in async functions."""
        issues = self._scan_for_blocking_async(repository_path)
        
        if not issues:
            return None
        
        proposal = IntelligenceProposal()
        proposal.bug_class = BugClass.RELIABILITY_ANTI_PATTERNS
        proposal.severity = Severity.HIGH
        
        issue_count = len(issues)
        
        proposal.problem_statement = (
            f"Found {issue_count} blocking operations in async functions. "
            f"time.sleep(), requests.*, open() block the event loop."
        )
        
        proposal.risk_explanation = (
            f"Blocking in async code destroys concurrency. One blocking call freezes entire event loop. "
            f"All concurrent operations stall. Impact: request latency spike, throughput collapse, "
            f"timeouts. Defeats purpose of async. This is a CRITICAL async programming error."
        )
        
        proposal.root_cause_hypothesis = (
            f"Developers new to async use sync libraries in async functions. "
            f"Common: time.sleep instead of asyncio.sleep, requests instead of aiohttp, "
            f"open() instead of aiofiles. Works but blocks entire loop."
        )
        
        # Group issues by file
        issues_by_file = {}
        for file_path, line_num, blocking_op, code_snippet in issues:
            if file_path not in issues_by_file:
                issues_by_file[file_path] = []
            issues_by_file[file_path].append((line_num, blocking_op, code_snippet))
        
        proposal.affected_files = [
            AffectedFile(
                path=file_path,
                line_range=f"{min(l for l, _, _ in locations)}-{max(l for l, _, _ in locations)}",
                severity=Severity.HIGH,
            )
            for file_path, locations in issues_by_file.items()
        ]
        
        # Strategy 1: Replace with async equivalents
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Replace blocking calls with async equivalents",
                description=(
                    f"time.sleep → asyncio.sleep, requests → aiohttp, open → aiofiles, "
                    f"psycopg2 → asyncpg. Use 'await' for all IO operations."
                ),
                effort_estimate=EffortEstimate.MEDIUM,
                prerequisite_actions=[
                    "Install async libraries (aiohttp, aiofiles, asyncpg)",
                    "Replace sync calls with async equivalents",
                    "Add 'await' to all async calls",
                    "Test concurrency improvement",
                ],
                assumptions=[
                    "Async libraries available for dependencies",
                    "Team comfortable with async/await",
                ],
                risks=[
                    "May require significant refactoring",
                    "Async libraries have different APIs",
                ],
            )
        )
        
        # Strategy 2: Use run_in_executor for blocking code
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Run blocking code in thread pool executor",
                description=(
                    f"Use 'await loop.run_in_executor(None, blocking_func)' to run blocking code in thread. "
                    f"Prevents blocking event loop. Use for legacy sync libraries."
                ),
                effort_estimate=EffortEstimate.SMALL,
                prerequisite_actions=[
                    "Wrap blocking calls in sync functions",
                    "Use 'await loop.run_in_executor(None, func)' for each call",
                    "Configure thread pool size appropriately",
                ],
                assumptions=[
                    "Blocking operations are thread-safe",
                    "Thread pool overhead is acceptable",
                ],
                risks=[
                    "Adds thread overhead",
                    "May not scale as well as true async",
                ],
            )
        )
        
        proposal.confidence_level = 90
        proposal.confidence_explanation = (
            f"Very high confidence: detected blocking operations in async functions. "
            f"This is a well-known anti-pattern."
        )
        
        self.patterns_matched.append("blocking_in_async")
        
        return proposal
    
    def _scan_for_retry_patterns(self, repository_path: str) -> List[Tuple[str, int, str, str]]:
        """Scan files for retry patterns without backoff."""
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
                            # Check for retry patterns
                            if 'retry' in line.lower() or ('for' in line and 'range' in line):
                                # Check if backoff/sleep/delay present nearby
                                context = ''.join(lines[max(0, line_num-1):min(line_num+5, len(lines))])
                                if 'retry' in context.lower() and not any(word in context.lower() for word in ['sleep', 'backoff', 'delay', 'wait']):
                                    issues.append((rel_path, line_num, 'retry_no_backoff', line.strip()))
                            
                            # Check for immediate continue in except
                            if 'except' in line and 'continue' in line:
                                issues.append((rel_path, line_num, 'immediate_retry', line.strip()))
                
                except Exception:
                    continue
        
        return issues
    
    def _scan_for_missing_timeouts(self, repository_path: str) -> List[Tuple[str, int, str, str]]:
        """Scan files for operations without timeouts."""
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
                            # Check for requests without timeout
                            if 'requests.' in line and '(' in line:
                                if 'timeout' not in line:
                                    issues.append((rel_path, line_num, 'http_request', line.strip()))
                            
                            # Check for socket without timeout
                            if 'socket.socket(' in line:
                                if 'settimeout' not in line:
                                    issues.append((rel_path, line_num, 'socket', line.strip()))
                            
                            # Check for DB connection without timeout
                            if '.connect(' in line and 'timeout' not in line:
                                issues.append((rel_path, line_num, 'db_connection', line.strip()))
                
                except Exception:
                    continue
        
        return issues
    
    def _scan_for_silent_failures(self, repository_path: str) -> List[Tuple[str, int, str, str]]:
        """Scan files for silent failure patterns."""
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
                            # Check for bare except
                            if re.match(r'^\s*except\s*:\s*$', line):
                                issues.append((rel_path, line_num, 'bare_except', line.strip()))
                            
                            # Check for except: pass
                            if re.search(r'except[^:]*:\s*pass', line):
                                issues.append((rel_path, line_num, 'pass_except', line.strip()))
                            
                            # Check for except without logging
                            if line.strip().startswith('except') and ':' in line:
                                # Check next few lines for log/print/raise
                                next_lines = ''.join(lines[line_num:min(line_num+3, len(lines))])
                                if not any(word in next_lines for word in ['log', 'print', 'raise', 'raise']):
                                    if 'pass' not in next_lines and next_lines.strip():
                                        issues.append((rel_path, line_num, 'silent_except', line.strip()))
                
                except Exception:
                    continue
        
        return issues
    
    def _scan_for_blocking_async(self, repository_path: str) -> List[Tuple[str, int, str, str]]:
        """Scan files for blocking operations in async functions."""
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
                        
                        # Find async functions
                        async_funcs = []
                        for i, line in enumerate(lines):
                            if re.match(r'^\s*async\s+def\s+\w+', line):
                                async_funcs.append(i)
                        
                        # Check for blocking operations in async functions
                        for func_line in async_funcs:
                            # Check next 50 lines (rough function scope)
                            for offset in range(1, min(50, len(lines) - func_line)):
                                line = lines[func_line + offset]
                                line_num = func_line + offset + 1
                                
                                # End of function (next def or class)
                                if re.match(r'^\s*(def|class|async\s+def)\s+', line):
                                    break
                                
                                # Check for blocking operations
                                if 'time.sleep(' in line:
                                    issues.append((rel_path, line_num, 'time.sleep', line.strip()))
                                elif 'requests.' in line:
                                    issues.append((rel_path, line_num, 'requests', line.strip()))
                                elif re.search(r'\bopen\(', line):
                                    issues.append((rel_path, line_num, 'open', line.strip()))
                
                except Exception:
                    continue
        
        return issues
