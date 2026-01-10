"""Architecture Agent - Design patterns, SOLID principles, and code quality."""

import ast
import time
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple
from collections import defaultdict

from .base_agent import BaseAgent, AgentResult, AgentType, AgentIssue, IssueSeverity


class ArchitectureAgent(BaseAgent):
    """Specialized agent for architecture and design pattern analysis."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize ArchitectureAgent."""
        super().__init__(AgentType.ARCHITECTURE, config)
        self.max_class_size = config.get('max_class_size', 200) if config else 200
        self.max_function_size = config.get('max_function_size', 30) if config else 30
        self.max_parameters = config.get('max_parameters', 3) if config else 3
        self.max_methods_per_class = config.get('max_methods_per_class', 12) if config else 12
    
    async def analyze(self, repo_path: str, files: List[str]) -> AgentResult:
        """Analyze repository for architecture issues.
        
        Args:
            repo_path: Path to repository root
            files: List of files to analyze
            
        Returns:
            AgentResult with architecture findings
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
        """Analyze a Python file for architecture issues."""
        issues = []
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            try:
                tree = ast.parse(content)
                lines = content.split('\n')
                
                # Analyze classes
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        issues.extend(self._analyze_class(node, relative_path, lines))
                    elif isinstance(node, ast.FunctionDef):
                        issues.extend(self._analyze_function(node, relative_path, lines))
                
                # Check module-level design
                issues.extend(self._analyze_module_design(tree, relative_path, content))
                
            except SyntaxError:
                pass
                
        except Exception as e:
            self.logger.warning(f"Error analyzing {relative_path}: {e}")
        
        return issues
    
    def _analyze_class(self, node: ast.ClassDef, file_path: str, lines: List[str]) -> List[AgentIssue]:
        """Analyze a class for architectural issues."""
        issues = []
        
        # Check class size
        class_lines = self._count_class_lines(node)
        if class_lines > self.max_class_size:
            issues.append(AgentIssue(
                file_path=file_path,
                line_number=node.lineno,
                issue_type="ARCH_LARGE_CLASS",
                severity=IssueSeverity.MEDIUM,
                title=f"Large Class: {node.name} ({class_lines} lines)",
                description=f"Class '{node.name}' is too large ({class_lines} lines). Large classes violate Single Responsibility Principle.",
                recommendation=f"Split into smaller classes. Target: <{self.max_class_size} lines per class",
                tags=['architecture', 'solid', 'srp'],
                confidence=1.0,
            ))
        
        # Check number of methods
        methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
        if len(methods) > 20:
            issues.append(AgentIssue(
                file_path=file_path,
                line_number=node.lineno,
                issue_type="ARCH_TOO_MANY_METHODS",
                severity=IssueSeverity.MEDIUM,
                title=f"Too Many Methods: {node.name} ({len(methods)} methods)",
                description=f"Class '{node.name}' has {len(methods)} methods. This suggests multiple responsibilities.",
                recommendation="Apply Single Responsibility Principle - split into focused classes",
                tags=['architecture', 'solid', 'srp'],
                confidence=0.85,
            ))
        
        # Check for God Object (many instance variables)
        instance_vars = self._count_instance_variables(node)
        if instance_vars > 15:
            issues.append(AgentIssue(
                file_path=file_path,
                line_number=node.lineno,
                issue_type="ARCH_GOD_OBJECT",
                severity=IssueSeverity.HIGH,
                title=f"God Object: {node.name} ({instance_vars} instance variables)",
                description=f"Class '{node.name}' has {instance_vars} instance variables. This is a 'God Object' anti-pattern.",
                recommendation="Decompose into smaller, focused classes with clear responsibilities",
                tags=['architecture', 'anti-pattern', 'god-object'],
                confidence=0.9,
            ))
        
        # Check for multiple inheritance (except common patterns)
        if len(node.bases) > 1:
            base_names = [self._get_name(base) for base in node.bases]
            # Allow common patterns like (Base, Mixin)
            if not any('Mixin' in name or 'ABC' in name for name in base_names):
                issues.append(AgentIssue(
                    file_path=file_path,
                    line_number=node.lineno,
                    issue_type="ARCH_MULTIPLE_INHERITANCE",
                    severity=IssueSeverity.LOW,
                    title=f"Multiple Inheritance: {node.name}",
                    description=f"Class '{node.name}' uses multiple inheritance. Consider composition over inheritance.",
                    recommendation="Use composition, mixins, or protocols instead of multiple inheritance",
                    tags=['architecture', 'inheritance'],
                    confidence=0.6,
                ))
        
        # Check for tight coupling (many imports/dependencies)
        dependencies = self._count_class_dependencies(node)
        if dependencies > 10:
            issues.append(AgentIssue(
                file_path=file_path,
                line_number=node.lineno,
                issue_type="ARCH_HIGH_COUPLING",
                severity=IssueSeverity.MEDIUM,
                title=f"High Coupling: {node.name}",
                description=f"Class '{node.name}' depends on {dependencies} different classes/modules.",
                recommendation="Apply Dependency Inversion Principle - depend on abstractions, not concretions",
                tags=['architecture', 'solid', 'dip', 'coupling'],
                confidence=0.7,
            ))
        
        return issues
    
    def _analyze_function(self, node: ast.FunctionDef, file_path: str, lines: List[str]) -> List[AgentIssue]:
        """Analyze a function for architectural issues."""
        issues = []
        
        # Skip magic methods and property setters
        if node.name.startswith('__') and node.name.endswith('__'):
            return issues
        
        # Check function size
        func_lines = self._count_function_lines(node)
        if func_lines > self.max_function_size:
            issues.append(AgentIssue(
                file_path=file_path,
                line_number=node.lineno,
                issue_type="ARCH_LARGE_FUNCTION",
                severity=IssueSeverity.MEDIUM,
                title=f"Large Function: {node.name} ({func_lines} lines)",
                description=f"Function '{node.name}' is too large ({func_lines} lines). Extract smaller functions.",
                recommendation=f"Split into smaller functions. Target: <{self.max_function_size} lines per function",
                tags=['architecture', 'function-size'],
                confidence=1.0,
            ))
        
        # Check parameter count
        param_count = len(node.args.args)
        if param_count > self.max_parameters:
            issues.append(AgentIssue(
                file_path=file_path,
                line_number=node.lineno,
                issue_type="ARCH_TOO_MANY_PARAMS",
                severity=IssueSeverity.LOW,
                title=f"Too Many Parameters: {node.name} ({param_count} params)",
                description=f"Function '{node.name}' has {param_count} parameters. This makes it hard to use and test.",
                recommendation="Group related parameters into objects or use **kwargs with validation",
                tags=['architecture', 'parameters'],
                confidence=0.9,
            ))
        
        # Check for feature envy (accessing another object's data frequently)
        feature_envy = self._detect_feature_envy(node)
        if feature_envy:
            for obj_name, access_count in feature_envy.items():
                if access_count > 5:
                    issues.append(AgentIssue(
                        file_path=file_path,
                        line_number=node.lineno,
                        issue_type="ARCH_FEATURE_ENVY",
                        severity=IssueSeverity.LOW,
                        title=f"Feature Envy: {node.name} → {obj_name}",
                        description=f"Function '{node.name}' accesses '{obj_name}' {access_count} times. Consider moving logic there.",
                        recommendation=f"Move this method to '{obj_name}' class or refactor responsibilities",
                        tags=['architecture', 'code-smell', 'feature-envy'],
                        confidence=0.65,
                    ))
        
        return issues
    
    def _analyze_module_design(self, tree: ast.AST, file_path: str, content: str) -> List[AgentIssue]:
        """Analyze module-level design issues."""
        issues = []
        
        # Check module size
        lines = content.split('\n')
        code_lines = len([l for l in lines if l.strip() and not l.strip().startswith('#')])
        
        if code_lines > 1000:
            issues.append(AgentIssue(
                file_path=file_path,
                line_number=1,
                issue_type="ARCH_LARGE_MODULE",
                severity=IssueSeverity.MEDIUM,
                title=f"Large Module ({code_lines} lines)",
                description=f"Module has {code_lines} lines of code. Large modules are hard to maintain.",
                recommendation="Split into multiple focused modules",
                tags=['architecture', 'module-size'],
                confidence=1.0,
            ))
        
        # Check for too many imports (high coupling)
        import_count = sum(1 for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom)))
        if import_count > 20:
            issues.append(AgentIssue(
                file_path=file_path,
                line_number=1,
                issue_type="ARCH_TOO_MANY_IMPORTS",
                severity=IssueSeverity.MEDIUM,
                title=f"Too Many Imports ({import_count})",
                description=f"Module has {import_count} import statements, indicating high coupling",
                recommendation="Reduce dependencies or split module into smaller focused units",
                tags=['architecture', 'coupling'],
                confidence=0.85,
            ))
        
        # Check for God Module (too many classes)
        class_count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
        if class_count > 10:
            issues.append(AgentIssue(
                file_path=file_path,
                line_number=1,
                issue_type="ARCH_GOD_MODULE",
                severity=IssueSeverity.MEDIUM,
                title=f"God Module ({class_count} classes)",
                description=f"Module contains {class_count} classes - too many responsibilities",
                recommendation="Split into separate modules by domain or layer",
                tags=['architecture', 'god-module'],
                confidence=0.9,
            ))
        
        # Check for circular dependencies (heuristic: mutual imports)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module)
        
        # Count imports
        if len(imports) > 30:
            issues.append(AgentIssue(
                file_path=file_path,
                line_number=1,
                issue_type="ARCH_TOO_MANY_IMPORTS",
                severity=IssueSeverity.LOW,
                title=f"Too Many Imports ({len(imports)})",
                description=f"Module has {len(imports)} imports. This suggests high coupling.",
                recommendation="Reduce dependencies, consider facade pattern or dependency injection",
                tags=['architecture', 'coupling', 'imports'],
                confidence=0.7,
            ))
        
        return issues
    
    def _count_class_lines(self, node: ast.ClassDef) -> int:
        """Count lines in a class."""
        if not hasattr(node, 'end_lineno'):
            return 0
        return node.end_lineno - node.lineno + 1
    
    def _count_function_lines(self, node: ast.FunctionDef) -> int:
        """Count lines in a function."""
        if not hasattr(node, 'end_lineno'):
            return 0
        return node.end_lineno - node.lineno + 1
    
    def _count_instance_variables(self, node: ast.ClassDef) -> int:
        """Count instance variables in a class."""
        instance_vars = set()
        
        for child in ast.walk(node):
            if isinstance(child, ast.Attribute):
                if isinstance(child.value, ast.Name) and child.value.id == 'self':
                    instance_vars.add(child.attr)
        
        return len(instance_vars)
    
    def _count_class_dependencies(self, node: ast.ClassDef) -> int:
        """Count dependencies of a class (rough heuristic)."""
        dependencies = set()
        
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                # Skip built-ins and self
                if child.id not in ['self', 'cls', 'True', 'False', 'None']:
                    dependencies.add(child.id)
        
        return len(dependencies)
    
    def _detect_feature_envy(self, node: ast.FunctionDef) -> Dict[str, int]:
        """Detect feature envy pattern."""
        attribute_access = defaultdict(int)
        
        for child in ast.walk(node):
            if isinstance(child, ast.Attribute):
                if isinstance(child.value, ast.Name):
                    obj_name = child.value.id
                    if obj_name != 'self':
                        attribute_access[obj_name] += 1
        
        return dict(attribute_access)
    
    def _get_name(self, node: ast.AST) -> str:
        """Get name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return ''
    
    def _calculate_metrics(self, issues: List[AgentIssue], files: List[str]) -> Dict[str, Any]:
        """Calculate architecture metrics."""
        severity_counts = {}
        for issue in issues:
            severity = issue.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        issue_types = {}
        for issue in issues:
            issue_types[issue.issue_type] = issue_types.get(issue.issue_type, 0) + 1
        
        # Calculate architecture score
        high_count = severity_counts.get('high', 0)
        medium_count = severity_counts.get('medium', 0)
        
        architecture_score = max(0, 100 - (high_count * 12) - (medium_count * 6))
        
        return {
            'files_analyzed': len(files),
            'total_issues': len(issues),
            'severity_breakdown': severity_counts,
            'issue_types': issue_types,
            'architecture_score': architecture_score,
            'design_violations': high_count + medium_count,
        }
    
    def _generate_summary(self, issues: List[AgentIssue], metrics: Dict[str, Any]) -> str:
        """Generate human-readable summary."""
        total = len(issues)
        violations = metrics['design_violations']
        score = metrics['architecture_score']
        
        if total == 0:
            return "✅ No significant architecture issues detected. Architecture score: 100/100"
        
        summary_parts = [f"Found {total} architecture issue{'s' if total != 1 else ''}."]
        
        if violations > 0:
            summary_parts.append(f"⚠️ {violations} design violation{'s' if violations != 1 else ''} detected.")
        
        summary_parts.append(f"Architecture score: {score}/100")
        
        return " ".join(summary_parts)
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get agent capabilities."""
        return {
            'name': 'Architecture Agent',
            'description': 'Analyzes design patterns, SOLID principles, and code structure',
            'supported_languages': ['Python'],
            'checks': [
                'Class size analysis',
                'Function complexity',
                'Parameter count validation',
                'SOLID principles (SRP, DIP)',
                'God Object detection',
                'Feature Envy detection',
                'High coupling detection',
                'Module size analysis',
            ],
            'metrics': ['architecture_score', 'design_violations'],
        }
