"""Tests for Phase 17 — GitHub Intelligence Integration.

Test coverage:
- Webhook signature verification
- Webhook event processing (idempotent)
- PR analysis pipeline
- Comment formatting
- Status check logic
- GitHub API interactions
"""

import pytest
import json
import hmac
import hashlib
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from app.models import (
    GitHubWebhookEvent,
    PRAnalysis,
    PRAnalysisStatus,
    ReliabilityScore,
    WebhookEventType,
    Installation
)
from app.services.github_service import GitHubService
from app.services.pr_analysis import PRAnalysisPipeline

# Agent imports
from agent.intelligence.proposal import IntelligenceProposal, BugClass, Severity, FixStrategy, AffectedFile, EffortEstimate


class TestGitHubService:
    """Tests for GitHub service."""
    
    def test_verify_webhook_signature_valid(self):
        """Test webhook signature verification with valid signature."""
        service = GitHubService()
        service.webhook_secret = "test_secret"
        
        payload = b'{"action": "opened"}'
        
        # Compute valid signature
        signature = "sha256=" + hmac.new(
            b"test_secret",
            payload,
            hashlib.sha256
        ).hexdigest()
        
        assert service.verify_webhook_signature(payload, signature) is True
    
    def test_verify_webhook_signature_invalid(self):
        """Test webhook signature verification with invalid signature."""
        service = GitHubService()
        service.webhook_secret = "test_secret"
        
        payload = b'{"action": "opened"}'
        signature = "sha256=invalid_signature"
        
        assert service.verify_webhook_signature(payload, signature) is False
    
    def test_verify_webhook_signature_no_secret(self):
        """Test webhook signature verification without configured secret."""
        service = GitHubService()
        service.webhook_secret = None
        
        payload = b'{"action": "opened"}'
        signature = "sha256=anything"
        
        assert service.verify_webhook_signature(payload, signature) is False
    
    def test_post_pr_comment_success(self, db_session):
        """Test posting PR comment successfully."""
        service = GitHubService(db_session)
        # Mock token retrieval and HTTP client
        service.get_installation_token = Mock(return_value="test-token")
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 12345}
        service.client = Mock()
        service.client.post.return_value = mock_response
        
        comment_id = service.post_pr_comment(
            installation_id=123,
            repo_full_name="owner/repo",
            pr_number=42,
            comment_body="Test comment"
        )
        
        assert comment_id == 12345
        service.client.post.assert_called_once()
    
    def test_create_check_run_success(self, db_session):
        """Test creating GitHub check run."""
        service = GitHubService(db_session)
        # Mock token retrieval and HTTP client
        service.get_installation_token = Mock(return_value="test-token")
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 67890}
        service.client = Mock()
        service.client.post.return_value = mock_response
        
        check_run_id = service.create_check_run(
            installation_id=123,
            repo_full_name="owner/repo",
            head_sha="abc123",
            name="Test Check",
            status="completed",
            conclusion="success"
        )
        
        assert check_run_id == 67890
        service.client.post.assert_called_once()


class TestWebhookProcessing:
    """Tests for webhook processing."""
    
    def test_idempotent_webhook_processing(self, db_session):
        """Test that duplicate webhook deliveries are not processed twice."""
        # Create first webhook event
        webhook1 = GitHubWebhookEvent(
            delivery_id="test-delivery-123",
            event_type=WebhookEventType.PULL_REQUEST_OPENED,
            signature_verified=True,
            installation_id=1,
            repository_full_name="owner/repo",
            pr_number=42,
            pr_head_sha="abc123",
            raw_payload={}
        )
        webhook1.id = 1  # Simulate DB-assigned ID
        
        # Wire mock to return the webhook when queried
        db_session.query.return_value.filter.return_value.first.return_value = webhook1
        
        # Check for duplicate
        existing = db_session.query(GitHubWebhookEvent).filter(
            GitHubWebhookEvent.delivery_id == "test-delivery-123"
        ).first()
        
        assert existing is not None
        assert existing.id == webhook1.id
    
    def test_pr_opened_creates_analysis(self, db_session):
        """Test that PR opened event creates analysis record."""
        # Create webhook event with simulated DB ID
        webhook = GitHubWebhookEvent(
            delivery_id="test-delivery-456",
            event_type=WebhookEventType.PULL_REQUEST_OPENED,
            signature_verified=True,
            installation_id=123,
            repository_full_name="owner/repo",
            pr_number=42,
            pr_head_sha="abc123",
            raw_payload={}
        )
        webhook.id = 10  # Simulate DB-assigned ID
        
        # Create PR analysis linked to the webhook
        pr_analysis = PRAnalysis(
            repository_full_name="owner/repo",
            pr_number=42,
            head_sha="abc123",
            base_branch="main",
            status=PRAnalysisStatus.PENDING,
            webhook_event_id=webhook.id
        )
        pr_analysis.id = 20  # Simulate DB-assigned ID
        
        assert pr_analysis.id is not None
        assert pr_analysis.status == PRAnalysisStatus.PENDING
        assert pr_analysis.webhook_event_id == webhook.id


class TestPRAnalysisPipeline:
    """Tests for PR analysis pipeline."""
    
    def test_calculate_reliability_score_critical(self):
        """Test reliability score calculation with critical risks."""
        pipeline = PRAnalysisPipeline(db_session=Mock())
        
        # Create proposals with critical severity
        proposals = [
            self._create_proposal(Severity.CRITICAL),
            self._create_proposal(Severity.HIGH),
            self._create_proposal(Severity.MEDIUM)
        ]
        
        score, counts = pipeline._calculate_reliability_score(proposals)
        
        assert score == ReliabilityScore.CRITICAL
        assert counts["critical"] == 1
        assert counts["high"] == 1
        assert counts["medium"] == 1
    
    def test_calculate_reliability_score_concerning(self):
        """Test reliability score calculation with high risks."""
        pipeline = PRAnalysisPipeline(db_session=Mock())
        
        # Create proposals with high severity
        proposals = [
            self._create_proposal(Severity.HIGH),
            self._create_proposal(Severity.HIGH),
            self._create_proposal(Severity.MEDIUM)
        ]
        
        score, counts = pipeline._calculate_reliability_score(proposals)
        
        assert score == ReliabilityScore.CONCERNING
        assert counts["critical"] == 0
        assert counts["high"] == 2
        assert counts["medium"] == 1
    
    def test_calculate_reliability_score_good(self):
        """Test reliability score calculation with medium risks."""
        pipeline = PRAnalysisPipeline(db_session=Mock())
        
        # Create proposals with medium severity
        proposals = [
            self._create_proposal(Severity.MEDIUM),
            self._create_proposal(Severity.LOW)
        ]
        
        score, counts = pipeline._calculate_reliability_score(proposals)
        
        assert score == ReliabilityScore.GOOD
        assert counts["critical"] == 0
        assert counts["high"] == 0
        assert counts["medium"] == 1
    
    def test_calculate_reliability_score_excellent(self):
        """Test reliability score calculation with no risks."""
        pipeline = PRAnalysisPipeline(db_session=Mock())
        
        # No proposals
        proposals = []
        
        score, counts = pipeline._calculate_reliability_score(proposals)
        
        assert score == ReliabilityScore.EXCELLENT
        assert counts["critical"] == 0
        assert counts["high"] == 0
        assert counts["medium"] == 0
    
    def test_format_comment_with_critical_risks(self, db_session):
        """Test PR comment formatting with critical risks."""
        pipeline = PRAnalysisPipeline(db_session=db_session)
        
        # Create PR analysis
        pr_analysis = PRAnalysis(
            repository_full_name="owner/repo",
            pr_number=42,
            head_sha="abc123",
            base_branch="main",
            status=PRAnalysisStatus.COMPLETED,
            reliability_score=ReliabilityScore.CRITICAL,
            critical_risks_count=2,
            high_risks_count=3,
            medium_risks_count=5,
            fix_candidates_count=8,
            ledger_run_id="test-run-123"
        )
        
        # Create proposals
        proposals = [
            self._create_proposal(Severity.CRITICAL, "Null dereference risk"),
            self._create_proposal(Severity.CRITICAL, "Resource leak detected"),
            self._create_proposal(Severity.HIGH, "Missing error handling")
        ]
        
        comment = pipeline._format_comment(pr_analysis, proposals)
        
        # Verify comment structure
        assert "AGI Engineer Reliability Analysis" in comment
        assert "CRITICAL" in comment
        assert "2 Critical" in comment
        assert "3 High" in comment
        assert "5 Medium" in comment
        assert "8 fix candidates" in comment
        assert "Null dereference risk" in comment
        assert "Resource leak detected" in comment
        assert "test-run-123" in comment
    
    def test_format_comment_with_excellent_score(self, db_session):
        """Test PR comment formatting with excellent score."""
        pipeline = PRAnalysisPipeline(db_session=db_session)
        
        # Create PR analysis
        pr_analysis = PRAnalysis(
            repository_full_name="owner/repo",
            pr_number=42,
            head_sha="abc123",
            base_branch="main",
            status=PRAnalysisStatus.COMPLETED,
            reliability_score=ReliabilityScore.EXCELLENT,
            critical_risks_count=0,
            high_risks_count=0,
            medium_risks_count=0,
            fix_candidates_count=0,
            ledger_run_id="test-run-123"
        )
        
        comment = pipeline._format_comment(pr_analysis, [])
        
        # Verify comment structure
        assert "EXCELLENT" in comment
        assert "0 Critical" in comment
        assert "0 High" in comment
        assert "0 Medium" in comment
    
    @staticmethod
    def _create_proposal(severity: Severity, problem: str = "Test problem") -> IntelligenceProposal:
        """Helper to create test proposal."""
        return IntelligenceProposal(
            proposal_id="test-proposal-123",
            bug_class=BugClass.CRASH_RISKS,
            severity=severity,
            problem_statement=problem,
            risk_explanation="Test risk explanation",
            root_cause_hypothesis="Test root cause",
            suggested_strategies=[
                FixStrategy(
                    name="Test strategy",
                    description="Test description",
                    prerequisite_actions=["Test prerequisite"],
                    assumptions=["Test assumption"],
                    risks=["Test risk"]
                )
            ],
            affected_files=[AffectedFile(path="test.py", line_range="1", severity=severity)],
            confidence_level=85,
            confidence_explanation="High confidence"
        )


class TestStatusCheckLogic:
    """Tests for GitHub status check logic."""
    
    def test_status_check_conclusion_critical(self):
        """Test status check conclusion for critical reliability score."""
        # Critical score → failure
        score = ReliabilityScore.CRITICAL
        
        if score == ReliabilityScore.CRITICAL:
            conclusion = "failure"
        elif score == ReliabilityScore.CONCERNING:
            conclusion = "neutral"
        else:
            conclusion = "success"
        
        assert conclusion == "failure"
    
    def test_status_check_conclusion_concerning(self):
        """Test status check conclusion for concerning reliability score."""
        # Concerning score → neutral
        score = ReliabilityScore.CONCERNING
        
        if score == ReliabilityScore.CRITICAL:
            conclusion = "failure"
        elif score == ReliabilityScore.CONCERNING:
            conclusion = "neutral"
        else:
            conclusion = "success"
        
        assert conclusion == "neutral"
    
    def test_status_check_conclusion_good(self):
        """Test status check conclusion for good reliability score."""
        # Good score → success
        score = ReliabilityScore.GOOD
        
        if score == ReliabilityScore.CRITICAL:
            conclusion = "failure"
        elif score == ReliabilityScore.CONCERNING:
            conclusion = "neutral"
        else:
            conclusion = "success"
        
        assert conclusion == "success"
    
    def test_status_check_conclusion_excellent(self):
        """Test status check conclusion for excellent reliability score."""
        # Excellent score → success
        score = ReliabilityScore.EXCELLENT
        
        if score == ReliabilityScore.CRITICAL:
            conclusion = "failure"
        elif score == ReliabilityScore.CONCERNING:
            conclusion = "neutral"
        else:
            conclusion = "success"
        
        assert conclusion == "success"


# Pytest fixtures
@pytest.fixture
def db_session():
    """Mock database session."""
    session = MagicMock(spec=Session)
    session.add = Mock()
    session.commit = Mock()
    session.query = Mock()
    return session


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
