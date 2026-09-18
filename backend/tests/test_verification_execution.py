"""Tests for safe deterministic verification command execution."""

import subprocess
from pathlib import Path
from unittest.mock import patch

from app.models.change_impact import ChangeImpactReport, Confidence, RiskLevel
from app.services.change_risk_engine import ChangeRiskAssessment
from app.services.verification_execution import VerificationExecutor


def _impact(changed_files=("tests/test_sample.py",)):
    return ChangeImpactReport(
        repository="owner/repo",
        base_revision="base",
        target_revision="target",
        changed_files=list(changed_files),
        confidence=Confidence.HIGH,
    ).finalize()


def _risk(level=RiskLevel.LOW):
    return ChangeRiskAssessment(
        risk_level=level,
        score=20 if level == RiskLevel.LOW else 90,
        confidence="high",
    ).finalize()


def _repo(tmp_path: Path, *, pytest_file=True, ruff=False, package=False):
    if pytest_file:
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_sample.py").write_text("def test_sample():\n    assert 1 == 1\n")
    if ruff:
        (tmp_path / "pyproject.toml").write_text("[tool.ruff]\nline-length = 88\n")
    if package:
        (tmp_path / "package.json").write_text('{"scripts":{"test":"echo unsafe"}}')
    return tmp_path


def test_pytest_is_discovered_selected_and_passed(tmp_path):
    result = VerificationExecutor(timeout_seconds=30).execute(
        str(_repo(tmp_path)), "target", _impact(), _risk(), []
    )

    command = next(item for item in result.command_results if item["check"] == "pytest")
    assert command["discovered"] is True
    assert command["executed"] is True
    assert command["status"] == "PASSED"
    assert command["exit_code"] == 0
    assert command["executed_test_count"] == 1
    assert result.test_execution_result == "passed"


def test_pytest_failure_becomes_structured_evidence(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_sample.py").write_text("def test_sample():\n    assert False\n")
    result = VerificationExecutor(timeout_seconds=30).execute(
        str(tmp_path), "target", _impact(), _risk(), []
    )

    command = result.command_results[0]
    assert command["status"] == "FAILED"
    assert command["executed"] is True
    assert result.test_execution_result == "failed"


def test_pytest_is_discovered_but_not_executed_without_deterministic_target(tmp_path):
    result = VerificationExecutor().execute(
        str(_repo(tmp_path)), "target", _impact(("src/service.py",)), _risk(), []
    )

    command = result.command_results[0]
    assert command["check"] == "pytest"
    assert command["discovered"] is True
    assert command["executed"] is False
    assert result.relevant_test_selection == "unavailable"
    assert result.test_execution_result is None


def test_pytest_unavailable_is_not_installed_or_executed(tmp_path):
    with patch("app.services.verification_execution.importlib.util.find_spec", return_value=None):
        result = VerificationExecutor().execute(
            str(_repo(tmp_path)), "target", _impact(), _risk(), []
        )

    command = result.command_results[0]
    assert command["executed"] is False
    assert "unavailable" in command["reason"]


def test_timeout_becomes_structured_evidence(tmp_path):
    timeout = subprocess.TimeoutExpired(["pytest"], 1, output=b"partial", stderr=b"late")
    with patch(
        "app.services.verification_execution.subprocess.run",
        side_effect=timeout,
    ):
        result = VerificationExecutor(timeout_seconds=1).execute(
            str(_repo(tmp_path)), "target", _impact(), _risk(), []
        )

    command = result.command_results[0]
    assert command["status"] == "TIMEOUT"
    assert command["executed"] is True
    assert command["exit_code"] is None
    assert result.test_execution_result == "blocked"


def test_ruff_pass_and_failure_are_structured(tmp_path):
    repository = _repo(tmp_path, pytest_file=False, ruff=True)
    passing = VerificationExecutor(timeout_seconds=30).execute(
        str(repository), "target", _impact(("service.py",)), _risk(), []
    )
    ruff = next(item for item in passing.command_results if item["check"] == "ruff")
    assert ruff["executed"] is True
    assert ruff["status"] == "PASSED"

    (repository / "service.py").write_text("import os\n")
    failing = VerificationExecutor(timeout_seconds=30).execute(
        str(repository), "target", _impact(("service.py",)), _risk(), []
    )
    ruff = next(item for item in failing.command_results if item["check"] == "ruff")
    assert ruff["status"] == "FAILED"
    assert failing.static_analysis_result == "failed"


def test_npm_scripts_are_discovered_but_never_executed(tmp_path):
    with patch("app.services.verification_execution.subprocess.run") as run:
        result = VerificationExecutor().execute(
            str(_repo(tmp_path, pytest_file=False, package=True)),
            "target",
            _impact(("service.js",)),
            _risk(),
            [],
        )

    command = next(item for item in result.command_results if item["check"] == "javascript_tests")
    assert command["discovered"] is True
    assert command["executed"] is False
    assert "not executed" in command["reason"]
    run.assert_not_called()


def test_command_order_and_identity_are_stable(tmp_path):
    repository = _repo(tmp_path, ruff=True, package=True)
    first = VerificationExecutor().execute(
        str(repository), "target", _impact(), _risk(), []
    )
    second = VerificationExecutor().execute(
        str(repository), "target", _impact(), _risk(), []
    )

    stable_fields = (
        "check",
        "command",
        "revision",
        "working_directory",
        "discovered",
        "executed",
        "status",
        "exit_code",
        "discovered_test_count",
        "executed_test_count",
        "reason",
    )
    assert [
        tuple(item[field] for field in stable_fields) for item in first.command_results
    ] == [
        tuple(item[field] for field in stable_fields) for item in second.command_results
    ]
    assert [item["check"] for item in first.command_results] == ["javascript_tests", "pytest", "ruff"]