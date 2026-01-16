"""Database models for AI-generated fixes and PR suggestions.

Phase 15.1: Governed Fix Approval & Application
- Approval workflow (proposed → approved/rejected → applied/failed)
- Ledger integration for audit trail
- Plan-based access control
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db import Base


class FixStatus(str, enum.Enum):
    """Status of AI-generated fix lifecycle."""
    PROPOSED = "proposed"      # Initial state: fix generated, awaiting review
    APPROVED = "approved"      # Human approved, ready to apply
    REJECTED = "rejected"      # Human rejected, will not be applied
    APPLIED = "applied"        # Successfully applied to codebase
    FAILED = "failed"          # Application failed (technical error)
    
    # Legacy states (backward compatibility)
    PENDING = "pending"
    GENERATED = "generated"


class CodeFix(Base):
    """AI-generated code fix for an issue.
    
    Phase 15.1 Governance:
    - Lifecycle: proposed → approved/rejected → applied/failed
    - All state transitions recorded in ledger
    - Plan-based access control enforced
    """
    
    __tablename__ = "code_fixes"
    
    id = Column(Integer, primary_key=True)
    
    # Relationships
    result_id = Column(Integer, ForeignKey("analysis_results.id"), nullable=False)
    result = relationship("AnalysisResult", back_populates="code_fixes")
    
    # Fix details
    file_path = Column(String(500), nullable=True)  # Target file path
    original_code = Column(Text, nullable=False)
    fixed_code = Column(Text, nullable=False)
    explanation = Column(Text)
    patch = Column(Text, nullable=True)  # Unified diff patch
    
    # Status & lifecycle
    status = Column(Enum(FixStatus), default=FixStatus.PROPOSED, nullable=False)
    
    # Governance (Phase 15.1)
    approved_by = Column(String(255), nullable=True)  # User email/ID
    approved_at = Column(DateTime, nullable=True)
    approval_plan = Column(String(50), nullable=True)  # Plan at approval time
    
    applied_by = Column(String(255), nullable=True)  # User email/ID
    applied_at = Column(DateTime, nullable=True)
    application_plan = Column(String(50), nullable=True)  # Plan at application time
    
    rejected_by = Column(String(255), nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Ledger integration
    ledger_run_id = Column(String(100), nullable=True)  # Run ID for ledger lookup
    approval_ledger_event_id = Column(String(100), nullable=True)  # Ledger event UUID
    application_ledger_event_id = Column(String(100), nullable=True)
    
    # Application outcome
    application_error = Column(Text, nullable=True)  # Error message if failed
    application_metadata = Column(JSON, nullable=True)  # Additional context
    
    # PR generation (legacy)
    pr_url = Column(String(255))  # URL to generated PR
    pr_created_at = Column(DateTime)
    
    # Metadata
    ai_provider = Column(String(50), default="groq")  # "groq" or "claude"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "result_id": self.result_id,
            "file_path": self.file_path,
            "original_code": self.original_code,
            "fixed_code": self.fixed_code,
            "explanation": self.explanation,
            "patch": self.patch,
            "status": self.status.value if self.status else None,
            
            # Governance
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "approval_plan": self.approval_plan,
            
            "applied_by": self.applied_by,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
            "application_plan": self.application_plan,
            
            "rejected_by": self.rejected_by,
            "rejected_at": self.rejected_at.isoformat() if self.rejected_at else None,
            "rejection_reason": self.rejection_reason,
            
            # Ledger
            "ledger_run_id": self.ledger_run_id,
            "approval_ledger_event_id": self.approval_ledger_event_id,
            "application_ledger_event_id": self.application_ledger_event_id,
            
            # Application
            "application_error": self.application_error,
            "application_metadata": self.application_metadata,
            
            # Legacy
            "pr_url": self.pr_url,
            "ai_provider": self.ai_provider,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class GitHubPullRequest(Base):
    """Tracked GitHub PR created by AGI Engineer."""
    
    __tablename__ = "github_pull_requests"
    
    id = Column(Integer, primary_key=True)
    
    # Relationships
    run_id = Column(Integer, ForeignKey("analysis_runs.id"), nullable=False)
    run = relationship("AnalysisRun", back_populates="generated_prs")
    
    # PR details
    pr_number = Column(Integer, nullable=False)
    pr_url = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Branch info
    branch_name = Column(String(255), nullable=False)
    base_branch = Column(String(255), default="main")
    
    # Status
    is_merged = Column(Boolean, default=False)
    merged_at = Column(DateTime)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "run_id": self.run_id,
            "pr_number": self.pr_number,
            "pr_url": self.pr_url,
            "title": self.title,
            "branch_name": self.branch_name,
            "is_merged": self.is_merged,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
