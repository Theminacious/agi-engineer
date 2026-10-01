"""Target-tree identity at the verification execution boundary (real git + pytest).

These exercise the real VerificationExecutor.execute path against disposable git
repositories: pytest actually runs only when HEAD is the claimed target commit
and the worktree is clean.
"""

import os
import subprocess

from app.models.change_impact import ChangeImpactReport
from app.services.change_risk_engine import ChangeRiskAssessment, RiskLevel
from app.services.verification_engine import (
    TARGET_IDENTITY_DIRTY,
    TARGET_IDENTITY_MISMATCH,
    TARGET_IDENTITY_UNVERIFIABLE,
    TARGET_IDENTITY_VERIFIED,
    VerificationEngine,
    VerificationState,
)
from app.services.verification_execution import VerificationExecutor


def _git(repo, *args):
    return subprocess.run(
        ["git", "-C", repo, *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def _repo(tmp_path):
    repo = str(tmp_path / "repo")
    subprocess.run(["git", "init", "--quiet", "-b", "main", repo], check=True)
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Target Identity Test")
    _git(repo, "config", "commit.gpgsign", "false")
    _write(repo, ".gitignore", "*.ignored\n")
    _write(repo, "tests/test_mod.py", "def test_ok():\n    assert True\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "target")
    return repo, _git(repo, "rev-parse", "HEAD")


def _write(repo, rel, body):
    full = os.path.join(repo, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as fh:
        fh.write(body)


def _impact():
    return ChangeImpactReport(
        repository="r", base_revision="base", target_revision="target",
        changed_files=["tests/test_mod.py"],
    )


def _risk():
    return ChangeRiskAssessment(risk_level=RiskLevel.LOW, score=10, confidence="high")


def _execute(repo, expected_sha):
    return VerificationExecutor().execute(
        repo_path=repo, revision=expected_sha, impact=_impact(), risk=_risk(),
        contexts=[], capture_node_results=True, expected_target_sha=expected_sha,
    )


def _proof(evidence):
    return VerificationEngine().assess(_impact(), [], _risk(), evidence)


# --- Valid case: HEAD == expected, clean -> verification proceeds ------------

def test_matching_clean_target_verifies_and_runs(tmp_path):
    repo, sha = _repo(tmp_path)
    ev = _execute(repo, sha)
    assert ev.target_identity == TARGET_IDENTITY_VERIFIED
    assert ev.tests_executed == ["tests/test_mod.py"]
    assert ev.test_execution_result == "passed"
    proof = _proof(ev)
    assert proof.target_identity == TARGET_IDENTITY_VERIFIED
    assert proof.state in (VerificationState.VERIFIED, VerificationState.PARTIALLY_VERIFIED)


def test_ignored_file_does_not_count_as_dirty(tmp_path):
    repo, sha = _repo(tmp_path)
    _write(repo, "build.ignored", "artifact\n")
    ev = _execute(repo, sha)
    assert ev.target_identity == TARGET_IDENTITY_VERIFIED
    assert ev.test_execution_result == "passed"


# --- Mismatch: HEAD != expected -> refuse trustworthy verification -----------

def test_head_mismatch_blocks_and_does_not_run(tmp_path):
    repo, _sha = _repo(tmp_path)
    ev = _execute(repo, "0" * 40)
    assert ev.target_identity == TARGET_IDENTITY_MISMATCH
    assert "TARGET_REVISION_MISMATCH" in (ev.target_identity_reason or "")
    assert ev.tests_executed is None
    assert ev.test_execution_result is None
    assert ev.command_results == []
    proof = _proof(ev)
    assert proof.state == VerificationState.BLOCKED
    assert proof.test_execution_result is None


def test_exact_full_sha_required_no_prefix_match(tmp_path):
    repo, sha = _repo(tmp_path)
    ev = _execute(repo, sha[:39])  # 39-char prefix must NOT be accepted
    assert ev.target_identity == TARGET_IDENTITY_MISMATCH


# --- Dirty worktree variants -> refuse trustworthy verification --------------

def test_modified_tracked_file_is_dirty(tmp_path):
    repo, sha = _repo(tmp_path)
    _write(repo, "tests/test_mod.py", "def test_ok():\n    assert True  # changed\n")
    ev = _execute(repo, sha)
    assert ev.target_identity == TARGET_IDENTITY_DIRTY
    assert "TARGET_WORKTREE_DIRTY" in (ev.target_identity_reason or "")
    assert ev.tests_executed is None
    assert _proof(ev).state == VerificationState.BLOCKED


def test_staged_modification_is_dirty(tmp_path):
    repo, sha = _repo(tmp_path)
    _write(repo, "tests/test_mod.py", "def test_ok():\n    assert True  # staged\n")
    _git(repo, "add", "tests/test_mod.py")
    ev = _execute(repo, sha)
    assert ev.target_identity == TARGET_IDENTITY_DIRTY


def test_deleted_tracked_file_is_dirty(tmp_path):
    repo, sha = _repo(tmp_path)
    os.unlink(os.path.join(repo, "tests/test_mod.py"))
    ev = _execute(repo, sha)
    assert ev.target_identity == TARGET_IDENTITY_DIRTY


def test_untracked_non_ignored_file_is_dirty(tmp_path):
    repo, sha = _repo(tmp_path)
    _write(repo, "stray.py", "x = 1\n")
    ev = _execute(repo, sha)
    assert ev.target_identity == TARGET_IDENTITY_DIRTY


# --- Unreadable HEAD (not a git repo) -> unverifiable ------------------------

def test_non_git_tree_is_unverifiable(tmp_path):
    plain = str(tmp_path / "plain")
    os.makedirs(os.path.join(plain, "tests"))
    _write(plain, "tests/test_mod.py", "def test_ok():\n    assert True\n")
    ev = _execute(plain, "0" * 40)
    assert ev.target_identity == TARGET_IDENTITY_UNVERIFIABLE
    assert "TARGET_REVISION_UNVERIFIABLE" in (ev.target_identity_reason or "")
    assert ev.tests_executed is None


# --- Backward compatibility: no expected SHA -> no identity gating -----------

def test_no_expected_sha_skips_identity_check(tmp_path):
    repo, _sha = _repo(tmp_path)
    ev = VerificationExecutor().execute(
        repo_path=repo, revision="target", impact=_impact(), risk=_risk(),
        contexts=[], capture_node_results=True,
    )
    assert ev.target_identity is None
    assert ev.test_execution_result == "passed"
