"""Tenant authorization regression tests: cross-tenant access is refused."""

import pytest
from fastapi.testclient import TestClient

from app.db import get_db
from app.main import app as fastapi_app
from app.security import JWTManager
from app.models import GitHubWebhookEvent, Installation, PRAnalysis
from app.models.github_integration import PRAnalysisStatus, WebhookEventType


@pytest.fixture
def client(db_session):
    def _override():
        yield db_session
    fastapi_app.dependency_overrides[get_db] = _override
    with TestClient(fastapi_app) as tc:
        yield tc
    fastapi_app.dependency_overrides.clear()


def _installation(db_session, gh_id, user):
    inst = Installation(installation_id=gh_id, github_user=user)
    db_session.add(inst)
    db_session.commit()
    return inst


def _pr(db_session, inst, *, delivery, pr_number, repo="owner/repo"):
    webhook = GitHubWebhookEvent(
        delivery_id=delivery,
        event_type=WebhookEventType.PULL_REQUEST_OPENED,
        signature_verified=True,
        installation_id=inst.id,
        repository_full_name=repo,
        repository_id=1000 + pr_number,
        pr_number=pr_number,
        pr_head_sha="a" * 40,
        pr_base_branch="main",
        pr_head_branch="feature",
        raw_payload={"pull_request": {"base": {"ref": "main"}}},
    )
    db_session.add(webhook)
    db_session.commit()
    analysis = PRAnalysis(
        repository_full_name=repo,
        pr_number=pr_number,
        head_sha="a" * 40,
        base_branch="main",
        status=PRAnalysisStatus.COMPLETED,
        webhook_event_id=webhook.id,
    )
    db_session.add(analysis)
    db_session.commit()
    return analysis


def _headers(inst):
    token = JWTManager.create_token({"user": inst.github_user, "installation_id": inst.id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def two_tenants(db_session):
    a = _installation(db_session, 1001, "tenant-a")
    b = _installation(db_session, 2002, "tenant-b")
    pr_a = _pr(db_session, a, delivery="da", pr_number=11)
    pr_b = _pr(db_session, b, delivery="db", pr_number=22)
    return a, b, pr_a, pr_b


# 1. Unauthenticated -----------------------------------------------------------

def test_unauthenticated_pr_detail_is_401(client, two_tenants):
    _a, _b, pr_a, _pr_b = two_tenants
    assert client.get(f"/api/github/pr-analyses/{pr_a.id}").status_code == 401


def test_unauthenticated_pr_list_is_401(client, two_tenants):
    assert client.get("/api/github/pr-analyses").status_code == 401


def test_unauthenticated_installations_is_401(client, two_tenants):
    assert client.get("/installations/").status_code == 401


# 2/4. Cross-tenant read is refused as 404 (no existence leak) -----------------

def test_cross_tenant_pr_detail_is_404(client, two_tenants):
    a, _b, _pr_a, pr_b = two_tenants
    resp = client.get(f"/api/github/pr-analyses/{pr_b.id}", headers=_headers(a))
    assert resp.status_code == 404


def test_cross_tenant_pr_proof_not_leaked(client, two_tenants):
    a, _b, _pr_a, pr_b = two_tenants
    # tenant A listing never includes tenant B's analysis
    body = client.get("/api/github/pr-analyses", headers=_headers(a)).json()
    assert all(row["id"] != pr_b.id for row in body["analyses"])
    assert body["count"] == 1


# 3. Legitimate same-tenant access still works --------------------------------

def test_same_tenant_pr_detail_ok(client, two_tenants):
    a, _b, pr_a, _pr_b = two_tenants
    resp = client.get(f"/api/github/pr-analyses/{pr_a.id}", headers=_headers(a))
    assert resp.status_code == 200
    assert resp.json()["id"] == pr_a.id


def test_same_tenant_list_scoped(client, two_tenants):
    b, = (two_tenants[1],)
    body = client.get("/api/github/pr-analyses", headers=_headers(b)).json()
    assert body["count"] == 1
    assert body["analyses"][0]["id"] == two_tenants[3].id


# 5. Missing installation claim / malformed identity --------------------------

def test_token_without_installation_is_401(client, two_tenants):
    token = JWTManager.create_token({"user": "ghost"})  # no installation_id
    resp = client.get("/api/github/pr-analyses", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_forged_token_is_401(client, two_tenants):
    bad = {"Authorization": "Bearer not.a.valid.jwt"}
    assert client.get("/api/github/pr-analyses", headers=bad).status_code == 401


def test_installations_list_scoped_to_self(client, two_tenants):
    a, _b, _pr_a, _pr_b = two_tenants
    rows = client.get("/installations/", headers=_headers(a)).json()
    assert [r["id"] for r in rows] == [a.id]


def test_cross_tenant_installation_detail_is_404(client, two_tenants):
    a, b, _pr_a, _pr_b = two_tenants
    assert client.get(f"/installations/{b.id}", headers=_headers(a)).status_code == 404
    assert client.get(f"/installations/{a.id}", headers=_headers(a)).status_code == 200


# 6. Mutation authorization ----------------------------------------------------

def test_cross_tenant_uninstall_is_404_and_no_mutation(client, two_tenants, db_session):
    a, b, _pr_a, _pr_b = two_tenants
    assert b.is_active is True
    resp = client.delete(f"/installations/{b.id}", headers=_headers(a))
    assert resp.status_code == 404
    db_session.refresh(b)
    assert b.is_active is True  # tenant B unchanged


def test_cross_tenant_fix_apply_is_404(client, two_tenants):
    a, _b, _pr_a, _pr_b = two_tenants
    # A fix id that does not belong to tenant A must not be mutable.
    resp = client.post("/api/fixes/999999/apply", headers=_headers(a))
    assert resp.status_code in (404, 401)
    assert resp.status_code == 404
