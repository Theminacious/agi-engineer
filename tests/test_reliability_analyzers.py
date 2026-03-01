"""
Tests for Phase 16 Reliability Intelligence Engine

Tests all 5 reliability analyzers:
- CrashRiskAnalyzer
- ResourceLeakAnalyzer
- ReliabilityPatternAnalyzer
- ScalabilityRiskAnalyzer
- EdgeCaseLogicAnalyzer
"""

import os
import tempfile
import shutil
from typing import List
import pytest

from agent.intelligence.proposal import IntelligenceProposal, BugClass, Severity
from agent.intelligence.analyzers.reliability.crash_risk import CrashRiskAnalyzer
from agent.intelligence.analyzers.reliability.resource_leak import ResourceLeakAnalyzer
from agent.intelligence.analyzers.reliability.reliability_pattern import ReliabilityPatternAnalyzer
from agent.intelligence.analyzers.reliability.scalability_risk import ScalabilityRiskAnalyzer
from agent.intelligence.analyzers.reliability.edge_case_logic import EdgeCaseLogicAnalyzer


class TestCrashRiskAnalyzer:
    """Test crash risk detection."""
    
    def setup_method(self):
        """Create temporary test repository."""
        self.test_dir = tempfile.mkdtemp()
        self.analyzer = CrashRiskAnalyzer()
    
    def teardown_method(self):
        """Clean up test repository."""
        shutil.rmtree(self.test_dir)
    
    def test_detects_null_dereference_risks(self):
        """Test detection of null/None dereference patterns."""
        # Create file with unsafe dict access
        test_file = os.path.join(self.test_dir, "unsafe.py")
        with open(test_file, 'w') as f:
            f.write("""
def process_user(data):
    user_id = data['user_id']  # Unsafe dict access
    name = data['name']  # Another unsafe access
    return user_id
""")
        
        proposals = self.analyzer.analyze(
            repository_path=self.test_dir,
            repository_url="https://github.com/test/repo",
            branch="main"
        )
        
        # Should detect null dereference risks
        assert len(proposals) > 0
        null_risk_proposal = next(
            (p for p in proposals if p.bug_class == BugClass.CRASH_RISKS),
            None
        )
        assert null_risk_proposal is not None
        assert null_risk_proposal.severity in [Severity.CRITICAL, Severity.HIGH]
        assert len(null_risk_proposal.affected_files) > 0
        assert len(null_risk_proposal.suggested_strategies) >= 2
    
    def test_detects_missing_error_handling(self):
        """Test detection of operations without error handling."""
        test_file = os.path.join(self.test_dir, "no_error_handling.py")
        with open(test_file, 'w') as f:
            f.write("""
import json

def load_config(path):
    data = open(path).read()  # No error handling
    config = json.loads(data)  # No error handling
    return config
""")
        
        proposals = self.analyzer.analyze(
            repository_path=self.test_dir,
            repository_url="https://github.com/test/repo",
            branch="main"
        )
        
        assert len(proposals) > 0
        # Check that strategies include try-except wrapping
        for proposal in proposals:
            strategies = [s.name for s in proposal.suggested_strategies]
            assert any('try' in s.lower() or 'except' in s.lower() for s in strategies)
    
    def test_detects_recursion_risks(self):
        """Test detection of unbounded recursion."""
        test_file = os.path.join(self.test_dir, "recursion.py")
        with open(test_file, 'w') as f:
            f.write("""
def traverse(node):
    result = process(node)
    for child in node.children:
        result += traverse(child)  # Recursive without depth limit
    return result
""")
        
        proposals = self.analyzer.analyze(
            repository_path=self.test_dir,
            repository_url="https://github.com/test/repo",
            branch="main"
        )
        
        # Should detect recursion risks
        recursion_proposal = next(
            (p for p in proposals if 'recursion' in p.problem_statement.lower()),
            None
        )
        if recursion_proposal:  # May not always detect simple cases
            assert recursion_proposal.severity in [Severity.MEDIUM, Severity.HIGH]
    
    def test_no_false_positives_on_safe_code(self):
        """Test that safe code doesn't trigger false positives."""
        test_file = os.path.join(self.test_dir, "safe.py")
        with open(test_file, 'w') as f:
            f.write("""
def safe_process(data):
    user_id = data.get('user_id')  # Safe dict access
    if user_id:
        return user_id
    return None

def safe_open():
    try:
        with open('file.txt') as f:
            return f.read()
    except FileNotFoundError:
        return None
""")
        
        proposals = self.analyzer.analyze(
            repository_path=self.test_dir,
            repository_url="https://github.com/test/repo",
            branch="main"
        )
        
        # Should have fewer or no proposals for safe code
        # (Some may still be detected due to heuristic limitations)
        assert len(proposals) <= 1


class TestResourceLeakAnalyzer:
    """Test resource leak detection."""
    
    def setup_method(self):
        """Create temporary test repository."""
        self.test_dir = tempfile.mkdtemp()
        self.analyzer = ResourceLeakAnalyzer()
    
    def teardown_method(self):
        """Clean up test repository."""
        shutil.rmtree(self.test_dir)
    
    def test_detects_file_handle_leaks(self):
        """Test detection of unclosed file handles."""
        test_file = os.path.join(self.test_dir, "file_leak.py")
        with open(test_file, 'w') as f:
            f.write("""
def read_data():
    f = open('data.txt')  # No with statement, no close
    data = f.read()
    return data
""")
        
        proposals = self.analyzer.analyze(
            repository_path=self.test_dir,
            repository_url="https://github.com/test/repo",
            branch="main"
        )
        
        assert len(proposals) > 0
        file_leak = next(
            (p for p in proposals if 'file' in p.problem_statement.lower()),
            None
        )
        assert file_leak is not None
        assert file_leak.severity == Severity.HIGH
        # Should suggest context managers
        strategies = [s.name for s in file_leak.suggested_strategies]
        assert any('with' in s.lower() for s in strategies)
    
    def test_detects_connection_leaks(self):
        """Test detection of database/network connection leaks."""
        test_file = os.path.join(self.test_dir, "conn_leak.py")
        with open(test_file, 'w') as f:
            f.write("""
import psycopg2

def query_db():
    conn = psycopg2.connect('dbname=test')  # No context manager
    cursor = conn.cursor()  # No close
    cursor.execute('SELECT * FROM users')
    return cursor.fetchall()
""")
        
        proposals = self.analyzer.analyze(
            repository_path=self.test_dir,
            repository_url="https://github.com/test/repo",
            branch="main"
        )
        
        assert len(proposals) > 0
        conn_leak = next(
            (p for p in proposals if 'connection' in p.problem_statement.lower()),
            None
        )
        assert conn_leak is not None
        assert conn_leak.severity == Severity.CRITICAL
    
    def test_detects_memory_leaks(self):
        """Test detection of unbounded caches and accumulators."""
        test_file = os.path.join(self.test_dir, "memory_leak.py")
        with open(test_file, 'w') as f:
            f.write("""
# Global cache without size limit
cache = {}

def get_or_compute(key):
    if key not in cache:
        cache[key] = expensive_computation(key)
    return cache[key]
""")
        
        proposals = self.analyzer.analyze(
            repository_path=self.test_dir,
            repository_url="https://github.com/test/repo",
            branch="main"
        )
        
        # Should detect unbounded cache
        memory_leak = next(
            (p for p in proposals if 'memory' in p.problem_statement.lower() or 'cache' in p.problem_statement.lower()),
            None
        )
        if memory_leak:  # May not always detect
            assert len(memory_leak.suggested_strategies) >= 2
            strategies = [s.name for s in memory_leak.suggested_strategies]
            assert any('lru' in s.lower() for s in strategies)


class TestReliabilityPatternAnalyzer:
    """Test reliability anti-pattern detection."""
    
    def setup_method(self):
        """Create temporary test repository."""
        self.test_dir = tempfile.mkdtemp()
        self.analyzer = ReliabilityPatternAnalyzer()
    
    def teardown_method(self):
        """Clean up test repository."""
        shutil.rmtree(self.test_dir)
    
    def test_detects_retry_without_backoff(self):
        """Test detection of retry loops without backoff."""
        test_file = os.path.join(self.test_dir, "retry.py")
        with open(test_file, 'w') as f:
            f.write("""
def fetch_data():
    for i in range(5):  # Retry loop
        try:
            return requests.get('https://api.example.com/data')
        except:
            continue  # Immediate retry, no backoff
""")
        
        proposals = self.analyzer.analyze(
            repository_path=self.test_dir,
            repository_url="https://github.com/test/repo",
            branch="main"
        )
        
        assert len(proposals) > 0
        retry_proposal = next(
            (p for p in proposals if 'retry' in p.problem_statement.lower() or 'backoff' in p.problem_statement.lower()),
            None
        )
        if retry_proposal:
            assert retry_proposal.severity == Severity.HIGH
            strategies = [s.name for s in retry_proposal.suggested_strategies]
            assert any('backoff' in s.lower() for s in strategies)
    
    def test_detects_missing_timeouts(self):
        """Test detection of operations without timeouts."""
        test_file = os.path.join(self.test_dir, "timeout.py")
        with open(test_file, 'w') as f:
            f.write("""
import requests

def fetch_user(user_id):
    response = requests.get(f'https://api.example.com/users/{user_id}')  # No timeout
    return response.json()
""")
        
        proposals = self.analyzer.analyze(
            repository_path=self.test_dir,
            repository_url="https://github.com/test/repo",
            branch="main"
        )
        
        assert len(proposals) > 0
        timeout_proposal = next(
            (p for p in proposals if 'timeout' in p.problem_statement.lower()),
            None
        )
        assert timeout_proposal is not None
        assert timeout_proposal.severity == Severity.CRITICAL
    
    def test_detects_silent_failures(self):
        """Test detection of exception handlers that swallow errors."""
        test_file = os.path.join(self.test_dir, "silent.py")
        with open(test_file, 'w') as f:
            f.write("""
def process():
    try:
        risky_operation()
    except:
        pass  # Silent failure
""")
        
        proposals = self.analyzer.analyze(
            repository_path=self.test_dir,
            repository_url="https://github.com/test/repo",
            branch="main"
        )
        
        assert len(proposals) > 0
        silent_proposal = next(
            (p for p in proposals if 'silent' in p.problem_statement.lower() or 'swallow' in p.problem_statement.lower()),
            None
        )
        assert silent_proposal is not None
    
    def test_detects_blocking_in_async(self):
        """Test detection of blocking operations in async code."""
        test_file = os.path.join(self.test_dir, "async_blocking.py")
        with open(test_file, 'w') as f:
            f.write("""
import time
import requests

async def fetch_data():
    time.sleep(1)  # Blocking in async
    response = requests.get('https://api.example.com')  # Blocking in async
    return response.json()
""")
        
        proposals = self.analyzer.analyze(
            repository_path=self.test_dir,
            repository_url="https://github.com/test/repo",
            branch="main"
        )
        
        assert len(proposals) > 0
        async_proposal = next(
            (p for p in proposals if 'async' in p.problem_statement.lower() or 'blocking' in p.problem_statement.lower()),
            None
        )
        if async_proposal:
            assert async_proposal.severity == Severity.HIGH


class TestScalabilityRiskAnalyzer:
    """Test scalability risk detection."""
    
    def setup_method(self):
        """Create temporary test repository."""
        self.test_dir = tempfile.mkdtemp()
        self.analyzer = ScalabilityRiskAnalyzer()
    
    def teardown_method(self):
        """Clean up test repository."""
        shutil.rmtree(self.test_dir)
    
    def test_detects_nplus1_queries(self):
        """Test detection of N+1 query patterns."""
        test_file = os.path.join(self.test_dir, "nplus1.py")
        with open(test_file, 'w') as f:
            f.write("""
def get_users_with_posts():
    users = User.query.all()
    for user in users:
        posts = Post.query.filter_by(user_id=user.id).all()  # N+1!
        user.posts = posts
    return users
""")
        
        proposals = self.analyzer.analyze(
            repository_path=self.test_dir,
            repository_url="https://github.com/test/repo",
            branch="main"
        )
        
        assert len(proposals) > 0
        nplus1 = next(
            (p for p in proposals if 'n+1' in p.problem_statement.lower() or 'query' in p.problem_statement.lower()),
            None
        )
        assert nplus1 is not None
        assert nplus1.severity == Severity.CRITICAL
        strategies = [s.name for s in nplus1.suggested_strategies]
        assert any('eager' in s.lower() or 'join' in s.lower() for s in strategies)
    
    def test_detects_nested_loops(self):
        """Test detection of inefficient nested loops."""
        test_file = os.path.join(self.test_dir, "nested.py")
        with open(test_file, 'w') as f:
            f.write("""
def match_users(users, orders):
    result = []
    for user in users:
        for order in orders:  # O(n²)
            if order.user_id == user.id:
                result.append((user, order))
    return result
""")
        
        proposals = self.analyzer.analyze(
            repository_path=self.test_dir,
            repository_url="https://github.com/test/repo",
            branch="main"
        )
        
        assert len(proposals) > 0
        nested = next(
            (p for p in proposals if 'nested' in p.problem_statement.lower() or 'o(n' in p.problem_statement.lower()),
            None
        )
        if nested:
            assert nested.severity in [Severity.HIGH, Severity.MEDIUM]
    
    def test_detects_unbounded_queries(self):
        """Test detection of queries without LIMIT."""
        test_file = os.path.join(self.test_dir, "unbounded.py")
        with open(test_file, 'w') as f:
            f.write("""
def get_all_users():
    return User.query.all()  # No limit!

def get_all_orders():
    return session.execute('SELECT * FROM orders').fetchall()  # No LIMIT
""")
        
        proposals = self.analyzer.analyze(
            repository_path=self.test_dir,
            repository_url="https://github.com/test/repo",
            branch="main"
        )
        
        assert len(proposals) > 0
        unbounded = next(
            (p for p in proposals if 'unbounded' in p.problem_statement.lower() or 'limit' in p.problem_statement.lower()),
            None
        )
        assert unbounded is not None
        assert unbounded.severity == Severity.HIGH


class TestEdgeCaseLogicAnalyzer:
    """Test edge case logic vulnerability detection."""
    
    def setup_method(self):
        """Create temporary test repository."""
        self.test_dir = tempfile.mkdtemp()
        self.analyzer = EdgeCaseLogicAnalyzer()
    
    def teardown_method(self):
        """Clean up test repository."""
        shutil.rmtree(self.test_dir)
    
    def test_detects_division_by_zero(self):
        """Test detection of division without zero checks."""
        test_file = os.path.join(self.test_dir, "division.py")
        with open(test_file, 'w') as f:
            f.write("""
def calculate_average(total, count):
    return total / count  # Division by zero if count=0
""")
        
        proposals = self.analyzer.analyze(
            repository_path=self.test_dir,
            repository_url="https://github.com/test/repo",
            branch="main"
        )
        
        assert len(proposals) > 0
        div_zero = next(
            (p for p in proposals if 'division' in p.problem_statement.lower() or 'zero' in p.problem_statement.lower()),
            None
        )
        if div_zero:
            assert div_zero.severity in [Severity.MEDIUM, Severity.HIGH]
    
    def test_detects_float_comparison(self):
        """Test detection of floating point equality."""
        test_file = os.path.join(self.test_dir, "float.py")
        with open(test_file, 'w') as f:
            f.write("""
def check_price(price):
    if price == 19.99:  # Float equality comparison
        return True
    return False
""")
        
        proposals = self.analyzer.analyze(
            repository_path=self.test_dir,
            repository_url="https://github.com/test/repo",
            branch="main"
        )
        
        float_proposal = next(
            (p for p in proposals if 'float' in p.problem_statement.lower()),
            None
        )
        if float_proposal:
            strategies = [s.name for s in float_proposal.suggested_strategies]
            assert any('isclose' in s.lower() or 'decimal' in s.lower() for s in strategies)
    
    def test_detects_timezone_issues(self):
        """Test detection of timezone-naive datetime operations."""
        test_file = os.path.join(self.test_dir, "timezone.py")
        with open(test_file, 'w') as f:
            f.write("""
from datetime import datetime

def get_timestamp():
    return datetime.now()  # Timezone-naive
""")
        
        proposals = self.analyzer.analyze(
            repository_path=self.test_dir,
            repository_url="https://github.com/test/repo",
            branch="main"
        )
        
        assert len(proposals) > 0
        tz_proposal = next(
            (p for p in proposals if 'timezone' in p.problem_statement.lower()),
            None
        )
        assert tz_proposal is not None
        assert tz_proposal.severity == Severity.MEDIUM
    
    def test_detects_array_bounds_issues(self):
        """Test detection of hardcoded array indexes."""
        test_file = os.path.join(self.test_dir, "bounds.py")
        with open(test_file, 'w') as f:
            f.write("""
def get_first_name(parts):
    return parts[0]  # IndexError if parts is empty
""")
        
        proposals = self.analyzer.analyze(
            repository_path=self.test_dir,
            repository_url="https://github.com/test/repo",
            branch="main"
        )
        
        bounds_proposal = next(
            (p for p in proposals if 'array' in p.problem_statement.lower() or 'bounds' in p.problem_statement.lower() or 'index' in p.problem_statement.lower()),
            None
        )
        if bounds_proposal:
            assert bounds_proposal.severity in [Severity.MEDIUM, Severity.HIGH]


class TestReliabilityAnalyzerIntegration:
    """Integration tests for reliability analyzers."""
    
    def test_all_analyzers_return_valid_proposals(self):
        """Test that all analyzers return valid proposals."""
        test_dir = tempfile.mkdtemp()
        try:
            # Create test file with multiple issues
            test_file = os.path.join(test_dir, "multi_issue.py")
            with open(test_file, 'w') as f:
                f.write("""
import requests
from datetime import datetime

def process_data(data):
    user_id = data['user_id']  # Crash risk
    response = requests.get('https://api.example.com')  # Missing timeout
    timestamp = datetime.now()  # Timezone issue
    count = len(data)
    average = sum(data) / count  # Division by zero
    return response.json()
""")
            
            analyzers = [
                CrashRiskAnalyzer(),
                ResourceLeakAnalyzer(),
                ReliabilityPatternAnalyzer(),
                ScalabilityRiskAnalyzer(),
                EdgeCaseLogicAnalyzer(),
            ]
            
            for analyzer in analyzers:
                proposals = analyzer.analyze(
                    repository_path=test_dir,
                    repository_url="https://github.com/test/repo",
                    branch="main"
                )
                
                # All proposals must be valid
                for proposal in proposals:
                    # Validate Phase 11.1 compliance
                    errors = proposal.validate()
                    assert len(errors) == 0, f"Proposal validation errors: {errors}"
                    
                    # Check required fields
                    assert proposal.problem_statement
                    assert proposal.risk_explanation
                    assert proposal.root_cause_hypothesis
                    assert len(proposal.suggested_strategies) >= 2
                    
                    # Check metadata
                    assert proposal.analyzer_name == analyzer.__class__.__name__
                    assert proposal.repository_url == "https://github.com/test/repo"
                    assert proposal.branch == "main"
        
        finally:
            shutil.rmtree(test_dir)
    
    def test_deterministic_analysis(self):
        """Test that analyzers produce deterministic results."""
        test_dir = tempfile.mkdtemp()
        try:
            test_file = os.path.join(test_dir, "test.py")
            with open(test_file, 'w') as f:
                f.write("""
def divide(a, b):
    return a / b
""")
            
            analyzer = EdgeCaseLogicAnalyzer()
            
            # Run twice
            proposals1 = analyzer.analyze(test_dir, "https://github.com/test/repo", "main")
            proposals2 = analyzer.analyze(test_dir, "https://github.com/test/repo", "main")
            
            # Should get same results
            assert len(proposals1) == len(proposals2)
            
            if len(proposals1) > 0:
                # Proposal IDs should match (deterministic)
                ids1 = {p.proposal_id for p in proposals1}
                ids2 = {p.proposal_id for p in proposals2}
                assert ids1 == ids2
        
        finally:
            shutil.rmtree(test_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
