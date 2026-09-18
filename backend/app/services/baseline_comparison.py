"""Isolated baseline analyzer execution and deterministic finding comparison."""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

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

        root = Path(tempfile.mkdtemp(prefix="agi-verification-baseline-"))
        worktree = root / "repo"
        added = False
        try:
            subprocess.run(
                ["git", "-C", str(Path(repo_path).resolve()), "worktree", "add", "--detach", str(worktree), base_revision],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                shell=False,
                check=True,
            )
            added = True
            proposals = analyze(str(worktree))
            findings = normalize(proposals)
            return BaselineComparison("COMPLETED", "COMPLETED", findings)
        except subprocess.TimeoutExpired:
            return BaselineComparison("TIMEOUT", "UNKNOWN", None, "baseline worktree or analyzer timed out")
        except (OSError, subprocess.CalledProcessError, ValueError) as exc:
            return BaselineComparison("UNAVAILABLE", "UNKNOWN", None, str(exc))
        except Exception as exc:
            return BaselineComparison("FAILED", "UNKNOWN", None, str(exc))
        finally:
            if added:
                try:
                    subprocess.run(
                        ["git", "-C", str(Path(repo_path).resolve()), "worktree", "remove", "--force", str(worktree)],
                        capture_output=True,
                        text=True,
                        timeout=self.timeout_seconds,
                        shell=False,
                    )
                except (OSError, subprocess.TimeoutExpired, subprocess.CalledProcessError):
                    pass
            safe_rmtree(str(root), kind="verification_baseline")