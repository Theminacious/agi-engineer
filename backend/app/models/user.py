"""Minimal User model to satisfy relationships in Team and ActivityLog."""

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base


class User(Base):
    """Application user record.
    This is a minimal placeholder used for relationship mapping.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships will be established from other models (e.g., Team.members, ActivityLog.user)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, name={self.name})>"
