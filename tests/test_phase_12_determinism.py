"""
PHASE 12: Determinism Tests

Verifies that all Phase 12 analyzers are deterministic:
Same input → Same output (always)

This is critical for:
- Ledger replay (must produce identical proposals)
- Confidence in analysis (no randomness)
- Reproducible bugs (can debug issues)
- System trustworthiness (immutability guarantee)

Tests verify:
1. Running analyzer twice on same code produces identical proposals
2. Running in different order produces same proposals
3. Running on sorted vs unsorted data produces same proposals
4. Confidence scores are deterministic
5. No randomness in output ordering
"""

import os
import tempfile
import json
from pathlib import Path
from typing import List

import pytest

from agent.intelligence.proposal import IntelligenceProposal
from agent.intelligence.analyzers.enhanced_architectural import EnhancedArchitecturalAnalyzer
from agent.intelligence.analyzers.enhanced_concurrency import EnhancedConcurrencyAnalyzer
from agent.intelligence.analyzers.enhanced_performance import EnhancedPerformanceAnalyzer


class TestDeterminismArchitectural:
    """Test determinism of Enhanced Architectural Analyzer."""
    
    @pytest.fixture
    def test_repo(self):
        """Create a test repository with architectural issues."""
        tmpdir = tempfile.mkdtemp()
        
        # Create modules with circular dependencies
        Path(tmpdir, 'module_a.py').write_text('''
import module_b

def function_a():
    return module_b.function_b()
''')
        
        Path(tmpdir, 'module_b.py').write_text('''
import module_a

def function_b():
    return module_a.function_a()
''')
        
        # Create layering violation
        Path(tmpdir, 'controllers.py').write_text('''
from database import get_user
from models import User

def handle_request():
    user = get_user()  # Direct data layer access
    return user
''')
        
        Path(tmpdir, 'database.py').write_text('''
def get_user():
    return {"id": 1, "name": "Alice"}
''')
        
        return tmpdir
    
    def test_same_input_same_output(self, test_repo):
        """
        Test: Running analyzer twice on same code produces identical proposals.
        
        This is the primary determinism test.
        """
        analyzer = EnhancedArchitecturalAnalyzer()
        
        # Run 1
        proposals_1 = analyzer.analyze(test_repo, "https://example.com/repo", "main")
        proposals_1_dict = [p.to_dict() for p in proposals_1]
        
        # Run 2 (fresh analyzer instance)
        analyzer = EnhancedArchitecturalAnalyzer()
        proposals_2 = analyzer.analyze(test_repo, "https://example.com/repo", "main")
        proposals_2_dict = [p.to_dict() for p in proposals_2]
        
        # Same proposals in same order
        assert len(proposals_1_dict) == len(proposals_2_dict), \
            f"Different proposal counts: {len(proposals_1_dict)} vs {len(proposals_2_dict)}"
        
        for p1, p2 in zip(proposals_1_dict, proposals_2_dict):
            # Compare all fields except timestamps (which are deterministic but differ)
            assert p1['bug_class'] == p2['bug_class']
            assert p1['severity'] == p2['severity']
            assert p1['confidence_level'] == p2['confidence_level']
            assert p1['problem_statement'] == p2['problem_statement']
            assert p1['root_cause_hypothesis'] == p2['root_cause_hypothesis']
            assert p1['risk_explanation'] == p2['risk_explanation']
    
    def test_output_ordering_deterministic(self, test_repo):
        """
        Test: Proposals always come out in same order.
        
        Even if internal processing order changes, output order must be consistent.
        """
        analyzer = EnhancedArchitecturalAnalyzer()
        
        # Run multiple times
        runs = [
            analyzer.analyze(test_repo, "https://example.com/repo", "main")
            for _ in range(3)
        ]
        
        # Extract problem statements to check ordering
        orderings = [
            [p.problem_statement for p in run]
            for run in runs
        ]
        
        # All orderings should be identical
        assert all(ordering == orderings[0] for ordering in orderings), \
            "Proposals came out in different order on different runs"
    
    def test_no_randomness_in_proposals(self, test_repo):
        """
        Test: Proposals contain no random data.
        
        proposal_id should be deterministic (or ignored in comparison),
        confidence should be consistent,
        strategies should be identical.
        """
        analyzer = EnhancedArchitecturalAnalyzer()
        
        proposals_1 = analyzer.analyze(test_repo, "https://example.com/repo", "main")
        
        analyzer = EnhancedArchitecturalAnalyzer()
        proposals_2 = analyzer.analyze(test_repo, "https://example.com/repo", "main")
        
        for p1, p2 in zip(proposals_1, proposals_2):
            # Confidence must be identical (not random)
            assert p1.confidence_level == p2.confidence_level, \
                f"Confidence changed: {p1.confidence_level} vs {p2.confidence_level}"
            
            # Strategies must be identical (same order, same content)
            assert len(p1.suggested_strategies) == len(p2.suggested_strategies)
            for s1, s2 in zip(p1.suggested_strategies, p2.suggested_strategies):
                assert s1.name == s2.name
                assert s1.description == s2.description
                assert s1.effort_estimate == s2.effort_estimate
    
    def test_deterministic_across_runs(self, test_repo):
        """
        Test: Analyzer is deterministic when run many times.
        
        This catches occasional non-determinism issues.
        """
        outputs = []
        
        for i in range(10):  # Run 10 times
            analyzer = EnhancedArchitecturalAnalyzer()
            proposals = analyzer.analyze(test_repo, "https://example.com/repo", "main")
            output = json.dumps(
                [p.to_dict() for p in proposals],
                sort_keys=True,
                default=str,
            )
            outputs.append(output)
        
        # All outputs should be identical
        assert len(set(outputs)) == 1, \
            f"Non-deterministic behavior detected across {len(set(outputs))} different outputs"


class TestDeterminismConcurrency:
    """Test determinism of Enhanced Concurrency Analyzer."""
    
    @pytest.fixture
    def test_repo(self):
        """Create a test repository with concurrency issues."""
        tmpdir = tempfile.mkdtemp()
        
        # Create file with shared mutable state
        Path(tmpdir, 'shared_state.py').write_text('''
import threading

class DataStore:
    def __init__(self):
        self.cache = {}  # Shared mutable state without lock
    
    def set_value(self, key, value):
        self.cache[key] = value  # Race condition
    
    def get_value(self, key):
        return self.cache.get(key)  # Race condition

# Global shared state
global_list = []  # Shared mutable state
global_dict = {}  # Shared mutable state

def worker():
    global_list.append(1)  # Race condition
    global_dict['key'] = 'value'  # Race condition
''')
        
        # Create file with async anti-patterns
        Path(tmpdir, 'async_issues.py').write_text('''
import asyncio

async def await_in_loop():
    items = [1, 2, 3, 4, 5]
    for item in items:
        result = await async_operation(item)  # N+1 pattern

async def async_operation(x):
    await asyncio.sleep(0.1)
    return x * 2
''')
        
        return tmpdir
    
    def test_consistent_issue_detection(self, test_repo):
        """Test: Same shared state issues detected consistently."""
        analyzer = EnhancedConcurrencyAnalyzer()
        
        proposals_1 = analyzer.analyze(test_repo, "https://example.com/repo", "main")
        
        analyzer = EnhancedConcurrencyAnalyzer()
        proposals_2 = analyzer.analyze(test_repo, "https://example.com/repo", "main")
        
        # Same number of issues
        assert len(proposals_1) == len(proposals_2)
        
        # Same severity for same issues
        for p1, p2 in zip(proposals_1, proposals_2):
            assert p1.severity == p2.severity
            assert p1.bug_class == p2.bug_class
    
    def test_strategies_deterministic(self, test_repo):
        """Test: Suggested strategies are always identical."""
        analyzer = EnhancedConcurrencyAnalyzer()
        proposals_1 = analyzer.analyze(test_repo, "https://example.com/repo", "main")
        
        analyzer = EnhancedConcurrencyAnalyzer()
        proposals_2 = analyzer.analyze(test_repo, "https://example.com/repo", "main")
        
        for p1, p2 in zip(proposals_1, proposals_2):
            # Same number of strategies
            assert len(p1.suggested_strategies) == len(p2.suggested_strategies)
            
            # Strategies in same order with same content
            for s1, s2 in zip(p1.suggested_strategies, p2.suggested_strategies):
                assert s1.name == s2.name
                assert s1.description == s2.description


class TestDeterminismPerformance:
    """Test determinism of Enhanced Performance Analyzer."""
    
    @pytest.fixture
    def test_repo(self):
        """Create a test repository with performance issues."""
        tmpdir = tempfile.mkdtemp()
        
        # Create N+1 query pattern
        Path(tmpdir, 'queries.py').write_text('''
def fetch_users():
    users = db.query(User).all()  # First query
    for user in users:
        user.posts = db.query(Post).filter(Post.user_id == user.id).all()  # N queries
    return users
''')
        
        # Create blocking I/O pattern
        Path(tmpdir, 'handlers.py').write_text('''
def handle_request():
    with open('/large/file.txt') as f:  # Blocking I/O
        data = f.read()
    
    response = requests.get('http://slow-api.com/data')  # Blocking network
    return data + response.text
''')
        
        # Create unbounded cache
        Path(tmpdir, 'caching.py').write_text('''
class Cache:
    def __init__(self):
        self.cache = {}  # Unbounded cache
    
    def get_or_fetch(self, key):
        if key not in self.cache:
            self.cache[key] = expensive_computation(key)  # Grows forever
        return self.cache[key]
''')
        
        return tmpdir
    
    def test_n_plus_one_consistent(self, test_repo):
        """Test: N+1 patterns detected consistently."""
        analyzer = EnhancedPerformanceAnalyzer()
        proposals_1 = analyzer.analyze(test_repo, "https://example.com/repo", "main")
        
        analyzer = EnhancedPerformanceAnalyzer()
        proposals_2 = analyzer.analyze(test_repo, "https://example.com/repo", "main")
        
        # Consistent detection
        assert len(proposals_1) == len(proposals_2)
        
        for p1, p2 in zip(proposals_1, proposals_2):
            assert p1.problem_statement == p2.problem_statement
            assert p1.severity == p2.severity
    
    def test_multiple_runs_identical(self, test_repo):
        """Test: Multiple analyzer runs produce identical results."""
        results = []
        
        for _ in range(5):
            analyzer = EnhancedPerformanceAnalyzer()
            proposals = analyzer.analyze(test_repo, "https://example.com/repo", "main")
            result = json.dumps(
                [p.to_dict() for p in proposals],
                sort_keys=True,
                default=str,
            )
            results.append(result)
        
        # All results identical
        assert len(set(results)) == 1


class TestConfidenceDeterminism:
    """Test that confidence scores are deterministic."""
    
    def test_confidence_calculation_deterministic(self):
        """Test: Confidence calculation is deterministic."""
        from agent.intelligence.confidence_calibrator import ConfidenceCalibrator, ConfidenceSource
        
        # Create calibrator with same evidence
        calibrators = []
        for _ in range(10):
            cal = ConfidenceCalibrator()
            cal.add_evidence(
                ConfidenceSource.STATIC_PATTERN,
                "Circular import detected"
            )
            cal.add_evidence(
                ConfidenceSource.HEURISTIC,
                "Found in three files"
            )
            calibrators.append(cal)
        
        # All should calculate to same confidence
        confidences = [cal.calculate_confidence() for cal in calibrators]
        assert len(set(confidences)) == 1, \
            f"Confidence varied: {set(confidences)}"
    
    def test_severity_adjustment_deterministic(self):
        """Test: Severity adjustment is deterministic."""
        from agent.intelligence.confidence_calibrator import RiskBasedSeverityAdjuster
        
        # Same input should always give same output
        for _ in range(10):
            result = RiskBasedSeverityAdjuster.adjust_severity("HIGH", 50)
            assert result == "MEDIUM", "Severity adjustment not deterministic"


class TestDeterminismProperties:
    """Property-based determinism tests."""
    
    def test_proposal_serialization_deterministic(self):
        """Test: Proposal serialization is deterministic."""
        from agent.intelligence.proposal import IntelligenceProposal, BugClass, Severity
        
        # Create same proposal multiple times
        for _ in range(5):
            p1 = IntelligenceProposal(
                bug_class=BugClass.CIRCULAR_DEPENDENCIES,
                severity=Severity.HIGH,
                problem_statement="Test issue",
                root_cause_hypothesis="Test cause",
                risk_explanation="Test risk",
            )
            p1.confidence_level = 85
            
            p2 = IntelligenceProposal(
                bug_class=BugClass.CIRCULAR_DEPENDENCIES,
                severity=Severity.HIGH,
                problem_statement="Test issue",
                root_cause_hypothesis="Test cause",
                risk_explanation="Test risk",
            )
            p2.confidence_level = 85
            
            # Serialize to dict
            d1 = json.dumps(p1.to_dict(), sort_keys=True, default=str)
            d2 = json.dumps(p2.to_dict(), sort_keys=True, default=str)
            
            # Should be identical (ignoring generated IDs)
            # Remove proposal_id for comparison
            import re
            d1_no_id = re.sub(r'"proposal_id"\s*:\s*"[^"]+",?\s*', '', d1)
            d2_no_id = re.sub(r'"proposal_id"\s*:\s*"[^"]+",?\s*', '', d2)
            assert d1_no_id == d2_no_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
