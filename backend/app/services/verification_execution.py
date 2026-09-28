"""Safe, deterministic execution of repository verification commands."""

from __future__ import annotations

import ast
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
from app.services.verification_engine import BehavioralTestComparison, VerificationEvidence


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
    node_results: Optional[Dict[str, str]] = None

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
            "node_results": dict(self.node_results) if self.node_results is not None else None,
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


def _conventional_test_candidates(path: str) -> set[str]:
    """Deterministic conventional mirror candidates for one changed file.

    Only two objectively derivable layouts are considered, mirroring the
    repository's own structure. Candidate generation is purely structural;
    a candidate only becomes a selected target when it also exists in the
    discovered test-file set AND carries deterministic static import
    evidence (see _has_static_import_evidence).
    """
    normalized = str(path).replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized.startswith("src/"):
        normalized = normalized[len("src/"):]
    if not normalized.endswith(".py"):
        return set()
    parent, _, filename = normalized.rpartition("/")
    stem = filename[: -len(".py")]
    candidates: set[str] = set()
    if parent:
        candidates.add(f"tests/{parent}/test_{stem}.py")
    candidates.add(f"tests/test_{stem}.py")
    return candidates


def _module_dotted_path(normalized_path: str) -> Optional[str]:
    """Dotted import path for a normalized repository-relative module path."""
    if not normalized_path.endswith(".py") or normalized_path.endswith("__init__.py"):
        # __init__.py is a package, not a module with a stable import stem.
        return None
    return normalized_path[: -len(".py")].replace("/", ".")


def _has_static_import_evidence(test_file: Path, module: str) -> bool:
    """Whether the test file deterministically imports the changed module.

    Accepted absolute forms, checked on the AST without executing anything:
      import <module>                      import <module> as alias
      from <module> import <anything>      from <parent> import <stem> [as alias]

    Importing an ancestor package alone (e.g. ``import starlette``) is NOT
    evidence for a submodule, and relative imports are not resolved. A file
    that cannot be parsed provides no evidence at all.
    """
    try:
        tree = ast.parse(test_file.read_text(errors="replace"))
    except (OSError, SyntaxError, ValueError):
        return False
    parent, _, stem = module.rpartition(".")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name == module for alias in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            if node.level != 0:
                continue
            if node.module == module:
                return True
            if parent and node.module == parent and any(
                alias.name == stem for alias in node.names
            ):
                return True
    return False


def _test_targets(root: Path, changed_files: Iterable[str]) -> List[str]:
    """Select changed test files plus evidence-backed conventional mirrors.

    A source file contributes a pytest target only for a conventional mirror
    candidate that (a) exists in the discovered test-file set and (b) carries
    deterministic static import evidence that the test imports the changed
    module. Existence and stem similarity alone establish no relationship:
    without import evidence nothing is selected, nothing is guessed, and
    pytest does not run. Every candidate is judged independently; multiple
    deterministically-related candidates are all selected, never ranked.
    """
    known = set(_pytest_files(root))
    targets = set()
    for path in changed_files:
        normalized = str(path).replace("\\", "/")
        while normalized.startswith("./"):
            normalized = normalized[2:]
        if normalized in known:
            targets.add(normalized)
            continue
        module = _module_dotted_path(
            normalized[len("src/"):] if normalized.startswith("src/") else normalized
        )
        if module is None:
            continue
        for candidate in sorted(_conventional_test_candidates(normalized)):
            if candidate not in known:
                continue
            if _has_static_import_evidence(root / candidate, module):
                targets.add(candidate)
    return sorted(targets)


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


# Node-level pytest result extraction (requires -rA in the pytest command).
# The trailing " - reason" is stripped non-greedily: a parametrized id that
# itself contains " - " is truncated identically on both sides, so identities
# remain comparable; full fidelity is not required for base/target matching.
_PYTEST_NODE_LINE = re.compile(r"^(PASSED|FAILED|ERROR)\s+(.+?)(?:\s+-\s.*)?$")
_NODE_STATUS = {"PASSED": "passed", "FAILED": "failed", "ERROR": "error"}


def parse_pytest_node_results(output: str) -> Dict[str, str]:
    """Extract per-test results from pytest -rA short-summary lines.

    Only PASSED/FAILED/ERROR lines with a real node id (containing ``.py::``)
    are returned; skipped/xfailed markers and unparsable lines are ignored.
    Absence from the result map means the node's outcome could not be
    established and must be treated as unavailable, never guessed.
    """
    results: Dict[str, str] = {}
    for line in output.splitlines():
        line = line.strip()
        match = _PYTEST_NODE_LINE.match(line)
        if not match:
            continue
        node_id = match.group(2).strip()
        if ".py::" not in node_id:
            continue
        results[node_id] = _NODE_STATUS[match.group(1)]
    return results


# Signals that a pytest process did not really execute the selected tests:
# dependency/conftest import failures, collection problems, usage errors.
# Any of these must classify as infrastructure failure (unknown), never as
# test failure evidence.
_PYTEST_INFRA_MARKERS = (
    "ModuleNotFoundError",
    "ImportError while",
    "ConftestImportFailure",
    "INTERNALERROR",
    "collected 0 items",
    "no tests ran",
)


def _pytest_infra_reason(
    status: str, exit_code: Optional[int], output: str,
    node_results: Optional[Dict[str, str]],
) -> Optional[str]:
    if status == "TIMEOUT":
        return "timeout"
    if status == "ERROR":
        return "execution error"
    if exit_code in (2, 3, 4, 5):
        return f"pytest exit code {exit_code}"
    if not node_results:
        for marker in _PYTEST_INFRA_MARKERS:
            if marker in output:
                return f"infrastructure failure: {marker}"
    return None


def _behavioral_execution_provenance(
    *, command: Optional[List[str]], working_directory: Optional[str],
    revision: str, duration_ms: Optional[int],
    stdout: str, stderr: str,
) -> Dict[str, Any]:
    src_layout = bool(
        working_directory and (Path(working_directory) / "src").is_dir()
    )
    return {
        "command": list(command) if command else None,
        "working_directory": working_directory,
        "revision": revision,
        "src_layout_pythonpath": src_layout,
        "duration_ms": duration_ms,
        "stdout": stdout,
        "stderr": stderr,
    }


def behavioral_bundle_from_command_result(
    cmd: Optional[Dict[str, Any]],
    *,
    revision: str,
) -> Dict[str, Any]:
    """Build a behavioral side-bundle from a persisted pytest command result."""
    if not cmd:
        return {
            "status": "UNAVAILABLE",
            "reason": "no pytest command result was captured",
            "exit_code": None,
            "node_results": {},
            "missing_selected_tests": [],
            "execution": _behavioral_execution_provenance(
                command=None, working_directory=None, revision=revision,
                duration_ms=None, stdout="", stderr="",
            ),
        }
    stdout = cmd.get("stdout") or ""
    stderr = cmd.get("stderr") or ""
    node_results = cmd.get("node_results") or {}
    status = cmd.get("status")
    infra = _pytest_infra_reason(status, cmd.get("exit_code"), stdout + "\n" + stderr, node_results)
    if status == "NOT_EXECUTED":
        bundle_status = "UNAVAILABLE"
    elif infra:
        bundle_status = "INFRA_FAILURE"
    else:
        bundle_status = "EXECUTED"
    return {
        "status": bundle_status,
        "reason": cmd.get("reason") or infra,
        "exit_code": cmd.get("exit_code"),
        "node_results": dict(node_results),
        "missing_selected_tests": [],
        "execution": _behavioral_execution_provenance(
            command=cmd.get("command"),
            working_directory=cmd.get("working_directory"),
            revision=revision,
            duration_ms=cmd.get("duration_ms"),
            stdout=stdout,
            stderr=stderr,
        ),
    }


def run_selected_tests(
    repo_path: str,
    revision: str,
    pytest_targets: Sequence[str],
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    """Execute exactly the given test files against one checkout.

    Used for the BASE side of the behavioral comparison: the target list comes
    verbatim from the target-side deterministic selection. Test files that do
    not exist at this revision are reported as missing (-> unavailable), never
    skipped silently. Uses the same _run machinery, src-layout PYTHONPATH
    handling, and node-result capture as the target side, so the two sides
    differ only in the checked-out code.
    """
    root = Path(repo_path).resolve()
    targets = [str(t).replace("\\", "/") for t in pytest_targets]
    existing = [t for t in targets if (root / t).is_file()]
    missing = [t for t in targets if t not in existing]
    bundle: Dict[str, Any] = {
        "status": "UNAVAILABLE",
        "reason": None,
        "exit_code": None,
        "node_results": {},
        "missing_selected_tests": missing,
        "execution": _behavioral_execution_provenance(
            command=None, working_directory=str(root), revision=revision,
            duration_ms=None, stdout="", stderr="",
        ),
    }
    if not existing:
        bundle["reason"] = (
            "no selected test files exist at this revision" if missing
            else "no selected tests provided"
        )
        return bundle

    command = [sys.executable, "-m", "pytest", "--color=no", "--tb=short", "-rA"] + existing
    result = VerificationExecutor(timeout_seconds)._run(
        "pytest", command, root, revision,
        parser=_parse_pytest_counts, include_src=True, capture_node_results=True,
    )
    output = result.stdout + "\n" + result.stderr
    infra = _pytest_infra_reason(result.status, result.exit_code, output, result.node_results)
    bundle["status"] = "INFRA_FAILURE" if infra else "EXECUTED"
    bundle["reason"] = infra
    bundle["exit_code"] = result.exit_code
    bundle["node_results"] = dict(result.node_results or {})
    bundle["execution"].update({
        "command": list(result.command),
        "duration_ms": result.duration_ms,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "discovered_test_count": result.discovered_test_count,
        "executed_test_count": result.executed_test_count,
    })
    return bundle


def compare_behavioral_results(
    base_bundle: Dict[str, Any],
    target_bundle: Dict[str, Any],
    *,
    test_files: Sequence[str],
    changed_files: Sequence[str],
    changed_symbols: Sequence[str],
    selection_provenance: str,
) -> List[BehavioralTestComparison]:
    """Deterministic base-vs-target comparison of per-node pytest results.

    REGRESSION   only when the same node passed on base and failed on target.
    PRE_EXISTING both failed. CONSISTENT both passed (or both skipped).
    IMPROVED     base failed, target passed — never a regression.
    UNKNOWN      any unavailable element: infrastructure failure, timeout,
                 missing file at base, collection error, or a node whose
                 result could not be established on either side.
    """
    base_exec = base_bundle or {}
    target_exec = target_bundle or {}
    base_ok = base_exec.get("status") == "EXECUTED"
    target_ok = target_exec.get("status") == "EXECUTED"

    if not base_ok or not target_ok:
        return [BehavioralTestComparison(
            test_file="; ".join(test_files) or None,
            test_node_id=None,
            baseline_status="executed" if base_ok else "unavailable",
            target_status="executed" if target_ok else "unavailable",
            regression=None,
            comparison_status="UNKNOWN",
            changed_files=list(changed_files),
            changed_symbols=list(changed_symbols),
            selection_provenance=selection_provenance,
            baseline_execution=base_exec,
            target_execution=target_exec,
        )]

    base_nodes = base_exec.get("node_results") or {}
    target_nodes = target_exec.get("node_results") or {}
    comparisons: List[BehavioralTestComparison] = []
    for missing_file in base_exec.get("missing_selected_tests") or []:
        comparisons.append(BehavioralTestComparison(
            test_file=missing_file, test_node_id=None,
            baseline_status="unavailable", target_status="unavailable",
            regression=None, comparison_status="UNKNOWN",
            changed_files=list(changed_files),
            changed_symbols=list(changed_symbols),
            selection_provenance=selection_provenance,
            baseline_execution=base_exec, target_execution=target_exec,
        ))

    union = sorted(set(base_nodes) | set(target_nodes))
    if not union and (target_exec.get("exit_code") not in (0, None)
                      or base_exec.get("exit_code") not in (0, None)):
        # Executed but no per-node results could be established on a
        # non-clean run: refuse to guess (conservative unknown).
        comparisons.append(BehavioralTestComparison(
            test_file="; ".join(test_files) or None,
            test_node_id=None,
            baseline_status="unavailable", target_status="unavailable",
            regression=None, comparison_status="UNKNOWN",
            changed_files=list(changed_files),
            changed_symbols=list(changed_symbols),
            selection_provenance=selection_provenance,
            baseline_execution=base_exec, target_execution=target_exec,
        ))
        return comparisons

    for node in union:
        base_status = base_nodes.get(node) or "unavailable"
        target_status = target_nodes.get(node) or "unavailable"
        if "error" in (base_status, target_status):
            verdict = "UNKNOWN"
        elif "skipped" in (base_status, target_status):
            verdict = "CONSISTENT" if base_status == target_status else "UNKNOWN"
        elif "unavailable" in (base_status, target_status):
            verdict = "UNKNOWN"
        elif base_status == "passed" and target_status == "failed":
            verdict = "REGRESSION"
        elif base_status == "failed" and target_status == "failed":
            verdict = "PRE_EXISTING"
        elif base_status == "passed" and target_status == "passed":
            verdict = "CONSISTENT"
        else:
            verdict = "IMPROVED"  # base failed, target passed
        regression = (
            True if verdict == "REGRESSION"
            else False if verdict in ("CONSISTENT", "PRE_EXISTING", "IMPROVED")
            else None
        )
        comparisons.append(BehavioralTestComparison(
            test_file=node.split("::")[0],
            test_node_id=node,
            baseline_status=base_status,
            target_status=target_status,
            regression=regression,
            comparison_status=verdict,
            changed_files=list(changed_files),
            changed_symbols=list(changed_symbols),
            selection_provenance=selection_provenance,
            baseline_execution=base_exec,
            target_execution=target_exec,
        ))
    return comparisons


def _command_env(root: Path, *, include_src: bool) -> Dict[str, str]:
    """Subprocess-local environment for verification commands.

    Base is the inherited environment plus the determinism seed; nothing in
    os.environ is mutated. When ``include_src`` is set and the repository
    uses a conventional src layout (an existing ``<root>/src`` directory),
    that exact directory — resolved and absolute — is prepended to
    PYTHONPATH so pytest imports the cloned revision rather than any
    package installed in the host environment. Existing PYTHONPATH entries
    are preserved, never replaced, and no other directory is ever added.
    """
    env = {**os.environ, "PYTHONHASHSEED": "0"}
    if include_src:
        src = root / "src"
        if src.is_dir():
            existing = env.get("PYTHONPATH")
            resolved = str(src.resolve())
            env["PYTHONPATH"] = (
                resolved + os.pathsep + existing if existing else resolved
            )
    return env


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
        capture_node_results: bool = False,
    ) -> VerificationEvidence:
        root = Path(repo_path).resolve()
        changed_files = impact.changed_files
        results: List[VerificationCommandResult] = []

        pytest_files = _pytest_files(root)
        pytest_targets = _test_targets(root, changed_files)
        pytest_discovered = bool(pytest_files or _has_pytest_config(root))
        if pytest_discovered:
            pytest_command = [sys.executable, "-m", "pytest", "--color=no"] + pytest_targets
            if capture_node_results:
                # Additive output-only flags: per-node results for the
                # behavioral base-vs-target comparison. Exit codes, counts,
                # and all existing semantics are unchanged.
                pytest_command = pytest_command + ["--tb=short", "-rA"]
            if pytest_targets and importlib.util.find_spec("pytest") is not None:
                results.append(self._run(
                    "pytest", pytest_command, root, revision, parser=_parse_pytest_counts,
                    include_src=True, capture_node_results=capture_node_results,
                ))
            else:
                if pytest_targets:
                    # A deterministic target exists; pytest itself is missing.
                    reason = (
                        "pytest is unavailable in the current environment; "
                        "no installation attempted"
                    )
                elif pytest_files:
                    reason = "relevant_test_selection=unavailable"
                else:
                    reason = "pytest configuration found but no tests discovered"
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
                    reason=reason,
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
        include_src: bool = False,
        capture_node_results: bool = False,
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
                env=_command_env(root, include_src=include_src),
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
        node_results = (
            parse_pytest_node_results(completed.stdout + "\n" + completed.stderr)
            if capture_node_results
            else None
        )
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
            node_results=node_results,
        )