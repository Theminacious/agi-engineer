"""Trend Analysis Service for Phase 18 — Time-series analytics.

Analyzes score trends, risk trends, and historical patterns.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models import (
    RepoMetrics,
    RiskSnapshot,
    ReliabilityScoreMetric,
    Repository
)

logger = logging.getLogger(__name__)


class TrendAnalysisService:
    """Service for analyzing reliability trends and patterns.
    
    Features:
    - Score trend calculation
    - Risk trend analysis
    - Period-over-period comparisons
    - Forecasting support
    """
    
    def __init__(self, db_session: Session):
        """Initialize trend analysis service.
        
        Args:
            db_session: Database session
        """
        self.db_session = db_session
    
    def get_score_trend(
        self,
        repository_id: int,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get reliability score trend over time.
        
        Args:
            repository_id: Repository ID
            days: Number of days to look back
        
        Returns:
            List of daily score data points
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get repo metrics
        metrics = self.db_session.query(RepoMetrics).filter(
            RepoMetrics.repository_id == repository_id
        ).first()
        
        if not metrics:
            return []
        
        # Get risk snapshots (which include reliability_score)
        snapshots = self.db_session.query(RiskSnapshot).filter(
            and_(
                RiskSnapshot.repo_metrics_id == metrics.id,
                RiskSnapshot.created_at >= cutoff_date
            )
        ).order_by(RiskSnapshot.created_at.asc()).all()
        
        # Convert to data points
        trend_data = []
        for snapshot in snapshots:
            trend_data.append({
                "date": snapshot.created_at.isoformat(),
                "score": snapshot.reliability_score,
                "critical_risks": snapshot.critical_risks,
                "high_risks": snapshot.high_risks,
                "total_risks": snapshot.total_risks,
                "snapshot_type": snapshot.snapshot_type
            })
        
        return trend_data
    
    def get_risk_trend(
        self,
        repository_id: int,
        days: int = 30
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get risk count trends by severity.
        
        Args:
            repository_id: Repository ID
            days: Number of days to look back
        
        Returns:
            Dict with trend data for each severity level
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get repo metrics
        metrics = self.db_session.query(RepoMetrics).filter(
            RepoMetrics.repository_id == repository_id
        ).first()
        
        if not metrics:
            return {
                "critical": [],
                "high": [],
                "medium": [],
                "low": []
            }
        
        # Get risk snapshots
        snapshots = self.db_session.query(RiskSnapshot).filter(
            and_(
                RiskSnapshot.repo_metrics_id == metrics.id,
                RiskSnapshot.created_at >= cutoff_date
            )
        ).order_by(RiskSnapshot.created_at.asc()).all()
        
        # Organize by severity
        critical_trend = []
        high_trend = []
        medium_trend = []
        low_trend = []
        
        for snapshot in snapshots:
            date_str = snapshot.created_at.isoformat()
            
            critical_trend.append({
                "date": date_str,
                "count": snapshot.critical_risks
            })
            high_trend.append({
                "date": date_str,
                "count": snapshot.high_risks
            })
            medium_trend.append({
                "date": date_str,
                "count": snapshot.medium_risks
            })
            low_trend.append({
                "date": date_str,
                "count": snapshot.low_risks
            })
        
        return {
            "critical": critical_trend,
            "high": high_trend,
            "medium": medium_trend,
            "low": low_trend
        }
    
    def get_fix_adoption_trend(
        self,
        repository_id: int,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get fix adoption rate trend over time.
        
        Args:
            repository_id: Repository ID
            days: Number of days to look back
        
        Returns:
            List of fix adoption data points
        """
        # Get repo metrics
        metrics = self.db_session.query(RepoMetrics).filter(
            RepoMetrics.repository_id == repository_id
        ).first()
        
        if not metrics:
            return []
        
        # For Phase 18.1, return current rate
        # In Phase 18.2, we'd track historical rates
        return [{
            "date": datetime.utcnow().isoformat(),
            "adoption_rate": metrics.fix_adoption_rate,
            "success_rate": metrics.fix_success_rate,
            "total_fixes_proposed": metrics.total_fixes_proposed,
            "total_fixes_applied": metrics.total_fixes_applied
        }]
    
    def calculate_velocity(
        self,
        repository_id: int,
        days: int = 30
    ) -> Dict[str, float]:
        """Calculate improvement velocity metrics.
        
        Args:
            repository_id: Repository ID
            days: Number of days to analyze
        
        Returns:
            Dict with velocity metrics
        """
        # Get score trend
        trend = self.get_score_trend(repository_id, days=days)
        
        if len(trend) < 2:
            return {
                "score_velocity": 0.0,
                "risk_reduction_velocity": 0.0,
                "days_analyzed": len(trend)
            }
        
        # Calculate score change rate (points per day)
        first_score = trend[0]["score"]
        last_score = trend[-1]["score"]
        time_span = len(trend)
        
        score_velocity = (last_score - first_score) / time_span if time_span > 0 else 0.0
        
        # Calculate risk reduction rate
        first_risks = trend[0]["total_risks"]
        last_risks = trend[-1]["total_risks"]
        
        risk_reduction_velocity = (first_risks - last_risks) / time_span if time_span > 0 else 0.0
        
        return {
            "score_velocity": round(score_velocity, 2),
            "risk_reduction_velocity": round(risk_reduction_velocity, 2),
            "days_analyzed": time_span
        }
    
    def get_score_forecast(
        self,
        repository_id: int,
        forecast_days: int = 7
    ) -> Optional[Dict[str, Any]]:
        """Forecast future reliability score based on trends.
        
        Args:
            repository_id: Repository ID
            forecast_days: Number of days to forecast
        
        Returns:
            Forecast data or None
        """
        # Get velocity
        velocity = self.calculate_velocity(repository_id, days=30)
        
        if velocity["days_analyzed"] < 7:
            return None  # Not enough data
        
        # Get current score
        metrics = self.db_session.query(RepoMetrics).filter(
            RepoMetrics.repository_id == repository_id
        ).first()
        
        if not metrics:
            return None
        
        # Simple linear forecast
        forecasted_score = metrics.reliability_score + (velocity["score_velocity"] * forecast_days)
        
        # Clamp to [0, 100]
        forecasted_score = max(0.0, min(100.0, forecasted_score))
        
        return {
            "current_score": metrics.reliability_score,
            "forecasted_score": round(forecasted_score, 1),
            "forecast_days": forecast_days,
            "velocity": velocity["score_velocity"],
            "confidence": "low" if velocity["days_analyzed"] < 14 else "medium"
        }
    
    def get_period_comparison(
        self,
        repository_id: int,
        period_days: int = 7
    ) -> Dict[str, Any]:
        """Compare current period vs previous period.
        
        Args:
            repository_id: Repository ID
            period_days: Period length in days
        
        Returns:
            Comparison data
        """
        now = datetime.utcnow()
        
        # Get metrics for current period
        current_start = now - timedelta(days=period_days)
        current_trend = self.get_score_trend(repository_id, days=period_days)
        
        # Get metrics for previous period
        previous_start = now - timedelta(days=period_days * 2)
        previous_end = current_start
        
        # Get repo metrics
        metrics = self.db_session.query(RepoMetrics).filter(
            RepoMetrics.repository_id == repository_id
        ).first()
        
        if not metrics:
            return {}
        
        # Get snapshots for both periods
        current_snapshots = self.db_session.query(RiskSnapshot).filter(
            and_(
                RiskSnapshot.repo_metrics_id == metrics.id,
                RiskSnapshot.created_at >= current_start
            )
        ).all()
        
        previous_snapshots = self.db_session.query(RiskSnapshot).filter(
            and_(
                RiskSnapshot.repo_metrics_id == metrics.id,
                RiskSnapshot.created_at >= previous_start,
                RiskSnapshot.created_at < previous_end
            )
        ).all()
        
        # Calculate averages
        current_avg_score = sum(s.reliability_score for s in current_snapshots) / len(current_snapshots) if current_snapshots else 0
        previous_avg_score = sum(s.reliability_score for s in previous_snapshots) / len(previous_snapshots) if previous_snapshots else 0
        
        current_avg_risks = sum(s.total_risks for s in current_snapshots) / len(current_snapshots) if current_snapshots else 0
        previous_avg_risks = sum(s.total_risks for s in previous_snapshots) / len(previous_snapshots) if previous_snapshots else 0
        
        return {
            "current_period": {
                "avg_score": round(current_avg_score, 1),
                "avg_risks": round(current_avg_risks, 1),
                "data_points": len(current_snapshots)
            },
            "previous_period": {
                "avg_score": round(previous_avg_score, 1),
                "avg_risks": round(previous_avg_risks, 1),
                "data_points": len(previous_snapshots)
            },
            "change": {
                "score_change": round(current_avg_score - previous_avg_score, 1),
                "risk_change": round(current_avg_risks - previous_avg_risks, 1),
                "score_change_pct": round(((current_avg_score - previous_avg_score) / previous_avg_score * 100) if previous_avg_score > 0 else 0, 1),
                "risk_change_pct": round(((current_avg_risks - previous_avg_risks) / previous_avg_risks * 100) if previous_avg_risks > 0 else 0, 1)
            }
        }
