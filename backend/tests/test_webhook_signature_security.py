import hashlib
import hmac
import json

import pytest

from app.models import GitHubWebhookEvent, PRAnalysis

WEBHOOK_PATH = "/api/github/webhook"
SECRET = "test_webhook_secret_value"


def _sign(body: bytes, secret: str = SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _pr_payload() -> dict:
    return {
        "action": "opened",
        "pull_request": {
            "number": 7,
            "head": {"sha": "a" * 40, "ref": "feature"},
            "base": {"ref": "main"},
        },
        "repository": {
            "id": 999,
            "full_name": "owner/repo",
            "owner": {"login": "owner", "type": "User"},
        },
        "installation": {"id": 12345},
    }


@pytest.fixture
def enqueue_spy(monkeypatch):
    calls = []

    def _spy(pr_analysis_id):
        calls.append(pr_analysis_id)

    monkeypatch.setattr(
        "app.routers.github_webhooks._run_pr_analysis", _spy
    )
    return calls


@pytest.fixture
def with_secret(monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", SECRET)


def test_valid_signature_enqueues_and_records(
    client, db_session, enqueue_spy, with_secret
):
    body = json.dumps(_pr_payload()).encode()
    resp = client.post(
        WEBHOOK_PATH,
        content=body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": "delivery-valid-1",
            "X-Hub-Signature-256": _sign(body),
            "Content-Type": "application/json",
        },
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "queued"
    assert len(enqueue_spy) == 1

    events = db_session.query(GitHubWebhookEvent).all()
    analyses = db_session.query(PRAnalysis).all()
    assert len(events) == 1
    assert events[0].signature_verified is True
    assert len(analyses) == 1
    assert enqueue_spy[0] == analyses[0].id


def test_invalid_signature_rejected_no_work(
    client, db_session, enqueue_spy, with_secret
):
    body = json.dumps(_pr_payload()).encode()
    resp = client.post(
        WEBHOOK_PATH,
        content=body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": "delivery-invalid-1",
            "X-Hub-Signature-256": "sha256=" + "0" * 64,
            "Content-Type": "application/json",
        },
    )

    assert resp.status_code == 401
    assert enqueue_spy == []
    assert db_session.query(GitHubWebhookEvent).count() == 0
    assert db_session.query(PRAnalysis).count() == 0


def test_missing_signature_rejected_no_work(
    client, db_session, enqueue_spy, with_secret
):
    body = json.dumps(_pr_payload()).encode()
    resp = client.post(
        WEBHOOK_PATH,
        content=body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": "delivery-missing-1",
            "Content-Type": "application/json",
        },
    )

    assert resp.status_code == 401
    assert enqueue_spy == []
    assert db_session.query(GitHubWebhookEvent).count() == 0
    assert db_session.query(PRAnalysis).count() == 0


def test_malformed_signature_rejected_no_work(
    client, db_session, enqueue_spy, with_secret
):
    body = json.dumps(_pr_payload()).encode()
    resp = client.post(
        WEBHOOK_PATH,
        content=body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": "delivery-malformed-1",
            "X-Hub-Signature-256": "not-a-sha256-prefixed-value",
            "Content-Type": "application/json",
        },
    )

    assert resp.status_code == 401
    assert enqueue_spy == []
    assert db_session.query(GitHubWebhookEvent).count() == 0
    assert db_session.query(PRAnalysis).count() == 0


def test_unconfigured_secret_fails_closed(
    client, db_session, enqueue_spy, monkeypatch
):
    monkeypatch.delenv("GITHUB_WEBHOOK_SECRET", raising=False)
    body = json.dumps(_pr_payload()).encode()
    resp = client.post(
        WEBHOOK_PATH,
        content=body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": "delivery-nosecret-1",
            "X-Hub-Signature-256": _sign(body),
            "Content-Type": "application/json",
        },
    )

    assert resp.status_code == 401
    assert enqueue_spy == []
    assert db_session.query(PRAnalysis).count() == 0


def test_replayed_delivery_is_idempotent(
    client, db_session, enqueue_spy, with_secret
):
    body = json.dumps(_pr_payload()).encode()
    headers = {
        "X-GitHub-Event": "pull_request",
        "X-GitHub-Delivery": "delivery-replay-1",
        "X-Hub-Signature-256": _sign(body),
        "Content-Type": "application/json",
    }

    first = client.post(WEBHOOK_PATH, content=body, headers=headers)
    second = client.post(WEBHOOK_PATH, content=body, headers=headers)

    assert first.status_code == 200
    assert first.json()["status"] == "queued"
    assert second.status_code == 200
    assert second.json()["status"] == "already_processed"
    assert len(enqueue_spy) == 1
    assert db_session.query(GitHubWebhookEvent).count() == 1
    assert db_session.query(PRAnalysis).count() == 1


def test_stack_a_rejects_missing_signature(client):
    resp = client.post(
        "/webhooks/github",
        json={"action": "opened", "repository": {"id": 1}},
        headers={"X-GitHub-Event": "pull_request"},
    )
    assert resp.status_code == 401


def test_stack_a_rejects_invalid_signature(client):
    resp = client.post(
        "/webhooks/github",
        json={"action": "opened", "repository": {"id": 1}},
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": "sha256=" + "0" * 64,
        },
    )
    assert resp.status_code == 401
