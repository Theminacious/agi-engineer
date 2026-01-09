"""Database models for AI-generated fixes and PR suggestions."""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db import Base


class FixStatus(str, enum.Enum):
    """Status of AI-generated fix."""
    PENDING = "pending"
    GENERATED = "generated"
    APPLIED = "applied"
    REJECTED = "rejected"
    FAILED = "failed"


class CodeFix(Base):
    """AI-generated code fix for an issue."""
    
    __tablename__ = "code_fixes"
    
    id = Column(Integer, primary_key=True)
    
    # Relationships
    result_id = Column(Integer, ForeignKey("analysis_results.id"), nullable=False)
    result = relationship("AnalysisResult", back_populates="code_fixes")
    
    # Fix details
    original_code = Column(Text, nullable=False)
    fixed_code = Column(Text, nullable=False)
    explanation = Column(Text)
    
    # Status
    status = Column(Enum(FixStatus), default=FixStatus.GENERATED, nullable=False)
    
    # PR generation
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
            "original_code": self.original_code,
            "fixed_code": self.fixed_code,
            "explanation": self.explanation,
            "status": self.status.value if self.status else None,
            "pr_url": self.pr_url,
            "ai_provider": self.ai_provider,
            "created_at": self.created_at.isoformat() if self.created_at else None,
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
