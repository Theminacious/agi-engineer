"""Safe, deterministic execution of repository verification commands."""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from app.models.change_impact import ChangeImpactReport, RiskLevel
from app.services.change_risk_engine import ChangeRiskAssessment
from app.services.finding_context import FindingContext
from app.services.verification_engine import (
    BehavioralTestComparison,
    TARGET_IDENTITY_DIRTY,
    TARGET_IDENTITY_MISMATCH,
    TARGET_IDENTITY_UNVERIFIABLE,
    TARGET_IDENTITY_VERIFIED,
    VerificationEvidence,
)


MAX_OUTPUT = 4000
DEFAULT_TIMEOUT_SECONDS = 120

_ENV_ALLOWLIST = frozenset(
    {
        "PATH",
        "HOME",
        "TMPDIR",
        "TMP",
        "TEMP",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "TZ",
        "TERM",
        "PYTHONPATH",
        "PYTHONDONTWRITEBYTECODE",
        "SYSTEMROOT",
        "COMSPEC",
        "PATHEXT",
    }
)
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
    node_events: Optional[Dict[str, Any]] = None

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
            "node_events": dict(self.node_events) if self.node_events is not None else None,
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
    """Dotted import path for a normalized repository-relative module path.

    A package ``__init__.py`` resolves to its package dotted path so that a
    changed package initializer has a deterministic module identity; a
    top-level ``__init__.py`` at the repository root has no package identity.
    """
    if not normalized_path.endswith(".py"):
        return None
    if normalized_path.endswith("__init__.py"):
        package = normalized_path[: -len("/__init__.py")] if "/" in normalized_path else ""
        return package.replace("/", ".") or None
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
    return sorted({record.test_file for record in _select_tests(root, changed_files)})


@dataclass(frozen=True)
class TestSelectionEvidence:
    test_file: str
    changed_file: str
    changed_module: Optional[str]
    evidence: str
    name_mirror: bool
    symbols: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_file": self.test_file,
            "changed_file": self.changed_file,
            "changed_module": self.changed_module,
            "evidence": self.evidence,
            "name_mirror": self.name_mirror,
            "symbols": list(self.symbols),
        }


def _normalize_repo_path(path: str) -> str:
    normalized = str(path).replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _changed_symbols_by_file(changed_symbols: Iterable[Any]) -> Dict[str, Tuple[str, ...]]:
    grouped: Dict[str, set] = {}
    for symbol in changed_symbols or ():
        file_path = getattr(symbol, "file_path", None)
        name = getattr(symbol, "name", None)
        if not file_path or not name:
            continue
        grouped.setdefault(_normalize_repo_path(file_path), set()).add(
            str(name).split(".")[-1]
        )
    return {path: tuple(sorted(names)) for path, names in grouped.items()}


def _referenced_symbols(tree: ast.AST, short_names: Sequence[str]) -> Tuple[str, ...]:
    if not short_names:
        return ()
    wanted = set(short_names)
    found: set = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in wanted:
            found.add(node.id)
        elif isinstance(node, ast.Attribute) and node.attr in wanted:
            found.add(node.attr)
    return tuple(sorted(found))


_EVIDENCE_RANK = {
    "CHANGED_TEST": 5,
    "DIRECT_IMPORT_AND_SYMBOL": 4,
    "DIRECT_IMPORT": 3,
    "REEXPORT_IMPORT_AND_SYMBOL": 2,
    "REEXPORT_IMPORT": 1,
}


def _package_init_for(normalized_path: str) -> List[Tuple[str, str]]:
    """Ancestor package initializers for a changed module, nearest package first.

    Each entry is ``(init_repo_path, package_dotted)``: ``init_repo_path`` keeps
    any ``src/`` prefix so it can be read from disk; ``package_dotted`` is
    src-stripped so it matches import-resolvable origins. A re-export is only
    ever matched by exact origin equality, so scanning ancestors resolves a
    single re-export hop (e.g. ``flask/__init__.py`` naming ``.json.provider``)
    without following import chains. A repository-root module has no package.
    """
    if not normalized_path.endswith(".py"):
        return []
    inits: List[Tuple[str, str]] = []
    parent = normalized_path.rpartition("/")[0]
    while parent:
        stripped = parent[len("src/"):] if parent.startswith("src/") else parent
        if not stripped:
            break
        inits.append((parent + "/__init__.py", stripped.replace("/", ".")))
        if "/" not in parent:
            break
        parent = parent.rpartition("/")[0]
    return inits


def _relative_base(package: str, level: int) -> Optional[str]:
    """Absolute package a level-``N`` relative import in ``package``'s __init__ targets."""
    if level < 1:
        return None
    parts = package.split(".")
    drop = level - 1
    if drop >= len(parts):
        return None
    kept = parts if drop == 0 else parts[: len(parts) - drop]
    return ".".join(kept) if kept else None


def _init_reexport_map(init_tree: ast.AST, package: str) -> Dict[str, Tuple[str, Optional[str]]]:
    """Map an exported name to ``(origin_submodule_dotted, underlying_symbol_or_None)``.

    Only relative re-exports whose absolute origin is safely resolvable are
    recorded, without executing anything:
      ``from .sub import Name [as A]``    -> A/Name : (package.sub, Name)
      ``from . import sub [as A]``        -> A/sub  : (package.sub, None)
    Star imports and locally-defined names carry no submodule origin.
    """
    mapping: Dict[str, Tuple[str, Optional[str]]] = {}
    for node in ast.walk(init_tree):
        if not isinstance(node, ast.ImportFrom) or node.level == 0:
            continue
        base = _relative_base(package, node.level)
        if base is None:
            continue
        if node.module:
            origin = base + "." + node.module
            for alias in node.names:
                if alias.name == "*":
                    continue
                mapping[alias.asname or alias.name] = (origin, alias.name)
        else:
            for alias in node.names:
                if alias.name == "*":
                    continue
                mapping[alias.asname or alias.name] = (base + "." + alias.name, None)
    return mapping


def _names_imported_from_package(test_tree: ast.AST, package: str) -> set:
    """Names bound by ``from <package> import <name>`` (absolute imports only)."""
    names: set = set()
    for node in ast.walk(test_tree):
        if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module == package:
            for alias in node.names:
                if alias.name != "*":
                    names.add(alias.name)
    return names


def _select_tests(
    root: Path,
    changed_files: Iterable[str],
    changed_symbols: Iterable[Any] = (),
) -> List[TestSelectionEvidence]:
    known = set(_pytest_files(root))
    symbols_by_file = _changed_symbols_by_file(changed_symbols)
    parse_cache: Dict[str, Optional[ast.AST]] = {}

    def _tree(candidate: str) -> Optional[ast.AST]:
        if candidate not in parse_cache:
            try:
                parse_cache[candidate] = ast.parse(
                    (root / candidate).read_text(errors="replace")
                )
            except (OSError, SyntaxError, ValueError):
                parse_cache[candidate] = None
        return parse_cache[candidate]

    selections: Dict[Tuple[str, str], TestSelectionEvidence] = {}

    def _offer(key: Tuple[str, str], record: TestSelectionEvidence) -> None:
        existing = selections.get(key)
        if existing is None or _EVIDENCE_RANK[record.evidence] > _EVIDENCE_RANK[existing.evidence]:
            selections[key] = record

    for path in changed_files:
        normalized = _normalize_repo_path(str(path))
        if normalized in known:
            _offer((normalized, normalized), TestSelectionEvidence(
                test_file=normalized, changed_file=normalized,
                changed_module=None, evidence="CHANGED_TEST", name_mirror=False,
            ))
            continue
        module = _module_dotted_path(
            normalized[len("src/"):] if normalized.startswith("src/") else normalized
        )
        if module is None:
            continue
        mirrors = _conventional_test_candidates(normalized)
        short_names = symbols_by_file.get(normalized, ())
        for candidate in sorted(known):
            if not _has_static_import_evidence(root / candidate, module):
                continue
            symbols: Tuple[str, ...] = ()
            if short_names:
                tree = _tree(candidate)
                if tree is not None:
                    symbols = _referenced_symbols(tree, short_names)
            evidence = "DIRECT_IMPORT_AND_SYMBOL" if symbols else "DIRECT_IMPORT"
            _offer((normalized, candidate), TestSelectionEvidence(
                test_file=candidate, changed_file=normalized,
                changed_module=module, evidence=evidence,
                name_mirror=candidate in mirrors, symbols=symbols,
            ))

        for init_repo_path, package in _package_init_for(normalized):
            init_tree = _tree(init_repo_path)
            if init_tree is None:
                continue
            changed_exports = {
                exported: symbol
                for exported, (origin, symbol) in _init_reexport_map(init_tree, package).items()
                if origin == module
            }
            if not changed_exports:
                continue
            for candidate in sorted(known):
                cand_tree = _tree(candidate)
                if cand_tree is None:
                    continue
                matched = _names_imported_from_package(cand_tree, package) & set(changed_exports)
                if not matched:
                    continue
                symbols = tuple(sorted({
                    changed_exports[name] for name in matched
                    if changed_exports[name] is not None and changed_exports[name] in short_names
                }))
                evidence = "REEXPORT_IMPORT_AND_SYMBOL" if symbols else "REEXPORT_IMPORT"
                _offer((normalized, candidate), TestSelectionEvidence(
                    test_file=candidate, changed_file=normalized,
                    changed_module=module, evidence=evidence,
                    name_mirror=candidate in mirrors, symbols=symbols,
                ))
    return [selections[key] for key in sorted(selections)]


def format_selection_provenance(records: Sequence[TestSelectionEvidence]) -> str:
    if not records:
        return "unavailable"
    payload = [record.to_dict() for record in records]
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


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


OUTCOME_STATUS_PASSED = "PASSED"
OUTCOME_STATUS_FAILED = "FAILED"
OUTCOME_STATUS_ERROR = "ERROR"
OUTCOME_STATUS_TIMEOUT = "TIMEOUT"
OUTCOME_STATUS_UNAVAILABLE = "UNAVAILABLE"

OUTCOME_SOURCE_PYTEST_NODE = "PYTEST_NODE_RESULT"
OUTCOME_SOURCE_PYTEST_TIMEOUT_PLUGIN = "PYTEST_TIMEOUT_PLUGIN"
OUTCOME_SOURCE_EXECUTION_BOUNDARY = "AGI_ENGINEER_EXECUTION_BOUNDARY"
OUTCOME_SOURCE_NONE = "NONE"

VERIFICATION_RESULT_PASSED = "passed"
VERIFICATION_RESULT_FAILED = "failed"
VERIFICATION_RESULT_UNAVAILABLE = "unavailable"

STATIC_RESULT_PASSED = "passed"
STATIC_RESULT_FAILED = "failed"
STATIC_RESULT_UNAVAILABLE = "unavailable"

RUFF_EXIT_VIOLATIONS_FOUND = 1

TARGET_STATUS_EXECUTION_TIMEOUT = "execution_timeout"
TARGET_STATUS_NOT_EXECUTED = "not_executed_after_timeout"

TIMEOUT_ATTRIBUTION_CONFIRMED = "NODE_TIMEOUT_CONFIRMED"
TIMEOUT_ATTRIBUTION_UNATTRIBUTED = "EXECUTION_TIMEOUT_UNATTRIBUTED"
TIMEOUT_ATTRIBUTION_NOT_EXECUTED = "NOT_EXECUTED_AFTER_TIMEOUT"
TIMEOUT_ATTRIBUTION_NORMAL = "NORMAL_NODE_RESULT"

NODE_EVENT_SOURCE = "PYTEST_NODE_LIFECYCLE_EVENTS"

_NODE_TRACKER_PLUGIN = "agi_node_tracker"
_NODE_TRACKER_DIR = str((Path(__file__).parent / "_pytest_support").resolve())
_NODE_EVENTS_ENV = "AGI_NODE_EVENTS"
_NODE_EVENT_OUTCOMES = {"passed": "passed", "failed": "failed", "error": "error"}

# Provenance of the per-node outcome map consumed by the behavioral
# comparison. Lifecycle events carry the full pytest node id exactly as
# reported and cannot collide; the -rA text summary can truncate ids at
# " - " and is only a conservative fallback.
NODE_RESULTS_SOURCE_LIFECYCLE = "PYTEST_NODE_LIFECYCLE_EVENTS"
NODE_RESULTS_SOURCE_TEXT_SUMMARY = "PYTEST_RA_SUMMARY_TEXT"
NODE_RESULTS_SOURCE_NONE = "NONE"


def _parse_node_events(text: str) -> Dict[str, Any]:
    """Reconstruct deterministic node lifecycle from tracker plugin events.

    ``started`` preserves execution order. ``active`` is every node that
    started but never finished — under sequential pytest execution the process
    boundary can leave at most one such node, which is the node that was
    running when the executor terminated the process. ``results`` holds only
    terminal PASSED/FAILED/ERROR outcomes, mirroring parse_pytest_node_results.
    """
    started: List[str] = []
    finished: set = set()
    results: Dict[str, str] = {}
    for raw in text.splitlines():
        parts = raw.split("\t")
        if len(parts) < 2:
            continue
        kind, node = parts[0], parts[1]
        if ".py::" not in node:
            continue
        if kind == "START":
            if node not in started:
                started.append(node)
        elif kind == "FINISH":
            finished.add(node)
        elif kind == "RESULT" and len(parts) >= 3:
            status = _NODE_EVENT_OUTCOMES.get(parts[2])
            if status:
                results[node] = status
    active = [node for node in started if node not in finished]
    return {
        "source": NODE_EVENT_SOURCE,
        "started": started,
        "finished": sorted(finished),
        "results": results,
        "active": active,
    }


def _authoritative_node_results(
    node_events: Optional[Dict[str, Any]],
    text_node_results: Optional[Dict[str, str]],
) -> Tuple[Dict[str, str], str]:
    """Select the authoritative per-node outcome map and its provenance.

    Lifecycle RESULT events (``node_events['results']``) are preferred: they
    key on the full pytest node id exactly as reported, so distinct
    parametrized ids containing ``" - "`` remain distinct and cannot overwrite
    one another. The truncatable ``-rA`` text summary is used only when
    lifecycle evidence is unavailable or malformed, and the returned source
    lets downstream evidence distinguish the two. Nodes that produced no
    terminal RESULT event are never fabricated.
    """
    if isinstance(node_events, dict):
        results = node_events.get("results")
        if isinstance(results, dict) and results:
            return dict(results), NODE_RESULTS_SOURCE_LIFECYCLE
    if text_node_results:
        return dict(text_node_results), NODE_RESULTS_SOURCE_TEXT_SUMMARY
    return {}, NODE_RESULTS_SOURCE_NONE


_PYTEST_TIMEOUT_PLUGIN_SIGNATURE = re.compile(
    r"\++\s*Timeout\s*\++|Failed:\s*Timeout\s*>|pytest[-_]timeout"
)
_TIMEOUT_BOUNDARY_SECONDS = re.compile(r"timeout after\s+(\d+)\s*s")


def _timeout_boundary_seconds(reason: Optional[str]) -> Optional[int]:
    if not reason:
        return None
    match = _TIMEOUT_BOUNDARY_SECONDS.search(reason)
    return int(match.group(1)) if match else None


def classify_execution_outcome(
    *,
    status: Optional[str],
    exit_code: Optional[int],
    output: str,
    node_results: Optional[Dict[str, str]],
    reason: Optional[str],
) -> Dict[str, Any]:
    """Classify how a pytest execution terminated and which mechanism produced it.

    The distinction the model preserves:

    * A per-node pytest result (PASSED/FAILED/ERROR) means pytest itself
      completed the node and reported a terminal outcome
      (``PYTEST_NODE_RESULT``).
    * A repository-configured pytest-timeout aborts within pytest and leaves a
      recognizable plugin signature (``PYTEST_TIMEOUT_PLUGIN``).
    * An execution that exceeded AGI Engineer's bounded execution boundary was
      terminated by the executor before pytest produced a terminal result
      (``AGI_ENGINEER_EXECUTION_BOUNDARY``). This is an infrastructure safety
      boundary, never a fabricated pytest node failure.
    """
    plugin_signal = bool(_PYTEST_TIMEOUT_PLUGIN_SIGNATURE.search(output or ""))
    has_terminal = bool(node_results)
    if status == "NOT_EXECUTED":
        return {
            "status": OUTCOME_STATUS_UNAVAILABLE,
            "source": OUTCOME_SOURCE_NONE,
            "pytest_produced_terminal_result": False,
            "executor_terminated_process": False,
            "timeout_boundary_seconds": None,
            "exit_code": None,
            "pytest_timeout_plugin_signal": plugin_signal,
        }
    if status == "TIMEOUT":
        return {
            "status": OUTCOME_STATUS_TIMEOUT,
            "source": OUTCOME_SOURCE_EXECUTION_BOUNDARY,
            "pytest_produced_terminal_result": has_terminal,
            "executor_terminated_process": True,
            "timeout_boundary_seconds": _timeout_boundary_seconds(reason),
            "exit_code": None,
            "pytest_timeout_plugin_signal": plugin_signal,
        }
    if status == "ERROR":
        return {
            "status": OUTCOME_STATUS_ERROR,
            "source": OUTCOME_SOURCE_NONE,
            "pytest_produced_terminal_result": has_terminal,
            "executor_terminated_process": False,
            "timeout_boundary_seconds": None,
            "exit_code": exit_code,
            "pytest_timeout_plugin_signal": plugin_signal,
        }
    infra = _pytest_infra_reason(status, exit_code, output, node_results)
    if infra:
        return {
            "status": OUTCOME_STATUS_ERROR,
            "source": OUTCOME_SOURCE_NONE,
            "pytest_produced_terminal_result": has_terminal,
            "executor_terminated_process": False,
            "timeout_boundary_seconds": None,
            "exit_code": exit_code,
            "pytest_timeout_plugin_signal": plugin_signal,
        }
    outcome_status = OUTCOME_STATUS_PASSED if exit_code == 0 else OUTCOME_STATUS_FAILED
    source = (
        OUTCOME_SOURCE_PYTEST_TIMEOUT_PLUGIN
        if plugin_signal and outcome_status == OUTCOME_STATUS_FAILED
        else OUTCOME_SOURCE_PYTEST_NODE
    )
    return {
        "status": outcome_status,
        "source": source,
        "pytest_produced_terminal_result": has_terminal,
        "executor_terminated_process": False,
        "timeout_boundary_seconds": None,
        "exit_code": exit_code,
        "pytest_timeout_plugin_signal": plugin_signal,
    }


def _bundle_status_for_outcome(outcome: Dict[str, Any], *, infra: Optional[str]) -> str:
    if outcome["status"] == OUTCOME_STATUS_UNAVAILABLE:
        return "UNAVAILABLE"
    if (
        outcome["status"] == OUTCOME_STATUS_TIMEOUT
        and outcome["source"] == OUTCOME_SOURCE_EXECUTION_BOUNDARY
    ):
        return "TIMED_OUT"
    if infra:
        return "INFRA_FAILURE"
    return "EXECUTED"


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
            "node_results_source": NODE_RESULTS_SOURCE_NONE,
            "node_events": None,
            "missing_selected_tests": [],
            "execution_outcome": classify_execution_outcome(
                status=None, exit_code=None, output="", node_results={},
                reason=None,
            ),
            "execution": _behavioral_execution_provenance(
                command=None, working_directory=None, revision=revision,
                duration_ms=None, stdout="", stderr="",
            ),
        }
    stdout = cmd.get("stdout") or ""
    stderr = cmd.get("stderr") or ""
    node_results, node_results_source = _authoritative_node_results(
        cmd.get("node_events"), cmd.get("node_results")
    )
    status = cmd.get("status")
    output = stdout + "\n" + stderr
    infra = _pytest_infra_reason(status, cmd.get("exit_code"), output, node_results)
    outcome = classify_execution_outcome(
        status=status, exit_code=cmd.get("exit_code"), output=output,
        node_results=node_results, reason=cmd.get("reason"),
    )
    bundle_status = _bundle_status_for_outcome(outcome, infra=infra)
    return {
        "status": bundle_status,
        "reason": cmd.get("reason") or infra,
        "exit_code": cmd.get("exit_code"),
        "node_results": dict(node_results),
        "node_results_source": node_results_source,
        "node_events": cmd.get("node_events"),
        "missing_selected_tests": [],
        "execution_outcome": outcome,
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
        "node_results_source": NODE_RESULTS_SOURCE_NONE,
        "node_events": None,
        "missing_selected_tests": missing,
        "execution_outcome": classify_execution_outcome(
            status="NOT_EXECUTED", exit_code=None, output="",
            node_results={}, reason=None,
        ),
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
    node_results, node_results_source = _authoritative_node_results(
        result.node_events, result.node_results
    )
    output = result.stdout + "\n" + result.stderr
    infra = _pytest_infra_reason(result.status, result.exit_code, output, node_results)
    outcome = classify_execution_outcome(
        status=result.status, exit_code=result.exit_code, output=output,
        node_results=node_results, reason=result.reason,
    )
    bundle["status"] = _bundle_status_for_outcome(outcome, infra=infra)
    bundle["reason"] = result.reason or infra
    bundle["exit_code"] = result.exit_code
    bundle["node_results"] = node_results
    bundle["node_results_source"] = node_results_source
    bundle["node_events"] = result.node_events
    bundle["execution_outcome"] = outcome
    bundle["execution"].update({
        "command": list(result.command),
        "duration_ms": result.duration_ms,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "discovered_test_count": result.discovered_test_count,
        "executed_test_count": result.executed_test_count,
    })
    return bundle


def _node_verdict(base_status: str, target_status: str) -> str:
    if "error" in (base_status, target_status):
        return "UNKNOWN"
    if "skipped" in (base_status, target_status):
        return "CONSISTENT" if base_status == target_status else "UNKNOWN"
    if "unavailable" in (base_status, target_status):
        return "UNKNOWN"
    if base_status == "passed" and target_status == "failed":
        return "REGRESSION"
    if base_status == "failed" and target_status == "failed":
        return "PRE_EXISTING"
    if base_status == "passed" and target_status == "passed":
        return "CONSISTENT"
    return "IMPROVED"


def _regression_flag(verdict: str) -> Optional[bool]:
    if verdict == "REGRESSION":
        return True
    if verdict in ("CONSISTENT", "PRE_EXISTING", "IMPROVED"):
        return False
    return None


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

    REGRESSION   the same node passed on base and failed on target, or passed
                 on base and was the node confirmed (by pytest node lifecycle
                 events) to be executing when AGI Engineer's execution boundary
                 terminated the process.
    PRE_EXISTING both failed. CONSISTENT both passed (or both skipped).
    IMPROVED     base failed, target passed — never a regression.
    UNKNOWN      any unavailable element: infrastructure failure, target error,
                 missing file at base, collection error, an unattributable
                 execution timeout, or a node with no evidence of execution
                 after the timeout point.

    An execution-boundary timeout is represented as the ``execution_timeout``
    (or ``not_executed_after_timeout``) target status carrying
    ``AGI_ENGINEER_EXECUTION_BOUNDARY`` provenance; it is never rewritten into a
    fabricated pytest ``failed`` node. A base-passing node is only called a
    timeout regression when node lifecycle events confirm it was the single
    active node at termination; nodes that completed keep their real results and
    nodes never reached remain UNKNOWN.
    """
    base_exec = base_bundle or {}
    target_exec = target_bundle or {}
    base_outcome = base_exec.get("execution_outcome")
    target_outcome = target_exec.get("execution_outcome")
    base_ok = base_exec.get("status") == "EXECUTED"
    target_ok = target_exec.get("status") == "EXECUTED"
    target_timed_out = (
        target_exec.get("status") == "TIMED_OUT"
        and (target_outcome or {}).get("source") == OUTCOME_SOURCE_EXECUTION_BOUNDARY
    )

    if not base_ok or not (target_ok or target_timed_out):
        return [BehavioralTestComparison(
            test_file="; ".join(test_files) or None,
            test_node_id=None,
            baseline_status="executed" if base_ok else "unavailable",
            target_status=(
                "executed" if target_ok
                else TARGET_STATUS_EXECUTION_TIMEOUT if target_timed_out
                else "unavailable"
            ),
            regression=None,
            comparison_status="UNKNOWN",
            changed_files=list(changed_files),
            changed_symbols=list(changed_symbols),
            selection_provenance=selection_provenance,
            baseline_execution=base_exec,
            target_execution=target_exec,
            baseline_outcome=base_outcome,
            target_outcome=target_outcome,
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
            baseline_outcome=base_outcome, target_outcome=target_outcome,
        ))

    if target_timed_out:
        events = target_exec.get("node_events") or {}
        started = list(events.get("started") or [])
        active = list(events.get("active") or [])
        confirmed_node = active[0] if len(active) == 1 else None
        have_events = bool(started)
        for node in sorted(base_nodes):
            base_status = base_nodes.get(node) or "unavailable"
            terminal_target = target_nodes.get(node)
            if terminal_target:
                target_status = terminal_target
                verdict = _node_verdict(base_status, target_status)
                attribution = TIMEOUT_ATTRIBUTION_NORMAL
                source = NODE_EVENT_SOURCE
            elif confirmed_node is not None and node == confirmed_node:
                target_status = TARGET_STATUS_EXECUTION_TIMEOUT
                verdict = "REGRESSION" if base_status == "passed" else "UNKNOWN"
                attribution = TIMEOUT_ATTRIBUTION_CONFIRMED
                source = NODE_EVENT_SOURCE
            elif node in started:
                target_status = TARGET_STATUS_EXECUTION_TIMEOUT
                verdict = "UNKNOWN"
                attribution = TIMEOUT_ATTRIBUTION_UNATTRIBUTED
                source = NODE_EVENT_SOURCE
            elif have_events:
                target_status = TARGET_STATUS_NOT_EXECUTED
                verdict = "UNKNOWN"
                attribution = TIMEOUT_ATTRIBUTION_NOT_EXECUTED
                source = NODE_EVENT_SOURCE
            else:
                target_status = TARGET_STATUS_EXECUTION_TIMEOUT
                verdict = "UNKNOWN"
                attribution = TIMEOUT_ATTRIBUTION_UNATTRIBUTED
                source = None
            comparisons.append(BehavioralTestComparison(
                test_file=node.split("::")[0],
                test_node_id=node,
                baseline_status=base_status,
                target_status=target_status,
                regression=_regression_flag(verdict),
                comparison_status=verdict,
                changed_files=list(changed_files),
                changed_symbols=list(changed_symbols),
                selection_provenance=selection_provenance,
                baseline_execution=base_exec,
                target_execution=target_exec,
                baseline_outcome=base_outcome,
                target_outcome=target_outcome,
                timeout_attribution=attribution,
                timeout_attribution_source=source,
            ))
        return comparisons

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
            baseline_outcome=base_outcome, target_outcome=target_outcome,
        ))
        return comparisons

    for node in union:
        base_status = base_nodes.get(node) or "unavailable"
        target_status = target_nodes.get(node) or "unavailable"
        verdict = _node_verdict(base_status, target_status)
        comparisons.append(BehavioralTestComparison(
            test_file=node.split("::")[0],
            test_node_id=node,
            baseline_status=base_status,
            target_status=target_status,
            regression=_regression_flag(verdict),
            comparison_status=verdict,
            changed_files=list(changed_files),
            changed_symbols=list(changed_symbols),
            selection_provenance=selection_provenance,
            baseline_execution=base_exec,
            target_execution=target_exec,
            baseline_outcome=base_outcome,
            target_outcome=target_outcome,
        ))
    return comparisons


def _command_env(
    root: Path, *, include_src: bool,
    extra_path: Optional[str] = None,
    extra_env: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """Subprocess-local environment for verification commands.

    Customer repository code (pytest, conftest.py, Ruff) runs in this
    environment, so it is built from an explicit allowlist of non-sensitive
    variables (``_ENV_ALLOWLIST``) rather than the inherited process
    environment. AGI Engineer's own secrets — GitHub App private key, OAuth
    tokens, JWT/webhook secrets, database and Redis URLs, AI API keys — live
    in os.environ but are never in the allowlist, so they are not visible to
    executed repository code. Nothing in os.environ is mutated.

    When ``include_src`` is set and the repository uses a conventional src
    layout (an existing ``<root>/src`` directory), that exact directory —
    resolved and absolute — is prepended to PYTHONPATH so pytest imports the
    cloned revision rather than any package installed in the host
    environment. Any allowlisted PYTHONPATH is preserved, never replaced.

    ``extra_path`` is appended (never prepended) to PYTHONPATH so AGI
    Engineer's own read-only pytest plugin is importable without shadowing
    any repository or src module. ``extra_env`` sets additional variables
    (e.g. the node-event sink path) local to this invocation only.
    """
    env = {
        name: value
        for name, value in os.environ.items()
        if name in _ENV_ALLOWLIST
    }
    env["PYTHONHASHSEED"] = "0"
    if include_src:
        src = root / "src"
        if src.is_dir():
            existing = env.get("PYTHONPATH")
            resolved = str(src.resolve())
            env["PYTHONPATH"] = (
                resolved + os.pathsep + existing if existing else resolved
            )
    if extra_path:
        existing = env.get("PYTHONPATH")
        env["PYTHONPATH"] = (
            existing + os.pathsep + extra_path if existing else extra_path
        )
    if extra_env:
        env.update(extra_env)
    return env


def _test_execution_result_for(result: "VerificationCommandResult") -> str:
    outcome = classify_execution_outcome(
        status=result.status,
        exit_code=result.exit_code,
        output=(result.stdout or "") + "\n" + (result.stderr or ""),
        node_results=result.node_results,
        reason=result.reason,
    )
    if outcome["status"] == OUTCOME_STATUS_PASSED:
        return VERIFICATION_RESULT_PASSED
    if outcome["status"] == OUTCOME_STATUS_FAILED:
        return VERIFICATION_RESULT_FAILED
    return VERIFICATION_RESULT_UNAVAILABLE


def _static_analysis_result_for(result: "VerificationCommandResult") -> str:
    if not result.executed:
        return STATIC_RESULT_UNAVAILABLE
    if result.status == "PASSED":
        return STATIC_RESULT_PASSED
    if result.status == "FAILED" and result.exit_code == RUFF_EXIT_VIOLATIONS_FOUND:
        return STATIC_RESULT_FAILED
    return STATIC_RESULT_UNAVAILABLE


TARGET_REVISION_MISMATCH = "TARGET_REVISION_MISMATCH"
TARGET_REVISION_UNVERIFIABLE = "TARGET_REVISION_UNVERIFIABLE"
TARGET_WORKTREE_DIRTY = "TARGET_WORKTREE_DIRTY"


def _verify_target_identity(root: Path, expected_target_sha: str) -> Tuple[str, Optional[str]]:
    """Prove the tree about to be executed IS the claimed target commit, clean.

    Returns ``(identity, reason)``. Only ``TARGET_IDENTITY_VERIFIED`` (with a
    ``None`` reason) permits trustworthy verification. Comparison is exact
    full-SHA equality — never a prefix. ``git status --porcelain=v1`` reports
    modified/staged/deleted tracked files and untracked non-ignored files while
    excluding git-ignored files, so a clean committed target tree is required
    but ignored artifacts do not count as dirty.
    """
    try:
        head = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, shell=False,
        )
    except OSError as exc:
        return TARGET_IDENTITY_UNVERIFIABLE, f"{TARGET_REVISION_UNVERIFIABLE}: {exc}"
    if head.returncode != 0 or not head.stdout.strip():
        return (
            TARGET_IDENTITY_UNVERIFIABLE,
            f"{TARGET_REVISION_UNVERIFIABLE}: git HEAD is unreadable",
        )
    actual = head.stdout.strip()
    if actual != expected_target_sha:
        return (
            TARGET_IDENTITY_MISMATCH,
            f"{TARGET_REVISION_MISMATCH}: expected {expected_target_sha}, HEAD is {actual}",
        )
    try:
        status = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain=v1"],
            capture_output=True, text=True, shell=False,
        )
    except OSError as exc:
        return TARGET_IDENTITY_UNVERIFIABLE, f"{TARGET_REVISION_UNVERIFIABLE}: {exc}"
    if status.returncode != 0:
        return (
            TARGET_IDENTITY_UNVERIFIABLE,
            f"{TARGET_REVISION_UNVERIFIABLE}: git status is unreadable",
        )
    if status.stdout.strip():
        return (
            TARGET_IDENTITY_DIRTY,
            f"{TARGET_WORKTREE_DIRTY}: target worktree has uncommitted changes",
        )
    return TARGET_IDENTITY_VERIFIED, None


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
        expected_target_sha: Optional[str] = None,
    ) -> VerificationEvidence:
        root = Path(repo_path).resolve()

        # Target-tree identity is the execution boundary: pytest/Ruff below run
        # against this tree, so unless it IS the claimed target commit and is
        # clean, no result produced here is trustworthy. Nothing mutates the
        # repository between this check and the subprocess launches.
        if expected_target_sha is not None:
            identity, identity_reason = _verify_target_identity(root, expected_target_sha)
            if identity != TARGET_IDENTITY_VERIFIED:
                return VerificationEvidence(
                    tests_discovered=_pytest_files(root) or None,
                    tests_executed=None,
                    test_execution_result=None,
                    static_analysis_executed=None,
                    static_analysis_result=None,
                    findings_after=contexts,
                    command_results=[],
                    relevant_test_selection="unavailable",
                    blocked_reason=identity_reason,
                    target_identity=identity,
                    target_identity_reason=identity_reason,
                )

        changed_files = impact.changed_files
        results: List[VerificationCommandResult] = []

        pytest_files = _pytest_files(root)
        selection = _select_tests(root, changed_files, impact.changed_symbols)
        pytest_targets = sorted({record.test_file for record in selection})
        selection_provenance = format_selection_provenance(selection)
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
            test_result = _test_execution_result_for(pytest_result)

        static_executed = ruff_result is not None and ruff_result.executed
        static_result = None
        if ruff_result is not None:
            static_result = _static_analysis_result_for(ruff_result)
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
            test_selection_provenance=selection_provenance if pytest_targets else None,
            target_identity=(
                TARGET_IDENTITY_VERIFIED if expected_target_sha is not None else None
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
        run_command = list(command)
        extra_path = extra_env = events_path = None
        if capture_node_results:
            fd, events_path = tempfile.mkstemp(prefix="agi_node_events_", suffix=".tsv")
            os.close(fd)
            run_command = run_command + ["-p", _NODE_TRACKER_PLUGIN]
            extra_path = _NODE_TRACKER_DIR
            extra_env = {_NODE_EVENTS_ENV: events_path}

        def _events() -> Optional[Dict[str, Any]]:
            if not events_path:
                return None
            try:
                text = Path(events_path).read_text(errors="replace")
            except OSError:
                text = ""
            return _parse_node_events(text)

        try:
            completed = subprocess.run(
                run_command,
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                shell=False,
                env=_command_env(
                    root, include_src=include_src,
                    extra_path=extra_path, extra_env=extra_env,
                ),
            )
            node_events_completed = _events()
        except subprocess.TimeoutExpired as exc:
            node_events = _events()
            timeout_results = dict((node_events or {}).get("results") or {}) if node_events else None
            return VerificationCommandResult(
                check=check,
                command=run_command,
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
                node_results=timeout_results,
                node_events=node_events,
            )
        except (OSError, ValueError) as exc:
            return VerificationCommandResult(
                check=check,
                command=run_command,
                revision=revision,
                working_directory=str(root),
                discovered=True,
                executed=True,
                status="ERROR",
                exit_code=None,
                duration_ms=int((time.monotonic() - started) * 1000),
                reason=str(exc),
                node_events=_events(),
            )
        finally:
            if events_path:
                try:
                    os.unlink(events_path)
                except OSError:
                    pass

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
            command=run_command,
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
            node_events=node_events_completed,
        )