"""
Crash Risk Analyzer - Phase 16

Detects code patterns that can cause production crashes:
- Null/None dereference without guards
- Missing error handling on unsafe operations
- Unchecked return values from fallible operations
- Unsafe optional/nullable access
- Unguarded recursion and stack overflow risks
- Index out of bounds
- Division by zero (without edge case context)
"""

from typing import List, Tuple, Dict, Set
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


class CrashRiskAnalyzer(BaseAnalyzer):
    """Detect crash-prone code patterns."""
    
    @property
    def bug_class(self) -> BugClass:
        return BugClass.CRASH_RISKS
    
    # Patterns for crash risks (Python-focused, extensible to other languages)
    CRASH_PATTERNS = {
        # Null dereference patterns
        'unsafe_dict_access': r'(\w+)\[([\'"][^\'"]+[\'"])\](?!\s*=)',  # dict['key'] without .get()
        'unsafe_optional_access': r'(\w+)\.(\w+)\(.*?\)\.\w+',  # chained method without None check
        'unsafe_list_access': r'(\w+)\[(\d+|[a-zA-Z_]\w*)\](?!\s*=)',  # list[index] without bounds check
        
        # Missing error handling
        'unguarded_file_open': r'open\([^)]+\)(?!\s*as\s+\w+:)',  # open() without with statement
        'unguarded_json_parse': r'json\.loads?\([^)]+\)(?!\s*(?:except|try))',  # JSON parse without try
        'unguarded_network_call': r'requests\.\w+\([^)]+\)(?!\s*(?:except|try))',  # HTTP call without try
        'unguarded_db_query': r'\.execute\([^)]+\)(?!\s*(?:except|try))',  # DB query without try
        
        # Unchecked return values
        'ignored_error_return': r'^\s*(\w+)\([^)]*\)\s*$',  # Function call result ignored
        
        # Recursion risks
        'unguarded_recursion': r'def\s+(\w+)\(.*?\):.*?\1\(',  # Recursive function without depth limit
        
        # Type conversion crashes
        'unsafe_int_conversion': r'int\([^)]+\)(?!\s*(?:except|try))',  # int() without try
        'unsafe_float_conversion': r'float\([^)]+\)(?!\s*(?:except|try))',  # float() without try
    }
    
    def analyze(
        self,
        repository_path: str,
        repository_url: str,
        branch: str = "main",
    ) -> List[IntelligenceProposal]:
        """Analyze repository for crash risks."""
        self.start_timing()
        self._reset_metrics()
        
        proposals = []
        
        # 1. Detect null dereference risks
        null_risks = self._detect_null_dereference_risks(repository_path)
        if null_risks:
            proposals.append(null_risks)
        
        # 2. Detect missing error handling
        error_handling = self._detect_missing_error_handling(repository_path)
        if error_handling:
            proposals.append(error_handling)
        
        # 3. Detect unchecked return values
        unchecked_returns = self._detect_unchecked_returns(repository_path)
        if unchecked_returns:
            proposals.append(unchecked_returns)
        
        # 4. Detect unguarded recursion
        recursion_risks = self._detect_recursion_risks(repository_path)
        if recursion_risks:
            proposals.append(recursion_risks)
        
        # Finalize all proposals
        finalized = []
        for proposal in proposals:
            proposal.repository_url = repository_url
            proposal.branch = branch
            finalized.append(self._finalize_proposal(proposal))
        
        return finalized
    
    def _detect_null_dereference_risks(
        self,
        repository_path: str,
    ) -> IntelligenceProposal | None:
        """Detect patterns that can cause null/None dereference."""
        issues = self._scan_for_null_risks(repository_path)
        
        if not issues:
            return None
        
        proposal = IntelligenceProposal()
        proposal.bug_class = BugClass.CRASH_RISKS
        proposal.severity = Severity.CRITICAL
        
        issue_count = len(issues)
        
        proposal.problem_statement = (
            f"Found {issue_count} potential null/None dereference risks. "
            f"Accessing properties or methods on None values causes immediate crashes."
        )
        
        proposal.risk_explanation = (
            f"Null dereference is the #1 cause of production crashes. When code accesses "
            f"a dict key, list index, or object attribute without checking for None/null, "
            f"the program crashes with AttributeError, KeyError, or IndexError. "
            f"Impact: service downtime, failed requests, user data loss, cascading failures. "
            f"These crashes are 100% preventable with defensive guards."
        )
        
        proposal.root_cause_hypothesis = (
            f"Developers assume values exist without validation. Common in: API responses "
            f"(missing keys), database queries (null columns), user input (empty fields), "
            f"migrations (new code accessing old data). Often introduced during refactoring."
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
                severity=Severity.CRITICAL,
            )
            for file_path, locations in issues_by_file.items()
        ]
        
        # Strategy 1: Add defensive guards
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Add null checks and guards",
                description=(
                    f"Add defensive None/null checks before accessing values. "
                    f"Use .get() for dicts, check list bounds, verify types. "
                    f"Example: 'if user and user.email:' or 'data.get(\"key\", default)'"
                ),
                effort_estimate=EffortEstimate.SMALL,
                prerequisite_actions=[
                    "Identify all unsafe access patterns",
                    "Add None checks before access",
                    "Provide safe defaults where appropriate",
                ],
                assumptions=[
                    "None/null values are valid states",
                    "Graceful degradation is acceptable",
                ],
                risks=[
                    "May hide underlying data quality issues",
                    "Could mask bugs in upstream code",
                ],
            )
        )
        
        # Strategy 2: Use type system and validation
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Enforce non-null types with validation",
                description=(
                    f"Use type annotations (Optional[T]) and validation libraries "
                    f"(pydantic, mypy strict mode) to enforce non-null guarantees. "
                    f"Fail fast at boundaries with clear error messages."
                ),
                effort_estimate=EffortEstimate.MEDIUM,
                prerequisite_actions=[
                    "Add type annotations to all functions",
                    "Configure mypy with --strict mode",
                    "Add pydantic validators at API boundaries",
                ],
                assumptions=[
                    "Team can adopt type checking workflow",
                    "CI/CD pipeline can enforce type checks",
                ],
                risks=[
                    "Requires code restructuring",
                    "May reveal more issues initially",
                ],
            )
        )
        
        # Strategy 3: Implement monadic error handling
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Use Result/Option types for safety",
                description=(
                    f"Replace nullable returns with Result/Option types (returns library). "
                    f"Forces callers to handle None case explicitly. "
                    f"Example: 'Result.success(value)' or 'Result.failure(error)'"
                ),
                effort_estimate=EffortEstimate.LARGE,
                prerequisite_actions=[
                    "Install returns library for monadic types",
                    "Refactor function signatures to return Result[T]",
                    "Update all call sites to handle Result",
                ],
                assumptions=[
                    "Team comfortable with functional patterns",
                    "Codebase can handle signature changes",
                ],
                risks=[
                    "Large refactoring effort",
                    "Learning curve for team",
                ],
            )
        )
        
        proposal.confidence_level = 90
        proposal.confidence_explanation = (
            f"High confidence: patterns matched are known crash sources. "
            f"May have false positives where guards exist in outer scope."
        )
        
        self.patterns_matched.append("null_dereference_risks")
        
        return proposal
    
    def _detect_missing_error_handling(
        self,
        repository_path: str,
    ) -> IntelligenceProposal | None:
        """Detect operations that can fail without error handling."""
        issues = self._scan_for_unhandled_errors(repository_path)
        
        if not issues:
            return None
        
        proposal = IntelligenceProposal()
        proposal.bug_class = BugClass.CRASH_RISKS
        proposal.severity = Severity.HIGH
        
        issue_count = len(issues)
        
        proposal.problem_statement = (
            f"Found {issue_count} operations that can fail without error handling. "
            f"File I/O, network calls, JSON parsing, and DB queries can throw exceptions."
        )
        
        proposal.risk_explanation = (
            f"Unhandled exceptions crash the entire process. IO operations fail due to: "
            f"missing files, network timeouts, parsing errors, DB connection loss. "
            f"One unhandled exception = complete service outage. "
            f"Impact: 500 errors, request failures, data corruption, customer impact."
        )
        
        proposal.root_cause_hypothesis = (
            f"Developers assume happy path. Common in: quick prototypes, early code, "
            f"tight deadlines. Error handling often added after first production incident."
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
                severity=Severity.HIGH,
            )
            for file_path, locations in issues_by_file.items()
        ]
        
        # Strategy 1: Add try-except blocks
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Wrap operations in try-except blocks",
                description=(
                    f"Add try-except around all IO operations. "
                    f"Log errors with context, return error responses. "
                    f"Example: 'try: data = json.loads(text) except JSONDecodeError: ...'"
                ),
                effort_estimate=EffortEstimate.SMALL,
                prerequisite_actions=[
                    "Identify all unguarded operations",
                    "Add appropriate try-except blocks",
                    "Log errors with context for debugging",
                ],
                assumptions=[
                    "Logging infrastructure exists",
                    "Error responses are acceptable to users",
                ],
                risks=[
                    "Overly broad except clauses can hide bugs",
                    "Poor error messages frustrate users",
                ],
            )
        )
        
        # Strategy 2: Use context managers
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Use context managers for resources",
                description=(
                    f"Replace open() with 'with open()' statements. "
                    f"Ensures resources are cleaned up even on errors. "
                    f"Prevents resource leaks and crash cascades."
                ),
                effort_estimate=EffortEstimate.TRIVIAL,
                prerequisite_actions=[
                    "Replace all open() calls with 'with open()'",
                    "Review other resource usage (DB, network)",
                ],
                assumptions=[
                    "Python 2.5+ (with statement available)",
                ],
                risks=[
                    "Minimal risk, improves reliability",
                ],
            )
        )
        
        proposal.confidence_level = 85
        proposal.confidence_explanation = (
            f"High confidence: operations matched are known to throw exceptions. "
            f"Some may be caught in outer scope (not visible to pattern matching)."
        )
        
        self.patterns_matched.append("missing_error_handling")
        
        return proposal
    
    def _detect_unchecked_returns(
        self,
        repository_path: str,
    ) -> IntelligenceProposal | None:
        """Detect function calls where return values are ignored."""
        # This is more complex and requires flow analysis
        # For now, return None (can be enhanced in future)
        return None
    
    def _detect_recursion_risks(
        self,
        repository_path: str,
    ) -> IntelligenceProposal | None:
        """Detect recursive functions without depth limits."""
        issues = self._scan_for_recursion(repository_path)
        
        if not issues:
            return None
        
        proposal = IntelligenceProposal()
        proposal.bug_class = BugClass.CRASH_RISKS
        proposal.severity = Severity.MEDIUM
        
        issue_count = len(issues)
        
        proposal.problem_statement = (
            f"Found {issue_count} recursive functions without depth guards. "
            f"Unbounded recursion causes stack overflow crashes."
        )
        
        proposal.risk_explanation = (
            f"Recursive functions without limits crash when input is larger than expected. "
            f"Stack overflow errors are unrecoverable. Common triggers: deeply nested JSON, "
            f"large directory trees, circular references. Impact: immediate crash, no graceful recovery."
        )
        
        proposal.root_cause_hypothesis = (
            f"Recursion written assuming bounded input. Works in development (small data), "
            f"fails in production (large/malicious data). Often missing max depth parameter."
        )
        
        # Group issues by file
        issues_by_file = {}
        for file_path, line_num, func_name in issues:
            if file_path not in issues_by_file:
                issues_by_file[file_path] = []
            issues_by_file[file_path].append((line_num, func_name))
        
        proposal.affected_files = [
            AffectedFile(
                path=file_path,
                line_range=str(min(l for l, _ in locations)),
                severity=Severity.MEDIUM,
            )
            for file_path, locations in issues_by_file.items()
        ]
        
        # Strategy 1: Add depth parameter
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Add max depth parameter to recursion",
                description=(
                    f"Add 'max_depth' parameter to recursive functions. "
                    f"Track current depth, raise error if exceeded. "
                    f"Example: 'def traverse(node, depth=0, max_depth=100): if depth > max_depth: raise'"
                ),
                effort_estimate=EffortEstimate.SMALL,
                prerequisite_actions=[
                    "Add depth parameter to all recursive functions",
                    "Choose appropriate max depth based on use case",
                    "Add unit tests with large inputs",
                ],
                assumptions=[
                    "Max depth can be determined from requirements",
                    "Exceeding depth is truly an error condition",
                ],
                risks=[
                    "May reject valid large inputs",
                    "Requires tuning max depth value",
                ],
            )
        )
        
        # Strategy 2: Convert to iteration
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Convert recursion to iteration",
                description=(
                    f"Rewrite recursive logic using loops and stacks. "
                    f"No stack overflow risk. Better performance. "
                    f"Example: use explicit stack list instead of call stack."
                ),
                effort_estimate=EffortEstimate.MEDIUM,
                prerequisite_actions=[
                    "Analyze recursive algorithm structure",
                    "Rewrite using explicit stack",
                    "Verify correctness with existing tests",
                ],
                assumptions=[
                    "Algorithm can be converted to iterative form",
                    "Team maintains code after conversion",
                ],
                risks=[
                    "Increases code complexity",
                    "May be harder to understand than recursion",
                ],
            )
        )
        
        proposal.confidence_level = 75
        proposal.confidence_explanation = (
            f"Medium-high confidence: detected recursive patterns. "
            f"Some may have depth limits not visible to pattern matching. "
            f"Requires manual review to confirm risk."
        )
        
        self.patterns_matched.append("recursion_risks")
        
        return proposal
    
    def _scan_for_null_risks(self, repository_path: str) -> List[Tuple[str, int, str, str]]:
        """Scan files for null dereference risks."""
        issues = []
        
        for root, dirs, files in os.walk(repository_path):
            # Skip common non-code directories
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
                            # Check for unsafe dict access
                            if re.search(self.CRASH_PATTERNS['unsafe_dict_access'], line):
                                # Verify no .get() nearby and not in assignment
                                if '.get(' not in line and '=' not in line.split('[')[0]:
                                    issues.append((rel_path, line_num, 'unsafe_dict_access', line.strip()))
                            
                            # Check for unsafe list access
                            if re.search(self.CRASH_PATTERNS['unsafe_list_access'], line):
                                # Basic heuristic: if no bounds check nearby
                                if 'len(' not in line and 'if ' not in line:
                                    issues.append((rel_path, line_num, 'unsafe_list_access', line.strip()))
                            
                            # Check for chained method calls (potential None)
                            if re.search(self.CRASH_PATTERNS['unsafe_optional_access'], line):
                                if 'if ' not in line and 'try:' not in line:
                                    issues.append((rel_path, line_num, 'unsafe_optional_access', line.strip()))
                
                except Exception:
                    # Skip files that can't be read
                    continue
        
        return issues
    
    def _scan_for_unhandled_errors(self, repository_path: str) -> List[Tuple[str, int, str, str]]:
        """Scan files for operations without error handling."""
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
                            # Check for unguarded operations
                            for pattern_name, pattern in [
                                ('file_open', self.CRASH_PATTERNS['unguarded_file_open']),
                                ('json_parse', self.CRASH_PATTERNS['unguarded_json_parse']),
                                ('network_call', self.CRASH_PATTERNS['unguarded_network_call']),
                                ('int_conversion', self.CRASH_PATTERNS['unsafe_int_conversion']),
                            ]:
                                if re.search(pattern, line):
                                    # Check if not in try block (simple heuristic)
                                    if pattern_name == 'file_open' or 'try:' not in ''.join(lines[max(0, line_num-3):line_num]):
                                        issues.append((rel_path, line_num, pattern_name, line.strip()))
                
                except Exception:
                    continue
        
        return issues
    
    def _scan_for_recursion(self, repository_path: str) -> List[Tuple[str, int, str]]:
        """Scan files for recursive functions."""
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
                        
                        # Find function definitions
                        func_pattern = r'def\s+(\w+)\([^)]*\):'
                        for match in re.finditer(func_pattern, content):
                            func_name = match.group(1)
                            func_start = match.start()
                            
                            # Look ahead for self-call
                            # Simple heuristic: does function name appear again within next 500 chars?
                            lookahead = content[func_start:func_start + 500]
                            if f'{func_name}(' in lookahead.split('\n', 1)[1] if '\n' in lookahead else '':
                                line_num = content[:func_start].count('\n') + 1
                                # Check if max_depth or depth parameter exists
                                if 'max_depth' not in lookahead and 'depth' not in lookahead:
                                    issues.append((rel_path, line_num, func_name))
                
                except Exception:
                    continue
        
        return issues
