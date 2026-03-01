"""Reliability Metrics models for Phase 18 — Insights Dashboard.

Models for tracking repository reliability scores, risk snapshots, and trends.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db import Base


class RepoMetrics(Base):
    """Aggregated reliability metrics for a repository.
    
    Updated after each PR analysis and fix application.
    Provides current snapshot of repository health.
    """
    
    __tablename__ = "repo_metrics"
    
    id = Column(Integer, primary_key=True)
    
    # Repository linkage
    repository_id = Column(Integer, ForeignKey("repositories.id"), unique=True, nullable=False, index=True)
    repository = relationship("Repository")
    
    # Overall reliability score (0-100)
    reliability_score = Column(Float, nullable=False, default=100.0)
    score_grade = Column(String(1), nullable=False, default="A")  # A, B, C, D, F
    
    # Risk counts
    total_risks = Column(Integer, nullable=False, default=0)
    critical_risks = Column(Integer, nullable=False, default=0)
    high_risks = Column(Integer, nullable=False, default=0)
    medium_risks = Column(Integer, nullable=False, default=0)
    low_risks = Column(Integer, nullable=False, default=0)
    
    # Fix metrics
    total_fixes_proposed = Column(Integer, nullable=False, default=0)
    total_fixes_approved = Column(Integer, nullable=False, default=0)
    total_fixes_applied = Column(Integer, nullable=False, default=0)
    total_fixes_failed = Column(Integer, nullable=False, default=0)
    fix_adoption_rate = Column(Float, nullable=False, default=0.0)  # % of proposed fixes applied
    fix_success_rate = Column(Float, nullable=False, default=0.0)   # % of applied fixes that succeeded
    
    # PR analysis metrics
    total_prs_analyzed = Column(Integer, nullable=False, default=0)
    prs_with_critical_risks = Column(Integer, nullable=False, default=0)
    prs_with_high_risks = Column(Integer, nullable=False, default=0)
    prs_with_no_risks = Column(Integer, nullable=False, default=0)
    
    # Risk category breakdown (from Phase 16)
    crash_risks = Column(Integer, nullable=False, default=0)
    resource_leaks = Column(Integer, nullable=False, default=0)
    reliability_antipatterns = Column(Integer, nullable=False, default=0)
    scalability_risks = Column(Integer, nullable=False, default=0)
    edge_case_vulnerabilities = Column(Integer, nullable=False, default=0)
    
    # Trend indicators
    score_change_7d = Column(Float, nullable=True)   # Change in score over last 7 days
    score_change_30d = Column(Float, nullable=True)  # Change in score over last 30 days
    risk_trend_7d = Column(String(20), nullable=True)  # increasing | stable | decreasing
    risk_trend_30d = Column(String(20), nullable=True)
    
    # Time tracking
    last_analysis_at = Column(DateTime, nullable=True)
    last_fix_applied_at = Column(DateTime, nullable=True)
    last_score_update_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    risk_snapshots = relationship("RiskSnapshot", back_populates="repo_metrics", cascade="all, delete-orphan")
    reliability_scores = relationship("ReliabilityScore", back_populates="repo_metrics", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<RepoMetrics(repo_id={self.repository_id}, score={self.reliability_score:.1f}, grade={self.score_grade})>"
    
    def calculate_score_grade(self) -> str:
        """Calculate letter grade from numeric score.
        
        Returns:
            Letter grade (A, B, C, D, F)
        """
        if self.reliability_score >= 90:
            return "A"
        elif self.reliability_score >= 80:
            return "B"
        elif self.reliability_score >= 70:
            return "C"
        elif self.reliability_score >= 60:
            return "D"
        else:
            return "F"


class RiskSnapshot(Base):
    """Point-in-time snapshot of repository risks.
    
    Created after each PR analysis to track risk trends over time.
    Enables trend analysis and risk trajectory visualization.
    """
    
    __tablename__ = "risk_snapshots"
    
    id = Column(Integer, primary_key=True)
    
    # Repository linkage
    repo_metrics_id = Column(Integer, ForeignKey("repo_metrics.id"), nullable=False, index=True)
    repo_metrics = relationship("RepoMetrics")
    
    # Snapshot metadata
    snapshot_type = Column(String(50), nullable=False, index=True)  # pr_analysis | fix_applied | daily_aggregation
    snapshot_reason = Column(String(255), nullable=True)  # PR #123 analyzed | Fix #456 applied
    
    # Risk counts at snapshot time
    critical_risks = Column(Integer, nullable=False)
    high_risks = Column(Integer, nullable=False)
    medium_risks = Column(Integer, nullable=False)
    low_risks = Column(Integer, nullable=False)
    total_risks = Column(Integer, nullable=False)
    
    # Risk category breakdown
    crash_risks = Column(Integer, nullable=False, default=0)
    resource_leaks = Column(Integer, nullable=False, default=0)
    reliability_antipatterns = Column(Integer, nullable=False, default=0)
    scalability_risks = Column(Integer, nullable=False, default=0)
    edge_case_vulnerabilities = Column(Integer, nullable=False, default=0)
    
    # Reliability score at snapshot time
    reliability_score = Column(Float, nullable=False)
    
    # Related analysis/fix
    pr_analysis_id = Column(Integer, ForeignKey("pr_analyses.id"), nullable=True)
    analysis_run_id = Column(Integer, ForeignKey("analysis_runs.id"), nullable=True)
    code_fix_id = Column(Integer, ForeignKey("code_fixes.id"), nullable=True)
    
    # Ledger reference
    ledger_run_id = Column(String(100), nullable=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Index for time-series queries
    __table_args__ = (
        Index('idx_risk_snapshots_repo_time', 'repo_metrics_id', 'created_at'),
    )
    
    def __repr__(self) -> str:
        return f"<RiskSnapshot(repo_metrics_id={self.repo_metrics_id}, type={self.snapshot_type}, risks={self.total_risks}, score={self.reliability_score:.1f})>"


class ReliabilityScore(Base):
    """Historical reliability score tracking.
    
    Maintains daily/weekly aggregated scores for trend analysis.
    Enables long-term reliability tracking and reporting.
    """
    
    __tablename__ = "reliability_scores"
    
    id = Column(Integer, primary_key=True)
    
    # Repository linkage
    repo_metrics_id = Column(Integer, ForeignKey("repo_metrics.id"), nullable=False, index=True)
    repo_metrics = relationship("RepoMetrics")
    
    # Score data
    reliability_score = Column(Float, nullable=False)
    score_grade = Column(String(1), nullable=False)
    
    # Aggregation period
    period_type = Column(String(20), nullable=False, index=True)  # daily | weekly | monthly
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Risk summary for period
    avg_critical_risks = Column(Float, nullable=False, default=0.0)
    avg_high_risks = Column(Float, nullable=False, default=0.0)
    avg_total_risks = Column(Float, nullable=False, default=0.0)
    
    # Activity summary for period
    prs_analyzed = Column(Integer, nullable=False, default=0)
    fixes_applied = Column(Integer, nullable=False, default=0)
    
    # Score change from previous period
    score_change = Column(Float, nullable=True)
    
    # Metadata
    calculation_metadata = Column(JSON, nullable=True)  # Additional context
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Index for time-series queries
    __table_args__ = (
        Index('idx_reliability_scores_repo_period', 'repo_metrics_id', 'period_type', 'period_start'),
    )
    
    def __repr__(self) -> str:
        return f"<ReliabilityScore(repo_metrics_id={self.repo_metrics_id}, score={self.reliability_score:.1f}, period={self.period_type})>"


class ReliabilityHotspot(Base):
    """Code hotspots with recurring reliability issues.
    
    Identifies files/modules with repeated risks across multiple analyses.
    Helps teams prioritize refactoring efforts.
    """
    
    __tablename__ = "reliability_hotspots"
    
    id = Column(Integer, primary_key=True)
    
    # Repository linkage
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False, index=True)
    repository = relationship("Repository")
    
    # File/module identification
    file_path = Column(String(500), nullable=False, index=True)
    module_name = Column(String(255), nullable=True)
    
    # Risk statistics
    total_risks_found = Column(Integer, nullable=False, default=1)
    critical_risks_found = Column(Integer, nullable=False, default=0)
    high_risks_found = Column(Integer, nullable=False, default=0)
    
    # Risk categories (most common)
    primary_risk_category = Column(String(100), nullable=True)  # crash_risks, resource_leaks, etc.
    risk_category_breakdown = Column(JSON, nullable=True)  # {"crash_risks": 3, "resource_leaks": 2}
    
    # Fix status
    fixes_proposed = Column(Integer, nullable=False, default=0)
    fixes_applied = Column(Integer, nullable=False, default=0)
    still_has_risks = Column(Boolean, nullable=False, default=True)
    
    # Hotspot score (higher = more urgent)
    hotspot_score = Column(Float, nullable=False, default=0.0)
    
    # Time tracking
    first_seen_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_seen_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_fix_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint: one hotspot per repo + file
    __table_args__ = (
        Index('idx_hotspot_repo_file', 'repository_id', 'file_path'),
    )
    
    def __repr__(self) -> str:
        return f"<ReliabilityHotspot(repo_id={self.repository_id}, file={self.file_path}, risks={self.total_risks_found}, score={self.hotspot_score:.1f})>"
