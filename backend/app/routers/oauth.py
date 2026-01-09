"""OAuth-related API endpoints."""

import uuid
from fastapi import APIRouter, Query, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.installation import Installation
from app.security import GitHubOAuthManager, JWTManager
from app.config import settings

router = APIRouter(prefix="/oauth", tags=["oauth"])


@router.get("/authorize")
async def authorize_oauth() -> dict:
    """Initiate GitHub OAuth flow.
    
    Returns:
        Authorization URL to redirect user to
    """
    # For development with placeholder credentials, enable demo mode
    if settings.github_client_id in ["dev_client_id", "abc123def456"]:
        # Return demo auth URL that redirects back with demo code
        return {
            "authorization_url": f"{settings.frontend_url}/oauth/callback?code=dev_code&state=dev_state",
            "state": "dev_state",
        }
    
    state = str(uuid.uuid4())  # CSRF protection
    auth_url = GitHubOAuthManager.get_authorization_url(state)
    return {
        "authorization_url": auth_url,
        "state": state,
    }


@router.get("/callback")
async def oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
) -> dict:
    """GitHub OAuth callback handler.
    
    Args:
        code: GitHub authorization code
        state: CSRF state token
        db: Database session
        
    Returns:
        JWT token and user info
        
    Raises:
        HTTPException: If OAuth flow fails
    """
    try:
        # Handle development/demo mode with placeholder credentials
        if settings.github_client_id in ["dev_client_id", "abc123def456"] or code == "dev_code":
            github_user = "demo_user"
            github_id = 999999
            access_token = "dev_token"
        else:
            # Exchange code for token
            token_response = GitHubOAuthManager.exchange_code_for_token(code)
            access_token = token_response.get("access_token")

            if not access_token:
                raise ValueError("No access token in response")

            # Get user info
            user_info = GitHubOAuthManager.get_user_info(access_token)
            github_user = user_info.get("login")
            github_id = user_info.get("id")

        # Store or update installation
        installation = db.query(Installation).filter(
            Installation.github_user == github_user
        ).first()

        if not installation:
            installation = Installation(
                installation_id=github_id,
                github_user=github_user,
                github_org="demo_org" if code == "dev_code" else None,
                access_token=access_token,
            )
            db.add(installation)
        else:
            installation.access_token = access_token
            installation.is_active = True

        db.commit()

        # Create JWT
        jwt_token = JWTManager.create_token({"user": github_user, "installation_id": installation.id})

        return {
            "token": jwt_token,
            "user": github_user,
            "installation_id": installation.id,
            "message": "Successfully authenticated with GitHub",
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth callback failed: {str(e)}")


@router.post("/refresh")
async def refresh_token(
    current_token: str = Query(...),
    db: Session = Depends(get_db),
) -> dict:
    """Refresh JWT token.
    
    Args:
        current_token: Current JWT token
        db: Database session
        
    Returns:
        New JWT token
    """
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


