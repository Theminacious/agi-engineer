"""Performance Agent - Algorithm complexity and performance issue detection."""

import re
import time
import ast
from pathlib import Path
from typing import Dict, List, Any, Set

from .base_agent import BaseAgent, AgentResult, AgentType, AgentIssue, IssueSeverity


class PerformanceAgent(BaseAgent):
    """Specialized agent for performance and algorithmic complexity analysis."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize PerformanceAgent."""
        super().__init__(AgentType.PERFORMANCE, config)
        self.complexity_threshold = config.get('complexity_threshold', 6) if config else 6
    
    async def analyze(self, repo_path: str, files: List[str]) -> AgentResult:
        """Analyze repository for performance issues.
        
        Args:
            repo_path: Path to repository root
            files: List of files to analyze
            
        Returns:
            AgentResult with performance findings
        """
        start_time = time.time()
        issues = []
        
        python_files = self.filter_files(files, ['.py'])
        self.log_analysis_start(repo_path, len(python_files))
        
        for file_path in python_files:
            full_path = Path(repo_path) / file_path
            issues.extend(self._analyze_python_file(str(full_path), file_path))
        
        execution_time = (time.time() - start_time) * 1000
        self.log_analysis_complete(len(issues), execution_time)
        
        metrics = self._calculate_metrics(issues, python_files)
        summary = self._generate_summary(issues, metrics)
        
        return AgentResult(
            agent_type=self.agent_type,
            issues=issues,
            metrics=metrics,
            summary=summary,
            execution_time_ms=execution_time
        )
    
    def _analyze_python_file(self, full_path: str, relative_path: str) -> List[AgentIssue]:
        """Analyze a Python file for performance issues."""
        issues = []
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            try:
                tree = ast.parse(content)
                issues.extend(self._analyze_ast(tree, relative_path, content))
            except SyntaxError:
                pass
                
        except Exception as e:
            self.logger.warning(f"Error analyzing {relative_path}: {e}")
        
        return issues
    
    def _analyze_ast(self, tree: ast.AST, file_path: str, content: str) -> List[AgentIssue]:
        """Analyze AST for performance issues."""
        issues = []
        lines = content.split('\n')
        
        for node in ast.walk(tree):
            # Detect nested loops (O(n^2) or worse)
            if isinstance(node, (ast.For, ast.While)):
                nested_loops = self._count_nested_loops(node)
                if nested_loops >= 2:
                    complexity = f"O(n^{nested_loops})"
                    issues.append(AgentIssue(
                        file_path=file_path,
                        line_number=node.lineno,
                        issue_type="PERF_NESTED_LOOPS",
                        severity=IssueSeverity.HIGH if nested_loops >= 3 else IssueSeverity.MEDIUM,
                        title=f"Nested Loops Detected ({complexity})",
                        description=f"Found {nested_loops} levels of nested loops, complexity: {complexity}",
                        recommendation="Consider using hash maps, sets, or refactoring to reduce complexity",
                        code_snippet=lines[node.lineno - 1].strip() if node.lineno <= len(lines) else "",
                        tags=['performance', 'complexity', 'nested-loops'],
                        confidence=0.9,
                    ))
            
            # Detect list comprehension inside loop
            if isinstance(node, (ast.For, ast.While)):
                for child in ast.walk(node):
                    if isinstance(child, ast.ListComp) and child != node:
                        issues.append(AgentIssue(
                            file_path=file_path,
                            line_number=child.lineno,
                            issue_type="PERF_LISTCOMP_IN_LOOP",
                            severity=IssueSeverity.MEDIUM,
                            title="List Comprehension Inside Loop",
                            description="Creating lists repeatedly in loops is inefficient",
                            recommendation="Move list comprehension outside loop or use generator expression",
                            code_snippet=lines[child.lineno - 1].strip() if child.lineno <= len(lines) else "",
                            tags=['performance', 'list-comprehension'],
                            confidence=0.8,
                        ))
                        break  # Only report once per loop
            
            # Detect repeated attribute access in loop
            if isinstance(node, (ast.For, ast.While)):
                repeated_attrs = self._find_repeated_attributes(node)
                for attr_name, count in repeated_attrs.items():
                    if count > 3:
                        issues.append(AgentIssue(
                            file_path=file_path,
                            line_number=node.lineno,
                            issue_type="PERF_REPEATED_ATTR",
                            severity=IssueSeverity.LOW,
                            title=f"Repeated Attribute Access: {attr_name}",
                            description=f"Attribute '{attr_name}' accessed {count} times in loop",
                            recommendation=f"Cache '{attr_name}' before loop: attr = obj.{attr_name}",
                            tags=['performance', 'attribute-access'],
                            confidence=0.7,
                        ))
            
            # Detect string concatenation in loop
            if isinstance(node, (ast.For, ast.While)):
                has_string_concat = self._has_string_concatenation(node)
                if has_string_concat:
                    issues.append(AgentIssue(
                        file_path=file_path,
                        line_number=node.lineno,
                        issue_type="PERF_STRING_CONCAT",
                        severity=IssueSeverity.MEDIUM,
                        title="String Concatenation in Loop",
                        description="Using += for strings in loop creates new string each time",
                        recommendation="Use list and ''.join() or io.StringIO() for better performance",
                        tags=['performance', 'string-concat'],
                        confidence=0.85,
                    ))
            
            # Detect use of list() on large data
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == 'list':
                    issues.append(AgentIssue(
                        file_path=file_path,
                        line_number=node.lineno,
                        issue_type="PERF_LIST_CONVERSION",
                        severity=IssueSeverity.LOW,
                        title="Potential Unnecessary list() Conversion",
                        description="Converting large iterables to list consumes memory",
                        recommendation="Consider using generator or iterator if full list not needed",
                        tags=['performance', 'memory'],
                        confidence=0.5,
                    ))
            
            # Detect N+1 query pattern in loops
            if isinstance(node, (ast.For, ast.While)):
                has_query_in_loop = self._has_query_in_loop(node)
                if has_query_in_loop:
                    issues.append(AgentIssue(
                        file_path=file_path,
                        line_number=node.lineno,
                        issue_type="PERF_N_PLUS_ONE",
                        severity=IssueSeverity.HIGH,
                        title="Potential N+1 Query Problem",
                        description="Database query detected inside loop - causes N+1 query problem",
                        recommendation="Use select_related(), prefetch_related(), or JOIN to fetch data in one query",
                        tags=['performance', 'database', 'n+1'],
                        confidence=0.75,
                    ))
            
            # Detect large function complexity
            if isinstance(node, ast.FunctionDef):
                complexity = self._calculate_cyclomatic_complexity(node)
                if complexity > self.complexity_threshold:
                    severity = IssueSeverity.HIGH if complexity > 20 else IssueSeverity.MEDIUM
                    issues.append(AgentIssue(
                        file_path=file_path,
                        line_number=node.lineno,
                        issue_type="PERF_HIGH_COMPLEXITY",
                        severity=severity,
                        title=f"High Cyclomatic Complexity: {complexity}",
                        description=f"Function '{node.name}' has complexity {complexity} (threshold: {self.complexity_threshold})",
                        recommendation="Refactor into smaller functions or simplify control flow",
                        tags=['performance', 'complexity', 'maintainability'],
                        confidence=1.0,
                    ))
        
        return issues
    
    def _count_nested_loops(self, node: ast.AST, depth: int = 1) -> int:
        """Count depth of nested loops."""
        max_depth = depth
        
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.For, ast.While)):
                child_depth = self._count_nested_loops(child, depth + 1)
                max_depth = max(max_depth, child_depth)
        
        return max_depth
    
    def _find_repeated_attributes(self, node: ast.AST) -> Dict[str, int]:
        """Find attributes accessed multiple times in a loop."""
        attributes = {}
        
        for child in ast.walk(node):
            if isinstance(child, ast.Attribute):
                attr_name = self._get_full_attribute_name(child)
                attributes[attr_name] = attributes.get(attr_name, 0) + 1
        
        return {k: v for k, v in attributes.items() if v > 1}
    
    def _get_full_attribute_name(self, node: ast.Attribute) -> str:
        """Get full dotted attribute name."""
        parts = [node.attr]
        current = node.value
        
        while isinstance(current, ast.Attribute):
            parts.insert(0, current.attr)
            current = current.value
        
        if isinstance(current, ast.Name):
            parts.insert(0, current.id)
        
        return '.'.join(parts)
    
    def _has_string_concatenation(self, node: ast.AST) -> bool:
        """Check if loop has string concatenation with +=."""
        for child in ast.walk(node):
            if isinstance(child, ast.AugAssign):
                if isinstance(child.op, ast.Add):
                    # Check if either side is a string (heuristic)
                    return True
        return False
    
    def _has_query_in_loop(self, node: ast.AST) -> bool:
        """Detect potential database queries in loop."""
        query_patterns = ['get', 'filter', 'all', 'select', 'query', 'fetch']
        
        for child in ast.walk(node):
            if isinstance(child, ast.Attribute):
                if child.attr in query_patterns:
                    return True
            elif isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    if child.func.id in query_patterns:
                        return True
        
        return False
    
    def _calculate_cyclomatic_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            # Add 1 for each decision point
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, (ast.And, ast.Or)):
                complexity += 1
        
        return complexity
    
    def _calculate_metrics(self, issues: List[AgentIssue], files: List[str]) -> Dict[str, Any]:
        """Calculate performance metrics."""
        severity_counts = {}
        for issue in issues:
            severity = issue.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        issue_types = {}
        for issue in issues:
            issue_types[issue.issue_type] = issue_types.get(issue.issue_type, 0) + 1
        
        # Calculate performance score
        high_count = severity_counts.get('high', 0)
        medium_count = severity_counts.get('medium', 0)
        
        performance_score = max(0, 100 - (high_count * 15) - (medium_count * 5))
        
        return {
            'files_analyzed': len(files),
            'total_issues': len(issues),
            'severity_breakdown': severity_counts,
            'issue_types': issue_types,
            'performance_score': performance_score,
            'high_impact_issues': high_count,
        }
    
    def _generate_summary(self, issues: List[AgentIssue], metrics: Dict[str, Any]) -> str:
        """Generate human-readable summary."""
        total = len(issues)
        high = metrics['high_impact_issues']
        score = metrics['performance_score']
        
        if total == 0:
            return "✅ No significant performance issues detected. Performance score: 100/100"
        
        summary_parts = [f"Found {total} performance issue{'s' if total != 1 else ''}."]
        
        if high > 0:
            summary_parts.append(f"⚠️ {high} high-impact issue{'s' if high != 1 else ''} may significantly affect performance.")
        
        summary_parts.append(f"Performance score: {score}/100")
        
        return " ".join(summary_parts)
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get agent capabilities."""
        return {
            'name': 'Performance Agent',
            'description': 'Analyzes algorithmic complexity and performance bottlenecks',
            'supported_languages': ['Python'],
            'checks': [
                'Nested loop detection (O(n^2), O(n^3))',
                'Cyclomatic complexity analysis',
                'N+1 query detection',
                'String concatenation in loops',
                'Repeated attribute access',
                'List comprehension inefficiencies',
                'Memory allocation patterns',
            ],
            'metrics': ['performance_score', 'complexity_levels'],
        }
