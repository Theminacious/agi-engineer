"""Team collaboration models for multi-user workspaces."""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum, Table
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db import Base


class TeamRole(str, enum.Enum):
    """User role within a team."""
    ADMIN = "admin"
    DEVELOPER = "developer"
    VIEWER = "viewer"


class ActivityType(str, enum.Enum):
    """Type of activity in team."""
    RUN_CREATED = "run_created"
    RUN_COMPLETED = "run_completed"
    ISSUE_FOUND = "issue_found"
    FIX_GENERATED = "fix_generated"
    PR_CREATED = "pr_created"
    USER_JOINED = "user_joined"
    SETTINGS_CHANGED = "settings_changed"


# Association table for team members
team_members = Table(
    'team_members',
    Base.metadata,
    Column('team_id', Integer, ForeignKey('teams.id'), primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('role', Enum(TeamRole), default=TeamRole.DEVELOPER),
    Column('joined_at', DateTime, default=datetime.utcnow),
)


class Team(Base):
    """Team workspace for collaborative code analysis."""
    
    __tablename__ = "teams"
    
    id = Column(Integer, primary_key=True)
    
    # Basic info
    name = Column(String(255), nullable=False)
    description = Column(Text)
    slug = Column(String(255), unique=True, nullable=False)  # URL-friendly name
    
    # Owner
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User", foreign_keys=[owner_id])
    
    # Members
    members = relationship(
        "User",
        secondary=team_members,
        backref="teams"
    )
    
    # Settings
    is_active = Column(Boolean, default=True)
    max_repositories = Column(Integer, default=10)  # Free tier limit
    max_concurrent_runs = Column(Integer, default=2)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    activity_logs = relationship("ActivityLog", back_populates="team")
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "slug": self.slug,
            "owner_id": self.owner_id,
            "member_count": len(self.members),
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ActivityLog(Base):
    """Log of team activities for audit and notifications."""
    
    __tablename__ = "activity_logs"
    
    id = Column(Integer, primary_key=True)
    
    # Relationships
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    team = relationship("Team", back_populates="activity_logs")
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User")
    
    # Activity details
    activity_type = Column(Enum(ActivityType), nullable=False)
    description = Column(Text)
    
    # Reference to affected resource
    run_id = Column(Integer, ForeignKey("analysis_runs.id"))
    result_id = Column(Integer, ForeignKey("analysis_results.id"))
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "team_id": self.team_id,
            "user_id": self.user_id,
            "user_name": self.user.name if self.user else "Unknown",
            "activity_type": self.activity_type.value if self.activity_type else None,
            "description": self.description,
            "run_id": self.run_id,
            "result_id": self.result_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Workspace(Base):
    """Personal or team workspace containing repositories and runs."""
    
    __tablename__ = "workspaces"
    
    id = Column(Integer, primary_key=True)
    
    # Basic info
    name = Column(String(255), nullable=False)
    type = Column(String(50), default="personal")  # "personal" or "team"
    
    # Owner
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User", foreign_keys=[owner_id])
    
    # Team reference (if type="team")
    team_id = Column(Integer, ForeignKey("teams.id"))
    team = relationship("Team")
    
    # Settings
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "owner_id": self.owner_id,
            "team_id": self.team_id,
            "is_default": self.is_default,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
