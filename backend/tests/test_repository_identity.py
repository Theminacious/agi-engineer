"""Regression tests: two different GitHub repositories must never collapse onto
the same ``Repository.github_repo_id``.

The failure these cover: the manual-import path inserted every repository with a
shared constant ``github_repo_id``, so the first import succeeded and every
later one died on ``UNIQUE constraint failed: repositories.github_repo_id``.
"""

import threading

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.installation import Installation
from app.models.repository import Repository
from app.services import repository_registry
from app.services.repository_registry import (
    PSEUDO_ID_FLOOR,
    get_or_create_repository,
    register_repository_from_url,
    resolve_github_repo_id,
    stable_pseudo_repo_id,
)

import app.models  # noqa: F401


MILLBROOK = {
    "id": 912_345_678,
    "node_id": "R_kgDONmMxLg",
    "name": "The-Millbrook-Chronicle",
    "full_name": "Theminacious/The-Millbrook-Chronicle",
    "private": False,
    "owner": {"login": "Theminacious", "id": 89_292_263, "type": "User"},
    "default_branch": "main",
}

CPYTHON = {
    "id": 81_598_961,
    "node_id": "MDEwOlJlcG9zaXRvcnk4MTU5ODk2MQ==",
    "name": "cpython",
    "full_name": "python/cpython",
    "private": False,
    "owner": {"login": "python", "id": 1_525_981, "type": "Organization"},
    "default_branch": "main",
}


@pytest.fixture
def fake_github(monkeypatch):
    """Serve the fixtures above in place of real GitHub API calls."""
    by_full_name = {r["full_name"]: r for r in (MILLBROOK, CPYTHON)}
    calls: list[str] = []

    def _fetch(repo_full_name, access_token=None, timeout=10.0):
        calls.append(repo_full_name)
        return by_full_name.get(repo_full_name)

    monkeypatch.setattr(repository_registry, "fetch_github_repo_metadata", _fetch)
    return calls


@pytest.fixture
def offline_github(monkeypatch):
    """Simulate GitHub being unreachable."""

    def _fetch(repo_full_name, access_token=None, timeout=10.0):
        return None

    monkeypatch.setattr(repository_registry, "fetch_github_repo_metadata", _fetch)


@pytest.fixture
def seeded_session(db_session):
    db_session.add(
        Installation(installation_id=89_292_263, github_user="Theminacious", is_active=True)
    )
    db_session.flush()
    return db_session


# ---------------------------------------------------------------------------
# The two fixtures carry genuinely different GitHub ids
# ---------------------------------------------------------------------------


def test_fixtures_are_not_both_id_one():
    """Guard the fixtures themselves — id=1 for both would hide the bug."""
    assert MILLBROOK["id"] != 1
    assert CPYTHON["id"] != 1
    assert MILLBROOK["id"] != CPYTHON["id"]


def test_repo_a_resolves_to_its_own_github_id(fake_github):
    repo_id, is_real = resolve_github_repo_id(MILLBROOK["full_name"])
    assert repo_id == MILLBROOK["id"]
    assert is_real is True


def test_repo_b_resolves_to_its_own_github_id(fake_github):
    repo_id, is_real = resolve_github_repo_id(CPYTHON["full_name"])
    assert repo_id == CPYTHON["id"]
    assert is_real is True


def test_the_two_repos_resolve_to_different_ids(fake_github):
    a, _ = resolve_github_repo_id(MILLBROOK["full_name"])
    b, _ = resolve_github_repo_id(CPYTHON["full_name"])
    assert a != b


# ---------------------------------------------------------------------------
# Creating each repository twice yields exactly one row
# ---------------------------------------------------------------------------


def test_creating_repo_a_twice_produces_one_row(seeded_session, fake_github):
    first, _ = register_repository_from_url(
        seeded_session, repo_full_name=MILLBROOK["full_name"]
    )
    seeded_session.commit()
    second, _ = register_repository_from_url(
        seeded_session, repo_full_name=MILLBROOK["full_name"]
    )
    seeded_session.commit()

    assert first.id == second.id
    rows = (
        seeded_session.query(Repository)
        .filter(Repository.repo_full_name == MILLBROOK["full_name"])
        .all()
    )
    assert len(rows) == 1
    assert rows[0].github_repo_id == MILLBROOK["id"]


def test_creating_repo_b_twice_produces_one_row(seeded_session, fake_github):
    first, _ = register_repository_from_url(
        seeded_session, repo_full_name=CPYTHON["full_name"]
    )
    seeded_session.commit()
    second, _ = register_repository_from_url(
        seeded_session, repo_full_name=CPYTHON["full_name"]
    )
    seeded_session.commit()

    assert first.id == second.id
    rows = (
        seeded_session.query(Repository)
        .filter(Repository.repo_full_name == CPYTHON["full_name"])
        .all()
    )
    assert len(rows) == 1
    assert rows[0].github_repo_id == CPYTHON["id"]


def test_both_repositories_coexist(seeded_session, fake_github):
    """The exact scenario that used to fail on the second insert."""
    repo_a, _ = register_repository_from_url(
        seeded_session, repo_full_name=MILLBROOK["full_name"]
    )
    seeded_session.commit()
    repo_b, _ = register_repository_from_url(
        seeded_session, repo_full_name=CPYTHON["full_name"]
    )
    seeded_session.commit()

    assert repo_a.id != repo_b.id
    assert repo_a.github_repo_id == MILLBROOK["id"]
    assert repo_b.github_repo_id == CPYTHON["id"]
    assert repo_a.github_repo_id != repo_b.github_repo_id

    stored = {r.repo_full_name: r.github_repo_id for r in seeded_session.query(Repository)}
    assert stored == {
        MILLBROOK["full_name"]: MILLBROOK["id"],
        CPYTHON["full_name"]: CPYTHON["id"],
    }


# ---------------------------------------------------------------------------
# Offline fallback stays unique and stable
# ---------------------------------------------------------------------------


def test_offline_fallback_ids_differ_per_repository(seeded_session, offline_github):
    repo_a, real_a = register_repository_from_url(
        seeded_session, repo_full_name=MILLBROOK["full_name"]
    )
    seeded_session.commit()
    repo_b, real_b = register_repository_from_url(
        seeded_session, repo_full_name=CPYTHON["full_name"]
    )
    seeded_session.commit()

    assert real_a is False and real_b is False
    assert repo_a.github_repo_id != repo_b.github_repo_id
    assert repo_a.github_repo_id != 0 and repo_b.github_repo_id != 0
    assert repo_a.github_repo_id != 1 and repo_b.github_repo_id != 1


def test_pseudo_id_is_stable_across_calls():
    """Not `hash()`-derived: the same name must map to the same id every time."""
    assert stable_pseudo_repo_id("python/cpython") == stable_pseudo_repo_id(
        "python/cpython"
    )
    assert stable_pseudo_repo_id("python/cpython") != stable_pseudo_repo_id(
        "Theminacious/The-Millbrook-Chronicle"
    )


def test_pseudo_id_cannot_be_mistaken_for_a_real_github_id():
    assert stable_pseudo_repo_id(CPYTHON["full_name"]) > PSEUDO_ID_FLOOR
    assert CPYTHON["id"] < PSEUDO_ID_FLOOR


def test_placeholder_id_is_upgraded_when_github_becomes_reachable(
    seeded_session, monkeypatch
):
    def _offline(repo_full_name, access_token=None, timeout=10.0):
        return None

    monkeypatch.setattr(repository_registry, "fetch_github_repo_metadata", _offline)
    repo, real = register_repository_from_url(
        seeded_session, repo_full_name=CPYTHON["full_name"]
    )
    seeded_session.commit()
    assert real is False
    placeholder_row_id = repo.id

    def _online(repo_full_name, access_token=None, timeout=10.0):
        return CPYTHON

    monkeypatch.setattr(repository_registry, "fetch_github_repo_metadata", _online)
    repo, real = register_repository_from_url(
        seeded_session, repo_full_name=CPYTHON["full_name"]
    )
    seeded_session.commit()

    assert real is True
    assert repo.id == placeholder_row_id
    assert repo.github_repo_id == CPYTHON["id"]
    assert seeded_session.query(Repository).count() == 1


# ---------------------------------------------------------------------------
# Concurrency: a lost race must not poison the session
# ---------------------------------------------------------------------------


def test_race_on_same_repo_reuses_winning_row_without_poisoning_session(
    seeded_session,
):
    """Simulate a competing writer committing between our lookup and insert."""
    engine = seeded_session.get_bind()
    other = sessionmaker(bind=engine)()
    try:
        other.add(
            Repository(
                installation_id=seeded_session.query(Installation).first().id,
                repo_name=CPYTHON["name"],
                repo_full_name=CPYTHON["full_name"],
                github_repo_id=CPYTHON["id"],
                is_enabled=True,
            )
        )
        other.commit()
        winner_id = (
            other.query(Repository)
            .filter(Repository.github_repo_id == CPYTHON["id"])
            .one()
            .id
        )
    finally:
        other.close()

    repo = get_or_create_repository(
        seeded_session,
        repo_full_name=CPYTHON["full_name"],
        github_repo_id=CPYTHON["id"],
        repo_name=CPYTHON["name"],
    )

    assert repo.github_repo_id == CPYTHON["id"]
    assert repo.id == winner_id
    assert seeded_session.query(Repository).count() == 1

    # Session must still be usable — no PendingRollbackError.
    seeded_session.query(Repository).count()
    other_repo = get_or_create_repository(
        seeded_session,
        repo_full_name=MILLBROOK["full_name"],
        github_repo_id=MILLBROOK["id"],
        repo_name=MILLBROOK["name"],
    )
    seeded_session.commit()
    assert other_repo.github_repo_id == MILLBROOK["id"]
    assert seeded_session.query(Repository).count() == 2


def test_no_pending_rollback_error_after_unique_collision(seeded_session):
    """A collision must leave the transaction usable, not poisoned."""
    installation_id = seeded_session.query(Installation).first().id
    seeded_session.add(
        Repository(
            installation_id=installation_id,
            repo_name=CPYTHON["name"],
            repo_full_name="python/cpython-mirror",
            github_repo_id=CPYTHON["id"],
            is_enabled=True,
        )
    )
    seeded_session.commit()

    repo = get_or_create_repository(
        seeded_session,
        repo_full_name=CPYTHON["full_name"],
        github_repo_id=CPYTHON["id"],
        repo_name=CPYTHON["name"],
    )
    assert repo.github_repo_id == CPYTHON["id"]

    seeded_session.commit()
    assert seeded_session.query(Repository).count() == 1


def test_parallel_creation_of_same_repository_creates_one_row(fake_github, tmp_path):
    """Threads racing on one repository must settle on a single row.

    Backed by a file database: an in-memory SQLite with StaticPool shares one
    connection across threads, so it cannot exercise a real race.
    """
    engine = create_engine(
        f"sqlite:///{tmp_path / 'race.db'}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    setup = Session()
    setup.add(Installation(installation_id=1, github_user="Theminacious", is_active=True))
    setup.commit()
    setup.close()

    barrier = threading.Barrier(4)
    errors: list[Exception] = []
    lock = threading.Lock()

    def worker(full_name):
        session = Session()
        try:
            barrier.wait(timeout=10)
            register_repository_from_url(session, repo_full_name=full_name)
            session.commit()
        except Exception as exc:  # noqa: BLE001
            with lock:
                errors.append(exc)
            session.rollback()
        finally:
            session.close()

    threads = [
        threading.Thread(target=worker, args=(name,))
        for name in (
            MILLBROOK["full_name"],
            MILLBROOK["full_name"],
            CPYTHON["full_name"],
            CPYTHON["full_name"],
        )
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert not errors, f"concurrent creation raised: {errors}"

    check = Session()
    try:
        stored = {r.repo_full_name: r.github_repo_id for r in check.query(Repository)}
        assert stored == {
            MILLBROOK["full_name"]: MILLBROOK["id"],
            CPYTHON["full_name"]: CPYTHON["id"],
        }
        assert check.query(Repository).count() == 2
    finally:
        check.close()
        engine.dispose()


# ---------------------------------------------------------------------------
# End-to-end through the API the dashboard actually calls
# ---------------------------------------------------------------------------


@pytest.fixture
def no_background_analysis(monkeypatch):
    """Keep /api/analysis/run from cloning anything during the test."""
    from app.routers import analysis as analysis_router

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(analysis_router, "_execute_analysis_background", _noop)


def test_starting_analysis_for_both_repositories_succeeds(
    client, seeded_session, fake_github, no_background_analysis
):
    """The reported reproduction: analyse repo A, then repo B."""
    for meta in (MILLBROOK, CPYTHON):
        response = client.post(
            "/api/analysis/run",
            json={
                "repository_url": f"https://github.com/{meta['full_name']}",
                "branch": "main",
                "event": "manual",
            },
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "pending"

    stored = {r.repo_full_name: r.github_repo_id for r in seeded_session.query(Repository)}
    assert stored == {
        MILLBROOK["full_name"]: MILLBROOK["id"],
        CPYTHON["full_name"]: CPYTHON["id"],
    }


def test_rerunning_analysis_for_both_repositories_adds_no_duplicates(
    client, seeded_session, fake_github, no_background_analysis
):
    """Second pass over both repositories: new runs, no new repository rows."""
    from app.models.analysis_run import AnalysisRun

    urls = [f"https://github.com/{m['full_name']}" for m in (MILLBROOK, CPYTHON)]

    for _ in range(2):
        for url in urls:
            response = client.post(
                "/api/analysis/run",
                json={"repository_url": url, "branch": "main", "event": "manual"},
            )
            assert response.status_code == 200, response.text

    assert seeded_session.query(Repository).count() == 2
    assert seeded_session.query(AnalysisRun).count() == 4

    ids = [r.github_repo_id for r in seeded_session.query(Repository)]
    assert len(set(ids)) == 2
    assert sorted(ids) == sorted([MILLBROOK["id"], CPYTHON["id"]])
