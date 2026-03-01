"""Tests for Phase 18 — Reliability Insights Dashboard.

Tests for metrics calculation, trend analysis, and API endpoints.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models import (
    RepoMetrics,
    RiskSnapshot,
    ReliabilityScoreMetric,
    Repository,
    PRAnalysis,
    AnalysisRun,
    CodeFix,
    FixStatus
)
from app.models.analysis_run import RunStatus
from app.models.github_integration import PRAnalysisStatus
from app.services.reliability_metrics import ReliabilityMetricsService
from app.services.trend_analysis import TrendAnalysisService
from app.services.metrics_pipeline import MetricsPipeline


class TestReliabilityScoreCalculation:
    """Test reliability score calculation logic."""
    
    def test_perfect_score(self, db_session: Session):
        """Test perfect score with no risks."""
        service = ReliabilityMetricsService(db_session)
        
        score = service.calculate_reliability_score(
            critical_risks=0,
            high_risks=0,
            medium_risks=0,
            low_risks=0,
            fix_adoption_rate=0.0
        )
        
        assert score == 100.0
    
    def test_critical_risk_penalty(self, db_session: Session):
        """Test that critical risks heavily impact score."""
        service = ReliabilityMetricsService(db_session)
        
        score = service.calculate_reliability_score(
            critical_risks=2,
            high_risks=0,
            medium_risks=0,
            low_risks=0,
            fix_adoption_rate=0.0
        )
        
        # 100 - (2 * 10) = 80
        assert score == 80.0
    
    def test_mixed_risks_scoring(self, db_session: Session):
        """Test scoring with mixed risk severities."""
        service = ReliabilityMetricsService(db_session)
        
        score = service.calculate_reliability_score(
            critical_risks=1,  # -10
            high_risks=2,      # -10
            medium_risks=3,    # -6
            low_risks=4,       # -2
            fix_adoption_rate=0.0
        )
        
        # 100 - 10 - 10 - 6 - 2 = 72
        assert score == 72.0
    
    def test_fix_adoption_bonus(self, db_session: Session):
        """Test that high fix adoption improves score."""
        service = ReliabilityMetricsService(db_session)
        
        score = service.calculate_reliability_score(
            critical_risks=2,  # -20
            high_risks=0,
            medium_risks=0,
            low_risks=0,
            fix_adoption_rate=0.90  # +9
        )
        
        # 100 - 20 + 9 = 89
        assert score == 89.0
    
    def test_score_clamping(self, db_session: Session):
        """Test that score is clamped to [0, 100]."""
        service = ReliabilityMetricsService(db_session)
        
        # Test lower bound
        score_low = service.calculate_reliability_score(
            critical_risks=20,  # Way too many
            high_risks=0,
            medium_risks=0,
            low_risks=0,
            fix_adoption_rate=0.0
        )
        assert score_low == 0.0
        
        # Test upper bound (already at 100, can't go higher)
        score_high = service.calculate_reliability_score(
            critical_risks=0,
            high_risks=0,
            medium_risks=0,
            low_risks=0,
            fix_adoption_rate=1.0  # Perfect adoption
        )
        assert score_high == 100.0


class TestScoreGradeCalculation:
    """Test letter grade assignment."""
    
    def test_grade_a(self):
        """Test A grade for scores >= 90."""
        metrics = RepoMetrics(
            repository_id=1,
            reliability_score=95.0
        )
        assert metrics.calculate_score_grade() == "A"
    
    def test_grade_b(self):
        """Test B grade for scores 80-89."""
        metrics = RepoMetrics(
            repository_id=1,
            reliability_score=85.0
        )
        assert metrics.calculate_score_grade() == "B"
    
    def test_grade_c(self):
        """Test C grade for scores 70-79."""
        metrics = RepoMetrics(
            repository_id=1,
            reliability_score=75.0
        )
        assert metrics.calculate_score_grade() == "C"
    
    def test_grade_d(self):
        """Test D grade for scores 60-69."""
        metrics = RepoMetrics(
            repository_id=1,
            reliability_score=65.0
        )
        assert metrics.calculate_score_grade() == "D"
    
    def test_grade_f(self):
        """Test F grade for scores < 60."""
        metrics = RepoMetrics(
            repository_id=1,
            reliability_score=50.0
        )
        assert metrics.calculate_score_grade() == "F"


class TestMetricsUpdates:
    """Test metrics updates after PR analysis and fix application."""
    
    def test_create_initial_metrics(self, db_session: Session, test_repository):
        """Test creating initial metrics for repository."""
        service = ReliabilityMetricsService(db_session)
        
        metrics = service.get_or_create_repo_metrics(test_repository.id)
        
        assert metrics.repository_id == test_repository.id
        assert metrics.reliability_score == 100.0
        assert metrics.score_grade == "A"
        assert metrics.total_risks == 0
    
    def test_metrics_update_after_pr_analysis(
        self,
        db_session: Session,
        test_repository,
        test_pr_analysis
    ):
        """Test metrics update after PR analysis."""
        service = ReliabilityMetricsService(db_session)
        
        # Update metrics
        metrics = service.update_metrics_after_pr_analysis(
            pr_analysis_id=test_pr_analysis.id
        )
        
        assert metrics is not None
        assert metrics.total_prs_analyzed > 0
        assert metrics.last_analysis_at is not None
    
    def test_risk_snapshot_creation(
        self,
        db_session: Session,
        test_repository
    ):
        """Test that risk snapshots are created."""
        service = ReliabilityMetricsService(db_session)
        
        metrics = service.get_or_create_repo_metrics(test_repository.id)
        
        # Create snapshot
        snapshot = service._create_risk_snapshot(
            repo_metrics_id=metrics.id,
            snapshot_type="pr_analysis",
            snapshot_reason="Test snapshot",
            critical_risks=2,
            high_risks=3,
            medium_risks=5,
            low_risks=0,
            reliability_score=75.0
        )
        
        assert snapshot.repo_metrics_id == metrics.id
        assert snapshot.critical_risks == 2
        assert snapshot.total_risks == 10
        assert snapshot.reliability_score == 75.0


class TestTrendAnalysis:
    """Test trend analysis calculations."""
    
    def test_score_trend_retrieval(
        self,
        db_session: Session,
        test_repository,
        test_repo_metrics_with_snapshots
    ):
        """Test retrieving score trend data."""
        service = TrendAnalysisService(db_session)
        
        trend = service.get_score_trend(test_repository.id, days=30)
        
        assert len(trend) > 0
        assert "date" in trend[0]
        assert "score" in trend[0]
        assert "total_risks" in trend[0]
    
    def test_risk_trend_by_severity(
        self,
        db_session: Session,
        test_repository,
        test_repo_metrics_with_snapshots
    ):
        """Test risk trends broken down by severity."""
        service = TrendAnalysisService(db_session)
        
        trends = service.get_risk_trend(test_repository.id, days=30)
        
        assert "critical" in trends
        assert "high" in trends
        assert "medium" in trends
        assert "low" in trends
    
    def test_velocity_calculation(
        self,
        db_session: Session,
        test_repository,
        test_repo_metrics_with_snapshots
    ):
        """Test improvement velocity calculation."""
        service = TrendAnalysisService(db_session)
        
        velocity = service.calculate_velocity(test_repository.id, days=30)
        
        assert "score_velocity" in velocity
        assert "risk_reduction_velocity" in velocity
        assert "days_analyzed" in velocity
    
    def test_score_forecast(
        self,
        db_session: Session,
        test_repository,
        test_repo_metrics_with_snapshots
    ):
        """Test score forecasting."""
        service = TrendAnalysisService(db_session)
        
        forecast = service.get_score_forecast(test_repository.id, forecast_days=7)
        
        if forecast:
            assert "current_score" in forecast
            assert "forecasted_score" in forecast
            assert "velocity" in forecast
            assert 0 <= forecast["forecasted_score"] <= 100


class TestMetricsPipeline:
    """Test metrics pipeline integration."""
    
    def test_process_pr_analysis_completion(
        self,
        db_session: Session,
        test_pr_analysis
    ):
        """Test pipeline processing after PR analysis."""
        pipeline = MetricsPipeline(db_session)
        
        result = pipeline.process_pr_analysis_completion(
            pr_analysis_id=test_pr_analysis.id
        )
        
        assert result is True
    
    def test_process_fix_application(
        self,
        db_session: Session,
        test_code_fix
    ):
        """Test pipeline processing after fix application."""
        pipeline = MetricsPipeline(db_session)
        
        result = pipeline.process_fix_application(
            fix_id=test_code_fix.id
        )
        
        assert result is True


class TestAPIEndpoints:
    """Test API endpoints for insights."""
    
    def test_get_repo_insights(self, client, test_repository):
        """Test GET /api/insights/repo/{repo_id}."""
        response = client.get(f"/api/insights/repo/{test_repository.id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["repository_id"] == test_repository.id
        assert "score" in data
        assert "risk_breakdown" in data
        assert "fix_metrics" in data
        assert "pr_metrics" in data
    
    def test_get_repo_score(self, client, test_repository):
        """Test GET /api/insights/repo/{repo_id}/score."""
        response = client.get(f"/api/insights/repo/{test_repository.id}/score")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "reliability_score" in data
        assert "score_grade" in data
        assert 0 <= data["reliability_score"] <= 100
    
    def test_get_repo_trends(self, client, test_repository):
        """Test GET /api/insights/repo/{repo_id}/trends."""
        response = client.get(f"/api/insights/repo/{test_repository.id}/trends?days=30")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "data_points" in data
        assert "period_days" in data
    
    def test_get_velocity(self, client, test_repository):
        """Test GET /api/insights/repo/{repo_id}/velocity."""
        response = client.get(f"/api/insights/repo/{test_repository.id}/velocity?days=30")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "score_velocity" in data
        assert "risk_reduction_velocity" in data
    
    def test_recalculate_metrics(self, client, test_repository):
        """Test POST /api/insights/repo/{repo_id}/recalculate."""
        response = client.post(f"/api/insights/repo/{test_repository.id}/recalculate")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "reliability_score" in data
        assert "score_grade" in data
    
    def test_repo_not_found(self, client):
        """Test 404 error for non-existent repository."""
        response = client.get("/api/insights/repo/99999")
        
        assert response.status_code == 404


# Fixtures

@pytest.fixture
def test_repository(db_session: Session):
    """Create test repository."""
    repo = Repository(
        installation_id=1,
        repo_name="test-repo",
        repo_full_name="test-org/test-repo",
        github_repo_id=100001,
        is_enabled=True,
    )
    db_session.add(repo)
    db_session.commit()
    return repo


@pytest.fixture
def test_pr_analysis(db_session: Session, test_repository):
    """Create test PR analysis."""
    # Create analysis run
    analysis_run = AnalysisRun(
        repository_id=test_repository.id,
        github_event="pull_request",
        github_branch="main",
        github_commit_sha="abc123def456abc123def456abc123def456abcd",
        status=RunStatus.COMPLETED,
    )
    db_session.add(analysis_run)
    db_session.flush()

    # Create PR analysis
    pr_analysis = PRAnalysis(
        repository_full_name=test_repository.repo_full_name,
        pr_number=123,
        head_sha="abc123def456abc123def456abc123def456abcd",
        base_branch="main",
        status=PRAnalysisStatus.COMPLETED,
        analysis_run_id=analysis_run.id,
        critical_risks_count=2,
        high_risks_count=3,
        medium_risks_count=5,
        completed_at=datetime.utcnow(),
    )
    db_session.add(pr_analysis)
    db_session.commit()
    return pr_analysis


@pytest.fixture
def test_code_fix(db_session: Session, test_repository):
    """Create test code fix."""
    from app.models.analysis_result import AnalysisResult, IssueCategory

    # Create analysis run
    analysis_run = AnalysisRun(
        repository_id=test_repository.id,
        github_event="push",
        github_branch="main",
        github_commit_sha="def456def456def456def456def456def456def4",
        status=RunStatus.COMPLETED,
    )
    db_session.add(analysis_run)
    db_session.flush()

    # Create analysis result (needed as FK target for CodeFix)
    result = AnalysisResult(
        run_id=analysis_run.id,
        file_path="src/app.py",
        line_number=10,
        issue_code="E501",
        issue_name="line-too-long",
        category=IssueCategory.SUGGESTION,
        severity="warning",
        message="Line too long",
    )
    db_session.add(result)
    db_session.flush()

    # Create fix
    fix = CodeFix(
        result_id=result.id,
        original_code="old code",
        fixed_code="new code",
        status=FixStatus.APPLIED,
    )
    db_session.add(fix)
    db_session.commit()
    return fix


@pytest.fixture
def test_repo_metrics_with_snapshots(db_session: Session, test_repository):
    """Create repo metrics with historical snapshots."""
    service = ReliabilityMetricsService(db_session)
    
    metrics = service.get_or_create_repo_metrics(test_repository.id)
    
    # Create snapshots over past 30 days
    for i in range(30):
        date = datetime.utcnow() - timedelta(days=i)
        service._create_risk_snapshot(
            repo_metrics_id=metrics.id,
            snapshot_type="daily_aggregation",
            snapshot_reason=f"Day {i}",
            critical_risks=max(0, 5 - i // 10),  # Decreasing trend
            high_risks=max(0, 10 - i // 5),
            medium_risks=15,
            low_risks=20,
            reliability_score=min(100, 70 + i)  # Improving trend
        )
    
    return metrics
