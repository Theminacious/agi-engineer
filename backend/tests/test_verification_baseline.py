"""Tests for isolated baseline execution and semantic finding comparison."""

import subprocess
from pathlib import Path
from unittest.mock import patch

from app.models.change_impact import ChangeImpactReport, Confidence, RiskLevel
from app.services.baseline_comparison import BaselineComparisonService
from app.services.change_risk_engine import ChangeRiskAssessment
from app.services.verification_engine import (
    VerificationEngine,
    VerificationEvidence,
    VerificationState,
)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _repo(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "--quiet", "-b", "main", str(repo)], check=True)
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Baseline Test")
    (repo / "service.py").write_text("def handle():\n    return 'base'\n")
    _git(repo, "add", "service.py")
    _git(repo, "commit", "--quiet", "-m", "base")
    base = _git(repo, "rev-parse", "HEAD")
    (repo / "service.py").write_text("def handle():\n    return 'target'\n")
    _git(repo, "commit", "--quiet", "-am", "target")
    target = _git(repo, "rev-parse", "HEAD")
    return repo, base, target


def _impact():
    return ChangeImpactReport(
        repository="owner/repo",
        base_revision="base",
        target_revision="target",
        changed_files=["service.py"],
        confidence=Confidence.HIGH,
    ).finalize()


def _risk():
    return ChangeRiskAssessment(
        risk_level=RiskLevel.LOW,
        score=20,
        confidence="high",
    ).finalize()


def test_baseline_runs_in_isolated_worktree_and_cleans_up(tmp_path):
    repo, base, target = _repo(tmp_path)
    seen = {}

    def analyze(worktree):
        seen["worktree"] = Path(worktree)
        seen["content"] = (Path(worktree) / "service.py").read_text()
        return [{"file_path": "service.py", "issue_code": "R001", "symbol": "handle"}]

    result = BaselineComparisonService().compare(
        str(repo), base, target, [], analyze, lambda findings: list(findings)
    )

    assert result.baseline_status == "COMPLETED"
    assert result.comparison_status == "COMPLETED"
    assert result.findings_before == [{"file_path": "service.py", "issue_code": "R001", "symbol": "handle"}]
    assert seen["content"] == "def handle():\n    return 'base'\n"
    assert not seen["worktree"].exists()
    assert (repo / "service.py").read_text() == "def handle():\n    return 'target'\n"


def test_unavailable_baseline_preserves_none(tmp_path):
    repo, _, target = _repo(tmp_path)
    result = BaselineComparisonService().compare(
        str(repo), "missing-revision", target, [], lambda _: [], lambda values: list(values)
    )

    assert result.baseline_status == "UNAVAILABLE"
    assert result.comparison_status == "UNKNOWN"
    assert result.findings_before is None


def test_analyzer_failure_becomes_structured_and_cleans_up(tmp_path):
    repo, base, target = _repo(tmp_path)

    def analyze(_):
        raise RuntimeError("baseline analyzer failed")

    result = BaselineComparisonService().compare(
        str(repo), base, target, [], analyze, lambda values: list(values)
    )

    assert result.baseline_status == "FAILED"
    assert result.findings_before is None
    assert "baseline analyzer failed" in result.error


def test_timeout_becomes_structured_and_cleans_up(tmp_path):
    repo, base, target = _repo(tmp_path)
    timeout = subprocess.TimeoutExpired(["git"], 1)
    with patch("app.services.baseline_comparison.subprocess.run", side_effect=timeout):
        result = BaselineComparisonService(timeout_seconds=1).compare(
            str(repo), base, target, [], lambda _: [], lambda values: list(values)
        )

    assert result.baseline_status == "TIMEOUT"
    assert result.findings_before is None


def test_semantic_comparison_ignores_line_movement_and_deduplicates():
    impact = _impact()
    risk = _risk()
    before = [{
        "file_path": "service.py",
        "line_number": 10,
        "issue_code": "R001",
        "symbol": "handle",
        "message": "unsafe line 10",
    }, {
        "file_path": "service.py",
        "line_number": 10,
        "issue_code": "R001",
        "symbol": "handle",
        "message": "unsafe line 10",
    }]
    after = [{
        "file_path": "service.py",
        "line_number": 30,
        "issue_code": "R001",
        "symbol": "handle",
        "message": "unsafe line 30",
    }]
    proof = VerificationEngine().assess(
        impact,
        [],
        risk,
        VerificationEvidence(
            findings_before=before,
            findings_after=after,
            baseline_status="COMPLETED",
            comparison_status="COMPLETED",
        ),
    )

    assert proof.state is VerificationState.PARTIALLY_VERIFIED
    assert proof.new_findings == []
    assert proof.unchanged_findings == ["service.py|R001|handle"]
    assert proof.resolved_findings == []


def test_new_and_resolved_findings_change_the_proof_hash():
    impact = _impact()
    risk = _risk()
    base = VerificationEvidence(
        findings_before=[{"file_path": "a.py", "issue_code": "R", "message": "old"}],
        findings_after=[{"file_path": "a.py", "issue_code": "R", "message": "old"}],
        baseline_status="COMPLETED",
        comparison_status="COMPLETED",
    )
    changed = VerificationEvidence(
        findings_before=base.findings_before,
        findings_after=[{"file_path": "a.py", "issue_code": "R", "message": "new"}],
        baseline_status="COMPLETED",
        comparison_status="COMPLETED",
    )
    first = VerificationEngine().assess(impact, [], risk, base)
    second = VerificationEngine().assess(impact, [], risk, changed)

    assert first.deterministic_hash != second.deterministic_hash
    assert second.new_findings