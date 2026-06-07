"""OAuth-related API endpoints."""

import uuid
import logging
from fastapi import APIRouter, Query, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.installation import Installation
from app.security import GitHubOAuthManager, JWTManager
from app.config import settings

router = APIRouter(prefix="/oauth", tags=["oauth"])


@router.get("/authorize")
async def authorize_oauth() -> dict:
    state = str(uuid.uuid4())
    auth_url = GitHubOAuthManager.get_authorization_url(state)
    return {"authorization_url": auth_url, "state": state}


@router.get("/callback")
async def oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
) -> dict:
    try:
        token_response = GitHubOAuthManager.exchange_code_for_token(code)
        access_token = token_response.get("access_token")

        if not access_token:
            raise ValueError(f"No access token. Response: {token_response}")

        user_info = GitHubOAuthManager.get_user_info(access_token)
        github_user = user_info.get("login")
        github_id = user_info.get("id")

        logging.error(f"Got user: {github_user}, id: {github_id}")

        installation = db.query(Installation).filter(
            Installation.github_user == github_user
        ).first()

        if not installation:
            installation = Installation(
                installation_id=github_id,
                github_user=github_user,
                github_org=None,
                access_token=access_token,
            )
            db.add(installation)
        else:
            installation.access_token = access_token
            installation.is_active = True

        db.commit()
        db.refresh(installation)
        logging.error(f"Saved installation id: {installation.id}")

        jwt_token = JWTManager.create_token({
            "user": github_user,
            "installation_id": installation.id
        })

        return {
            "token": jwt_token,
            "user": github_user,
            "installation_id": installation.id,
            "message": "Successfully authenticated with GitHub",
        }

    except Exception as e:
        logging.error(f"OAuth callback error: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=400, detail=f"OAuth callback failed: {str(e)}")


@router.post("/refresh")
async def refresh_token(
    current_token: str = Query(...),
    db: Session = Depends(get_db),
) -> dict:
    try:
        claims = JWTManager.verify_token(current_token)
        installation_id = claims.get("installation_id")
        installation = db.query(Installation).filter(
            Installation.id == installation_id
        ).first()
        if not installation or not installation.is_active:
            raise HTTPException(status_code=401, detail="Installation not found or inactive")
        new_token = JWTManager.create_token({
            "user": installation.github_user,
            "installation_id": installation.id,
        })
        return {"token": new_token}
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token refresh failed: {str(e)}")
