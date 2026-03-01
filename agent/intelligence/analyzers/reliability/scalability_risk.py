"""
Scalability Risk Analyzer - Phase 16

Detects patterns that don't scale under load:
- N+1 query patterns (database)
- Nested loops on large collections
-Heavy computation in request path
- Inefficient algorithms (O(n²) or worse)
- Missing pagination
- Unbounded result sets
- Memory-intensive operations in hot path
- Synchronous processing of batch operations
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


class ScalabilityRiskAnalyzer(BaseAnalyzer):
    """Detect code patterns that create scalability bottlenecks."""
    
    @property
    def bug_class(self) -> BugClass:
        return BugClass.SCALABILITY_RISKS
    
    # Patterns for scalability risks
    SCALABILITY_PATTERNS = {
        # N+1 queries (more sophisticated than performance analyzer)
        'query_in_loop': r'for\s+\w+\s+in\s+.*:.*(?:\.query|\.filter|\.get|select|SELECT)',
        'orm_lazy_load': r'for\s+\w+\s+in\s+.*:\s*\w+\.\w+',  # Lazy relationship access
        
        # Nested loops on collections
        'nested_loops': r'for\s+\w+\s+in\s+.*:\s*for\s+\w+\s+in',
        'triple_nested': r'for\s+\w+.*:\s*for\s+\w+.*:\s*for\s+\w+',
        
        # Heavy computation in request path
        'complex_computation': r'(?:def|async def)\s+\w+.*request.*:.*(?:sum|sort|sorted|map|filter)',
        'file_processing_sync': r'(?:def|async def).*:.*(?:csv\.reader|json\.load|xml\.parse)',
        
        # Unbounded queries
        'no_limit_query': r'\.(?:query|filter)\([^)]*\)(?!.*limit\(|.*\[:)\.all\(\)',
        'select_all': r'SELECT.*FROM.*(?!LIMIT|TOP)',
        
        # Missing pagination
        'list_endpoint_no_page': r'@app\.route\([\'"][^\'"]*list[^\'"]*[\'"]\)',  # List endpoint pattern
        
        # In-memory sorting of large data
        'sort_large_data': r'sorted\(.*\.all\(\)',
    }
    
    def analyze(
        self,
        repository_path: str,
        repository_url: str,
        branch: str = "main",
    ) -> List[IntelligenceProposal]:
        """Analyze repository for scalability risks."""
        self.start_timing()
        self._reset_metrics()
        
        proposals = []
        
        # 1. Detect N+1 query patterns
        nplus1 = self._detect_nplus1_queries(repository_path)
        if nplus1:
            proposals.append(nplus1)
        
        # 2. Detect inefficient algorithms
        algorithms = self._detect_inefficient_algorithms(repository_path)
        if algorithms:
            proposals.append(algorithms)
        
        # 3. Detect unbounded queries
        unbounded = self._detect_unbounded_queries(repository_path)
        if unbounded:
            proposals.append(unbounded)
        
        # 4. Detect heavy computation in request handlers
        heavy_compute = self._detect_heavy_computation_in_requests(repository_path)
        if heavy_compute:
            proposals.append(heavy_compute)
        
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
    ) -> IntelligenceProposal | None:
        """Detect N+1 query anti-patterns."""
        issues = self._scan_for_nplus1(repository_path)
        
        if not issues:
            return None
        
        proposal = IntelligenceProposal()
        proposal.bug_class = BugClass.SCALABILITY_RISKS
        proposal.severity = Severity.CRITICAL
        
        issue_count = len(issues)
        
        proposal.problem_statement = (
            f"Found {issue_count} potential N+1 query patterns. "
            f"Queries in loops cause exponential database load and response time."
        )
        
        proposal.risk_explanation = (
            f"N+1 queries are THE #1 scalability killer. Pattern: fetch N items, then query for each item. "
            f"10 users → 11 queries. 1000 users → 1001 queries. Database becomes bottleneck. "
            f"Impact: slow page loads (seconds → minutes), database CPU spike, connection exhaustion, "
            f"cascading failures, complete outage. Scales VERY badly: 10x traffic = 10x queries = complete collapse."
        )
        
        proposal.root_cause_hypothesis = (
            f"ORM lazy loading + loops. Developer fetches collection, iterates, accesses relationships. "
            f"ORM issues query per relationship. Common in: listing pages, API endpoints returning collections, "
            f"report generation. Works in dev (small data), collapses in production (large data, many users)."
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
                severity=Severity.CRITICAL,
            )
            for file_path, locations in issues_by_file.items()
        ]
        
        # Strategy 1: Use eager loading
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Add eager loading with joinedload/selectinload",
                description=(
                    f"Use SQLAlchemy joinedload() or selectinload() to fetch relationships upfront. "
                    f"Reduces N+1 queries to 1-2 queries total. "
                    f"Example: 'query.options(joinedload(User.posts))' or 'select_related()' in Django."
                ),
                effort_estimate=EffortEstimate.SMALL,
                prerequisite_actions=[
                    "Identify which relationships are accessed in loop",
                    "Add joinedload() or selectinload() to query",
                    "Measure query count before/after (should drop dramatically)",
                    "Profile to ensure no other N+1 patterns remain",
                ],
                assumptions=[
                    "ORM supports eager loading (SQLAlchemy, Django ORM do)",
                    "Relationships are defined in models",
                ],
                risks=[
                    "May fetch more data than needed (joinedload)",
                    "Requires understanding ORM loading strategies",
                ],
            )
        )
        
        # Strategy 2: Batch loading
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Implement batch loading with DataLoader pattern",
                description=(
                    f"Collect all IDs, then fetch in one batch query. "
                    f"Use DataLoader (GraphQL pattern) or manual batching. "
                    f"Example: collect user_ids → query WHERE id IN (ids)."
                ),
                effort_estimate=EffortEstimate.MEDIUM,
                prerequisite_actions=[
                    "Collect all foreign keys from loop",
                    "Make single batch query with IN clause",
                    "Map results back to original items",
                    "Consider caching batch results",
                ],
                assumptions=[
                    "Batch size is reasonable (< 1000 IDs)",
                    "Database supports IN queries efficiently",
                ],
                risks=[
                    "Large IN clauses have limits (database-dependent)",
                    "More complex code logic",
                ],
            )
        )
        
        # Strategy 3: Denormalize data
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Denormalize frequently accessed data",
                description=(
                    f"Store computed/joined data directly in main table. "
                    f"Trade storage for query performance. "
                    f"Example: store author_name in posts table instead of joining users."
                ),
                effort_estimate=EffortEstimate.LARGE,
                prerequisite_actions=[
                    "Identify frequently accessed relationships",
                    "Add columns to store denormalized data",
                    "Create migration to populate existing data",
                    "Add triggers/hooks to keep data in sync",
                    "Monitor data consistency",
                ],
                assumptions=[
                    "Data doesn't change frequently",
                    "Storage cost is acceptable",
                    "Consistency can be maintained",
                ],
                risks=[
                    "Data duplication and sync complexity",
                    "Stale data if sync fails",
                    "Increased storage cost",
                ],
            )
        )
        
        proposal.confidence_level = 90
        proposal.confidence_explanation = (
            f"Very high confidence: query patterns in loops are classic N+1. "
            f"Some may have caching or batching not visible to pattern matching."
        )
        
        self.patterns_matched.append("nplus1_queries")
        
        return proposal
    
    def _detect_inefficient_algorithms(
        self,
        repository_path: str,
    ) -> IntelligenceProposal | None:
        """Detect O(n²) and worse algorithms."""
        issues = self._scan_for_nested_loops(repository_path)
        
        if not issues:
            return None
        
        proposal = IntelligenceProposal()
        proposal.bug_class = BugClass.SCALABILITY_RISKS
        proposal.severity = Severity.HIGH
        
        issue_count = len(issues)
        
        proposal.problem_statement = (
            f"Found {issue_count} nested loops that may have O(n²) or worse complexity. "
            f"Performance degrades exponentially with data size."
        )
        
        proposal.risk_explanation = (
            f"Nested loops = O(n²) or O(n³) complexity. 10 items = 100 operations. 1000 items = 1,000,000 operations. "
            f"Impact: timeouts on large datasets, CPU spikes, request backlog, degraded UX. "
            f"Works in dev (small data), fails in production (large data). "
            f"This scales VERY badly: 10x data = 100x slower."
        )
        
        proposal.root_cause_hypothesis = (
            f"Simple nested iteration without considering complexity. "
            f"Common in: data processing, reporting, filtering/joining collections in memory. "
            f"Developer writes straightforward code that works for small datasets."
        )
        
        # Group issues by file
        issues_by_file = {}
        for file_path, line_num, nesting_level, code_snippet in issues:
            if file_path not in issues_by_file:
                issues_by_file[file_path] = []
            issues_by_file[file_path].append((line_num, nesting_level, code_snippet))
        
        proposal.affected_files = [
            AffectedFile(
                path=file_path,
                line_range=f"{min(l for l, _, _ in locations)}-{max(l for l, _, _ in locations)}",
                severity=Severity.HIGH if len(locations) > 3 else Severity.MEDIUM,
            )
            for file_path, locations in issues_by_file.items()
        ]
        
        # Strategy 1: Use hash maps/sets
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Replace inner loop with hash map lookup",
                description=(
                    "Convert inner collection to dict/set for O(1) lookup. "
                    "Changes O(n²) to O(n). "
                    "Example: 'lookup = {item.id: item for item in collection}; ... result = lookup.get(id)'"
                ),
                effort_estimate=EffortEstimate.SMALL,
                prerequisite_actions=[
                    "Identify lookup key in inner loop",
                    "Create dict/set from inner collection",
                    "Replace inner loop with dict lookup",
                    "Profile to confirm performance improvement",
                ],
                assumptions=[
                    "Inner loop does simple lookup/matching",
                    "Items have unique keys",
                ],
                risks=[
                    "Increased memory usage (dict storage)",
                    "May not work for complex matching logic",
                ],
            )
        )
        
        # Strategy 2: Use database JOIN
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Push join logic to database",
                description=(
                    f"Let database do the join instead of nested loops in application. "
                    f"Databases are optimized for joins. "
                    f"Example: use SQL JOIN instead of fetch + loop + lookup."
                ),
                effort_estimate=EffortEstimate.MEDIUM,
                prerequisite_actions=[
                    "Identify data being joined in loops",
                    "Write SQL query with proper JOIN",
                    "Replace nested loops with single query",
                    "Add indexes on join columns",
                ],
                assumptions=[
                    "Data is in database (not external API)",
                    "Database can handle join efficiently",
                ],
                risks=[
                    "Complex queries harder to maintain",
                    "May need query optimization",
                ],
            )
        )
        
        # Strategy 3: Use better algorithm
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Refactor to use efficient algorithm",
                description=(
                    f"Use sort + merge (O(n log n)) or other efficient algorithm. "
                    f"Research algorithm design for specific use case. "
                    f"Example: two-pointer technique for sorted arrays."
                ),
                effort_estimate=EffortEstimate.LARGE,
                prerequisite_actions=[
                    "Analyze what operation is being performed",
                    "Research efficient algorithms (sorting, hashing, trees)",
                    "Implement optimized version",
                    "Add comprehensive tests",
                    "Profile to confirm improvement",
                ],
                assumptions=[
                    "Better algorithm exists for use case",
                    "Team can implement and maintain it",
                ],
                risks=[
                    "Increased code complexity",
                    "May introduce bugs",
                    "Requires algorithm expertise",
                ],
            )
        )
        
        proposal.confidence_level = 70
        proposal.confidence_explanation = (
            f"Medium confidence: nested loops detected but not all are problematic. "
            f"Small bounded loops are fine. Requires manual review of data sizes."
        )
        
        self.patterns_matched.append("inefficient_algorithms")
        
        return proposal
    
    def _detect_unbounded_queries(
        self,
        repository_path: str,
    ) -> IntelligenceProposal | None:
        """Detect queries without LIMIT or pagination."""
        issues = self._scan_for_unbounded_queries(repository_path)
        
        if not issues:
            return None
        
        proposal = IntelligenceProposal()
        proposal.bug_class = BugClass.SCALABILITY_RISKS
        proposal.severity = Severity.HIGH
        
        issue_count = len(issues)
        
        proposal.problem_statement = (
            f"Found {issue_count} database queries without LIMIT or pagination. "
            f"Unbounded queries can return millions of rows."
        )
        
        proposal.risk_explanation = (
            f"Unbounded queries cause OOM and database overload. Query fetches all rows → "
            f"huge memory allocation → GC thrashing → slow response → timeout. "
            f"Impact: service crash, database CPU spike, network saturation. "
            f"Works with 100 rows, fails with 10,000+ rows."
        )
        
        proposal.root_cause_hypothesis = (
            f"Missing pagination on listing endpoints. Common in: get all users, get all products, "
            f"admin dashboards. Starts fine, grows with business until table has millions of rows."
        )
        
        # Group issues by file
        issues_by_file = {}
        for file_path, line_num, query_type, code_snippet in issues:
            if file_path not in issues_by_file:
                issues_by_file[file_path] = []
            issues_by_file[file_path].append((line_num, query_type, code_snippet))
        
        proposal.affected_files = [
            AffectedFile(
                path=file_path,
                line_range=f"{min(l for l, _, _ in locations)}-{max(l for l, _, _ in locations)}",
                severity=Severity.HIGH,
            )
            for file_path, locations in issues_by_file.items()
        ]
        
        # Strategy 1: Add LIMIT clause
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Add LIMIT to all queries",
                description=(
                    f"Add .limit(N) or LIMIT N to queries. "
                    f"Typical: LIMIT 100 or 1000 depending on use case. "
                    f"Example: 'query.limit(100)' or 'SELECT ... LIMIT 100'"
                ),
                effort_estimate=EffortEstimate.TRIVIAL,
                prerequisite_actions=[
                    "Identify appropriate limit for each query",
                    "Add .limit() to ORM queries or LIMIT to SQL",
                    "Update API documentation if behavior changes",
                ],
                assumptions=[
                    "Clients can handle limited results",
                    "Limit is documented",
                ],
                risks=[
                    "May break clients expecting all results",
                    "Need to communicate change",
                ],
            )
        )
        
        # Strategy 2: Implement pagination
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Implement cursor or offset pagination",
                description=(
                    f"Add page/limit parameters for offset pagination or cursor for scalable pagination. "
                    f"Return page metadata (total, has_next). "
                    f"Example: '?page=1&limit=50' or cursor='eyJpZCI6MTIzfQ=='"
                ),
                effort_estimate=EffortEstimate.MEDIUM,
                prerequisite_actions=[
                    "Add pagination parameters to API endpoints",
                    "Implement offset/cursor logic in queries",
                    "Return pagination metadata in responses",
                    "Update API clients to handle pagination",
                    "Add API documentation for pagination",
                ],
                assumptions=[
                    "Clients can be updated for pagination",
                    "API versioning if breaking change",
                ],
                risks=[
                    "Breaking API change if not versioned",
                    "Cursor pagination more complex but more scalable",
                ],
            )
        )
        
        proposal.confidence_level = 85
        proposal.confidence_explanation = (
            f"High confidence: queries with .all() and no .limit() are unbounded. "
            f"Some may be intentional for small tables."
        )
        
        self.patterns_matched.append("unbounded_queries")
        
        return proposal
    
    def _detect_heavy_computation_in_requests(
        self,
        repository_path: str,
    ) -> IntelligenceProposal | None:
        """Detect heavy computation in synchronous request handlers."""
        issues = self._scan_for_heavy_computation(repository_path)
        
        if not issues:
            return None
        
        proposal = IntelligenceProposal()
        proposal.bug_class = BugClass.SCALABILITY_RISKS
        proposal.severity = Severity.MEDIUM
        
        issue_count = len(issues)
        
        proposal.problem_statement = (
            f"Found {issue_count} request handlers with heavy computation. "
            f"Slow operations in request path cause worker exhaustion and high latency."
        )
        
        proposal.risk_explanation = (
            f"Heavy computation blocks request workers. Workers exhausted → new requests queue → timeouts. "
            f"Impact: response time spike, throughput collapse, 503 errors, poor UX. "
            f"Each slow request reduces capacity for fast requests."
        )
        
        proposal.root_cause_hypothesis = (
            f"Synchronous processing of expensive operations. Common: CSV generation, PDF rendering, "
            f"image processing, complex calculations. Should be async background jobs."
        )
        
        # Group issues by file
        issues_by_file = {}
        for file_path, line_num, computation_type, code_snippet in issues:
            if file_path not in issues_by_file:
                issues_by_file[file_path] = []
            issues_by_file[file_path].append((line_num, computation_type, code_snippet))
        
        proposal.affected_files = [
            AffectedFile(
                path=file_path,
                line_range=f"{min(l for l, _, _ in locations)}-{max(l for l, _, _ in locations)}",
                severity=Severity.MEDIUM,
            )
            for file_path, locations in issues_by_file.items()
        ]
        
        # Strategy 1: Move to background jobs
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Move heavy operations to background jobs",
                description=(
                    "Use Celery, RQ, or similar to process asynchronously. "
                    "Request returns immediately with job ID. Client polls for result. "
                    "Example: 'task = generate_report.delay(params); return {\"job_id\": task.id}'"
                ),
                effort_estimate=EffortEstimate.MEDIUM,
                prerequisite_actions=[
                    "Set up task queue (Celery, RQ, etc.)",
                    "Move expensive logic to task function",
                    "Add job status endpoint for polling",
                    "Update clients to poll for results",
                ],
                assumptions=[
                    "Task queue infrastructure available",
                    "Async processing acceptable to users",
                ],
                risks=[
                    "Increased system complexity",
                    "Requires job status management",
                ],
            )
        )
        
        # Strategy 2: Add caching
        proposal.suggested_strategies.append(
            FixStrategy(
                name="Cache expensive computation results",
                description=(
                    f"Use Redis or similar to cache results. "
                    f"Check cache before computing. "
                    f"Example: '@cache.memoize(timeout=3600)' or manual cache checks."
                ),
                effort_estimate=EffortEstimate.SMALL,
                prerequisite_actions=[
                    "Identify cacheable computations",
                    "Add cache layer (Redis, Memcached)",
                    "Wrap operations with cache checks",
                    "Configure appropriate TTL",
                ],
                assumptions=[
                    "Results are cacheable (deterministic)",
                    "Stale data is acceptable for TTL period",
                ],
                risks=[
                    "Cache invalidation complexity",
                    "Stale data issues",
                ],
            )
        )
        
        proposal.confidence_level = 65
        proposal.confidence_explanation = (
            f"Medium confidence: detected operations that are often slow. "
            f"Actual impact depends on data size and frequency."
        )
        
        self.patterns_matched.append("heavy_computation_in_requests")
        
        return proposal
    
    def _scan_for_nplus1(self, repository_path: str) -> List[Tuple[str, int, str]]:
        """Scan for N+1 query patterns."""
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
                            # Check for query/DB operations in loops
                            if 'for ' in line and ' in ' in line:
                                # Check next few lines for query operations
                                context = ''.join(lines[line_num:min(line_num+5, len(lines))])
                                if any(pattern in context for pattern in ['.query', '.filter', '.get(', 'SELECT', 'select']):
                                    issues.append((rel_path, line_num, line.strip()))
                
                except Exception:
                    continue
        
        return issues
    
    def _scan_for_nested_loops(self, repository_path: str) -> List[Tuple[str, int, int, str]]:
        """Scan for nested loop patterns."""
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
                            # Count nesting level
                            if 'for ' in line and ' in ' in line:
                                indent = len(line) - len(line.lstrip())
                                # Check if we're already in a for loop (simple heuristic)
                                nesting_level = 1
                                for prev_line_num in range(max(0, line_num - 10), line_num):
                                    prev_line = lines[prev_line_num]
                                    prev_indent = len(prev_line) - len(prev_line.lstrip())
                                    if 'for ' in prev_line and prev_indent < indent:
                                        nesting_level += 1
                                
                                if nesting_level >= 2:
                                    issues.append((rel_path, line_num, nesting_level, line.strip()))
                
                except Exception:
                    continue
        
        return issues
    
    def _scan_for_unbounded_queries(self, repository_path: str) -> List[Tuple[str, int, str, str]]:
        """Scan for queries without limits."""
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
                            # Check for .all() without .limit()
                            if '.all()' in line:
                                # Check previous lines for .limit()
                                context = ''.join(lines[max(0, line_num-5):line_num])
                                if '.limit(' not in context and 'LIMIT' not in context:
                                    issues.append((rel_path, line_num, 'query_all', line.strip()))
                            
                            # Check for SELECT without LIMIT
                            if re.search(r'SELECT.*FROM', line, re.IGNORECASE):
                                if 'LIMIT' not in line.upper():
                                    issues.append((rel_path, line_num, 'select_no_limit', line.strip()))
                
                except Exception:
                    continue
        
        return issues
    
    def _scan_for_heavy_computation(self, repository_path: str) -> List[Tuple[str, int, str, str]]:
        """Scan for heavy computation in request handlers."""
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
                        
                        # Find request handler functions (Flask/FastAPI patterns)
                        for i, line in enumerate(lines):
                            if '@app.route' in line or '@router.' in line or 'async def' in line:
                                # Check next 30 lines for heavy operations
                                for offset in range(1, min(30, len(lines) - i)):
                                    check_line = lines[i + offset]
                                    line_num = i + offset + 1
                                    
                                    # End of function
                                    if re.match(r'^\s*(def|class|@)', check_line):
                                        break
                                    
                                    # Check for heavy operations
                                    if 'csv.reader' in check_line or 'csv.writer' in check_line:
                                        issues.append((rel_path, line_num, 'csv_processing', check_line.strip()))
                                    elif 'json.load' in check_line or 'json.loads' in check_line:
                                        issues.append((rel_path, line_num, 'json_processing', check_line.strip()))
                                    elif 'sorted(' in check_line:
                                        issues.append((rel_path, line_num, 'sorting', check_line.strip()))
                
                except Exception:
                    continue
        
        return issues
