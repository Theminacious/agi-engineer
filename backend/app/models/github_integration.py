"""GitHub Integration models for Phase 17.

Models for tracking GitHub webhooks, PR analyses, and integration activity.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db import Base


class WebhookEventType(str, enum.Enum):
    """Types of GitHub webhook events we process."""
    PULL_REQUEST_OPENED = "pull_request.opened"
    PULL_REQUEST_SYNCHRONIZE = "pull_request.synchronize"
    PULL_REQUEST_REOPENED = "pull_request.reopened"
    PUSH = "push"


class PRAnalysisStatus(str, enum.Enum):
    """Status of PR analysis lifecycle."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ReliabilityScore(str, enum.Enum):
    """Overall reliability assessment for a PR."""
    EXCELLENT = "excellent"  # No critical/high risks
    GOOD = "good"            # Some medium risks
    CONCERNING = "concerning"  # High risks present
    CRITICAL = "critical"    # Critical risks present


class GitHubWebhookEvent(Base):
    """Record of incoming GitHub webhook events.
    
    Idempotent processing: delivery_id ensures we don't process twice.
    """
    
    __tablename__ = "github_webhook_events"
    
    id = Column(Integer, primary_key=True)
    
    # Webhook metadata
    delivery_id = Column(String(100), unique=True, nullable=False, index=True)
    event_type = Column(Enum(WebhookEventType), nullable=False)
    signature_verified = Column(Boolean, default=False, nullable=False)
    
    # GitHub resource identifiers
    installation_id = Column(Integer, ForeignKey("installations.id"), nullable=False)
    installation = relationship("Installation")
    
    repository_full_name = Column(String(255), nullable=False)  # owner/repo
    repository_id = Column(Integer, nullable=True)  # GitHub repo ID
    
    # Pull request details (if event_type is PR-related)
    pr_number = Column(Integer, nullable=True)
    pr_head_sha = Column(String(40), nullable=True)
    pr_base_branch = Column(String(255), nullable=True)
    pr_head_branch = Column(String(255), nullable=True)
    
    # Push details (if event_type is push)
    push_ref = Column(String(255), nullable=True)  # refs/heads/main
    push_before_sha = Column(String(40), nullable=True)
    push_after_sha = Column(String(40), nullable=True)
    
    # Raw webhook payload (for debugging)
    raw_payload = Column(JSON, nullable=False)
    
    # Processing status
    processed_at = Column(DateTime, nullable=True)
    processing_error = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship to analysis
    pr_analysis = relationship("PRAnalysis", back_populates="webhook_event", uselist=False)
    
    def __repr__(self) -> str:
        return f"<GitHubWebhookEvent(delivery_id={self.delivery_id}, event_type={self.event_type})>"


class PRAnalysis(Base):
    """Analysis results for a GitHub pull request.
    
    One record per PR head SHA (re-analyze when new commits pushed).
    """
    
    __tablename__ = "pr_analyses"
    
    id = Column(Integer, primary_key=True)
    
    # GitHub identifiers
    repository_full_name = Column(String(255), nullable=False, index=True)
    pr_number = Column(Integer, nullable=False, index=True)
    head_sha = Column(String(40), nullable=False, index=True)
    base_branch = Column(String(255), nullable=False)
    
    # Analysis status
    status = Column(Enum(PRAnalysisStatus), default=PRAnalysisStatus.PENDING, nullable=False)
    
    # Analysis metadata
    analysis_run_id = Column(Integer, ForeignKey("analysis_runs.id"), nullable=True)
    analysis_run = relationship("AnalysisRun")
    
    ledger_run_id = Column(String(100), nullable=True)  # For ledger lookup
    
    # Reliability assessment
    reliability_score = Column(Enum(ReliabilityScore), nullable=True)
    critical_risks_count = Column(Integer, default=0, nullable=False)
    high_risks_count = Column(Integer, default=0, nullable=False)
    medium_risks_count = Column(Integer, default=0, nullable=False)
    
    # Fix candidates
    fix_candidates_count = Column(Integer, default=0, nullable=False)
    auto_fixable_count = Column(Integer, default=0, nullable=False)
    
    # GitHub integration
    comment_posted = Column(Boolean, default=False, nullable=False)
    comment_id = Column(Integer, nullable=True)  # GitHub comment ID
    comment_posted_at = Column(DateTime, nullable=True)
    
    status_check_posted = Column(Boolean, default=False, nullable=False)
    status_check_id = Column(Integer, nullable=True)  # GitHub check run ID
    status_check_conclusion = Column(String(50), nullable=True)  # success|neutral|failure
    
    # Governance link (for UI)
    report_url = Column(String(500), nullable=True)
    
    # Analysis timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Error tracking
    analysis_error = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    webhook_event_id = Column(Integer, ForeignKey("github_webhook_events.id"), nullable=True)
    webhook_event = relationship("GitHubWebhookEvent", back_populates="pr_analysis")
    
    # Unique constraint: one analysis per PR + SHA
    __table_args__ = (
        # Unique index on (repo, pr_number, head_sha)
    )
    
    def __repr__(self) -> str:
        return f"<PRAnalysis(repository={self.repository_full_name}, pr={self.pr_number}, sha={self.head_sha[:7]})>"


class GitHubIntegrationConfig(Base):
    """Per-repository GitHub integration configuration.
    
    Controls which features are enabled for each repository.
    """
    
    __tablename__ = "github_integration_configs"
    
    id = Column(Integer, primary_key=True)
    
    # Repository linkage
    repository_id = Column(Integer, ForeignKey("repositories.id"), unique=True, nullable=False)
    repository = relationship("Repository")
    
    # Feature toggles
    auto_analysis_enabled = Column(Boolean, default=True, nullable=False)
    post_comments = Column(Boolean, default=True, nullable=False)
    post_status_checks = Column(Boolean, default=True, nullable=False)
    
    # Analysis filters
    min_severity = Column(String(20), default="MEDIUM", nullable=False)  # MEDIUM|HIGH|CRITICAL
    analyzer_categories = Column(JSON, nullable=True)  # ["reliability", "security"]
    
    # Comment formatting preferences
    comment_template = Column(String(50), default="standard", nullable=False)
    include_fix_snippets = Column(Boolean, default=True, nullable=False)
    
    # Rate limiting (to avoid spam)
    max_comments_per_pr = Column(Integer, default=10, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self) -> str:
        return f"<GitHubIntegrationConfig(repo_id={self.repository_id}, auto_analysis={self.auto_analysis_enabled})>"
