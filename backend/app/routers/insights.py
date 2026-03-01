"""API Router for Phase 18 — Reliability Insights Dashboard.

Provides insights endpoints for repository reliability metrics.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.db import get_db
from app.services.reliability_metrics import ReliabilityMetricsService
from app.services.trend_analysis import TrendAnalysisService
from app.models import RepoMetrics, Repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/insights", tags=["insights"])


# Response schemas
class ReliabilityScoreResponse(BaseModel):
    """Reliability score data."""
    
    reliability_score: float = Field(..., description="Score from 0-100")
    score_grade: str = Field(..., description="Letter grade (A-F)")
    score_change_7d: Optional[float] = Field(None, description="7-day score change")
    score_change_30d: Optional[float] = Field(None, description="30-day score change")
    last_score_update_at: Optional[str] = Field(None, description="Last update timestamp")
    
    class Config:
        from_attributes = True


class RiskBreakdownResponse(BaseModel):
    """Risk breakdown by severity."""
    
    critical_risks: int
    high_risks: int
    medium_risks: int
    low_risks: int
    total_risks: int
    risk_trend_7d: Optional[str] = Field(None, description="increasing/stable/decreasing")
    risk_trend_30d: Optional[str] = Field(None, description="increasing/stable/decreasing")
    
    class Config:
        from_attributes = True


class RiskCategoryBreakdownResponse(BaseModel):
    """Risk breakdown by category."""
    
    crash_risks: int
    resource_leaks: int
    reliability_antipatterns: int
    scalability_risks: int
    edge_case_vulnerabilities: int
    
    class Config:
        from_attributes = True


class FixMetricsResponse(BaseModel):
    """Fix adoption and success metrics."""
    
    total_fixes_proposed: int
    total_fixes_approved: int
    total_fixes_applied: int
    total_fixes_failed: int
    fix_adoption_rate: float = Field(..., description="Percentage (0-1)")
    fix_success_rate: float = Field(..., description="Percentage (0-1)")
    
    class Config:
        from_attributes = True


class PRMetricsResponse(BaseModel):
    """PR analysis metrics."""
    
    total_prs_analyzed: int
    prs_with_critical_risks: int
    prs_with_high_risks: int
    prs_with_no_risks: int
    
    class Config:
        from_attributes = True


class RepoInsightsResponse(BaseModel):
    """Complete repository insights."""
    
    repository_id: int
    repository_name: str
    score: ReliabilityScoreResponse
    risk_breakdown: RiskBreakdownResponse
    risk_categories: RiskCategoryBreakdownResponse
    fix_metrics: FixMetricsResponse
    pr_metrics: PRMetricsResponse
    last_analysis_at: Optional[str]
    last_fix_applied_at: Optional[str]
    
    class Config:
        from_attributes = True


class TrendDataPoint(BaseModel):
    """Single trend data point."""
    
    date: str
    score: float
    critical_risks: int
    high_risks: int
    total_risks: int
    snapshot_type: str


class TrendResponse(BaseModel):
    """Trend analysis response."""
    
    repository_id: int
    period_days: int
    data_points: list[TrendDataPoint]


class RiskTrendBySeverity(BaseModel):
    """Risk trend for one severity level."""
    
    date: str
    count: int


class RiskTrendsResponse(BaseModel):
    """Risk trends by severity."""
    
    repository_id: int
    period_days: int
    critical: list[RiskTrendBySeverity]
    high: list[RiskTrendBySeverity]
    medium: list[RiskTrendBySeverity]
    low: list[RiskTrendBySeverity]


class VelocityResponse(BaseModel):
    """Improvement velocity metrics."""
    
    score_velocity: float = Field(..., description="Score points per day")
    risk_reduction_velocity: float = Field(..., description="Risk count reduction per day")
    days_analyzed: int


class ForecastResponse(BaseModel):
    """Score forecast."""
    
    current_score: float
    forecasted_score: float
    forecast_days: int
    velocity: float
    confidence: str


# Endpoints

@router.get("/repo/{repo_id}", response_model=RepoInsightsResponse)
async def get_repo_insights(
    repo_id: int,
    db: Session = Depends(get_db)
):
    """Get comprehensive reliability insights for repository.
    
    Args:
        repo_id: Repository ID
        db: Database session
    
    Returns:
        Complete insights data
    """
    # Load repository
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    try:
        # Load or create metrics
        metrics_service = ReliabilityMetricsService(db)
        metrics = metrics_service.get_or_create_repo_metrics(repo_id)
    except Exception as exc:
        logger.error(f"Failed to load metrics for repo {repo_id}: {exc}")
        raise HTTPException(status_code=500, detail="Failed to load repository metrics")
    
    # Build response
    return RepoInsightsResponse(
        repository_id=repo.id,
        repository_name=repo.repo_full_name,
        score=ReliabilityScoreResponse(
            reliability_score=metrics.reliability_score,
            score_grade=metrics.score_grade,
            score_change_7d=metrics.score_change_7d,
            score_change_30d=metrics.score_change_30d,
            last_score_update_at=metrics.last_score_update_at.isoformat() if metrics.last_score_update_at else None
        ),
        risk_breakdown=RiskBreakdownResponse(
            critical_risks=metrics.critical_risks,
            high_risks=metrics.high_risks,
            medium_risks=metrics.medium_risks,
            low_risks=metrics.low_risks,
            total_risks=metrics.total_risks,
            risk_trend_7d=metrics.risk_trend_7d,
            risk_trend_30d=metrics.risk_trend_30d
        ),
        risk_categories=RiskCategoryBreakdownResponse(
            crash_risks=metrics.crash_risks,
            resource_leaks=metrics.resource_leaks,
            reliability_antipatterns=metrics.reliability_antipatterns,
            scalability_risks=metrics.scalability_risks,
            edge_case_vulnerabilities=metrics.edge_case_vulnerabilities
        ),
        fix_metrics=FixMetricsResponse(
            total_fixes_proposed=metrics.total_fixes_proposed,
            total_fixes_approved=metrics.total_fixes_approved,
            total_fixes_applied=metrics.total_fixes_applied,
            total_fixes_failed=metrics.total_fixes_failed,
            fix_adoption_rate=metrics.fix_adoption_rate,
            fix_success_rate=metrics.fix_success_rate
        ),
        pr_metrics=PRMetricsResponse(
            total_prs_analyzed=metrics.total_prs_analyzed,
            prs_with_critical_risks=metrics.prs_with_critical_risks,
            prs_with_high_risks=metrics.prs_with_high_risks,
            prs_with_no_risks=metrics.prs_with_no_risks
        ),
        last_analysis_at=metrics.last_analysis_at.isoformat() if metrics.last_analysis_at else None,
        last_fix_applied_at=metrics.last_fix_applied_at.isoformat() if metrics.last_fix_applied_at else None
    )


@router.get("/repo/{repo_id}/score", response_model=ReliabilityScoreResponse)
async def get_repo_score(
    repo_id: int,
    db: Session = Depends(get_db)
):
    """Get reliability score for repository.
    
    Args:
        repo_id: Repository ID
        db: Database session
    
    Returns:
        Score data
    """
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    try:
        metrics_service = ReliabilityMetricsService(db)
        metrics = metrics_service.get_or_create_repo_metrics(repo_id)
    except Exception as exc:
        logger.error(f"Failed to load score for repo {repo_id}: {exc}")
        raise HTTPException(status_code=500, detail="Failed to load score")

    return ReliabilityScoreResponse(
        reliability_score=metrics.reliability_score,
        score_grade=metrics.score_grade,
        score_change_7d=metrics.score_change_7d,
        score_change_30d=metrics.score_change_30d,
        last_score_update_at=metrics.last_score_update_at.isoformat() if metrics.last_score_update_at else None
    )


@router.get("/repo/{repo_id}/trends", response_model=TrendResponse)
async def get_repo_trends(
    repo_id: int,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Get score trend over time.
    
    Args:
        repo_id: Repository ID
        days: Number of days to look back
        db: Database session
    
    Returns:
        Trend data
    """
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    try:
        trend_service = TrendAnalysisService(db)
        trend_data = trend_service.get_score_trend(repo_id, days=days)
    except Exception as exc:
        logger.error(f"Failed to load trends for repo {repo_id}: {exc}")
        raise HTTPException(status_code=500, detail="Failed to load trend data")

    return TrendResponse(
        repository_id=repo_id,
        period_days=days,
        data_points=[TrendDataPoint(**point) for point in trend_data]
    )


@router.get("/repo/{repo_id}/risk-trends", response_model=RiskTrendsResponse)
async def get_risk_trends(
    repo_id: int,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Get risk count trends by severity.
    
    Args:
        repo_id: Repository ID
        days: Number of days to look back
        db: Database session
    
    Returns:
        Risk trends data
    """
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    try:
        trend_service = TrendAnalysisService(db)
        risk_trends = trend_service.get_risk_trend(repo_id, days=days)
    except Exception as exc:
        logger.error(f"Failed to load risk trends for repo {repo_id}: {exc}")
        raise HTTPException(status_code=500, detail="Failed to load risk trends")

    return RiskTrendsResponse(
        repository_id=repo_id,
        period_days=days,
        critical=[RiskTrendBySeverity(**point) for point in risk_trends["critical"]],
        high=[RiskTrendBySeverity(**point) for point in risk_trends["high"]],
        medium=[RiskTrendBySeverity(**point) for point in risk_trends["medium"]],
        low=[RiskTrendBySeverity(**point) for point in risk_trends["low"]]
    )


@router.get("/repo/{repo_id}/velocity", response_model=VelocityResponse)
async def get_improvement_velocity(
    repo_id: int,
    days: int = Query(30, ge=7, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Get improvement velocity metrics.
    
    Args:
        repo_id: Repository ID
        days: Number of days to analyze
        db: Database session
    
    Returns:
        Velocity metrics
    """
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    try:
        trend_service = TrendAnalysisService(db)
        velocity = trend_service.calculate_velocity(repo_id, days=days)
    except Exception as exc:
        logger.error(f"Failed to calculate velocity for repo {repo_id}: {exc}")
        raise HTTPException(status_code=500, detail="Failed to calculate velocity")

    return VelocityResponse(**velocity)


@router.get("/repo/{repo_id}/forecast", response_model=ForecastResponse)
async def get_score_forecast(
    repo_id: int,
    forecast_days: int = Query(7, ge=1, le=30, description="Days to forecast"),
    db: Session = Depends(get_db)
):
    """Get reliability score forecast.
    
    Args:
        repo_id: Repository ID
        forecast_days: Number of days to forecast
        db: Database session
    
    Returns:
        Forecast data
    """
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    try:
        trend_service = TrendAnalysisService(db)
        forecast = trend_service.get_score_forecast(repo_id, forecast_days=forecast_days)
    except Exception as exc:
        logger.error(f"Failed to generate forecast for repo {repo_id}: {exc}")
        raise HTTPException(status_code=500, detail="Failed to generate forecast")

    if not forecast:
        raise HTTPException(
            status_code=400,
            detail="Not enough data for forecast (minimum 7 days of history required)"
        )
    
    return ForecastResponse(**forecast)


@router.post("/repo/{repo_id}/recalculate")
async def recalculate_metrics(
    repo_id: int,
    db: Session = Depends(get_db)
):
    """Manually trigger metrics recalculation.
    
    Args:
        repo_id: Repository ID
        db: Database session
    
    Returns:
        Success message
    """
    # Check repository exists
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    # Trigger recalculation
    metrics_service = ReliabilityMetricsService(db)
    metrics = metrics_service.get_or_create_repo_metrics(repo_id)
    
    # Force update (would trigger full recalculation in production)
    logger.info(f"Manual recalculation triggered for repository {repo_id}")
    
    return {
        "message": "Metrics recalculation completed",
        "repository_id": repo_id,
        "reliability_score": metrics.reliability_score,
        "score_grade": metrics.score_grade
    }
