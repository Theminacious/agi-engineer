"""Pydantic schemas for request/response validation."""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# OAuth Schemas
class OAuthAuthorizeResponse(BaseModel):
    """OAuth authorization URL response."""

    authorization_url: str
    state: str


class OAuthCallbackResponse(BaseModel):
    """OAuth callback response with JWT token."""

    token: str
    user: str
    installation_id: int
    message: str


class TokenRefreshRequest(BaseModel):
    """JWT token refresh request."""

    current_token: str


class TokenRefreshResponse(BaseModel):
    """JWT token refresh response."""

    token: str


# Analysis Schemas
class AnalysisRunResponse(BaseModel):
    """Analysis run response."""

    status: str
    event: str
    repository: str
    branch: str
    run_id: int
    pr: Optional[int] = None


# Webhook Schemas
class WebhookResponse(BaseModel):
    """Generic webhook response."""

    status: str
    event: str
    repository: str
    run_id: Optional[int] = None


class InstallationResponse(BaseModel):
    """Installation information."""

    id: int
    installation_id: Optional[int]
    github_user: str
    github_org: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
