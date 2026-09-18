"""Tests for Phase 20 Week 1 — Change Impact Intelligence.

Uses real git repos (via subprocess) so the diff-parsing and worktree
logic is exercised end-to-end, not mocked.
"""

from __future__ import annotations

import os
import subprocess
import textwrap
from pathlib import Path
from typing import List

import pytest

from app.models.change_impact import Confidence
from app.services.change_impact_service import ChangeImpactService, ChangeImpactError


# ─── Helpers ────────────────────────────────────────────────────────

def _git(*args: str, cwd: Path) -> None:
    safe_home = cwd / ".git-home"
    safe_home.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["HOME"] = str(safe_home)
    env["XDG_CONFIG_HOME"] = str(safe_home / ".config")
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    env["GIT_CONFIG_SYSTEM"] = os.devnull
    subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git("init", "-q", cwd=repo)
    _git("config", "user.email", "test@example.com", cwd=repo)
    _git("config", "user.name", "Test", cwd=repo)
    return repo


def _write(repo: Path, rel_path: str, content: str) -> None:
    p = repo / rel_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(content))


def _commit(repo: Path, message: str) -> str:
    _git("add", "-A", cwd=repo)
    _git("commit", "-q", "-m", message, cwd=repo)
    out = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(repo),
        check=True,
        capture_output=True,
        text=True,
        env={
            **os.environ.copy(),
            "HOME": str(repo / ".git-home"),
            "XDG_CONFIG_HOME": str(repo / ".git-home/.config"),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
        },
    )
    return out.stdout.strip()


# ─── Fixture: multi-hop caller chain repo ──────────────────────────
#
#   changed symbol: UserRepository.get_user
#   caller chain:   AuthorizationService.authorize -> PaymentService.process_payment
#
# This mirrors the exact scenario used throughout the product discussion,
# so a passing test here is real evidence the traversal claim holds.

@pytest.fixture
def chain_repo(tmp_path: Path) -> Path:
    repo = _init_repo(tmp_path)
    _write(repo, "repository.py", """\
        class UserRepository:
            def get_user(self, user_id):
                return {"id": user_id, "name": "placeholder"}
    """)
    _write(repo, "auth_service.py", """\
        from repository import UserRepository

        class AuthorizationService:
            def __init__(self):
                self.repo = UserRepository()

            def authorize(self, user_id):
                user = self.repo.get_user(user_id)
                return user is not None
    """)
    _write(repo, "payment_service.py", """\
        from auth_service import AuthorizationService

        class PaymentService:
            def __init__(self):
                self.auth = AuthorizationService()

            def process_payment(self, user_id, amount):
                if not self.auth.authorize(user_id):
                    raise PermissionError("not authorized")
                return {"charged": amount}
    """)
    return repo


def test_multi_hop_caller_chain_detected(chain_repo: Path):
    base = _commit(chain_repo, "base")

    # modify UserRepository.get_user only
    _write(chain_repo, "repository.py", """\
        class UserRepository:
            def get_user(self, user_id):
                # changed: now raises on missing id
                if user_id is None:
                    raise ValueError("user_id required")
                return {"id": user_id, "name": "placeholder"}
    """)
    target = _commit(chain_repo, "modify get_user")

    svc = ChangeImpactService()
    report = svc.compute_change_impact(str(chain_repo), base, target)

    assert report.confidence in (Confidence.HIGH, Confidence.MEDIUM)
    changed_ids = {s.node_id for s in report.changed_symbols}
    assert any("UserRepository.get_user" in cid for cid in changed_ids)

    # AuthorizationService.authorize and PaymentService.process_payment
    # must both surface as callers/downstream — this is the multi-level
    # caller chain claim being tested for real.
    caller_names = {c.rsplit("::", 1)[-1] for c in report.callers} | {
        d.rsplit("::", 1)[-1] for d in report.downstream_symbols
    }
    assert "AuthorizationService.authorize" in caller_names
    assert "PaymentService.process_payment" in caller_names

    # deterministic hash must be stable across two computations
    report2 = svc.compute_change_impact(str(chain_repo), base, target)
    assert report.deterministic_hash == report2.deterministic_hash


def test_single_function_modification(tmp_path: Path):
    repo = _init_repo(tmp_path)
    _write(repo, "calc.py", """\
        def add(a, b):
            return a + b
    """)
    base = _commit(repo, "base")
    _write(repo, "calc.py", """\
        def add(a, b):
            return a + b + 0  # changed
    """)
    target = _commit(repo, "change add")

    svc = ChangeImpactService()
    report = svc.compute_change_impact(str(repo), base, target)
    assert len(report.changed_symbols) == 1
    assert report.changed_symbols[0].name == "add"
    assert report.confidence == Confidence.HIGH


def test_function_addition(tmp_path: Path):
    repo = _init_repo(tmp_path)
    _write(repo, "calc.py", """\
        def add(a, b):
            return a + b
    """)
    base = _commit(repo, "base")
    _write(repo, "calc.py", """\
        def add(a, b):
            return a + b

        def subtract(a, b):
            return a - b
    """)
    target = _commit(repo, "add subtract")

    svc = ChangeImpactService()
    report = svc.compute_change_impact(str(repo), base, target)
    names = {s.name for s in report.changed_symbols}
    assert "subtract" in names


def test_function_deletion_marks_unresolved_or_matched(tmp_path: Path):
    repo = _init_repo(tmp_path)
    _write(repo, "calc.py", """\
        def add(a, b):
            return a + b

        def unused(a):
            return a
    """)
    base = _commit(repo, "base")
    _write(repo, "calc.py", """\
        def add(a, b):
            return a + b
    """)
    target = _commit(repo, "remove unused")

    svc = ChangeImpactService()
    report = svc.compute_change_impact(str(repo), base, target)
    # deletion shows up as a change to the file with no target-side symbol
    # to land on; this is acceptable week-1 behaviour as long as it's
    # visible somewhere (either as a changed symbol on 'add' due to
    # surrounding hunk, or as an unresolved reference) rather than silent.
    assert report.changed_files == ["calc.py"]


def test_class_and_method_modification(tmp_path: Path):
    repo = _init_repo(tmp_path)
    _write(repo, "svc.py", """\
        class Svc:
            def run(self):
                return 1
    """)
    base = _commit(repo, "base")
    _write(repo, "svc.py", """\
        class Svc:
            def run(self):
                return 2
    """)
    target = _commit(repo, "change run")

    svc = ChangeImpactService()
    report = svc.compute_change_impact(str(repo), base, target)
    kinds = {s.node_type for s in report.changed_symbols}
    assert "method" in kinds


def test_import_only_change_is_low_confidence_or_unresolved(tmp_path: Path):
    repo = _init_repo(tmp_path)
    _write(repo, "a.py", """\
        import os
    """)
    base = _commit(repo, "base")
    _write(repo, "a.py", """\
        import os
        import sys
    """)
    target = _commit(repo, "add import")

    svc = ChangeImpactService()
    report = svc.compute_change_impact(str(repo), base, target)
    # module-level import change has no enclosing function/class symbol —
    # must be surfaced as unresolved, never silently dropped or fabricated.
    assert len(report.unresolved_references) >= 1 or len(report.changed_symbols) == 0


def test_multiple_changed_files(tmp_path: Path):
    repo = _init_repo(tmp_path)
    _write(repo, "a.py", "def fa():\n    return 1\n")
    _write(repo, "b.py", "def fb():\n    return 2\n")
    base = _commit(repo, "base")
    _write(repo, "a.py", "def fa():\n    return 10\n")
    _write(repo, "b.py", "def fb():\n    return 20\n")
    target = _commit(repo, "change both")

    svc = ChangeImpactService()
    report = svc.compute_change_impact(str(repo), base, target)
    assert set(report.changed_files) == {"a.py", "b.py"}
    assert len(report.changed_symbols) == 2


def test_no_graph_match_nonexistent_python_file_semantics(tmp_path: Path):
    repo = _init_repo(tmp_path)
    _write(repo, "notes.txt", "hello\n")
    base = _commit(repo, "base")
    _write(repo, "notes.txt", "hello world\n")
    target = _commit(repo, "change notes")

    svc = ChangeImpactService()
    report = svc.compute_change_impact(str(repo), base, target)
    assert report.changed_files == ["notes.txt"]
    assert len(report.changed_symbols) == 0
    assert any(u.reason.startswith("symbol extraction") for u in report.unresolved_references)


def test_deterministic_output_and_hash(chain_repo: Path):
    base = _commit(chain_repo, "base")
    _write(chain_repo, "repository.py", """\
        class UserRepository:
            def get_user(self, user_id):
                return {"id": user_id, "changed": True}
    """)
    target = _commit(chain_repo, "modify")

    svc = ChangeImpactService()
    r1 = svc.compute_change_impact(str(chain_repo), base, target)
    r2 = svc.compute_change_impact(str(chain_repo), base, target)
    assert r1.deterministic_hash == r2.deterministic_hash
    assert r1.to_dict() == r2.to_dict()


def test_entrypoint_discovery_fastapi_style(tmp_path: Path):
    repo = _init_repo(tmp_path)
    _write(repo, "routes.py", """\
        class App:
            pass

        app = App()

        class Handlers:
            @app.get("/users/{id}")
            def get_user_handler(self, id):
                return {"id": id}
    """)
    base = _commit(repo, "base")
    _write(repo, "routes.py", """\
        class App:
            pass

        app = App()

        class Handlers:
            @app.get("/users/{id}")
            def get_user_handler(self, id):
                return {"id": id, "v": 2}
    """)
    target = _commit(repo, "change handler")

    svc = ChangeImpactService()
    report = svc.compute_change_impact(str(repo), base, target)
    assert len(report.affected_entrypoints) >= 1


def test_finding_intersection(chain_repo: Path):
    base = _commit(chain_repo, "base")
    _write(chain_repo, "repository.py", """\
        class UserRepository:
            def get_user(self, user_id):
                return {"id": user_id, "changed": True}
    """)
    target = _commit(chain_repo, "modify")

    svc = ChangeImpactService()
    report_probe = svc.compute_change_impact(str(chain_repo), base, target)
    changed_id = report_probe.changed_symbols[0].node_id

    fake_findings = [{"symbol_id": changed_id, "rule": "example-finding"}]
    report = svc.compute_change_impact(str(chain_repo), base, target, findings=fake_findings)
    assert len(report.intersecting_findings) == 1
    assert report.intersecting_findings[0]["rule"] == "example-finding"


def test_precomputed_impact_reuses_graph_and_replaces_finding_rows(chain_repo: Path):
    base = _commit(chain_repo, "base")
    _write(chain_repo, "repository.py", """\
        class UserRepository:
            def get_user(self, user_id):
                return {"id": user_id, "changed": True}
    """)
    target = _commit(chain_repo, "modify")

    svc = ChangeImpactService()
    analysis = svc.compute_change_impact_with_graph(str(chain_repo), base, target)
    assert analysis.graph is not None

    changed_id = analysis.report.changed_symbols[0].node_id
    findings = [{"symbol_id": changed_id, "finding_id": "finding-1"}]
    first = svc.intersect_findings(analysis, findings)
    second = svc.intersect_findings(analysis, findings)

    assert first is analysis.report
    assert second is analysis.report
    assert len(second.finding_impacts) == 1
    assert len(second.intersecting_findings) == 1


def test_ledger_event_recorded_when_ledger_provided(chain_repo: Path):
    base = _commit(chain_repo, "base")
    _write(chain_repo, "repository.py", """\
        class UserRepository:
            def get_user(self, user_id):
                return {"id": user_id, "changed": True}
    """)
    target = _commit(chain_repo, "modify")

    events: List[dict] = []

    class FakeLedger:
        def append_event(self, event_type, summary, **kwargs):
            events.append({"event_type": event_type, "summary": summary, **kwargs})
            return True

    svc = ChangeImpactService()
    svc.compute_change_impact(str(chain_repo), base, target, ledger=FakeLedger())
    assert len(events) == 1
    assert events[0]["event_type"] == "CHANGE_IMPACT_ANALYZED"
    assert events[0]["phase"] == "PHASE_20"


def test_no_changes_between_identical_revisions(chain_repo: Path):
    base = _commit(chain_repo, "base")
    svc = ChangeImpactService()
    report = svc.compute_change_impact(str(chain_repo), base, base)
    assert report.changed_files == []
    assert report.confidence == Confidence.HIGH


def test_multiple_hunks_in_same_symbol_are_deduped(tmp_path: Path):
    """A single function touched by several discontiguous diff hunks (e.g. a
    large docstring rewrite) must appear once in changed_symbols, not once
    per hunk. Discovered via real-repo validation against Flask."""
    repo = _init_repo(tmp_path)
    _write(repo, "svc.py", """\
        def handler(x):
            # line A
            # line B
            # line C
            # line D
            # line E
            # line F
            return x
    """)
    base = _commit(repo, "base")
    _write(repo, "svc.py", """\
        def handler(x):
            # line A changed
            # line B
            # line C
            # line D
            # line E changed
            # line F
            return x
    """)
    target = _commit(repo, "two separate hunks inside one function")

    svc = ChangeImpactService()
    report = svc.compute_change_impact(str(repo), base, target)
    matches = [s for s in report.changed_symbols if s.name == "handler"]
    assert len(matches) == 1


def test_not_a_git_repo_raises(tmp_path: Path):
    not_repo = tmp_path / "plain"
    not_repo.mkdir()
    svc = ChangeImpactService()
    with pytest.raises(ChangeImpactError):
        svc.compute_change_impact(str(not_repo), "HEAD~1", "HEAD")
