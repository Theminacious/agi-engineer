"""Installation management endpoints."""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.installation import Installation
from app.models.repository import Repository
from app.schemas import InstallationResponse
from typing import List

router = APIRouter(prefix="/installations", tags=["installations"])


@router.get("/", response_model=List[InstallationResponse])
async def list_installations(db: Session = Depends(get_db)) -> list:
    """List all installations.
    
    Returns:
        List of Installation objects
    """
    installations = db.query(Installation).all()
    return installations


@router.get("/{installation_id}", response_model=InstallationResponse)
async def get_installation(
    installation_id: int,
    db: Session = Depends(get_db),
) -> Installation:
    """Get installation by ID.
    
    Args:
        installation_id: Installation database ID
        db: Database session
        
    Returns:
        Installation object
        
    Raises:
        HTTPException: If installation not found
    """
    installation = db.query(Installation).filter(
        Installation.id == installation_id
    ).first()

    if not installation:
        raise HTTPException(status_code=404, detail="Installation not found")

    return installation


@router.delete("/{installation_id}")
async def uninstall(
    installation_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Uninstall the GitHub App for an installation.
    
    Marks installation as inactive but preserves history.
    
    Args:
        installation_id: Installation database ID
        db: Database session
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If installation not found
    """
    installation = db.query(Installation).filter(
        Installation.id == installation_id
    ).first()

    if not installation:
        raise HTTPException(status_code=404, detail="Installation not found")

    installation.is_active = False
    db.commit()

    return {"status": "uninstalled", "installation_id": installation_id}


@router.post("/{installation_id}/repositories/{repo_id}/enable")
async def enable_repository(
    installation_id: int,
    repo_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Enable analysis for a repository.
    
    Args:
        installation_id: Installation database ID
        repo_id: Repository database ID
        db: Database session
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If repository not found
    """
    repository = db.query(Repository).filter(
        Repository.id == repo_id,
        Repository.installation_id == installation_id,
    ).first()

    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")

    repository.is_enabled = True
    db.commit()

    return {"status": "enabled", "repository": repository.repo_full_name}


@router.post("/{installation_id}/repositories/{repo_id}/disable")
async def disable_repository(
    installation_id: int,
    repo_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Disable analysis for a repository.
    
    Args:
        installation_id: Installation database ID
        repo_id: Repository database ID
        db: Database session
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If repository not found
    """
    repository = db.query(Repository).filter(
        Repository.id == repo_id,
        Repository.installation_id == installation_id,
    ).first()

    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")

    repository.is_enabled = False
    db.commit()

    return {"status": "disabled", "repository": repository.repo_full_name}
