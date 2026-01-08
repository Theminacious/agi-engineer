"""GitHub App installation model."""

from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base


class Installation(Base):
    """GitHub App installation record."""

    __tablename__ = "installations"

    id = Column(Integer, primary_key=True)
    installation_id = Column(Integer, unique=True, index=True, nullable=False)
    github_user = Column(String(255), nullable=False)
    github_org = Column(String(255), nullable=True)
    access_token = Column(String(500), nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    repositories = relationship("Repository", back_populates="installation", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Installation(installation_id={self.installation_id}, github_user={self.github_user})>"
