"""Repository model for tracked GitHub repositories."""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base


class Repository(Base):
    """GitHub repository being analyzed."""

    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True)
    installation_id = Column(Integer, ForeignKey("installations.id"), nullable=False, index=True)
    repo_name = Column(String(255), nullable=False)
    repo_full_name = Column(String(255), nullable=False, unique=True, index=True)
    github_repo_id = Column(Integer, unique=True, index=True, nullable=False)
    is_enabled = Column(Boolean, default=True)
    analysis_config = Column(String(2000), nullable=True)  # JSON config
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    installation = relationship("Installation", back_populates="repositories")
    runs = relationship("AnalysisRun", back_populates="repository", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Repository(repo_full_name={self.repo_full_name})>"
