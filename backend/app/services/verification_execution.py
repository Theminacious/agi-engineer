"""Safe, deterministic execution of repository verification commands."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from app.models.change_impact import ChangeImpactReport, RiskLevel
from app.services.change_risk_engine import ChangeRiskAssessment
from app.services.finding_context import FindingContext
from app.services.verification_engine import VerificationEvidence


MAX_OUTPUT = 4000
DEFAULT_TIMEOUT_SECONDS = 120
_PYTEST_SUMMARY = re.compile(
    r"(?P<count>\d+)\s+(?P<kind>passed|failed|error|errors|skipped|xfailed|xpassed)"
)
_PYTEST_COLLECTED = re.compile(r"collected\s+(?P<count>\d+)\s+items?")


@dataclass(frozen=True)
class VerificationCommandResult:
    check: str
    command: List[str]
    revision: str
    working_directory: str
    discovered: bool
    executed: bool
    status: str
    exit_code: Optional[int]
    duration_ms: Optional[int]
    stdout: str = ""
    stderr: str = ""
    discovered_test_count: Optional[int] = None
    executed_test_count: Optional[int] = None
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check": self.check,
            "command": list(self.command),
            "revision": self.revision,
            "working_directory": self.working_directory,
            "discovered": self.discovered,
            "executed": self.executed,
            "status": self.status,
            "exit_code": self.exit_code,
            "duration_ms": self.duration_ms,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "discovered_test_count": self.discovered_test_count,
            "executed_test_count": self.executed_test_count,
            "reason": self.reason,
        }


def _bounded(value: Any) -> str:
    if isinstance(value, bytes):
        value = value.decode(errors="replace")
    value = str(value or "")
    if len(value) <= MAX_OUTPUT:
        return value
    return value[:MAX_OUTPUT] + "...[truncated]"


def _has_ruff_config(root: Path) -> bool:
    if any((root / name).is_file() for name in ("ruff.toml", ".ruff.toml")):
        return True
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        return "[tool.ruff" in pyproject.read_text(errors="replace")
    return False


def _pytest_files(root: Path) -> List[str]:
    paths = []
    for pattern in ("test_*.py", "*_test.py"):
        paths.extend(path.relative_to(root).as_posix() for path in root.rglob(pattern))
    return sorted({path for path in paths if ".venv" not in Path(path).parts})


def _has_pytest_config(root: Path) -> bool:
    if any((root / name).is_file() for name in ("pytest.ini", "tox.ini", "setup.cfg")):
        return True
    pyproject = root / "pyproject.toml"
    return pyproject.is_file() and "[tool.pytest" in pyproject.read_text(errors="replace")


def _test_targets(root: Path, changed_files: Iterable[str]) -> List[str]:
    """Select only changed test files; source-to-test naming is not inferred."""
    known = set(_pytest_files(root))
    targets = []
    for path in changed_files:
        normalized = str(path).replace("\\", "/").lstrip("./")
        if normalized in known:
            targets.append(normalized)
    return sorted(set(targets))


def _parse_pytest_counts(output: str) -> Tuple[Optional[int], Optional[int]]:
    discovered = None
    collected = _PYTEST_COLLECTED.search(output)
    if collected:
        discovered = int(collected.group("count"))
    executed = 0
    found = False
    for match in _PYTEST_SUMMARY.finditer(output):
        found = True
        if match.group("kind") not in {"skipped", "xfailed", "xpassed"}:
            executed += int(match.group("count"))
    return discovered, executed if found else None


class VerificationExecutor:
    """Discover and execute only fixed, locally-supported checks."""

    def __init__(self, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> None:
        self.timeout_seconds = timeout_seconds

    def execute(
        self,
        repo_path: str,
        revision: str,
        impact: ChangeImpactReport,
        risk: ChangeRiskAssessment,
        contexts: Sequence[FindingContext],
    ) -> VerificationEvidence:
        root = Path(repo_path).resolve()
        changed_files = impact.changed_files
        results: List[VerificationCommandResult] = []

        pytest_files = _pytest_files(root)
        pytest_targets = _test_targets(root, changed_files)
        pytest_discovered = bool(pytest_files or _has_pytest_config(root))
        if pytest_discovered:
            pytest_command = [sys.executable, "-m", "pytest", "--color=no"] + pytest_targets
            if pytest_targets and importlib.util.find_spec("pytest") is not None:
                results.append(self._run(
                    "pytest", pytest_command, root, revision, parser=_parse_pytest_counts
                ))
            else:
                results.append(VerificationCommandResult(
                    check="pytest",
                    command=pytest_command,
                    revision=revision,
                    working_directory=str(root),
                    discovered=True,
                    executed=False,
                    status="NOT_EXECUTED",
                    exit_code=None,
                    duration_ms=None,
                    discovered_test_count=len(pytest_files) if pytest_files else None,
                    reason=(
                        "relevant_test_selection=unavailable"
                        if pytest_files
                        else "pytest configuration found but no tests discovered"
                    ),
                ))

        ruff_discovered = _has_ruff_config(root) and importlib.util.find_spec("ruff") is not None
        if ruff_discovered:
            results.append(self._run(
                "ruff",
                [sys.executable, "-m", "ruff", "check", ".", "--output-format", "json"],
                root,
                revision,
                parser=None,
            ))
        elif _has_ruff_config(root):
            results.append(VerificationCommandResult(
                check="ruff",
                command=[sys.executable, "-m", "ruff", "check", ".", "--output-format", "json"],
                revision=revision,
                working_directory=str(root),
                discovered=True,
                executed=False,
                status="NOT_EXECUTED",
                exit_code=None,
                duration_ms=None,
                reason="ruff is unavailable in the current environment; no installation attempted",
            ))

        package = root / "package.json"
        if package.is_file():
            try:
                scripts = json.loads(package.read_text()).get("scripts", {})
            except (OSError, ValueError):
                scripts = {}
            if isinstance(scripts, dict) and "test" in scripts:
                results.append(VerificationCommandResult(
                    check="javascript_tests",
                    command=["npm", "test"],
                    revision=revision,
                    working_directory=str(root),
                    discovered=True,
                    executed=False,
                    status="NOT_EXECUTED",
                    exit_code=None,
                    duration_ms=None,
                    reason="repository-defined npm scripts are discovered but not executed",
                ))

        pytest_result = next((result for result in results if result.check == "pytest"), None)
        ruff_result = next((result for result in results if result.check == "ruff"), None)
        tests_discovered = pytest_files if pytest_discovered else None
        tests_executed = (
            pytest_targets
            if pytest_result is not None and pytest_result.executed
            else None
        )
        test_result = None
        if pytest_result is not None and pytest_result.executed:
            test_result = {
                "PASSED": "passed",
                "FAILED": "failed",
                "TIMEOUT": "blocked",
                "ERROR": "blocked",
            }.get(pytest_result.status, "blocked")

        static_executed = ruff_result is not None and ruff_result.executed
        static_result = None
        if ruff_result is not None:
            static_result = "passed" if ruff_result.status == "PASSED" else "failed"
        command_dicts = [result.to_dict() for result in sorted(results, key=lambda item: item.check)]
        return VerificationEvidence(
            tests_discovered=tests_discovered,
            tests_executed=tests_executed,
            test_execution_result=test_result,
            relevant_tests=pytest_targets or None,
            static_analysis_executed=static_executed if ruff_result is not None else None,
            static_analysis_result=static_result,
            findings_after=contexts,
            command_results=command_dicts,
            relevant_test_selection=(
                "deterministic_changed_test_files" if pytest_targets else "unavailable"
            ),
        )

    def _run(
        self,
        check: str,
        command: List[str],
        root: Path,
        revision: str,
        parser: Optional[Any],
    ) -> VerificationCommandResult:
        started = time.monotonic()
        try:
            completed = subprocess.run(
                command,
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                shell=False,
                env={**os.environ, "PYTHONHASHSEED": "0"},
            )
        except subprocess.TimeoutExpired as exc:
            return VerificationCommandResult(
                check=check,
                command=command,
                revision=revision,
                working_directory=str(root),
                discovered=True,
                executed=True,
                status="TIMEOUT",
                exit_code=None,
                duration_ms=int((time.monotonic() - started) * 1000),
                stdout=_bounded(exc.stdout or ""),
                stderr=_bounded(exc.stderr or ""),
                reason=f"timeout after {self.timeout_seconds}s",
            )
        except (OSError, ValueError) as exc:
            return VerificationCommandResult(
                check=check,
                command=command,
                revision=revision,
                working_directory=str(root),
                discovered=True,
                executed=True,
                status="ERROR",
                exit_code=None,
                duration_ms=int((time.monotonic() - started) * 1000),
                reason=str(exc),
            )

        stdout = _bounded(completed.stdout)
        stderr = _bounded(completed.stderr)
        discovered_count = executed_count = None
        if parser is not None:
            discovered_count, executed_count = parser(completed.stdout + "\n" + completed.stderr)
        return VerificationCommandResult(
            check=check,
            command=command,
            revision=revision,
            working_directory=str(root),
            discovered=True,
            executed=True,
            status="PASSED" if completed.returncode == 0 else "FAILED",
            exit_code=completed.returncode,
            duration_ms=int((time.monotonic() - started) * 1000),
            stdout=stdout,
            stderr=stderr,
            discovered_test_count=discovered_count,
            executed_test_count=executed_count,
        )