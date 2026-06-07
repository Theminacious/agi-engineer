"""GitHub OAuth utilities and JWT handling."""
import jwt
import requests
import hmac
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Request, Header
from app.config import settings
class GitHubOAuthManager:
    GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
    GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
    GITHUB_USER_URL = "https://api.github.com/user"
    @staticmethod
    def get_authorization_url(state: str) -> str:
        params = {
            "client_id": settings.github_client_id,
            "redirect_uri": f"{settings.frontend_url}/oauth/callback",
            "scope": "repo admin:repo_hook read:org",
            "state": state,
        }
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{GitHubOAuthManager.GITHUB_AUTH_URL}?{query_string}"
    @staticmethod
    def exchange_code_for_token(code: str) -> Dict[str, Any]:
        payload = {
            "client_id": settings.github_client_id,
            "client_secret": settings.github_client_secret,
            "code": code,
            "redirect_uri": f"{settings.frontend_url}/oauth/callback",
        }
        headers = {"Accept": "application/json"}
        logging.error(f"OAuth exchange: client_id={settings.github_client_id}, redirect_uri={settings.frontend_url}/oauth/callback")
        response = requests.post(GitHubOAuthManager.GITHUB_TOKEN_URL, json=payload, headers=headers)
        logging.error(f"GitHub response: {response.status_code} - {response.text}")
        if response.status_code != 200:
            raise ValueError(f"Failed to exchange code: {response.text}")
        data = response.json()
        if "error" in data:
            raise ValueError(f"GitHub OAuth error: {data.get('error_description', data.get('error'))}")
        return data
    @staticmethod
    def get_user_info(access_token: str) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github.v3+json",
        }
        response = requests.get(GitHubOAuthManager.GITHUB_USER_URL, headers=headers)
        response.raise_for_status()
        return response.json()
class JWTManager:
    @staticmethod
    def create_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + (expires_delta or timedelta(days=7))
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.jwt_secret_key, algorithm="HS256")
    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
def validate_webhook_signature(payload: bytes, signature: str) -> bool:
    expected_signature = "sha256=" + hmac.new(
        settings.webhook_secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(signature, expected_signature)
def verify_token(token: str | None = None, authorization: str = Header(None)):
    extracted = token
    if not extracted and authorization and authorization.startswith("Bearer "):
        extracted = authorization.split(" ", 1)[1]
    if not extracted:
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        return JWTManager.verify_token(extracted)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
def get_current_user(request: Request) -> Dict[str, Any]:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = auth_header.split(" ", 1)[1]
    claims = JWTManager.verify_token(token)
    return claims.get("user") or claims
