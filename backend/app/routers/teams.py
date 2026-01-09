"""Team collaboration API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db import get_db
from app.models.team import Team, TeamRole, ActivityLog, ActivityType
from app.models.installation import Installation
from app.security import verify_token, get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/api/teams", tags=["teams"])


class TeamCreate(BaseModel):
    """Schema for creating a team."""
    name: str
    description: str = ""
    slug: str


class TeamInvite(BaseModel):
    """Schema for inviting user to team."""
    user_id: int
    role: TeamRole = TeamRole.DEVELOPER


@router.post("")
async def create_team(
    team_data: TeamCreate,
    token: str = Depends(verify_token),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """Create a new team workspace.
    
    Args:
        team_data: Team creation data
        token: JWT token
        user: Current user
        db: Database session
        
    Returns:
        Created team details
    """
    # Check if slug is unique
    existing = db.query(Team).filter(Team.slug == team_data.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="Team slug already exists")
    
    # Create team
    team = Team(
        name=team_data.name,
        description=team_data.description,
        slug=team_data.slug,
        owner_id=user.get("user_id"),
    )
    
    db.add(team)
    db.commit()
    db.refresh(team)
    
    return team.to_dict()


@router.get("/{team_id}")
async def get_team(
    team_id: int,
    token: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> dict:
    """Get team details with members and activity.
    
    Args:
        team_id: ID of team
        token: JWT token
        db: Database session
        
    Returns:
        Team details
    """
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    return {
        **team.to_dict(),
        "members": [{"id": m.id, "name": m.name} for m in team.members],
        "role": "owner"  # TODO: Calculate actual role
    }


@router.get("/{team_id}/activity")
async def get_team_activity(
    team_id: int,
    limit: int = 50,
    token: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> dict:
    """Get recent team activity feed.
    
    Args:
        team_id: ID of team
        limit: Max activities to return
        token: JWT token
        db: Database session
        
    Returns:
        Activity log
    """
    activities = db.query(ActivityLog).filter(
        ActivityLog.team_id == team_id
    ).order_by(
        ActivityLog.created_at.desc()
    ).limit(limit).all()
    
    return {
        "team_id": team_id,
        "activities": [a.to_dict() for a in activities],
        "total": len(activities)
    }


@router.post("/{team_id}/members")
async def invite_to_team(
    team_id: int,
    invite_data: TeamInvite,
    token: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> dict:
    """Invite user to team.
    
    Args:
        team_id: ID of team
        invite_data: Invitation data with user and role
        token: JWT token
        db: Database session
        
    Returns:
        Invitation status
    """
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # TODO: Implement actual user invitation system with email
    # For now, just return success
    
    return {
        "status": "invited",
        "team_id": team_id,
        "user_id": invite_data.user_id,
        "role": invite_data.role.value,
        "message": "User invitation queued (email system not yet implemented)"
    }


@router.get("")
async def list_user_teams(
    token: str = Depends(verify_token),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """List all teams for current user.
    
    Args:
        token: JWT token
        user: Current user
        db: Database session
        
    Returns:
        List of user's teams
    """
    # TODO: Implement team membership query
    # For now, return empty
    
    return {
        "teams": [],
        "total": 0,
        "message": "Team system in development"
    }
