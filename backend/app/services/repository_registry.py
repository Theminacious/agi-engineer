"""Single place that turns GitHub repository metadata into a Repository row.

`Repository.github_repo_id` is the repository's identity on GitHub — the numeric
`id` from `GET /repos/{owner}/{repo}`. It is UNIQUE, so every caller that creates
a Repository must supply the repository's own id; a shared constant collapses
every repository onto one row and the second insert fails.

Three distinct identifiers must not be confused:

- ``Repository.github_repo_id``  — GitHub's id for the repository (this module).
- ``Installation.installation_id`` — GitHub's id for an App installation.
- ``Repository.id`` / ``Installation.id`` — local autoincrement primary keys.
"""

from __future__ import annotations

import hashlib
import logging
import os
from typing import Optional, Tuple

import httpx
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.models.installation import Installation
from app.models.repository import Repository

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"

PSEUDO_ID_FLOOR = 1 << 40


def stable_pseudo_repo_id(repo_full_name: str) -> int:
    """Deterministic stand-in id for when GitHub cannot be reached.

    SHA-256 rather than :func:`hash`, whose string hashing is salted per process.
    Offset above :data:`PSEUDO_ID_FLOOR` so it cannot be mistaken for a real id.
    """
    digest = hashlib.sha256(repo_full_name.encode("utf-8")).digest()
    return PSEUDO_ID_FLOOR + (int.from_bytes(digest[:6], "big") % PSEUDO_ID_FLOOR)


def fetch_github_repo_metadata(
    repo_full_name: str,
    access_token: Optional[str] = None,
    timeout: float = 10.0,
) -> Optional[dict]:
    """Return the GitHub repository object for ``owner/repo``, or None."""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = access_token or os.getenv("GITHUB_TOKEN") or settings.github_token
    if token and token != "ghp_your_github_personal_access_token_here":
        headers["Authorization"] = f"Bearer {token}"

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(
                f"{GITHUB_API_BASE}/repos/{repo_full_name}", headers=headers
            )
    except Exception as exc:
        logger.warning("GitHub lookup for %s failed: %s", repo_full_name, exc)
        return None

    if response.status_code != 200:
        logger.warning(
            "GitHub lookup for %s returned %s", repo_full_name, response.status_code
        )
        return None

    try:
        return response.json()
    except Exception as exc:
        logger.warning("GitHub returned unparseable body for %s: %s", repo_full_name, exc)
        return None


def resolve_github_repo_id(
    repo_full_name: str,
    access_token: Optional[str] = None,
) -> Tuple[int, bool]:
    """Resolve ``owner/repo`` to (github_repo_id, is_real_github_id)."""
    metadata = fetch_github_repo_metadata(repo_full_name, access_token)

    if metadata:
        raw_id = metadata.get("id")
        if isinstance(raw_id, int) and raw_id > 0:
            return raw_id, True
        logger.warning(
            "GitHub metadata for %s carried no usable id (got %r)",
            repo_full_name,
            raw_id,
        )

    return stable_pseudo_repo_id(repo_full_name), False


def resolve_installation(db: Session, preferred_id: Optional[int] = None) -> Installation:
    """Return an Installation to own a manually imported repository."""
    if preferred_id is not None:
        installation = (
            db.query(Installation).filter(Installation.id == preferred_id).first()
        )
        if installation:
            return installation

    installation = db.query(Installation).order_by(Installation.id).first()
    if installation:
        return installation

    installation = Installation(
        installation_id=0,
        github_user="local",
        is_active=True,
    )
    db.add(installation)
    db.flush()
    logger.info("Created local placeholder installation %s", installation.id)
    return installation


def get_or_create_repository(
    db: Session,
    *,
    repo_full_name: str,
    github_repo_id: int,
    repo_name: Optional[str] = None,
    installation_id: Optional[int] = None,
) -> Repository:
    """Return the Repository for ``github_repo_id``, creating it if absent.

    Safe under concurrency: the insert runs inside a SAVEPOINT, so losing the race
    rolls back only that savepoint and the session stays usable.
    """
    existing = (
        db.query(Repository).filter(Repository.github_repo_id == github_repo_id).first()
    )
    if existing:
        return existing

    existing = (
        db.query(Repository).filter(Repository.repo_full_name == repo_full_name).first()
    )
    if existing:
        # Same repository recorded under a placeholder id before GitHub was
        # reachable — adopt the real id instead of inserting a second row.
        if existing.github_repo_id != github_repo_id:
            logger.info(
                "Updating github_repo_id for %s: %s -> %s",
                repo_full_name,
                existing.github_repo_id,
                github_repo_id,
            )
            existing.github_repo_id = github_repo_id
            db.flush()
        return existing

    installation = resolve_installation(db, installation_id)

    repository = Repository(
        installation_id=installation.id,
        repo_name=repo_name or repo_full_name.split("/")[-1],
        repo_full_name=repo_full_name,
        github_repo_id=github_repo_id,
        is_enabled=True,
    )

    try:
        with db.begin_nested():
            db.add(repository)
            db.flush()
        return repository
    except IntegrityError:
        # The savepoint rollback normally evicts the pending instance already;
        # expunge only if it survived, or this raises over the real error.
        if repository in db:
            db.expunge(repository)
        logger.info(
            "Concurrent creation of %s (github_repo_id=%s); reusing existing row",
            repo_full_name,
            github_repo_id,
        )

    winner = (
        db.query(Repository)
        .filter(Repository.github_repo_id == github_repo_id)
        .first()
    ) or (
        db.query(Repository)
        .filter(Repository.repo_full_name == repo_full_name)
        .first()
    )

    if winner is None:
        raise RuntimeError(
            f"Repository insert for {repo_full_name} "
            f"(github_repo_id={github_repo_id}) conflicted but no row was found"
        )

    return winner


def register_repository_from_url(
    db: Session,
    *,
    repo_full_name: str,
    repo_name: Optional[str] = None,
    installation_id: Optional[int] = None,
    access_token: Optional[str] = None,
) -> Tuple[Repository, bool]:
    """Resolve ``owner/repo`` against GitHub and return (Repository, is_real_id)."""
    github_repo_id, is_real_id = resolve_github_repo_id(repo_full_name, access_token)

    repository = get_or_create_repository(
        db,
        repo_full_name=repo_full_name,
        github_repo_id=github_repo_id,
        repo_name=repo_name,
        installation_id=installation_id,
    )

    return repository, is_real_id
