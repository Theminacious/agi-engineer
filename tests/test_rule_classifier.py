"""Tests for rule_classifier.py"""
import pytest
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_DIR = os.path.join(BASE_DIR, "agent")
if AGENT_DIR not in sys.path:
    sys.path.insert(0, AGENT_DIR)

from rule_classifier import RuleClassifier


class TestRuleClassifier:
    """Test RuleClassifier"""
    
    def test_classify_safe_rule(self):
        """Test classification of safe rules"""
        classifier = RuleClassifier()
        
        result = classifier.classify('F401')
        assert result is not None
        assert 'code' in result
        assert result['code'] == 'F401'
    
    def test_classify_risky_rule(self):
        """Test classification of risky rules"""
        classifier = RuleClassifier()
        
        result = classifier.classify('F841')
        assert result is not None
        assert 'code' in result
        assert result['code'] == 'F841'
    
    def test_classify_suggestion_rule(self):
        """Test classification of suggestion rules"""
        classifier = RuleClassifier()
        
        result = classifier.classify('E402')
        assert result is not None
        assert 'code' in result
        assert 'category' in result
    
    def test_classify_unknown_rule(self):
        """Test classification of unknown rules"""
        classifier = RuleClassifier()
        
        result = classifier.classify('UNKNOWN')
        assert result is not None
        assert 'code' in result
    
    def test_get_summary(self, sample_issues):
        """Test summary generation"""
        classifier = RuleClassifier()
        
        summary = classifier.get_summary(sample_issues)
        assert 'safe' in summary['grouped']
        assert 'risky' in summary['grouped']
        assert 'suggest' in summary['grouped']
        assert len(summary['grouped']['safe']) > 0
    
    def test_group_by_category(self, sample_issues):
        """Test grouping by category"""
        classifier = RuleClassifier()
        
        grouped = classifier.group_by_category(sample_issues)
        assert isinstance(grouped, dict)
        assert len(grouped) > 0
    
    def test_multiple_issues_same_code(self):
        """Test handling multiple issues with same code"""
        classifier = RuleClassifier()
        issues = [
            {'code': 'F401', 'message': 'Unused import', 'filename': 'a.py'},
            {'code': 'F401', 'message': 'Unused import', 'filename': 'b.py'},
        ]
        
        summary = classifier.get_summary(issues)
        assert len(summary['grouped']['safe']) == 2
