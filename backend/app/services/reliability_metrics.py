"""Reliability Metrics Service for Phase 18 — Insights Dashboard.

Calculates reliability scores, tracks trends, and manages metrics updates.
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models import (
    RepoMetrics,
    RiskSnapshot,
    ReliabilityScoreMetric,
    ReliabilityHotspot,
    Repository,
    PRAnalysis,
    AnalysisRun,
    AnalysisResult,
    CodeFix,
    FixStatus,
)
from app.models.github_integration import PRAnalysisStatus
from agent.intelligence.proposal import BugClass, Severity
from agent.run_ledger import RunLedgerWriter

logger = logging.getLogger(__name__)


class ReliabilityMetricsService:
    """Service for calculating and managing repository reliability metrics.
    
    Features:
    - Reliability score calculation (0-100)
    - Risk trend analysis
    - Fix adoption tracking
    - Hotspot identification
    - Ledger recording
    """
    
    def __init__(self, db_session: Session):
        """Initialize metrics service.
        
        Args:
            db_session: Database session
        """
        self.db_session = db_session
    
    def get_or_create_repo_metrics(self, repository_id: int) -> RepoMetrics:
        """Get existing repo metrics or create new one.
        
        Args:
            repository_id: Repository ID
        
        Returns:
            RepoMetrics instance
        """
        metrics = self.db_session.query(RepoMetrics).filter(
            RepoMetrics.repository_id == repository_id
        ).first()
        
        if not metrics:
            metrics = RepoMetrics(
                repository_id=repository_id,
                reliability_score=100.0,
                score_grade="A"
            )
            self.db_session.add(metrics)
            self.db_session.commit()
            logger.info(f"Created new RepoMetrics for repository {repository_id}")
        
        return metrics
    
    def calculate_reliability_score(
        self,
        critical_risks: int,
        high_risks: int,
        medium_risks: int,
        low_risks: int,
        fix_adoption_rate: float = 0.0
    ) -> float:
        """Calculate reliability score (0-100) based on risk counts.
        
        Scoring algorithm:
        - Start at 100
        - Subtract points for each risk (weighted by severity)
        - Add bonus points for high fix adoption rate
        - Clamp to [0, 100]
        
        Args:
            critical_risks: Number of critical risks
            high_risks: Number of high risks
            medium_risks: Number of medium risks
            low_risks: Number of low risks
            fix_adoption_rate: Percentage of proposed fixes that were applied (0-1)
        
        Returns:
            Reliability score (0-100)
        """
        # Start at 100 (perfect score)
        score = 100.0
        
        # Deduct points for risks (weighted by severity)
        score -= critical_risks * 10.0  # Critical: -10 points each
        score -= high_risks * 5.0       # High: -5 points each
        score -= medium_risks * 2.0     # Medium: -2 points each
        score -= low_risks * 0.5        # Low: -0.5 points each
        
        # Add bonus for fix adoption (up to +10 points)
        if fix_adoption_rate > 0:
            score += fix_adoption_rate * 10.0
        
        # Clamp to [0, 100]
        score = max(0.0, min(100.0, score))
        
        return round(score, 2)
    
    def update_metrics_after_pr_analysis(
        self,
        pr_analysis_id: int,
        ledger_run_id: Optional[str] = None
    ) -> RepoMetrics:
        """Update repository metrics after PR analysis completes.
        
        Args:
            pr_analysis_id: PRAnalysis record ID
            ledger_run_id: Optional ledger run ID for event recording
        
        Returns:
            Updated RepoMetrics
        """
        # Load PR analysis
        pr_analysis = self.db_session.query(PRAnalysis).filter(
            PRAnalysis.id == pr_analysis_id
        ).first()
        
        if not pr_analysis or pr_analysis.status != PRAnalysisStatus.COMPLETED:
            logger.warning(f"PRAnalysis {pr_analysis_id} not found or not completed")
            return None
        
        # Get repository from analysis run
        if not pr_analysis.analysis_run_id:
            logger.warning(f"PRAnalysis {pr_analysis_id} has no analysis_run_id")
            return None
        
        analysis_run = self.db_session.query(AnalysisRun).filter(
            AnalysisRun.id == pr_analysis.analysis_run_id
        ).first()
        
        if not analysis_run:
            logger.warning(f"AnalysisRun {pr_analysis.analysis_run_id} not found")
            return None
        
        # Find repository by full_name
        repo = self.db_session.query(Repository).filter(
            Repository.repo_full_name == pr_analysis.repository_full_name
        ).first()
        
        if not repo:
            logger.warning(f"Repository {pr_analysis.repository_full_name} not found")
            return None
        
        # Get or create metrics
        metrics = self.get_or_create_repo_metrics(repo.id)
        
        # Update PR analysis counts
        metrics.total_prs_analyzed += 1
        if pr_analysis.critical_risks_count > 0:
            metrics.prs_with_critical_risks += 1
        elif pr_analysis.high_risks_count > 0:
            metrics.prs_with_high_risks += 1
        else:
            metrics.prs_with_no_risks += 1
        
        # Aggregate risk counts from all recent analyses (last 30 days)
        risk_summary = self._get_recent_risk_summary(repo.id, days=30)
        
        metrics.critical_risks = risk_summary["critical"]
        metrics.high_risks = risk_summary["high"]
        metrics.medium_risks = risk_summary["medium"]
        metrics.low_risks = risk_summary["low"]
        metrics.total_risks = risk_summary["total"]
        
        # Update risk category breakdown
        metrics.crash_risks = risk_summary.get("crash_risks", 0)
        metrics.resource_leaks = risk_summary.get("resource_leaks", 0)
        metrics.reliability_antipatterns = risk_summary.get("reliability_antipatterns", 0)
        metrics.scalability_risks = risk_summary.get("scalability_risks", 0)
        metrics.edge_case_vulnerabilities = risk_summary.get("edge_case_vulnerabilities", 0)
        
        # Calculate fix metrics
        fix_stats = self._get_fix_stats(repo.id)
        metrics.total_fixes_proposed = fix_stats["proposed"]
        metrics.total_fixes_approved = fix_stats["approved"]
        metrics.total_fixes_applied = fix_stats["applied"]
        metrics.total_fixes_failed = fix_stats["failed"]
        metrics.fix_adoption_rate = fix_stats["adoption_rate"]
        metrics.fix_success_rate = fix_stats["success_rate"]
        
        # Calculate reliability score
        metrics.reliability_score = self.calculate_reliability_score(
            critical_risks=metrics.critical_risks,
            high_risks=metrics.high_risks,
            medium_risks=metrics.medium_risks,
            low_risks=metrics.low_risks,
            fix_adoption_rate=metrics.fix_adoption_rate
        )
        metrics.score_grade = metrics.calculate_score_grade()
        
        # Calculate trends
        trends = self._calculate_trends(metrics.id)
        metrics.score_change_7d = trends.get("score_change_7d")
        metrics.score_change_30d = trends.get("score_change_30d")
        metrics.risk_trend_7d = trends.get("risk_trend_7d")
        metrics.risk_trend_30d = trends.get("risk_trend_30d")
        
        # Update timestamps
        metrics.last_analysis_at = datetime.utcnow()
        metrics.last_score_update_at = datetime.utcnow()
        
        self.db_session.commit()
        
        # Create risk snapshot
        self._create_risk_snapshot(
            repo_metrics_id=metrics.id,
            snapshot_type="pr_analysis",
            snapshot_reason=f"PR #{pr_analysis.pr_number} analyzed",
            critical_risks=pr_analysis.critical_risks_count,
            high_risks=pr_analysis.high_risks_count,
            medium_risks=pr_analysis.medium_risks_count,
            low_risks=0,
            reliability_score=metrics.reliability_score,
            pr_analysis_id=pr_analysis.id,
            ledger_run_id=ledger_run_id
        )
        
        # Record ledger event
        if ledger_run_id:
            self._record_ledger_event(
                ledger_run_id=ledger_run_id,
                event_type="RELIABILITY_SCORE_CALCULATED",
                summary=f"Score updated: {metrics.reliability_score:.1f} ({metrics.score_grade})",
                payload_ref=str(metrics.id)
            )
        
        logger.info(f"Updated metrics for repo {repo.id}: score={metrics.reliability_score:.1f}, grade={metrics.score_grade}")
        
        return metrics
    
    def update_metrics_after_fix_applied(
        self,
        fix_id: int,
        ledger_run_id: Optional[str] = None
    ) -> Optional[RepoMetrics]:
        """Update repository metrics after fix is applied.
        
        Args:
            fix_id: CodeFix record ID
            ledger_run_id: Optional ledger run ID
        
        Returns:
            Updated RepoMetrics or None
        """
        # Load fix
        fix = self.db_session.query(CodeFix).filter(
            CodeFix.id == fix_id
        ).first()
        
        if not fix or fix.status != FixStatus.APPLIED:
            logger.warning(f"Fix {fix_id} not found or not applied")
            return None
        
        # Get analysis result and run
        result = fix.result
        if not result:
            return None
        
        analysis_run = self.db_session.query(AnalysisRun).filter(
            AnalysisRun.id == result.run_id
        ).first()
        
        if not analysis_run:
            return None
        
        # Find repository
        repo = self.db_session.query(Repository).filter(
            Repository.id == analysis_run.repository_id
        ).first()
        
        if not repo:
            return None
        
        # Get metrics
        metrics = self.get_or_create_repo_metrics(repo.id)
        
        # Recalculate metrics (fix reduced risk count)
        risk_summary = self._get_recent_risk_summary(repo.id, days=30)
        metrics.critical_risks = risk_summary["critical"]
        metrics.high_risks = risk_summary["high"]
        metrics.medium_risks = risk_summary["medium"]
        metrics.low_risks = risk_summary["low"]
        metrics.total_risks = risk_summary["total"]
        
        # Update fix stats
        fix_stats = self._get_fix_stats(repo.id)
        metrics.total_fixes_proposed = fix_stats["proposed"]
        metrics.total_fixes_approved = fix_stats["approved"]
        metrics.total_fixes_applied = fix_stats["applied"]
        metrics.total_fixes_failed = fix_stats["failed"]
        metrics.fix_adoption_rate = fix_stats["adoption_rate"]
        metrics.fix_success_rate = fix_stats["success_rate"]
        
        # Recalculate score
        metrics.reliability_score = self.calculate_reliability_score(
            critical_risks=metrics.critical_risks,
            high_risks=metrics.high_risks,
            medium_risks=metrics.medium_risks,
            low_risks=metrics.low_risks,
            fix_adoption_rate=metrics.fix_adoption_rate
        )
        metrics.score_grade = metrics.calculate_score_grade()
        
        # Update timestamps
        metrics.last_fix_applied_at = datetime.utcnow()
        metrics.last_score_update_at = datetime.utcnow()
        
        self.db_session.commit()
        
        # Create risk snapshot
        self._create_risk_snapshot(
            repo_metrics_id=metrics.id,
            snapshot_type="fix_applied",
            snapshot_reason=f"Fix #{fix_id} applied",
            critical_risks=metrics.critical_risks,
            high_risks=metrics.high_risks,
            medium_risks=metrics.medium_risks,
            low_risks=metrics.low_risks,
            reliability_score=metrics.reliability_score,
            code_fix_id=fix_id,
            ledger_run_id=ledger_run_id
        )
        
        # Record ledger event
        if ledger_run_id:
            self._record_ledger_event(
                ledger_run_id=ledger_run_id,
                event_type="METRICS_UPDATED",
                summary=f"Metrics updated after fix #{fix_id} applied",
                payload_ref=str(metrics.id)
            )
        
        logger.info(f"Updated metrics after fix #{fix_id}: score={metrics.reliability_score:.1f}")
        
        return metrics
    
    def _get_recent_risk_summary(self, repository_id: int, days: int = 30) -> Dict[str, int]:
        """Get aggregated risk counts from recent analyses.
        
        Args:
            repository_id: Repository ID
            days: Number of days to look back
        
        Returns:
            Dict with risk counts by severity and category
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Query recent PR analyses
        repo = self.db_session.query(Repository).filter(
            Repository.id == repository_id
        ).first()
        
        if not repo:
            return {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "total": 0
            }
        
        # Get recent PR analyses for this repo
        pr_analyses = self.db_session.query(PRAnalysis).filter(
            and_(
                PRAnalysis.repository_full_name == repo.repo_full_name,
                PRAnalysis.status == PRAnalysisStatus.COMPLETED,
                PRAnalysis.completed_at >= cutoff_date
            )
        ).all()
        
        # Aggregate risk counts
        total_critical = sum(pa.critical_risks_count for pa in pr_analyses)
        total_high = sum(pa.high_risks_count for pa in pr_analyses)
        total_medium = sum(pa.medium_risks_count for pa in pr_analyses)
        
        # For category breakdown, we'd need to query AnalysisResult records
        # For now, return basic counts
        return {
            "critical": total_critical,
            "high": total_high,
            "medium": total_medium,
            "low": 0,
            "total": total_critical + total_high + total_medium,
            "crash_risks": 0,  # Would need analysis result details
            "resource_leaks": 0,
            "reliability_antipatterns": 0,
            "scalability_risks": 0,
            "edge_case_vulnerabilities": 0
        }
    
    def _get_fix_stats(self, repository_id: int) -> Dict[str, Any]:
        """Get fix statistics for repository.
        
        Args:
            repository_id: Repository ID
        
        Returns:
            Dict with fix counts and rates
        """
        repo = self.db_session.query(Repository).filter(
            Repository.id == repository_id
        ).first()
        
        if not repo:
            return {
                "proposed": 0,
                "approved": 0,
                "applied": 0,
                "failed": 0,
                "adoption_rate": 0.0,
                "success_rate": 0.0
            }
        
        # Query fixes for this repository's analysis runs
        analysis_runs = self.db_session.query(AnalysisRun).filter(
            AnalysisRun.repository_id == repo.id
        ).all()
        
        analysis_run_ids = [ar.id for ar in analysis_runs]
        
        # Get fix counts
        fixes = self.db_session.query(CodeFix).join(
            AnalysisResult
        ).filter(
            AnalysisResult.run_id.in_(analysis_run_ids)
        ).all()
        
        proposed = len([f for f in fixes if f.status in [FixStatus.PROPOSED, FixStatus.APPROVED, FixStatus.APPLIED]])
        approved = len([f for f in fixes if f.status in [FixStatus.APPROVED, FixStatus.APPLIED]])
        applied = len([f for f in fixes if f.status == FixStatus.APPLIED])
        failed = len([f for f in fixes if f.status == FixStatus.FAILED])
        
        # Calculate rates
        adoption_rate = (applied / proposed) if proposed > 0 else 0.0
        success_rate = (applied / (applied + failed)) if (applied + failed) > 0 else 0.0
        
        return {
            "proposed": proposed,
            "approved": approved,
            "applied": applied,
            "failed": failed,
            "adoption_rate": adoption_rate,
            "success_rate": success_rate
        }
    
    def _calculate_trends(self, repo_metrics_id: int) -> Dict[str, Any]:
        """Calculate score and risk trends.
        
        Args:
            repo_metrics_id: RepoMetrics ID
        
        Returns:
            Dict with trend data
        """
        now = datetime.utcnow()
        
        # Get snapshots from 7 and 30 days ago
        snapshot_7d_ago = self.db_session.query(RiskSnapshot).filter(
            and_(
                RiskSnapshot.repo_metrics_id == repo_metrics_id,
                RiskSnapshot.created_at <= now - timedelta(days=7)
            )
        ).order_by(RiskSnapshot.created_at.desc()).first()
        
        snapshot_30d_ago = self.db_session.query(RiskSnapshot).filter(
            and_(
                RiskSnapshot.repo_metrics_id == repo_metrics_id,
                RiskSnapshot.created_at <= now - timedelta(days=30)
            )
        ).order_by(RiskSnapshot.created_at.desc()).first()
        
        # Get current metrics
        current_metrics = self.db_session.query(RepoMetrics).filter(
            RepoMetrics.id == repo_metrics_id
        ).first()
        
        if not current_metrics:
            return {}
        
        # Calculate score changes
        score_change_7d = None
        score_change_30d = None
        
        if snapshot_7d_ago:
            score_change_7d = current_metrics.reliability_score - snapshot_7d_ago.reliability_score
        
        if snapshot_30d_ago:
            score_change_30d = current_metrics.reliability_score - snapshot_30d_ago.reliability_score
        
        # Determine risk trends
        def determine_trend(current_risks: int, past_risks: Optional[int]) -> str:
            if past_risks is None:
                return "stable"
            
            change_pct = ((current_risks - past_risks) / past_risks * 100) if past_risks > 0 else 0
            
            if change_pct > 10:
                return "increasing"
            elif change_pct < -10:
                return "decreasing"
            else:
                return "stable"
        
        risk_trend_7d = determine_trend(
            current_metrics.total_risks,
            snapshot_7d_ago.total_risks if snapshot_7d_ago else None
        )
        
        risk_trend_30d = determine_trend(
            current_metrics.total_risks,
            snapshot_30d_ago.total_risks if snapshot_30d_ago else None
        )
        
        return {
            "score_change_7d": score_change_7d,
            "score_change_30d": score_change_30d,
            "risk_trend_7d": risk_trend_7d,
            "risk_trend_30d": risk_trend_30d
        }
    
    def _create_risk_snapshot(
        self,
        repo_metrics_id: int,
        snapshot_type: str,
        snapshot_reason: str,
        critical_risks: int,
        high_risks: int,
        medium_risks: int,
        low_risks: int,
        reliability_score: float,
        pr_analysis_id: Optional[int] = None,
        analysis_run_id: Optional[int] = None,
        code_fix_id: Optional[int] = None,
        ledger_run_id: Optional[str] = None
    ) -> RiskSnapshot:
        """Create risk snapshot record.
        
        Args:
            repo_metrics_id: RepoMetrics ID
            snapshot_type: Type of snapshot
            snapshot_reason: Reason for snapshot
            critical_risks: Critical risk count
            high_risks: High risk count
            medium_risks: Medium risk count
            low_risks: Low risk count
            reliability_score: Score at snapshot time
            pr_analysis_id: Optional PR analysis ID
            analysis_run_id: Optional analysis run ID
            code_fix_id: Optional fix ID
            ledger_run_id: Optional ledger run ID
        
        Returns:
            Created RiskSnapshot
        """
        snapshot = RiskSnapshot(
            repo_metrics_id=repo_metrics_id,
            snapshot_type=snapshot_type,
            snapshot_reason=snapshot_reason,
            critical_risks=critical_risks,
            high_risks=high_risks,
            medium_risks=medium_risks,
            low_risks=low_risks,
            total_risks=critical_risks + high_risks + medium_risks + low_risks,
            reliability_score=reliability_score,
            pr_analysis_id=pr_analysis_id,
            analysis_run_id=analysis_run_id,
            code_fix_id=code_fix_id,
            ledger_run_id=ledger_run_id
        )
        
        self.db_session.add(snapshot)
        self.db_session.commit()
        
        logger.debug(f"Created risk snapshot: type={snapshot_type}, score={reliability_score:.1f}")
        
        return snapshot
    
    def _record_ledger_event(
        self,
        ledger_run_id: str,
        event_type: str,
        summary: str,
        payload_ref: Optional[str] = None
    ):
        """Record event in ledger.
        
        Args:
            ledger_run_id: Ledger run ID
            event_type: Event type
            summary: Event summary
            payload_ref: Optional payload reference
        """
        try:
            # Load ledger
            ledger = RunLedgerWriter(
                run_id=ledger_run_id,
                repo_id="metrics-service",
                environment="PRODUCTION",
                initiated_by="METRICS_SERVICE"
            )
            
            # Append event
            ledger.append_event(
                event_type=event_type,
                summary=summary,
                actor="metrics-service",
                actor_role="System",
                phase="PHASE_18",
                payload_ref=payload_ref
            )
        except Exception as e:
            logger.warning(f"Failed to record ledger event: {e}")
    
    def identify_hotspots(self, repository_id: int) -> List[ReliabilityHotspot]:
        """Identify code hotspots with recurring reliability issues.
        
        Args:
            repository_id: Repository ID
        
        Returns:
            List of hotspots ordered by severity
        """
        # Get recent analyses for this repository
        repo = self.db_session.query(Repository).filter(
            Repository.id == repository_id
        ).first()
        
        if not repo:
            return []
        
        # Query analysis results to find files with multiple risks
        analysis_runs = self.db_session.query(AnalysisRun).filter(
            AnalysisRun.repository_id == repo.id
        ).all()
        
        # This would require aggregating AnalysisResult records by file_path
        # For Phase 18.1, return empty list (implement in Phase 18.2)
        return []
