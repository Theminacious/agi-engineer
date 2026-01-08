"""Analysis run model for tracking code analysis executions."""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.db.base import Base


class RunStatus(str, enum.Enum):
    """Status of an analysis run."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AnalysisRun(Base):
    """Single code analysis execution."""

    __tablename__ = "analysis_runs"

    id = Column(Integer, primary_key=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False, index=True)
    github_event = Column(String(50), nullable=False)  # push, pull_request, etc.
    github_branch = Column(String(255), nullable=False)
    github_commit_sha = Column(String(40), nullable=False)
    pull_request_number = Column(Integer, nullable=True)
    status = Column(Enum(RunStatus), default=RunStatus.PENDING)
    error_message = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    repository = relationship("Repository", back_populates="runs")
    results = relationship("AnalysisResult", back_populates="run", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<AnalysisRun(id={self.id}, status={self.status}, branch={self.github_branch})>"
