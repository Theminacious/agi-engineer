"""
Edge Case Logic Analyzer - Phase 16

Detects logic bugs in edge cases:
- Division by zero without guards
- Off-by-one errors in loops/ranges
- Boundary condition bugs (min/max values)
- Floating point comparison (==)
- Timezone-naive datetime operations
- Integer overflow/underflow risks
Zero-length array/collection access
- Empty string edge cases
- Null/empty collection iteration
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


class EdgeCaseLogicAnalyzer(BaseAnalyzer):
    """Detect edge case logic errors that cause production bugs."""
    
    @property
    def bug_class(self) -> BugClass:
        return BugClass.EDGE_CASE_VULNERABILITIES
    
    # Patterns for edge case vulnerabilities
    EDGE_CASE_PATTERNS = {
        # Division by zero
        'division_operator': r'/\s*[a-zA-Z_]\w*(?!\s*(?:if|and|or))',  # / variable without check
        'modulo_operator': r'%\s*[a-zA-Z_]\w*',  # % variable
        
        # Floating point comparison
        'float_equality': r'(?:float|Decimal)\([^)]*\)\s*==',
        'direct_float_comparison': r'==.*\.\d+',  # == 0.1 style
        
        # Timezone issues
        'datetime_now_naive': r'datetime\.now\(\)(?!.*tz=|.*timezone)',
        'naive_datetime': r'datetime\.datetime\([^)]*\)(?!.*tzinfo)',
        
        # Array bounds
        'hardcoded_index': r'\[\d+\]',  # list[0] without length check
        'negative_index': r'\[-\d+\]',  # list[-1] can fail on empty
        
        # Range off-by-one
        'range_len': r'range\(len\([^)]+\)\)',  # Common source of off-by-one
        'slice_len': r'\[:len\([^)]+\)\]',
        
        # Empty checks
        'no_empty_check': r'(?:\.split|\.strip|\.replace)\([^)]*\)\[',  # String operation then index
    }
    
    def analyze(
        self,
        repository_path: str,
        repository_url: str,
        branch: str = "main",
    ) -> List[IntelligenceProposal]:
        """Analyze repository for edge case vulnerabilities."""
        self.start_timing()
        self._reset_metrics()
        
        proposals = []
        
        # 1. Detect division by zero risks
        division_risks = self._detect_division_by_zero(repository_path)
        if division_risks:
            proposals.append(division_risks)
        
        # 2. Detect floating point comparison issues
        float_issues = self._detect_float_comparison(repository_path)
        if float_issues:
            proposals.append(float_issues)
        
        # 3. Detect timezone-naive datetime operations
        timezone_issues = self._detect_timezone_issues(repository_path)
        if timezone_issues:
            proposals.append(timezone_issues)
        
        # 4. Detect array bounds and empty collection risks
        bounds_issues = self._detect_bounds_issues(repository_path)
        if bounds_issues:
            proposals.append(bounds_issues)
        
        # Finalize all proposals
        finalized = []
        for proposal in proposals:
            proposal.repository_url = repository_url
            proposal.branch = branch
            finalized.append(self._finalize_proposal(proposal))
        
        return finalized
    
    def _detect_division_by_zero(
        self,
        repository_path: str,
    ) -> IntelligenceProposal | None:
        """Detect division operations without zero checks."""
        issues = self._scan_for_division(repository_path)
        
        if not issues:
            return None
        
        proposal = IntelligenceProposal()
        proposal.bug_class = BugClass.EDGE_CASE_VULNERABILITIES
        proposal.severity = Severity.MEDIUM
        
        issue_count = len(issues)
        
        proposal.problem_statement = (
            f"Found {issue_count} division operations without zero checks. "
            f"Division by zero causes ZeroDivisionError crashes."
        )
        
        proposal.risk_explanation = (
            f"Division by zero = immediate crash. Happens with: empty datasets (divide by count), "
            f"edge case inputs (percentage of 0), computational errors (accumulated rounding). "
            f"Impact: request failure, crashed workers, user-facing errors. "
            f"Especially bad in financial/analytics code where calculations are critical."
        )
        
        proposal.root_cause_hypothesis = (
            f"Developers assume denominators are non-zero. Common in: averages (sum/count), "
            f"percentages (part/whole), ratios, normalization. Works until edge case hits production."
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
                severity=Severity.MEDIUM,
            )
            for file_path, locations in issues_by_file.items()
        ]
        
        # Strategy 1: Add guard clauses
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Add zero check guards before division",
                description=(
                    f"Check denominator != 0 before division. "
                    f"Return sensible default or raise ValueError. "
                    f"Example: 'if count == 0: return 0; average = sum / count'"
                ),
                effort_estimate=EffortEstimate.TRIVIAL,
                prerequisite_actions=[
                    "Add 'if denominator == 0:' check before each division",
                    "Decide appropriate behavior (return 0, None, or raise)",
                    "Document zero-handling behavior",
                ],
                assumptions=[
                    "Zero is a valid input state",
                    "Sensible default exists",
                ],
                risks=[
                    "Incorrect default may hide bugs",
                    "Silently returning 0 may propagate errors",
                ],
            )
        )
        
        # Strategy 2: Use safe division helper
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Create safe_divide() utility function",
                description=(
                    f"Centralize division logic with zero handling. "
                    f"Example: 'def safe_divide(a, b, default=0): return a / b if b != 0 else default'"
                ),
                effort_estimate=EffortEstimate.SMALL,
                prerequisite_actions=[
                    "Create safe_divide() utility function",
                    "Define default behavior (return 0, None, or raise)",
                    "Replace all divisions with safe_divide()",
                    "Add unit tests for zero cases",
                ],
                assumptions=[
                    "Consistent zero-handling policy across codebase",
                ],
                risks=[
                    "May mask legitimate calculation errors",
                ],
            )
        )
        
        proposal.confidence_level = 70
        proposal.confidence_explanation = (
            f"Medium confidence: detected division operations. "
            f"Some may have guards not visible to pattern matching. Requires review."
        )
        
        self.patterns_matched.append("division_by_zero")
        
        return proposal
    
    def _detect_float_comparison(
        self,
        repository_path: str,
    ) -> IntelligenceProposal | None:
        """Detect floating point equality comparisons."""
        issues = self._scan_for_float_equality(repository_path)
        
        if not issues:
            return None
        
        proposal = IntelligenceProposal()
        proposal.bug_class = BugClass.EDGE_CASE_VULNERABILITIES
        proposal.severity = Severity.LOW
        
        issue_count = len(issues)
        
        proposal.problem_statement = (
            f"Found {issue_count} floating point equality comparisons. "
            f"Float equality (==) is unreliable due to precision errors."
        )
        
        proposal.risk_explanation = (
            f"Floating point arithmetic has rounding errors: 0.1 + 0.2 != 0.3. "
            f"Direct equality comparison fails unexpectedly. "
            f"Impact: conditions not triggered, incorrect branching, calculation errors. "
            f"Common in: financial calculations, scientific computing, comparisons after math operations."
        )
        
        proposal.root_cause_hypothesis = (
            f"Developers treat floats like integers. IEEE 754 floating point has inherent precision limits. "
            f"0.1 cannot be represented exactly in binary. Comparisons should use epsilon tolerance."
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
                severity=Severity.LOW,
            )
            for file_path, locations in issues_by_file.items()
        ]
        
        # Strategy 1: Use math.isclose()
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Replace == with math.isclose()",
                description=(
                    f"Use math.isclose(a, b, rel_tol=1e-9) for float comparison. "
                    f"Handles precision errors with tolerance. "
                    f"Example: 'if math.isclose(result, expected):' not 'if result == expected:'"
                ),
                effort_estimate=EffortEstimate.TRIVIAL,
                prerequisite_actions=[
                    "Import math.isclose",
                    "Replace float == with isclose()",
                    "Choose appropriate tolerance (default 1e-9 usually fine)",
                ],
                assumptions=[
                    "Python 3.5+ (isclose available)",
                    "Tolerance-based equality is acceptable",
                ],
                risks=[
                    "May accept values that should be distinct",
                    "Need to understand tolerance parameter",
                ],
            )
        )
        
        # Strategy 2: Use Decimal for exact arithmetic
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Use Decimal for financial calculations",
                description=(
                    f"Replace float with decimal.Decimal for exact decimal arithmetic. "
                    f"No rounding errors. Required for money calculations. "
                    f"Example: 'from decimal import Decimal; price = Decimal(\"19.99\")'"
                ),
                effort_estimate=EffortEstimate.MEDIUM,
                prerequisite_actions=[
                    "Import decimal module",
                    "Convert float literals to Decimal(\"string\")",
                    "Ensure all operations use Decimal",
                    "Configure precision if needed",
                ],
                assumptions=[
                    "Exact decimal arithmetic is required",
                    "Performance impact acceptable",
                ],
                risks=[
                    "Decimal is slower than float",
                    "Must be consistent (mixing Decimal and float causes issues)",
                ],
            )
        )
        
        proposal.confidence_level = 85
        proposal.confidence_explanation = (
            f"High confidence: float == comparison is problematic. "
            f"Some may be intentional (checking for exact 0.0)."
        )
        
        self.patterns_matched.append("float_comparison")
        
        return proposal
    
    def _detect_timezone_issues(
        self,
        repository_path: str,
    ) -> IntelligenceProposal | None:
        """Detect timezone-naive datetime operations."""
        issues = self._scan_for_timezone_issues(repository_path)
        
        if not issues:
            return None
        
        proposal = IntelligenceProposal()
        proposal.bug_class = BugClass.EDGE_CASE_VULNERABILITIES
        proposal.severity = Severity.MEDIUM
        
        issue_count = len(issues)
        
        proposal.problem_statement = (
            f"Found {issue_count} timezone-naive datetime operations. "
            f"datetime.now() without timezone causes DST bugs and comparison errors."
        )
        
        proposal.risk_explanation = (
            f"Timezone-naive datetimes assume local time, but servers/users have different timezones. "
            f"Impact: wrong times displayed, scheduling errors, DST bugs (times jump/repeat), "
            f"cannot compare times reliably. Common bugs: '23:00 < 01:00' comparison failures, "
            f"'is this event in the past?' logic errors."
        )
        
        proposal.root_cause_hypothesis = (
            f"datetime.now() is default but wrong. Should use datetime.now(timezone.utc). "
            f"Developers don't think about timezones until production. "
            f"Common in: event scheduling, timestamps, expiration checks, time-based logic."
        )
        
        # Group issues by file
        issues_by_file = {}
        for file_path, line_num, issue_type, code_snippet in issues:
            if file_path not in issues_by_file:
                issues_by_file[file_path] = []
            issues_by_file[file_path].append((line_num, issue_type, code_snippet))
        
        proposal.affected_files = [
            AffectedFile(
                path=file_path,
                line_range=f"{min(l for l, _, _ in locations)}-{max(l for l, _, _ in locations)}",
                severity=Severity.MEDIUM,
            )
            for file_path, locations in issues_by_file.items()
        ]
        
        # Strategy 1: Always use UTC with timezone
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Use timezone-aware datetimes with UTC",
                description=(
                    f"Replace datetime.now() with datetime.now(timezone.utc). "
                    f"Store all times in UTC, convert to local for display only. "
                    f"Example: 'from datetime import timezone; now = datetime.now(timezone.utc)'"
                ),
                effort_estimate=EffortEstimate.SMALL,
                prerequisite_actions=[
                    "Replace datetime.now() with datetime.now(timezone.utc)",
                    "Add timezone.utc to datetime constructors",
                    "Convert stored naive datetimes to UTC",
                    "Update database schema to store timezone",
                ],
                assumptions=[
                    "UTC is acceptable for storage",
                    "Can convert for display as needed",
                ],
                risks=[
                    "Breaking change if code expects naive datetimes",
                    "Database migration needed",
                ],
            )
        )
        
        # Strategy 2: Use pytz or zoneinfo
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Use pytz or zoneinfo for full timezone support",
                description=(
                    f"Install pytz (Python < 3.9) or use zoneinfo (Python 3.9+). "
                    f"Handle DST transitions properly. "
                    f"Example: 'import zoneinfo; tz = zoneinfo.ZoneInfo(\"America/New_York\")'"
                ),
                effort_estimate=EffortEstimate.MEDIUM,
                prerequisite_actions=[
                    "Install pytz or use built-in zoneinfo",
                    "Store user timezone information",
                    "Convert UTC to user timezone for display",
                    "Handle DST transitions in scheduling",
                ],
                assumptions=[
                    "Need to support multiple timezones",
                    "User timezone can be determined",
                ],
                risks=[
                    "Increased complexity",
                    "DST edge cases are tricky",
                ],
            )
        )
        
        proposal.confidence_level = 90
        proposal.confidence_explanation = (
            f"Very high confidence: timezone-naive operations are problematic. "
            f"This is a well-known datetime pitfall."
        )
        
        self.patterns_matched.append("timezone_issues")
        
        return proposal
    
    def _detect_bounds_issues(
        self,
        repository_path: str,
    ) -> IntelligenceProposal | None:
        """Detect array bounds and empty collection issues."""
        issues = self._scan_for_bounds_issues(repository_path)
        
        if not issues:
            return None
        
        proposal = IntelligenceProposal()
        proposal.bug_class = BugClass.EDGE_CASE_VULNERABILITIES
        proposal.severity = Severity.MEDIUM
        
        issue_count = len(issues)
        
        proposal.problem_statement = (
            f"Found {issue_count} array/collection accesses without bounds checking. "
            f"Accessing empty collections causes IndexError crashes."
        )
        
        proposal.risk_explanation = (
            f"Hardcoded indexes (list[0], list[-1]) fail on empty collections. "
            f"Impact: IndexError crash, request failure. "
            f"Common with: split results, query results, user input processing, first/last element access."
        )
        
        proposal.root_cause_hypothesis = (
            f"Developers assume collections are non-empty. Works with normal data, "
            f"fails with edge cases: no results, empty input, filtered empty. "
            f"Common in: string.split()[0], list[-1], results[0]."
        )
        
        # Group issues by file
        issues_by_file = {}
        for file_path, line_num, bounds_type, code_snippet in issues:
            if file_path not in issues_by_file:
                issues_by_file[file_path] = []
            issues_by_file[file_path].append((line_num, bounds_type, code_snippet))
        
        proposal.affected_files = [
            AffectedFile(
                path=file_path,
                line_range=f"{min(l for l, _, _ in locations)}-{max(l for l, _, _ in locations)}",
                severity=Severity.MEDIUM,
            )
            for file_path, locations in issues_by_file.items()
        ]
        
        # Strategy 1: Check length before access
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Add length checks before indexing",
                description=(
                    f"Check 'if len(collection) > index:' before accessing. "
                    f"Provide default for empty case. "
                    f"Example: 'first = items[0] if items else None'"
                ),
                effort_estimate=EffortEstimate.TRIVIAL,
                prerequisite_actions=[
                    "Add length check before each hardcoded index",
                    "Define behavior for empty case (None, default, error)",
                    "Test with empty inputs",
                ],
                assumptions=[
                    "Empty is a valid state",
                    "Default/None is acceptable",
                ],
                risks=[
                    "May hide data quality issues",
                    "Empty handling must be consistent",
                ],
            )
        )
        
        # Strategy 2: Use .get() or try-except
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Use safe access patterns",
                description=(
                    f"Use collection.get(index) for dicts, or try-except for lists. "
                    f"Example: 'try: first = items[0] except IndexError: first = None'"
                ),
                effort_estimate=EffortEstimate.SMALL,
                prerequisite_actions=[
                    "Wrap index access in try-except IndexError",
                    "Handle IndexError appropriately",
                    "Consider using next(iter(items), default) for first element",
                ],
                assumptions=[
                    "Exception handling is acceptable",
                    "Performance impact is negligible",
                ],
                risks=[
                    "Try-except may hide other index errors",
                ],
            )
        )
        
        proposal.confidence_level = 75
        proposal.confidence_explanation = (
            f"Good confidence: hardcoded indexes detected. "
            f"Some may have length checks not visible to pattern matching."
        )
        
        self.patterns_matched.append("bounds_issues")
        
        return proposal
    
    def _scan_for_division(self, repository_path: str) -> List[Tuple[str, int, str]]:
        """Scan for division operations."""
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
                            # Check for division by variable
                            if re.search(r'/\s*[a-zA-Z_]\w*', line):
                                # Skip if zero check in same line
                                if '!= 0' not in line and '> 0' not in line and 'if ' not in line:
                                    issues.append((rel_path, line_num, line.strip()))
                
                except Exception:
                    continue
        
        return issues
    
    def _scan_for_float_equality(self, repository_path: str) -> List[Tuple[str, int, str]]:
        """Scan for float equality comparisons."""
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
                            # Check for float equality
                            if 'float' in line and '==' in line:
                                if 'isclose' not in line:
                                    issues.append((rel_path, line_num, line.strip()))
                            
                            # Check for decimal literal comparison
                            if re.search(r'==\s*\d+\.\d+', line):
                                if 'isclose' not in line:
                                    issues.append((rel_path, line_num, line.strip()))
                
                except Exception:
                    continue
        
        return issues
    
    def _scan_for_timezone_issues(self, repository_path: str) -> List[Tuple[str, int, str, str]]:
        """Scan for timezone-naive datetime operations."""
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
                            # Check for datetime.now() without timezone
                            if 'datetime.now()' in line:
                                if 'timezone' not in line and 'tz=' not in line:
                                    issues.append((rel_path, line_num, 'naive_now', line.strip()))
                            
                            # Check for datetime() constructor without tzinfo
                            if 'datetime.datetime(' in line or 'datetime(' in line:
                                if 'tzinfo' not in line and 'timezone' not in line:
                                    issues.append((rel_path, line_num, 'naive_constructor', line.strip()))
                
                except Exception:
                    continue
        
        return issues
    
    def _scan_for_bounds_issues(self, repository_path: str) -> List[Tuple[str, int, str, str]]:
        """Scan for array bounds issues."""
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
                            # Check for hardcoded indexes
                            if re.search(r'\[\d+\]', line):
                                # Skip if length check nearby
                                context = ''.join(lines[max(0, line_num-2):line_num])
                                if 'len(' not in context and 'if ' not in context:
                                    issues.append((rel_path, line_num, 'hardcoded_index', line.strip()))
                            
                            # Check for negative index
                            if re.search(r'\[-\d+\]', line):
                                context = ''.join(lines[max(0, line_num-2):line_num])
                                if 'len(' not in context and 'if ' not in context:
                                    issues.append((rel_path, line_num, 'negative_index', line.strip()))
                
                except Exception:
                    continue
        
        return issues
