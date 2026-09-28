"""Isolated baseline analyzer execution and deterministic finding comparison."""

from __future__ import annotations

import subprocess
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Sequence

from app.services.cleanup import safe_rmtree


@dataclass(frozen=True)
class BaselineComparison:
    baseline_status: str
    comparison_status: str
    findings_before: Optional[List[Dict[str, Any]]]
    error: Optional[str] = None


class BaselineComparisonService:
    """Run the existing analyzer callback in an isolated git worktree."""

    def __init__(self, timeout_seconds: int = 120) -> None:
        self.timeout_seconds = timeout_seconds

    @contextmanager
    def _base_worktree(self, repo_path: str, base_revision: str) -> Iterator[Path]:
        root = Path(tempfile.mkdtemp(prefix="agi-verification-baseline-"))
        worktree = root / "repo"
        added = False
        resolved = str(Path(repo_path).resolve())
        try:
            subprocess.run(
                ["git", "-C", resolved, "worktree", "add", "--detach", str(worktree), base_revision],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                shell=False,
                check=True,
            )
            added = True
            yield worktree
        finally:
            if added:
                try:
                    subprocess.run(
                        ["git", "-C", resolved, "worktree", "remove", "--force", str(worktree)],
                        capture_output=True,
                        text=True,
                        timeout=self.timeout_seconds,
                        shell=False,
                    )
                except (OSError, subprocess.TimeoutExpired, subprocess.CalledProcessError):
                    pass
            safe_rmtree(str(root), kind="verification_baseline")

    def compare(
        self,
        repo_path: str,
        base_revision: Optional[str],
        target_revision: Optional[str],
        target_findings: Optional[Sequence[Dict[str, Any]]],
        analyze: Callable[[str], Sequence[Any]],
        normalize: Callable[[Sequence[Any]], List[Dict[str, Any]]],
    ) -> BaselineComparison:
        if not base_revision:
            return BaselineComparison("UNAVAILABLE", "UNKNOWN", None, "base revision unavailable")
        if target_revision is None or target_findings is None:
            return BaselineComparison("UNAVAILABLE", "UNKNOWN", None, "target evidence unavailable")

        try:
            with self._base_worktree(repo_path, base_revision) as worktree:
                proposals = analyze(str(worktree))
                findings = normalize(proposals)
                return BaselineComparison("COMPLETED", "COMPLETED", findings)
        except subprocess.TimeoutExpired:
            return BaselineComparison("TIMEOUT", "UNKNOWN", None, "baseline worktree or analyzer timed out")
        except (OSError, subprocess.CalledProcessError, ValueError) as exc:
            return BaselineComparison("UNAVAILABLE", "UNKNOWN", None, str(exc))
        except Exception as exc:
            return BaselineComparison("FAILED", "UNKNOWN", None, str(exc))

    def compare_behavior(
        self,
        repo_path: str,
        base_revision: Optional[str],
        pytest_targets: Sequence[str],
        target_revision: Optional[str] = None,
    ) -> Dict[str, Any]:
        from app.services.verification_execution import (
            _behavioral_execution_provenance,
            run_selected_tests,
        )

        def _unavailable(reason: str) -> Dict[str, Any]:
            return {
                "status": "UNAVAILABLE",
                "reason": reason,
                "exit_code": None,
                "node_results": {},
                "missing_selected_tests": list(pytest_targets),
                "execution": _behavioral_execution_provenance(
                    command=None, working_directory=None,
                    revision=base_revision or "", duration_ms=None,
                    stdout="", stderr="",
                ),
            }

        if not base_revision:
            return _unavailable("base revision unavailable")
        if not pytest_targets:
            return _unavailable("no selected tests provided")

        try:
            with self._base_worktree(repo_path, base_revision) as worktree:
                return run_selected_tests(
                    str(worktree), base_revision, pytest_targets, self.timeout_seconds
                )
        except subprocess.TimeoutExpired:
            return _unavailable("baseline worktree timed out")
        except (OSError, subprocess.CalledProcessError, ValueError) as exc:
            return _unavailable(str(exc))
        except Exception as exc:
            return _unavailable(str(exc))