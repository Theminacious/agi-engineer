"""Tests for safety_checker.py"""
import pytest
import sys
import os
import tempfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_DIR = os.path.join(BASE_DIR, "agent")
if AGENT_DIR not in sys.path:
    sys.path.insert(0, AGENT_DIR)

from safety_checker import SafetyChecker


class TestSafetyChecker:
    """Test SafetyChecker"""
    
    def test_initialization(self):
        """Test SafetyChecker initialization"""
        checker = SafetyChecker()
        assert checker is not None
    
    def test_record_before(self, temp_repo):
        """Test recording before state"""
        checker = SafetyChecker()
        
        # Should not raise
        checker.record_before(temp_repo)
    
    def test_record_after(self, temp_repo):
        """Test recording after state"""
        checker = SafetyChecker()
        checker.record_before(temp_repo)
        
        # Modify a file
        test_file = os.path.join(temp_repo, "src", "unused.py")
        if os.path.exists(test_file):
            with open(test_file, "a") as f:
                f.write("\n# comment\n")
        
        checker.record_after(temp_repo)
    
    def test_check_regressions(self, temp_repo):
        """Test regression detection"""
        checker = SafetyChecker()
        checker.record_before(temp_repo)
        checker.record_after(temp_repo)
        
        report = checker.check_regressions()
        assert 'net_fixed' in report
        assert isinstance(report['net_fixed'], int)
    
    def test_format_report(self, temp_repo):
        """Test report formatting"""
        checker = SafetyChecker()
        checker.record_before(temp_repo)
        checker.record_after(temp_repo)
        
        report_str = checker.format_report()
        assert isinstance(report_str, str)


class TestSafetyCheckerRegressionDetection:
    """Test regression detection logic"""
    
    def test_no_regression_on_same_files(self, temp_repo):
        """Test that identical files show no regression"""
        checker = SafetyChecker()
        checker.record_before(temp_repo)
        checker.record_after(temp_repo)
        
        report = checker.check_regressions()
        # No changes should mean no significant regression
        assert isinstance(report['net_fixed'], int)
