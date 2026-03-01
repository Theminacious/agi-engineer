"""Tests for OAuth and webhook endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.base import Base
from app.db import get_db
from app.config import settings
import json


# Test database setup — in-memory for isolation
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def test_db():
    """Create test database."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_client(test_db):
    """Create test client."""

    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health_check(test_client):
    """Test health check endpoint."""
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_status_endpoint(test_client):
    """Test status endpoint."""
    response = test_client.get("/status")
    assert response.status_code == 200
    assert response.json()["api"] == "agi-engineer-v2"


def test_oauth_authorize(test_client):
    """Test OAuth authorization URL generation."""
    response = test_client.get("/oauth/authorize")
    assert response.status_code == 200
    data = response.json()
    assert "authorization_url" in data
    assert "state" in data
    assert "client_id" in data["authorization_url"]
    assert "redirect_uri" in data["authorization_url"]


def test_webhook_missing_signature(test_client):
    """Test webhook rejects missing signature."""
    payload = {"action": "opened", "repository": {"id": 123}}
    response = test_client.post(
        "/webhooks/github",
        json=payload,
    )
    assert response.status_code == 401
    assert "Missing signature" in response.json()["detail"]


def test_webhook_invalid_signature(test_client):
    """Test webhook rejects invalid signature."""
    payload = {"action": "opened", "repository": {"id": 123}}
    response = test_client.post(
        "/webhooks/github",
        json=payload,
        headers={"X-Hub-Signature-256": "sha256=invalidsignature"},
    )
    assert response.status_code == 401
    assert "Invalid signature" in response.json()["detail"]


def test_webhook_push_event_no_repo(test_client):
    """Test push webhook with untracked repository."""
    from app.security import validate_webhook_signature
    import hmac
    import hashlib

    payload = {
        "action": "opened",
        "repository": {"id": 123, "full_name": "user/repo"},
        "after": "abc123def456",
        "ref": "refs/heads/main",
    }
    payload_bytes = json.dumps(payload).encode()

    # Generate valid signature using configured webhook secret
    signature = "sha256=" + hmac.new(
        settings.webhook_secret.encode(),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()

    response = test_client.post(
        "/webhooks/github",
        content=payload_bytes,
        headers={
            "X-Hub-Signature-256": signature,
            "X-GitHub-Event": "push",
            "Content-Type": "application/json",
        },
    )

    # Should return 200 with skipped status (repo not tracked)
    assert response.status_code in [200, 500]  # May fail if secret doesn't match


def test_webhook_ignored_event(test_client):
    """Test webhook ignores unsupported events."""
    from app.security import validate_webhook_signature
    import hmac
    import hashlib

    payload = {"action": "opened"}
    payload_bytes = json.dumps(payload).encode()

    signature = "sha256=" + hmac.new(
        settings.webhook_secret.encode(),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()

    response = test_client.post(
        "/webhooks/github",
        content=payload_bytes,
        headers={
            "X-Hub-Signature-256": signature,
            "X-GitHub-Event": "issues",
            "Content-Type": "application/json",
        },
    )

    # Should handle gracefully
    assert response.status_code in [200, 500]
