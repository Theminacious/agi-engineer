"""Tenant authorization: scope every protected resource to the caller's installation.

Authentication (``app.security``) answers "who are you?"; this module answers
"are you allowed to access THIS resource?". A principal is bound to exactly one
installation (the ``installation_id`` claim == ``Installation.id``). Every
resource resolves to an owning installation through an explicit model join:

    PRAnalysis      -> webhook_event.installation_id
    Repository      -> installation_id
    AnalysisRun     -> repository.installation_id
    AnalysisResult  -> run.repository.installation_id
    CodeFix         -> result.run.repository.installation_id
    Installation    -> self.id

Cross-tenant access returns 404 (not 403) so existence is not leaked.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    AnalysisResult,
    AnalysisRun,
    CodeFix,
    GitHubWebhookEvent,
    Installation,
    PRAnalysis,
    Repository,
)
from app.security import JWTManager

_NOT_FOUND = 404


@dataclass(frozen=True)
class Principal:
    installation_id: int
    user: Optional[str]


def get_principal(authorization: str = Header(None)) -> Principal:
    """Resolve the authenticated principal, or raise 401.

    Requires a verifiable bearer token that carries an ``installation_id``
    claim. A token without a tenant binding cannot authorize any resource.
    """
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        claims = JWTManager.verify_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    installation_id = claims.get("installation_id")
    if not isinstance(installation_id, int):
        raise HTTPException(status_code=401, detail="Token missing installation binding")
    return Principal(installation_id=installation_id, user=claims.get("user"))


def _deny() -> HTTPException:
    return HTTPException(status_code=_NOT_FOUND, detail="Not found")


def pr_analysis_query(db: Session, principal: Principal):
    """Base PRAnalysis query scoped to the principal's installation."""
    return (
        db.query(PRAnalysis)
        .join(GitHubWebhookEvent, PRAnalysis.webhook_event_id == GitHubWebhookEvent.id)
        .filter(GitHubWebhookEvent.installation_id == principal.installation_id)
    )


def authorize_pr_analysis(db: Session, pr_analysis_id: int, principal: Principal) -> PRAnalysis:
    pr = pr_analysis_query(db, principal).filter(PRAnalysis.id == pr_analysis_id).first()
    if pr is None:
        raise _deny()
    return pr


def authorize_repository(db: Session, repository_id: int, principal: Principal) -> Repository:
    repo = (
        db.query(Repository)
        .filter(
            Repository.id == repository_id,
            Repository.installation_id == principal.installation_id,
        )
        .first()
    )
    if repo is None:
        raise _deny()
    return repo


def authorize_run(db: Session, run_id: int, principal: Principal) -> AnalysisRun:
    run = (
        db.query(AnalysisRun)
        .join(Repository, AnalysisRun.repository_id == Repository.id)
        .filter(
            AnalysisRun.id == run_id,
            Repository.installation_id == principal.installation_id,
        )
        .first()
    )
    if run is None:
        raise _deny()
    return run


def authorize_result(db: Session, result_id: int, principal: Principal) -> AnalysisResult:
    result = (
        db.query(AnalysisResult)
        .join(AnalysisRun, AnalysisResult.run_id == AnalysisRun.id)
        .join(Repository, AnalysisRun.repository_id == Repository.id)
        .filter(
            AnalysisResult.id == result_id,
            Repository.installation_id == principal.installation_id,
        )
        .first()
    )
    if result is None:
        raise _deny()
    return result


def authorize_fix(db: Session, fix_id: int, principal: Principal) -> CodeFix:
    fix = (
        db.query(CodeFix)
        .join(AnalysisResult, CodeFix.result_id == AnalysisResult.id)
        .join(AnalysisRun, AnalysisResult.run_id == AnalysisRun.id)
        .join(Repository, AnalysisRun.repository_id == Repository.id)
        .filter(
            CodeFix.id == fix_id,
            Repository.installation_id == principal.installation_id,
        )
        .first()
    )
    if fix is None:
        raise _deny()
    return fix


def authorize_fix_by_result(db: Session, result_id: int, principal: Principal) -> CodeFix:
    authorize_result(db, result_id, principal)
    fix = db.query(CodeFix).filter(CodeFix.result_id == result_id).first()
    if fix is None:
        raise HTTPException(status_code=_NOT_FOUND, detail="Fix not found")
    return fix
