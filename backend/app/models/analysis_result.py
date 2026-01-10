"""Analysis result model for storing discovered issues and fixes."""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.db.base import Base


class IssueCategory(str, enum.Enum):
    """Category of code issue."""

    SAFE = "safe"
    REVIEW = "review"
    SUGGESTION = "suggestion"


class AnalysisResult(Base):
    """Individual issue or fix result from analysis."""

    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("analysis_runs.id"), nullable=False, index=True)
    file_path = Column(String(500), nullable=False)
    line_number = Column(Integer, nullable=False)
    issue_code = Column(String(20), nullable=False)  # e.g., E501, F841
    issue_name = Column(String(255), nullable=False)
    category = Column(Enum(IssueCategory), nullable=False)
    severity = Column(String(20), nullable=False)  # error, warning, info
    message = Column(String(1000), nullable=False)
    suggestion = Column(Text, nullable=True)
    before_code = Column(Text, nullable=True)
    after_code = Column(Text, nullable=True)
    is_fixed = Column(Integer, default=0)  # 0=no, 1=yes, 2=partial
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    run = relationship("AnalysisRun", back_populates="results")
    # Link generated code fixes to this result
    code_fixes = relationship(
        "CodeFix",
        back_populates="result",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<AnalysisResult(file={self.file_path}:{self.line_number}, code={self.issue_code})>"
