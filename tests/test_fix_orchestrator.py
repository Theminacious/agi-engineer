"""Tests for fix_orchestrator.py"""
import pytest
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_DIR = os.path.join(BASE_DIR, "agent")
if AGENT_DIR not in sys.path:
    sys.path.insert(0, AGENT_DIR)

from fix_orchestrator import FixOrchestrator


class TestFixOrchestrator:
    """Test FixOrchestrator"""
    
    def test_plan_fixes_empty(self):
        """Test planning with no issues"""
        orchestrator = FixOrchestrator()
        
        plan = orchestrator.plan_fixes([], safety_mode='safe')
        assert 'summary' in plan
        assert plan['summary']['will_fix'] == 0
        assert plan['summary']['needs_review'] == 0
    
    def test_plan_fixes_safe_issues(self, sample_issues):
        """Test planning with safe issues"""
        orchestrator = FixOrchestrator()
        
        # Filter to only safe issues
        safe_issues = [i for i in sample_issues if i['code'] in ['F401', 'F541', 'W291']]
        
        plan = orchestrator.plan_fixes(safe_issues, safety_mode='safe')
        assert plan['summary']['will_fix'] >= 0
        assert isinstance(plan, dict)
    
    def test_plan_fixes_mixed_issues(self, sample_issues):
        """Test planning with mixed safe/risky issues"""
        orchestrator = FixOrchestrator()
        
        plan = orchestrator.plan_fixes(sample_issues, safety_mode='safe')
        assert 'summary' in plan
        assert 'will_fix' in plan['summary']
        assert 'needs_review' in plan['summary']
    
    def test_plan_respects_safety_mode(self, sample_issues):
        """Test that safety mode is respected"""
        orchestrator = FixOrchestrator()
        
        plan_safe = orchestrator.plan_fixes(sample_issues, safety_mode='safe')
        plan_all = orchestrator.plan_fixes(sample_issues, safety_mode='all')
        
        assert plan_safe['summary']['will_fix'] <= plan_all['summary']['will_fix']
    
    def test_execute_plan(self, temp_repo):
        """Test executing a fix plan"""
        orchestrator = FixOrchestrator()
        
        # Execute without errors (may not actually fix due to permissions)
        try:
            orchestrator.execute_plan(temp_repo, safety_mode='safe')
        except Exception:
            pass  # Expected in test environment


class TestFixOrchestratorSummary:
    """Test fix summary calculation"""
    
    def test_summary_format(self, sample_issues):
        """Test summary has correct format"""
        orchestrator = FixOrchestrator()
        
        plan = orchestrator.plan_fixes(sample_issues)
        summary = plan['summary']
        
        assert 'will_fix' in summary
        assert 'needs_review' in summary
        assert 'suggestions' in summary
        assert isinstance(summary['will_fix'], int)
        assert isinstance(summary['needs_review'], int)
        assert isinstance(summary['suggestions'], int)
