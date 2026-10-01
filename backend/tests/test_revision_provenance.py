"""Revision/provenance integrity: pin refs to SHAs and verify worktree identity."""

import os
import re
import subprocess

from app.models.change_impact import Confidence
from app.services.baseline_comparison import BaselineComparisonService
from app.services.change_impact_service import ChangeImpactService


SHA40 = re.compile(r"[0-9a-f]{40}")

BASE_MOD = "def value():\n    return 1\n"
TARGET_MOD = "def value():\n    return 2\n"
TEST_BODY = "from pkg import mod\n\ndef test_fn():\n    assert mod.value() == 1\n"


def _git(repo, *args):
    return subprocess.run(
        ["git", "-C", repo, *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def _init(repo):
    subprocess.run(["git", "init", "--quiet", "-b", "main", repo], check=True)
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Revision Test")
    _git(repo, "config", "commit.gpgsign", "false")


def _write(repo, rel, body):
    full = os.path.join(repo, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as fh:
        fh.write(body)


def _commit(repo, msg):
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", msg)
    return _git(repo, "rev-parse", "HEAD")


def _two_commit_repo(tmp_path):
    repo = str(tmp_path / "repo")
    _init(repo)
    _write(repo, "pkg/__init__.py", "")
    _write(repo, "pkg/mod.py", BASE_MOD)
    _write(repo, "tests/test_mod.py", TEST_BODY)
    base_sha = _commit(repo, "base")
    _git(repo, "branch", "basebr")
    _write(repo, "pkg/mod.py", TARGET_MOD)
    target_sha = _commit(repo, "target")
    return repo, base_sha, target_sha


def test_base_ref_is_pinned_to_commit_sha(tmp_path):
    repo, base_sha, target_sha = _two_commit_repo(tmp_path)
    analysis = ChangeImpactService().compute_change_impact_with_graph(
        repo_path=repo, base_revision="basebr", target_revision="HEAD",
        repository_label="r",
    )
    assert SHA40.fullmatch(analysis.report.base_revision)
    assert SHA40.fullmatch(analysis.report.target_revision)
    assert analysis.report.base_revision == base_sha
    assert analysis.report.target_revision == target_sha


def test_unresolvable_revision_fails_closed(tmp_path):
    import pytest

    from app.services.change_impact_service import ChangeImpactError

    repo, _base_sha, _target_sha = _two_commit_repo(tmp_path)
    with pytest.raises(ChangeImpactError, match="does not resolve"):
        ChangeImpactService().compute_change_impact_with_graph(
            repo_path=repo, base_revision="does-not-exist", target_revision="HEAD",
            repository_label="r",
        )


def test_impact_hash_is_stable_across_ref_and_sha_inputs(tmp_path):
    repo, base_sha, _target_sha = _two_commit_repo(tmp_path)
    service = ChangeImpactService()
    via_ref = service.compute_change_impact_with_graph(
        repo_path=repo, base_revision="basebr", target_revision="HEAD",
        repository_label="r",
    )
    via_sha = service.compute_change_impact_with_graph(
        repo_path=repo, base_revision=base_sha, target_revision="HEAD",
        repository_label="r",
    )
    assert via_ref.report.deterministic_hash == via_sha.report.deterministic_hash


def test_baseline_worktree_resolves_branch_ref(tmp_path):
    repo, base_sha, _target_sha = _two_commit_repo(tmp_path)
    bundle = BaselineComparisonService().compare_behavior(
        repo_path=repo, base_revision="basebr", pytest_targets=["tests/test_mod.py"],
    )
    assert bundle["status"] == "EXECUTED"
    assert bundle["node_results"] == {"tests/test_mod.py::test_fn": "passed"}
    assert bundle["execution"]["revision"] == "basebr"


def test_baseline_unresolvable_revision_is_unavailable(tmp_path):
    repo, _base_sha, _target_sha = _two_commit_repo(tmp_path)
    bundle = BaselineComparisonService().compare_behavior(
        repo_path=repo, base_revision="no-such-ref", pytest_targets=["tests/test_mod.py"],
    )
    assert bundle["status"] == "UNAVAILABLE"
    assert "resolve" in (bundle["reason"] or "")
