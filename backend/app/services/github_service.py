"""GitHub Service for Phase 17 — GitHub Intelligence Integration.

Handles GitHub App authentication, API interactions, and webhook verification.
"""

import hmac
import hashlib
import logging
import os
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

import httpx
from sqlalchemy.orm import Session

from app.models import Installation

logger = logging.getLogger(__name__)


class GitHubService:
    """Service for interacting with GitHub API.
    
    Features:
    - GitHub App authentication (installation tokens)
    - Webhook signature verification
    - PR comment posting
    - Status check creation
    - Repository cloning
    """
    
    def __init__(self, db_session: Optional[Session] = None):
        """Initialize GitHub service.
        
        Args:
            db_session: Optional database session for token storage
        """
        self.db_session = db_session
        self.client = httpx.Client(timeout=30.0)
        
        # Configuration from environment
        self.app_id = os.getenv("GITHUB_APP_ID")
        self.private_key = os.getenv("GITHUB_APP_PRIVATE_KEY")
        self.webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET")
        self.client_id = os.getenv("GITHUB_CLIENT_ID")
        self.client_secret = os.getenv("GITHUB_CLIENT_SECRET")
        
        self.api_base_url = "https://api.github.com"
    
    def verify_webhook_signature(
        self,
        payload: bytes,
        signature_header: str
    ) -> bool:
        """Verify GitHub webhook signature.
        
        Args:
            payload: Raw webhook payload bytes
            signature_header: X-Hub-Signature-256 header value
        
        Returns:
            True if signature is valid, False otherwise
        """
        if not self.webhook_secret:
            logger.warning("GITHUB_WEBHOOK_SECRET not configured, skipping signature verification")
            return False
        
        if not signature_header:
            logger.warning("No signature header provided")
            return False
        
        # Extract signature from header (format: "sha256=<signature>")
        if not signature_header.startswith("sha256="):
            logger.warning(f"Invalid signature format: {signature_header}")
            return False
        
        expected_signature = signature_header.split("=", 1)[1]
        
        # Compute HMAC-SHA256
        secret_bytes = self.webhook_secret.encode("utf-8")
        computed_signature = hmac.new(
            secret_bytes,
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Constant-time comparison
        is_valid = hmac.compare_digest(computed_signature, expected_signature)
        
        if not is_valid:
            logger.warning("Webhook signature verification failed")
        
        return is_valid
    
    def get_installation_token(
        self,
        installation_id: int
    ) -> Optional[str]:
        """Get installation access token for GitHub App.
        
        Args:
            installation_id: GitHub App installation ID
        
        Returns:
            Access token if successful, None otherwise
        """
        # Check database for cached token
        if self.db_session:
            installation = self.db_session.query(Installation).filter(
                Installation.installation_id == installation_id
            ).first()
            
            if installation and installation.access_token:
                # Check if token is still valid (expires in 1 hour)
                if installation.token_expires_at and installation.token_expires_at > datetime.utcnow():
                    logger.debug(f"Using cached token for installation {installation_id}")
                    return installation.access_token
        
        # Generate JWT for GitHub App authentication
        jwt_token = self._generate_jwt()
        if not jwt_token:
            return None
        
        # Request installation token from GitHub
        try:
            response = self.client.post(
                f"{self.api_base_url}/app/installations/{installation_id}/access_tokens",
                headers={
                    "Authorization": f"Bearer {jwt_token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28"
                }
            )
            
            if response.status_code == 201:
                data = response.json()
                token = data["token"]
                expires_at_str = data.get("expires_at")
                
                # Parse expiration time
                expires_at = None
                if expires_at_str:
                    expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
                
                # Update database with new token
                if self.db_session and installation:
                    installation.access_token = token
                    installation.token_expires_at = expires_at
                    installation.updated_at = datetime.utcnow()
                    self.db_session.commit()
                    logger.info(f"Refreshed token for installation {installation_id}")
                
                return token
            else:
                logger.error(f"Failed to get installation token: {response.status_code} {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting installation token: {e}")
            return None
    
    def _generate_jwt(self) -> Optional[str]:
        """Generate JWT for GitHub App authentication.
        
        Returns:
            JWT token if successful, None otherwise
        """
        if not self.app_id or not self.private_key:
            logger.error("GITHUB_APP_ID or GITHUB_APP_PRIVATE_KEY not configured")
            return None
        
        try:
            import jwt
            from cryptography.hazmat.primitives import serialization
            
            # Load private key
            private_key_bytes = self.private_key.encode("utf-8")
            private_key_obj = serialization.load_pem_private_key(
                private_key_bytes,
                password=None
            )
            
            # Create JWT payload
            now = datetime.utcnow()
            payload = {
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(minutes=10)).timestamp()),
                "iss": self.app_id
            }
            
            # Generate JWT
            token = jwt.encode(payload, private_key_obj, algorithm="RS256")
            
            return token
            
        except ImportError as e:
            logger.error(f"Missing required library for JWT generation: {e}")
            return None
        except Exception as e:
            logger.error(f"Error generating JWT: {e}")
            return None
    
    def post_pr_comment(
        self,
        installation_id: int,
        repo_full_name: str,
        pr_number: int,
        comment_body: str
    ) -> Optional[int]:
        """Post a comment on a GitHub pull request.
        
        Args:
            installation_id: GitHub App installation ID
            repo_full_name: Repository (owner/repo format)
            pr_number: Pull request number
            comment_body: Markdown comment body
        
        Returns:
            Comment ID if successful, None otherwise
        """
        token = self.get_installation_token(installation_id)
        if not token:
            logger.error(f"Failed to get token for installation {installation_id}")
            return None
        
        try:
            response = self.client.post(
                f"{self.api_base_url}/repos/{repo_full_name}/issues/{pr_number}/comments",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28"
                },
                json={"body": comment_body}
            )
            
            if response.status_code == 201:
                data = response.json()
                comment_id = data["id"]
                logger.info(f"Posted comment {comment_id} on PR {repo_full_name}#{pr_number}")
                return comment_id
            else:
                logger.error(f"Failed to post comment: {response.status_code} {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error posting PR comment: {e}")
            return None
    
    def create_check_run(
        self,
        installation_id: int,
        repo_full_name: str,
        head_sha: str,
        name: str,
        status: str,
        conclusion: Optional[str] = None,
        output: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """Create a GitHub check run (status check).
        
        Args:
            installation_id: GitHub App installation ID
            repo_full_name: Repository (owner/repo format)
            head_sha: Commit SHA
            name: Check run name (e.g., "AGI Engineer Reliability")
            status: queued | in_progress | completed
            conclusion: success | failure | neutral | cancelled | skipped | timed_out
            output: Check run output (title, summary, text)
        
        Returns:
            Check run ID if successful, None otherwise
        """
        token = self.get_installation_token(installation_id)
        if not token:
            logger.error(f"Failed to get token for installation {installation_id}")
            return None
        
        payload: Dict[str, Any] = {
            "name": name,
            "head_sha": head_sha,
            "status": status
        }
        
        if conclusion:
            payload["conclusion"] = conclusion
        
        if output:
            payload["output"] = output
        
        try:
            response = self.client.post(
                f"{self.api_base_url}/repos/{repo_full_name}/check-runs",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28"
                },
                json=payload
            )
            
            if response.status_code == 201:
                data = response.json()
                check_run_id = data["id"]
                logger.info(f"Created check run {check_run_id} for {repo_full_name}@{head_sha[:7]}")
                return check_run_id
            else:
                logger.error(f"Failed to create check run: {response.status_code} {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating check run: {e}")
            return None
    
    def update_check_run(
        self,
        installation_id: int,
        repo_full_name: str,
        check_run_id: int,
        status: str,
        conclusion: Optional[str] = None,
        output: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update an existing GitHub check run.
        
        Args:
            installation_id: GitHub App installation ID
            repo_full_name: Repository (owner/repo format)
            check_run_id: Check run ID to update
            status: queued | in_progress | completed
            conclusion: success | failure | neutral | cancelled | skipped | timed_out
            output: Check run output (title, summary, text)
        
        Returns:
            True if successful, False otherwise
        """
        token = self.get_installation_token(installation_id)
        if not token:
            logger.error(f"Failed to get token for installation {installation_id}")
            return False
        
        payload: Dict[str, Any] = {
            "status": status
        }
        
        if conclusion:
            payload["conclusion"] = conclusion
        
        if output:
            payload["output"] = output
        
        try:
            response = self.client.patch(
                f"{self.api_base_url}/repos/{repo_full_name}/check-runs/{check_run_id}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28"
                },
                json=payload
            )
            
            if response.status_code == 200:
                logger.info(f"Updated check run {check_run_id}")
                return True
            else:
                logger.error(f"Failed to update check run: {response.status_code} {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating check run: {e}")
            return False
    
    def get_pr_files(
        self,
        installation_id: int,
        repo_full_name: str,
        pr_number: int
    ) -> Optional[List[Dict[str, Any]]]:
        """Get list of files changed in a PR.
        
        Args:
            installation_id: GitHub App installation ID
            repo_full_name: Repository (owner/repo format)
            pr_number: Pull request number
        
        Returns:
            List of file objects if successful, None otherwise
        """
        token = self.get_installation_token(installation_id)
        if not token:
            logger.error(f"Failed to get token for installation {installation_id}")
            return None
        
        try:
            response = self.client.get(
                f"{self.api_base_url}/repos/{repo_full_name}/pulls/{pr_number}/files",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28"
                }
            )
            
            if response.status_code == 200:
                files = response.json()
                logger.info(f"Retrieved {len(files)} files from PR {repo_full_name}#{pr_number}")
                return files
            else:
                logger.error(f"Failed to get PR files: {response.status_code} {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting PR files: {e}")
            return None
    
    def clone_repository(
        self,
        installation_id: int,
        repo_full_name: str,
        ref: str,
        dest_path: str
    ) -> bool:
        """Clone a GitHub repository at a specific ref.
        
        Args:
            installation_id: GitHub App installation ID
            repo_full_name: Repository (owner/repo format)
            ref: Git ref (branch, tag, or commit SHA)
            dest_path: Local destination path
        
        Returns:
            True if successful, False otherwise
        """
        token = self.get_installation_token(installation_id)
        if not token:
            logger.error(f"Failed to get token for installation {installation_id}")
            return False
        
        # Use git clone with authentication
        clone_url = f"https://x-access-token:{token}@github.com/{repo_full_name}.git"
        
        try:
            import subprocess
            
            # Clone repository
            result = subprocess.run(
                ["git", "clone", "--depth=1", "--branch", ref, clone_url, dest_path],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                logger.info(f"Cloned {repo_full_name}@{ref} to {dest_path}")
                return True
            else:
                logger.error(f"Failed to clone repository: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"Repository clone timed out: {repo_full_name}")
            return False
        except Exception as e:
            logger.error(f"Error cloning repository: {e}")
            return False
    
    def close(self):
        """Close HTTP client."""
        self.client.close()
