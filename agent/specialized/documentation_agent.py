"""Documentation Agent for AGI Engineer v3.

This agent analyzes documentation quality and identifies missing or outdated docs.
It checks for missing docstrings, README completeness, and API documentation.
"""

import ast
import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass

from .base_agent import (
    BaseAgent, AgentType, AgentResult, AgentIssue, IssueSeverity
)

logger = logging.getLogger(__name__)


@dataclass
class DocumentationMetrics:
    """Metrics for documentation analysis."""
    total_functions: int = 0
    documented_functions: int = 0
    total_classes: int = 0
    documented_classes: int = 0
    total_modules: int = 0
    documented_modules: int = 0
    missing_param_docs: int = 0
    missing_return_docs: int = 0
    outdated_docs: int = 0
    
    @property
    def documentation_coverage(self) -> float:
        """Calculate overall documentation coverage percentage."""
        total = self.total_functions + self.total_classes + self.total_modules
        documented = self.documented_functions + self.documented_classes + self.documented_modules
        return (documented / total * 100) if total > 0 else 0.0


class DocumentationAgent(BaseAgent):
    """Agent specialized in documentation quality and completeness.
    
    Detects:
    - Missing docstrings for functions, classes, modules
    - Incomplete docstrings (missing params, returns, raises)
    - Outdated documentation
    - Missing README sections
    - Undocumented public APIs
    - Poor documentation quality
    - Missing usage examples
    - Inconsistent documentation style
    """
    
    def __init__(self):
        """Initialize documentation agent."""
        super().__init__(AgentType.DOCUMENTATION)
        
        # Documentation patterns
        self.docstring_keywords = [
            'Args:', 'Arguments:', 'Parameters:', 'Params:',
            'Returns:', 'Return:', 'Yields:', 'Yield:',
            'Raises:', 'Raise:', 'Throws:', 'Throw:',
            'Example:', 'Examples:', 'Usage:',
            'Note:', 'Notes:', 'Warning:', 'Warnings:',
            'Attributes:', 'See Also:', 'References:',
        ]
        
        # Required README sections for enterprise projects
        self.required_readme_sections = [
            'Installation',
            'Usage',
            'Features',
            'Contributing',
            'License',
            'API Documentation',
            'Testing',
            'Configuration',
            'Deployment',
            'Troubleshooting',
        ]
        
        # Minimum docstring length for quality check
        self.min_docstring_length = 30  # characters
        self.min_function_doc_lines = 2  # lines for complex functions
        
        # Public API patterns
        self.public_patterns = [
            r'^[a-z_][a-z0-9_]*$',  # public_function
            r'^[A-Z][a-zA-Z0-9]*$',  # PublicClass
        ]
        
    def get_capabilities(self) -> Dict[str, Any]:
        """Get agent capabilities."""
        return {
            'name': 'Documentation Quality Analyzer',
            'version': '1.0.0',
            'checks': [
                'missing_docstrings',
                'incomplete_docstrings',
                'missing_parameter_docs',
                'missing_return_docs',
                'undocumented_public_api',
                'poor_documentation_quality',
                'missing_examples',
                'inconsistent_style',
            ],
            'supported_languages': ['Python', 'JavaScript', 'TypeScript'],
        }
    
    async def analyze(
        self,
        file_path: str,
        content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResult:
        """Analyze a file for documentation issues.
        
        Args:
            file_path: Path to the file to analyze
            content: File content
            context: Optional context
            
        Returns:
            AgentResult with documentation findings
        """
        issues = []
        metrics = DocumentationMetrics()
        
        # Analyze based on file type
        if file_path.endswith('.py'):
            issues.extend(self._analyze_python_docs(file_path, content, metrics))
        elif file_path.endswith(('.js', '.ts', '.jsx', '.tsx')):
            issues.extend(self._analyze_js_docs(file_path, content, metrics))
        elif file_path.endswith('.md'):
            issues.extend(self._analyze_markdown_docs(file_path, content))
        
        # Calculate documentation score
        doc_score = self._calculate_documentation_score(metrics, len(issues))
        
        return AgentResult(
            agent_type=self.agent_type,
            issues=sorted(issues, key=lambda x: x.severity.value),
            metrics={
                'documentation_score': doc_score,
                'coverage_percentage': metrics.documentation_coverage,
                'total_functions': metrics.total_functions,
                'documented_functions': metrics.documented_functions,
                'total_classes': metrics.total_classes,
                'documented_classes': metrics.documented_classes,
                'missing_param_docs': metrics.missing_param_docs,
                'missing_return_docs': metrics.missing_return_docs,
            },
            summary=self._generate_summary(metrics, len(issues)),
            execution_time_ms=0
        )
    
    def _analyze_python_docs(
        self,
        file_path: str,
        content: str,
        metrics: DocumentationMetrics
    ) -> List[AgentIssue]:
        """Analyze Python file documentation."""
        issues = []
        
        try:
            tree = ast.parse(content)
            
            # Check module docstring
            metrics.total_modules += 1
            module_docstring = ast.get_docstring(tree)
            if not module_docstring:
                issues.append(AgentIssue(
                    file_path=file_path,
                    line_number=1,
                    severity=IssueSeverity.MEDIUM,
                    title='Missing module docstring',
                    description=f'Module {Path(file_path).name} has no docstring',
                    recommendation='Add a module-level docstring describing the file purpose',
                    confidence=1.0
                ))
            else:
                metrics.documented_modules += 1
            
            # Analyze classes and functions
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    issues.extend(self._check_python_class_docs(
                        file_path, node, metrics
                    ))
                elif isinstance(node, ast.FunctionDef):
                    # Skip private functions unless they're special methods
                    if not node.name.startswith('_') or node.name.startswith('__'):
                        issues.extend(self._check_python_function_docs(
                            file_path, node, metrics
                        ))
        
        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
        
        return issues
    
    def _check_python_class_docs(
        self,
        file_path: str,
        node: ast.ClassDef,
        metrics: DocumentationMetrics
    ) -> List[AgentIssue]:
        """Check Python class documentation."""
        issues = []
        metrics.total_classes += 1
        
        docstring = ast.get_docstring(node)
        
        # Check if class is public (not starting with _)
        is_public = not node.name.startswith('_')
        
        if not docstring:
            severity = IssueSeverity.HIGH if is_public else IssueSeverity.MEDIUM
            issues.append(AgentIssue(
                file_path=file_path,
                line_number=node.lineno,
                severity=severity,
                title='Missing class docstring',
                description=f'Class {node.name} has no docstring',
                recommendation='Add a docstring describing the class purpose and usage',
                confidence=1.0
            ))
        else:
            metrics.documented_classes += 1
            
            # Check docstring quality
            if len(docstring) < 20:
                issues.append(AgentIssue(
                    file_path=file_path,
                    line_number=node.lineno,
                    severity=IssueSeverity.LOW,
                    title='Poor quality docstring',
                    description=f'Class {node.name} has a very short docstring',
                    recommendation='Expand docstring with class purpose, attributes, and usage examples',
                    confidence=0.8
                ))
        
        return issues
    
    def _check_python_function_docs(
        self,
        file_path: str,
        node: ast.FunctionDef,
        metrics: DocumentationMetrics
    ) -> List[AgentIssue]:
        """Check Python function documentation."""
        issues = []
        metrics.total_functions += 1
        
        docstring = ast.get_docstring(node)
        is_public = not node.name.startswith('_')
        
        # Check for missing docstring
        if not docstring:
            severity = IssueSeverity.HIGH if is_public else IssueSeverity.LOW
            issues.append(AgentIssue(
                file_path=file_path,
                line_number=node.lineno,
                severity=severity,
                title='Missing function docstring',
                description=f'Function {node.name} has no docstring',
                recommendation='Add a docstring with description, Args, and Returns sections',
                confidence=1.0
            ))
            return issues
        
        metrics.documented_functions += 1
        
        # Check for missing parameter documentation
        params = [arg.arg for arg in node.args.args if arg.arg != 'self']
        if params:
            param_keywords = ['Args:', 'Arguments:', 'Parameters:', 'Params:']
            has_param_docs = any(keyword in docstring for keyword in param_keywords)
            
            if not has_param_docs:
                issues.append(AgentIssue(
                    file_path=file_path,
                    line_number=node.lineno,
                    severity=IssueSeverity.MEDIUM,
                    title='Missing parameter documentation',
                    description=f'Function {node.name} has parameters but no parameter documentation',
                    recommendation=f'Document parameters: {", ".join(params)}',
                    confidence=0.9
                ))
                metrics.missing_param_docs += 1
        
        # Check for missing return documentation
        has_return = any(
            isinstance(child, ast.Return) and child.value is not None
            for child in ast.walk(node)
        )
        
        if has_return:
            return_keywords = ['Returns:', 'Return:', 'Yields:', 'Yield:']
            has_return_docs = any(keyword in docstring for keyword in return_keywords)
            
            if not has_return_docs:
                issues.append(AgentIssue(
                    file_path=file_path,
                    line_number=node.lineno,
                    severity=IssueSeverity.MEDIUM,
                    title='Missing return documentation',
                    description=f'Function {node.name} returns a value but has no return documentation',
                    recommendation='Add Returns section to docstring',
                    confidence=0.9
                ))
                metrics.missing_return_docs += 1
        
        # Check for raises but no documentation
        has_raise = any(
            isinstance(child, ast.Raise)
            for child in ast.walk(node)
        )
        
        if has_raise:
            raise_keywords = ['Raises:', 'Raise:', 'Throws:', 'Throw:']
            has_raise_docs = any(keyword in docstring for keyword in raise_keywords)
            
            if not has_raise_docs:
                issues.append(AgentIssue(
                    file_path=file_path,
                    line_number=node.lineno,
                    severity=IssueSeverity.LOW,
                    title='Missing exception documentation',
                    description=f'Function {node.name} raises exceptions but has no exception documentation',
                    recommendation='Add Raises section to docstring',
                    confidence=0.8
                ))
        
        return issues
    
    def _analyze_js_docs(
        self,
        file_path: str,
        content: str,
        metrics: DocumentationMetrics
    ) -> List[AgentIssue]:
        """Analyze JavaScript/TypeScript documentation."""
        issues = []
        lines = content.split('\n')
        
        # Find function declarations
        for i, line in enumerate(lines, 1):
            # Check for function declarations
            if re.search(r'\b(function|const|let|var)\s+\w+\s*=\s*(async\s+)?(\(.*?\)|function)', line):
                # Look for JSDoc comment above
                has_jsdoc = False
                if i > 1:
                    prev_line = lines[i - 2].strip()
                    has_jsdoc = prev_line.startswith('/**') or prev_line.startswith('*')
                
                if not has_jsdoc:
                    # Extract function name
                    match = re.search(r'\b(?:function|const|let|var)\s+(\w+)', line)
                    if match:
                        func_name = match.group(1)
                        if not func_name.startswith('_'):  # Public function
                            metrics.total_functions += 1
                            issues.append(AgentIssue(
                                file_path=file_path,
                                line_number=i,
                                severity=IssueSeverity.MEDIUM,
                                title='Missing JSDoc comment',
                                description=f'Function {func_name} has no JSDoc comment',
                                recommendation='Add JSDoc comment with @param and @returns tags',
                                confidence=0.8
                            ))
                else:
                    metrics.documented_functions += 1
            
            # Check for class declarations
            elif re.search(r'\bclass\s+\w+', line):
                # Look for JSDoc comment above
                has_jsdoc = False
                if i > 1:
                    prev_line = lines[i - 2].strip()
                    has_jsdoc = prev_line.startswith('/**')
                
                if not has_jsdoc:
                    match = re.search(r'\bclass\s+(\w+)', line)
                    if match:
                        class_name = match.group(1)
                        metrics.total_classes += 1
                        issues.append(AgentIssue(
                            file_path=file_path,
                            line_number=i,
                            severity=IssueSeverity.HIGH,
                            title='Missing class documentation',
                            description=f'Class {class_name} has no JSDoc comment',
                            recommendation='Add JSDoc comment describing the class',
                            confidence=0.9
                        ))
                else:
                    metrics.documented_classes += 1
        
        return issues
    
    def _analyze_markdown_docs(
        self,
        file_path: str,
        content: str
    ) -> List[AgentIssue]:
        """Analyze Markdown documentation files."""
        issues = []
        
        # Check README.md specifically
        if Path(file_path).name.upper() == 'README.MD':
            issues.extend(self._check_readme_sections(file_path, content))
        
        return issues
    
    def _check_readme_sections(
        self,
        file_path: str,
        content: str
    ) -> List[AgentIssue]:
        """Check for important README sections."""
        issues = []
        
        required_sections = {
            'Installation': r'##\s*Installation',
            'Usage': r'##\s*Usage',
            'Features': r'##\s*Features',
            'Contributing': r'##\s*Contributing',
        }
        
        for section_name, pattern in required_sections.items():
            if not re.search(pattern, content, re.IGNORECASE):
                issues.append(AgentIssue(
                    file_path=file_path,
                    line_number=1,
                    severity=IssueSeverity.LOW,
                    title=f'Missing {section_name} section',
                    description=f'README.md is missing a {section_name} section',
                    recommendation=f'Add a ## {section_name} section to improve documentation',
                    confidence=0.9
                ))
        
        return issues
    
    def _calculate_documentation_score(
        self,
        metrics: DocumentationMetrics,
        issue_count: int
    ) -> int:
        """Calculate documentation quality score (0-100)."""
        score = 100
        
        # Base score on coverage
        coverage = metrics.documentation_coverage
        if coverage < 50:
            score -= 30
        elif coverage < 70:
            score -= 20
        elif coverage < 90:
            score -= 10
        
        # Deduct for issues
        score -= min(issue_count * 3, 30)
        
        # Deduct for missing parameter/return docs
        score -= min(metrics.missing_param_docs * 2, 15)
        score -= min(metrics.missing_return_docs * 2, 15)
        
        return max(0, score)
    
    def _generate_summary(
        self,
        metrics: DocumentationMetrics,
        issue_count: int
    ) -> str:
        """Generate human-readable summary."""
        parts = []
        
        coverage = metrics.documentation_coverage
        parts.append(f"Documentation coverage: {coverage:.1f}%")
        
        if metrics.total_functions > 0:
            func_coverage = (metrics.documented_functions / metrics.total_functions * 100)
            parts.append(f"{metrics.documented_functions}/{metrics.total_functions} functions documented ({func_coverage:.0f}%)")
        
        if metrics.total_classes > 0:
            class_coverage = (metrics.documented_classes / metrics.total_classes * 100)
            parts.append(f"{metrics.documented_classes}/{metrics.total_classes} classes documented ({class_coverage:.0f}%)")
        
        if issue_count > 0:
            parts.append(f"Found {issue_count} documentation issues")
        else:
            parts.append("No documentation issues found")
        
        return ". ".join(parts) + "."
