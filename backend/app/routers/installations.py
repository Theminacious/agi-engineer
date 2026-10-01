"""Installation management endpoints."""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.installation import Installation
from app.models.repository import Repository
from app.schemas import InstallationResponse
from app.authz import Principal, get_principal
from typing import List

router = APIRouter(prefix="/installations", tags=["installations"])


def _own_installation_id(installation_id: int, principal: Principal) -> int:
    if installation_id != principal.installation_id:
        raise HTTPException(status_code=404, detail="Not found")
    return installation_id


@router.get("/", response_model=List[InstallationResponse])
async def list_installations(
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_principal),
) -> list:
    """List installations owned by the authenticated principal."""
    return (
        db.query(Installation)
        .filter(Installation.id == principal.installation_id)
        .all()
    )


@router.get("/{installation_id}", response_model=InstallationResponse)
async def get_installation(
    installation_id: int,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_principal),
) -> Installation:
    """Get the caller's own installation by ID (404 for any other)."""
    _own_installation_id(installation_id, principal)
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
    principal: Principal = Depends(get_principal),
) -> dict:
    """Uninstall the GitHub App for the caller's own installation."""
    _own_installation_id(installation_id, principal)
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
    principal: Principal = Depends(get_principal),
) -> dict:
    """Enable analysis for a repository in the caller's own installation."""
    _own_installation_id(installation_id, principal)
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
    principal: Principal = Depends(get_principal),
) -> dict:
    """Disable analysis for a repository in the caller's own installation."""
    _own_installation_id(installation_id, principal)
    repository = db.query(Repository).filter(
        Repository.id == repo_id,
        Repository.installation_id == installation_id,
    ).first()

    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")

    repository.is_enabled = False
    db.commit()

    return {"status": "disabled", "repository": repository.repo_full_name}
