"""GitHub OAuth utilities and JWT handling."""

import jwt
import requests
import hmac
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from app.config import settings


class GitHubOAuthManager:
    """Handles GitHub OAuth flow and token management."""

    GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
    GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
    GITHUB_USER_URL = "https://api.github.com/user"

    @staticmethod
    def get_authorization_url(state: str) -> str:
        """Generate GitHub OAuth authorization URL.
        
        Args:
            state: CSRF protection token
            
        Returns:
            GitHub OAuth authorize URL
        """
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
        """Exchange authorization code for access token.
        
        Args:
            code: GitHub OAuth authorization code
            
        Returns:
            Dict with access_token, token_type, scope
            
        Raises:
            ValueError: If token exchange fails
        """
        payload = {
            "client_id": settings.github_client_id,
            "client_secret": settings.github_client_secret,
            "code": code,
            "redirect_uri": f"{settings.frontend_url}/oauth/callback",
        }
        headers = {"Accept": "application/json"}

        response = requests.post(GitHubOAuthManager.GITHUB_TOKEN_URL, json=payload, headers=headers)

        if response.status_code != 200:
            raise ValueError(f"Failed to exchange code: {response.text}")

        return response.json()

    @staticmethod
    def get_user_info(access_token: str) -> Dict[str, Any]:
        """Get authenticated user info from GitHub.
        
        Args:
            access_token: GitHub access token
            
        Returns:
            User info dict with login, id, name, email, etc.
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github.v3+json",
        }
        response = requests.get(GitHubOAuthManager.GITHUB_USER_URL, headers=headers)
        response.raise_for_status()
        return response.json()


class JWTManager:
    """JWT token creation and validation."""

    @staticmethod
    def create_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT token.
        
        Args:
            data: Claims to encode
            expires_delta: Expiration time delta (default 7 days)
            
        Returns:
            Encoded JWT token
        """
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=7)

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm="HS256")
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """Verify and decode JWT token.
        
        Args:
            token: JWT token to verify
            
        Returns:
            Decoded claims
            
        Raises:
            jwt.InvalidTokenError: If token is invalid
        """
        return jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])


def validate_webhook_signature(payload: bytes, signature: str) -> bool:
    """Validate GitHub webhook signature.
    
    Args:
        payload: Raw webhook payload bytes
        signature: X-Hub-Signature header value (format: sha256=hash)
        
    Returns:
        True if signature is valid
    """
    expected_signature = "sha256=" + hmac.new(
        settings.webhook_secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(signature, expected_signature)
