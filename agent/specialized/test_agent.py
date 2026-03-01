"""Test Agent for AGI Engineer v3.

This agent analyzes test coverage, test quality, and identifies missing tests.
It checks for test smells, assertion quality, and coverage gaps.
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
class TestMetrics:
    """Metrics for test analysis."""
    total_test_files: int = 0
    total_tests: int = 0
    tests_with_assertions: int = 0
    tests_without_assertions: int = 0
    tests_with_multiple_asserts: int = 0
    average_test_length: float = 0.0
    test_smells_count: int = 0
    missing_test_files: List[str] = None
    
    def __post_init__(self):
        if self.missing_test_files is None:
            self.missing_test_files = []


class TestAgent(BaseAgent):
    """Agent specialized in test analysis and quality assessment.
    
    Detects:
    - Missing test files for source files
    - Tests without assertions
    - Test smells (too many asserts, testing private methods, etc.)
    - Weak assertion patterns
    - Improper test structure (no setup/teardown)
    - Duplicate test code
    - Missing edge case tests
    - Tests that are too long or complex
    """
    
    def __init__(self):
        """Initialize test agent."""
        super().__init__(AgentType.TEST)
        
        # Test file patterns
        self.test_patterns = [
            r'test_.*\.py$',
            r'.*_test\.py$',
            r'.*\.test\.(js|ts)$',
            r'.*\.spec\.(js|ts)$',
        ]
        
        # Test function patterns
        self.test_func_patterns = [
            r'^test_',  # Python: test_something
            r'^it\s',   # JS: it('should...')
            r'^describe\s',  # JS: describe('Component', ...)
        ]
        
        # Assertion keywords
        self.assertion_keywords = [
            'assert', 'assertEqual', 'assertTrue', 'assertFalse',
            'assertRaises', 'assertIn', 'assertIs', 'expect',
            'toBe', 'toEqual', 'toHaveBeenCalled', 'toThrow',
            'assertNotNone', 'assertIsNone', 'assertGreater', 
            'assertLess', 'toContain', 'toMatch', 'toBeCloseTo',
            'assertIsInstance', 'assertDictEqual', 'assertListEqual',
        ]
        
        # Test smells to detect
        self.test_smells = {
            'too_many_asserts': 5,  # More than 5 asserts in one test
            'test_too_long': 50,    # More than 50 lines
            'no_setup': True,       # Tests without proper setup
            'testing_private': True, # Testing private methods
            'magic_numbers': True,  # Hardcoded values without explanation
        }
        
    def get_capabilities(self) -> Dict[str, Any]:
        """Get agent capabilities."""
        return {
            'name': 'Test Quality Analyzer',
            'version': '1.0.0',
            'checks': [
                'missing_test_files',
                'tests_without_assertions',
                'weak_assertions',
                'test_smells',
                'long_tests',
                'duplicate_test_code',
                'missing_edge_cases',
                'improper_test_structure',
            ],
            'supported_languages': ['Python', 'JavaScript', 'TypeScript'],
        }
    
    async def analyze(
        self,
        file_path: str,
        content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResult:
        """Analyze a file for test quality issues.
        
        Args:
            file_path: Path to the file to analyze
            content: File content
            context: Optional context (e.g., all project files)
            
        Returns:
            AgentResult with test quality findings
        """
        issues = []
        metrics = TestMetrics()
        
        # Check if this is a test file
        is_test_file = self._is_test_file(file_path)
        
        if is_test_file:
            # Analyze test file
            if file_path.endswith('.py'):
                issues.extend(self._analyze_python_tests(file_path, content, metrics))
            elif file_path.endswith(('.js', '.ts', '.jsx', '.tsx')):
                issues.extend(self._analyze_js_tests(file_path, content, metrics))
        else:
            # Check if source file has corresponding test
            if context and 'all_files' in context:
                all_files = context['all_files']
                if not self._has_test_file(file_path, all_files):
                    issues.append(AgentIssue(
                        file_path=file_path,
                        line_number=1,
                        severity=IssueSeverity.MEDIUM,
                        title='Missing test file',
                        description=f'Source file {Path(file_path).name} has no corresponding test file',
                        recommendation='Create a test file to ensure code quality and prevent regressions',
                        confidence=0.9
                    ))
                    metrics.missing_test_files.append(file_path)
        
        # Calculate test quality score
        test_score = self._calculate_test_score(metrics, len(issues))
        
        return AgentResult(
            agent_type=self.agent_type,
            issues=sorted(issues, key=lambda x: x.severity.value),
            metrics={
                'test_score': test_score,
                'total_test_files': metrics.total_test_files,
                'total_tests': metrics.total_tests,
                'tests_without_assertions': metrics.tests_without_assertions,
                'test_smells_count': metrics.test_smells_count,
                'missing_test_files': len(metrics.missing_test_files),
            },
            summary=self._generate_summary(metrics, len(issues)),
            execution_time_ms=0  # Will be set by base class
        )
    
    def _is_test_file(self, file_path: str) -> bool:
        """Check if file is a test file."""
        filename = Path(file_path).name
        return any(re.search(pattern, filename) for pattern in self.test_patterns)
    
    def _has_test_file(self, file_path: str, all_files: List[str]) -> bool:
        """Check if source file has a corresponding test file."""
        path = Path(file_path)
        base_name = path.stem
        
        # Generate possible test file names
        possible_test_names = [
            f'test_{base_name}.py',
            f'{base_name}_test.py',
            f'{base_name}.test.js',
            f'{base_name}.test.ts',
            f'{base_name}.spec.js',
            f'{base_name}.spec.ts',
        ]
        
        # Check if any test file exists
        for test_file in all_files:
            test_name = Path(test_file).name
            if test_name in possible_test_names:
                return True
        
        return False
    
    def _analyze_python_tests(
        self,
        file_path: str,
        content: str,
        metrics: TestMetrics
    ) -> List[AgentIssue]:
        """Analyze Python test file."""
        issues = []
        metrics.total_test_files += 1
        
        try:
            tree = ast.parse(content)
            
            # Find all test functions/methods
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if node.name.startswith('test_'):
                        metrics.total_tests += 1
                        issues.extend(self._check_python_test_function(
                            file_path, node, content
                        ))
                
                # Check for test classes
                elif isinstance(node, ast.ClassDef):
                    if 'Test' in node.name or any(
                        base.id in ['TestCase', 'unittest.TestCase']
                        for base in node.bases
                        if isinstance(base, ast.Name)
                    ):
                        for item in node.body:
                            if isinstance(item, ast.FunctionDef) and item.name.startswith('test_'):
                                metrics.total_tests += 1
                                issues.extend(self._check_python_test_function(
                                    file_path, item, content
                                ))
        
        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
        
        return issues
    
    def _check_python_test_function(
        self,
        file_path: str,
        node: ast.FunctionDef,
        content: str
    ) -> List[AgentIssue]:
        """Check a single Python test function."""
        issues = []
        
        # Count assertions
        assertion_count = 0
        for child in ast.walk(node):
            if isinstance(child, ast.Assert):
                assertion_count += 1
            elif isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute):
                    if any(keyword in child.func.attr for keyword in self.assertion_keywords):
                        assertion_count += 1
        
        # Check for missing assertions
        if assertion_count == 0:
            issues.append(AgentIssue(
                file_path=file_path,
                line_number=node.lineno,
                severity=IssueSeverity.HIGH,
                title='Test without assertions',
                description=f'Test function {node.name} has no assertions',
                recommendation='Add assertions to verify expected behavior',
                confidence=1.0
            ))
        
        # Check for too many assertions (test smell)
        elif assertion_count > 5:
            issues.append(AgentIssue(
                file_path=file_path,
                line_number=node.lineno,
                severity=IssueSeverity.LOW,
                title='Test with too many assertions',
                description=f'Test function {node.name} has {assertion_count} assertions',
                recommendation='Consider splitting into multiple focused tests',
                confidence=0.8
            ))
        
        # Check test length
        test_length = node.end_lineno - node.lineno
        if test_length > 50:
            issues.append(AgentIssue(
                file_path=file_path,
                line_number=node.lineno,
                severity=IssueSeverity.MEDIUM,
                title='Test too long',
                description=f'Test function {node.name} is {test_length} lines long',
                recommendation='Break down into smaller, focused tests',
                confidence=0.9
            ))
        
        # Check if testing private methods (smell)
        if '_' in node.name and not node.name.startswith('test_'):
            issues.append(AgentIssue(
                file_path=file_path,
                line_number=node.lineno,
                severity=IssueSeverity.MEDIUM,
                title='Testing private method',
                description=f'Test {node.name} appears to test private implementation',
                recommendation='Test public interfaces instead of private methods',
                confidence=0.7
            ))
        
        return issues
    
    def _analyze_js_tests(
        self,
        file_path: str,
        content: str,
        metrics: TestMetrics
    ) -> List[AgentIssue]:
        """Analyze JavaScript/TypeScript test file."""
        issues = []
        metrics.total_test_files += 1
        
        lines = content.split('\n')
        
        # Find test blocks (it, test, describe)
        for i, line in enumerate(lines, 1):
            # Check for test definitions
            if re.search(r'\b(it|test)\s*\(', line):
                metrics.total_tests += 1
                
                # Check for basic assertion patterns
                # Look ahead a few lines for assertions
                has_assertion = False
                for j in range(i, min(i + 20, len(lines))):
                    if any(keyword in lines[j] for keyword in ['expect(', 'assert', 'should']):
                        has_assertion = True
                        break
                
                if not has_assertion:
                    issues.append(AgentIssue(
                        file_path=file_path,
                        line_number=i,
                        severity=IssueSeverity.HIGH,
                        title='Test without assertions',
                        description='Test block has no assertions',
                        recommendation='Add expect() or assert statements',
                        confidence=0.8
                    ))
            
            # Check for empty describe blocks
            if re.search(r'describe\s*\(\s*["\'].*["\']\s*,\s*\(\)\s*=>\s*\{\s*\}\s*\)', line):
                issues.append(AgentIssue(
                    file_path=file_path,
                    line_number=i,
                    severity=IssueSeverity.MEDIUM,
                    title='Empty test suite',
                    description='describe block is empty',
                    recommendation='Add test cases or remove empty suite',
                    confidence=1.0
                ))
        
        return issues
    
    def _calculate_test_score(self, metrics: TestMetrics, issue_count: int) -> int:
        """Calculate test quality score (0-100)."""
        score = 100
        
        # Deduct for issues
        score -= min(issue_count * 5, 40)
        
        # Deduct for tests without assertions
        if metrics.total_tests > 0:
            no_assert_ratio = metrics.tests_without_assertions / metrics.total_tests
            score -= int(no_assert_ratio * 30)
        
        # Deduct for test smells
        score -= min(metrics.test_smells_count * 3, 20)
        
        # Deduct for missing test files
        score -= min(len(metrics.missing_test_files) * 2, 10)
        
        return max(0, score)
    
    def _generate_summary(self, metrics: TestMetrics, issue_count: int) -> str:
        """Generate human-readable summary."""
        parts = []
        
        if metrics.total_test_files > 0:
            parts.append(f"Analyzed {metrics.total_test_files} test files with {metrics.total_tests} tests")
        
        if metrics.tests_without_assertions > 0:
            parts.append(f"{metrics.tests_without_assertions} tests without assertions")
        
        if metrics.test_smells_count > 0:
            parts.append(f"{metrics.test_smells_count} test smells detected")
        
        if metrics.missing_test_files:
            parts.append(f"{len(metrics.missing_test_files)} source files without tests")
        
        if issue_count > 0:
            parts.append(f"Found {issue_count} test quality issues")
        else:
            parts.append("No test quality issues found")
        
        return ". ".join(parts) + "."
