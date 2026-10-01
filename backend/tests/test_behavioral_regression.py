"""Deterministic base-vs-target behavioral regression evidence."""

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from app.services.baseline_comparison import BaselineComparisonService
from app.services.verification_execution import (
    OUTCOME_SOURCE_EXECUTION_BOUNDARY,
    OUTCOME_SOURCE_PYTEST_NODE,
    OUTCOME_STATUS_FAILED,
    OUTCOME_STATUS_PASSED,
    TARGET_STATUS_EXECUTION_TIMEOUT,
    TARGET_STATUS_NOT_EXECUTED,
    _parse_node_events,
    compare_behavioral_results,
    parse_pytest_node_results,
    run_selected_tests,
)


def _git(repo: str, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", repo, *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def _init_repo(path: str) -> None:
    subprocess.run(["git", "init", "--quiet", "-b", "main", path], check=True)
    _git(path, "config", "user.email", "test@example.invalid")
    _git(path, "config", "user.name", "Behavioral Test")
    _git(path, "config", "commit.gpgsign", "false")


def _write(repo: str, rel_path: str, body: str) -> None:
    full = os.path.join(repo, rel_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as fh:
        fh.write(body)


def _commit(repo: str, message: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _exec(node_results, *, exit_code=0, missing=None, revision="r"):
    return {
        "status": "EXECUTED",
        "reason": None,
        "exit_code": exit_code,
        "node_results": dict(node_results),
        "missing_selected_tests": list(missing or []),
        "execution_outcome": {
            "status": OUTCOME_STATUS_PASSED if exit_code == 0 else OUTCOME_STATUS_FAILED,
            "source": OUTCOME_SOURCE_PYTEST_NODE,
            "pytest_produced_terminal_result": bool(node_results),
            "executor_terminated_process": False,
            "timeout_boundary_seconds": None,
            "exit_code": exit_code,
            "pytest_timeout_plugin_signal": False,
        },
        "execution": {
            "command": [sys.executable, "-m", "pytest"],
            "working_directory": "/repo",
            "revision": revision,
            "src_layout_pythonpath": False,
            "duration_ms": 1,
            "stdout": "",
            "stderr": "",
        },
    }


def _unavailable(reason="unavailable", *, status="UNAVAILABLE"):
    return {
        "status": status,
        "reason": reason,
        "exit_code": None,
        "node_results": {},
        "missing_selected_tests": [],
        "execution_outcome": {
            "status": "UNAVAILABLE",
            "source": "NONE",
            "pytest_produced_terminal_result": False,
            "executor_terminated_process": False,
            "timeout_boundary_seconds": None,
            "exit_code": None,
            "pytest_timeout_plugin_signal": False,
        },
        "execution": {
            "command": None,
            "working_directory": None,
            "revision": "r",
            "src_layout_pythonpath": False,
            "duration_ms": None,
            "stdout": "",
            "stderr": "",
        },
    }


def _events(started, *, finished=None, results=None):
    finished = list(finished or [])
    return {
        "source": "PYTEST_NODE_LIFECYCLE_EVENTS",
        "started": list(started),
        "finished": sorted(finished),
        "results": dict(results or {}),
        "active": [n for n in started if n not in finished],
    }


def _timed_out(node_results=None, *, node_events=None, boundary_seconds=150, revision="r"):
    if node_results is None and node_events is not None:
        node_results = dict(node_events.get("results") or {})
    return {
        "status": "TIMED_OUT",
        "reason": f"timeout after {boundary_seconds}s",
        "exit_code": None,
        "node_results": dict(node_results or {}),
        "node_events": node_events,
        "missing_selected_tests": [],
        "execution_outcome": {
            "status": "TIMEOUT",
            "source": OUTCOME_SOURCE_EXECUTION_BOUNDARY,
            "pytest_produced_terminal_result": bool(node_results),
            "executor_terminated_process": True,
            "timeout_boundary_seconds": boundary_seconds,
            "exit_code": None,
            "pytest_timeout_plugin_signal": False,
        },
        "execution": {
            "command": [sys.executable, "-m", "pytest"],
            "working_directory": "/repo",
            "revision": revision,
            "src_layout_pythonpath": False,
            "duration_ms": boundary_seconds * 1000,
            "stdout": "",
            "stderr": "",
        },
    }


def _compare(base, target, *, files=("tests/test_x.py",)):
    return compare_behavioral_results(
        base,
        target,
        test_files=list(files),
        changed_files=["x/mod.py"],
        changed_symbols=["x/mod.py::fn"],
        selection_provenance="deterministic_changed_test_files",
    )


NODE = "tests/test_x.py::test_fn"


class TestClassificationRules:
    def test_pass_to_fail_is_regression(self):
        result = _compare(
            _exec({NODE: "passed"}),
            _exec({NODE: "failed"}, exit_code=1),
        )
        assert len(result) == 1
        assert result[0].comparison_status == "REGRESSION"
        assert result[0].regression is True
        assert result[0].test_node_id == NODE

    def test_fail_to_fail_is_pre_existing(self):
        result = _compare(
            _exec({NODE: "failed"}, exit_code=1),
            _exec({NODE: "failed"}, exit_code=1),
        )
        assert result[0].comparison_status == "PRE_EXISTING"
        assert result[0].regression is False

    def test_pass_to_pass_is_consistent(self):
        result = _compare(_exec({NODE: "passed"}), _exec({NODE: "passed"}))
        assert result[0].comparison_status == "CONSISTENT"
        assert result[0].regression is False

    def test_fail_to_pass_is_improved_not_regression(self):
        result = _compare(
            _exec({NODE: "failed"}, exit_code=1),
            _exec({NODE: "passed"}),
        )
        assert result[0].comparison_status == "IMPROVED"
        assert result[0].regression is False


class TestUnavailability:
    def test_base_unavailable_target_fail_is_unknown(self):
        result = _compare(_unavailable(), _exec({NODE: "failed"}, exit_code=1))
        assert len(result) == 1
        assert result[0].comparison_status == "UNKNOWN"
        assert result[0].regression is None
        assert result[0].baseline_status == "unavailable"

    def test_base_fail_target_unavailable_is_unknown(self):
        result = _compare(_exec({NODE: "failed"}, exit_code=1), _unavailable())
        assert result[0].comparison_status == "UNKNOWN"
        assert result[0].regression is None
        assert result[0].target_status == "unavailable"

    def test_dependency_failure_is_unknown(self):
        infra = _unavailable(
            reason="infrastructure failure: ModuleNotFoundError",
            status="INFRA_FAILURE",
        )
        result = _compare(infra, _exec({NODE: "failed"}, exit_code=1))
        assert result[0].comparison_status == "UNKNOWN"
        assert result[0].regression is None

    def test_infra_timeout_without_boundary_provenance_is_unknown(self):
        timed_out = _unavailable(reason="timeout", status="INFRA_FAILURE")
        result = _compare(_exec({NODE: "passed"}), timed_out)
        assert result[0].comparison_status == "UNKNOWN"
        assert result[0].regression is None

    def test_missing_file_on_base_is_unknown(self):
        base = _exec({}, missing=["tests/test_x.py"])
        target = _exec({NODE: "failed"}, exit_code=1)
        result = _compare(base, target)
        statuses = {c.comparison_status for c in result}
        assert statuses == {"UNKNOWN"}
        assert not any(c.regression for c in result)

    def test_node_id_mismatch_is_unknown_each_side(self):
        base = _exec({"tests/test_x.py::test_a": "passed"})
        target = _exec({"tests/test_x.py::test_b": "failed"}, exit_code=1)
        result = _compare(base, target)
        assert {c.test_node_id for c in result} == {
            "tests/test_x.py::test_a",
            "tests/test_x.py::test_b",
        }
        assert all(c.comparison_status == "UNKNOWN" for c in result)
        assert not any(c.regression for c in result)


class TestNodeEventEvidence:
    def test_active_node_is_started_but_not_finished(self):
        events = _parse_node_events(
            "START\ttests/t.py::a\n"
            "RESULT\ttests/t.py::a\tpassed\n"
            "FINISH\ttests/t.py::a\n"
            "START\ttests/t.py::b\n"
        )
        assert events["started"] == ["tests/t.py::a", "tests/t.py::b"]
        assert events["finished"] == ["tests/t.py::a"]
        assert events["results"] == {"tests/t.py::a": "passed"}
        assert events["active"] == ["tests/t.py::b"]
        assert events["source"] == "PYTEST_NODE_LIFECYCLE_EVENTS"

    def test_non_node_and_skipped_lines_are_ignored(self):
        events = _parse_node_events(
            "START\tnot-a-node\n"
            "RESULT\ttests/t.py::a\tskipped\n"
            "START\ttests/t.py::a\n"
        )
        assert events["started"] == ["tests/t.py::a"]
        assert events["results"] == {}
        assert events["active"] == ["tests/t.py::a"]

    def test_no_active_node_when_killed_between_tests(self):
        events = _parse_node_events(
            "START\ttests/t.py::a\nFINISH\ttests/t.py::a\n"
        )
        assert events["active"] == []


class TestNodeParsing:
    def test_only_real_node_ids_are_parsed(self):
        output = (
            "PASSED tests/test_x.py::test_a\n"
            "FAILED tests/test_x.py::test_b - AssertionError\n"
            "ERROR tests/test_x.py::test_c\n"
            "PASSED not a node id\n"
            "SKIPPED tests/test_x.py::test_d\n"
        )
        assert parse_pytest_node_results(output) == {
            "tests/test_x.py::test_a": "passed",
            "tests/test_x.py::test_b": "failed",
            "tests/test_x.py::test_c": "error",
        }

    def test_error_node_forces_unknown(self):
        base = _exec({NODE: "passed"})
        target = _exec({NODE: "error"}, exit_code=1)
        result = _compare(base, target)
        assert result[0].comparison_status == "UNKNOWN"


class TestProvenance:
    def test_execution_provenance_is_attached(self):
        result = _compare(_exec({NODE: "passed"}), _exec({NODE: "failed"}, exit_code=1))
        payload = result[0].to_dict()
        assert payload["changed_files"] == ["x/mod.py"]
        assert payload["changed_symbols"] == ["x/mod.py::fn"]
        assert payload["selection_provenance"] == "deterministic_changed_test_files"
        assert payload["baseline_execution"]["execution"]["revision"] == "r"
        assert payload["target_execution"]["execution"]["command"]

    def test_outcome_provenance_is_attached(self):
        result = _compare(_exec({NODE: "passed"}), _exec({NODE: "failed"}, exit_code=1))
        payload = result[0].to_dict()
        assert payload["baseline_outcome"]["source"] == OUTCOME_SOURCE_PYTEST_NODE
        assert payload["baseline_outcome"]["status"] == OUTCOME_STATUS_PASSED
        assert payload["target_outcome"]["status"] == OUTCOME_STATUS_FAILED


class TestExecutionBoundaryTimeout:
    def test_confirmed_active_node_pass_is_regression(self):
        target = _timed_out(node_events=_events([NODE]))
        result = _compare(_exec({NODE: "passed"}), target)
        assert len(result) == 1
        assert result[0].comparison_status == "REGRESSION"
        assert result[0].regression is True
        assert result[0].baseline_status == "passed"
        assert result[0].target_status == TARGET_STATUS_EXECUTION_TIMEOUT
        assert result[0].timeout_attribution == "NODE_TIMEOUT_CONFIRMED"
        assert result[0].timeout_attribution_source == "PYTEST_NODE_LIFECYCLE_EVENTS"

    def test_confirmed_active_node_never_fabricates_failed(self):
        target = _timed_out(node_events=_events([NODE]))
        result = _compare(_exec({NODE: "passed"}), target)
        assert all(c.target_status != "failed" for c in result)

    def test_confirmed_provenance_records_boundary(self):
        target = _timed_out(node_events=_events([NODE]), boundary_seconds=150)
        payload = _compare(_exec({NODE: "passed"}), target)[0].to_dict()
        assert payload["target_outcome"]["status"] == "TIMEOUT"
        assert payload["target_outcome"]["source"] == OUTCOME_SOURCE_EXECUTION_BOUNDARY
        assert payload["target_outcome"]["executor_terminated_process"] is True
        assert payload["target_outcome"]["timeout_boundary_seconds"] == 150

    def test_unattributed_timeout_pass_is_unknown(self):
        target = _timed_out(node_events=None)
        result = _compare(_exec({NODE: "passed"}), target)
        assert result[0].comparison_status == "UNKNOWN"
        assert result[0].regression is None
        assert result[0].timeout_attribution == "EXECUTION_TIMEOUT_UNATTRIBUTED"

    def test_tests_after_timeout_are_not_regressions(self):
        base = _exec({
            "tests/test_x.py::test_a": "passed",
            "tests/test_x.py::test_b": "passed",
            "tests/test_x.py::test_c": "passed",
            "tests/test_x.py::test_d": "passed",
        })
        target = _timed_out(node_events=_events(
            ["tests/test_x.py::test_a", "tests/test_x.py::test_b", "tests/test_x.py::test_c"],
            finished=["tests/test_x.py::test_a", "tests/test_x.py::test_b"],
            results={"tests/test_x.py::test_a": "passed", "tests/test_x.py::test_b": "passed"},
        ))
        by_node = {c.test_node_id: c for c in _compare(base, target)}
        assert by_node["tests/test_x.py::test_a"].comparison_status == "CONSISTENT"
        assert by_node["tests/test_x.py::test_b"].comparison_status == "CONSISTENT"
        assert by_node["tests/test_x.py::test_c"].comparison_status == "REGRESSION"
        assert by_node["tests/test_x.py::test_c"].timeout_attribution == "NODE_TIMEOUT_CONFIRMED"
        d = by_node["tests/test_x.py::test_d"]
        assert d.comparison_status == "UNKNOWN"
        assert d.regression is None
        assert d.target_status == TARGET_STATUS_NOT_EXECUTED
        assert d.timeout_attribution == "NOT_EXECUTED_AFTER_TIMEOUT"

    def test_completed_nodes_retain_real_results(self):
        base = _exec({
            "tests/test_x.py::test_a": "passed",
            "tests/test_x.py::test_b": "passed",
        })
        target = _timed_out(
            node_results={"tests/test_x.py::test_a": "failed"},
            node_events=_events(
                ["tests/test_x.py::test_a", "tests/test_x.py::test_b"],
                finished=["tests/test_x.py::test_a"],
                results={"tests/test_x.py::test_a": "failed"},
            ),
        )
        by_node = {c.test_node_id: c for c in _compare(base, target)}
        assert by_node["tests/test_x.py::test_a"].comparison_status == "REGRESSION"
        assert by_node["tests/test_x.py::test_a"].target_status == "failed"
        assert by_node["tests/test_x.py::test_a"].timeout_attribution == "NORMAL_NODE_RESULT"
        assert by_node["tests/test_x.py::test_b"].comparison_status == "REGRESSION"
        assert by_node["tests/test_x.py::test_b"].target_status == TARGET_STATUS_EXECUTION_TIMEOUT

    def test_base_fail_confirmed_timeout_is_unknown(self):
        target = _timed_out(node_events=_events([NODE]))
        result = _compare(_exec({NODE: "failed"}, exit_code=1), target)
        assert result[0].comparison_status == "UNKNOWN"
        assert result[0].regression is None
        assert result[0].target_status == TARGET_STATUS_EXECUTION_TIMEOUT

    def test_multiple_active_nodes_are_unattributed(self):
        base = _exec({
            "tests/test_x.py::test_a": "passed",
            "tests/test_x.py::test_b": "passed",
        })
        target = _timed_out(node_events=_events(
            ["tests/test_x.py::test_a", "tests/test_x.py::test_b"],
        ))
        for c in _compare(base, target):
            assert c.comparison_status == "UNKNOWN"
            assert c.regression is None
            assert c.timeout_attribution == "EXECUTION_TIMEOUT_UNATTRIBUTED"

    def test_base_unavailable_then_boundary_timeout_is_unknown(self):
        result = _compare(_unavailable(), _timed_out(node_events=_events([NODE])))
        assert len(result) == 1
        assert result[0].comparison_status == "UNKNOWN"
        assert result[0].regression is None


PASSING_TEST = (
    "from pkg import mod\n\n"
    "def test_fn():\n"
    "    assert mod.value() == 1\n"
)
FAILING_MODULE = "def value():\n    return 2\n"
PASSING_MODULE = "def value():\n    return 1\n"


def _package_repo(root: str, module_body: str, *, src_layout=False) -> None:
    prefix = "src/" if src_layout else ""
    _init_repo(root)
    _write(root, f"{prefix}pkg/__init__.py", "")
    _write(root, f"{prefix}pkg/mod.py", module_body)
    _write(root, "tests/__init__.py", "")
    _write(root, "tests/test_mod.py", PASSING_TEST.replace("tests/test_x.py", ""))


class TestBaseWorktreeExecution:
    def test_end_to_end_regression_via_worktree(self, tmp_path):
        repo = str(tmp_path / "repo")
        _init_repo(repo)
        _write(repo, "pkg/__init__.py", "")
        _write(repo, "pkg/mod.py", PASSING_MODULE)
        _write(repo, "tests/test_mod.py", "from pkg import mod\n\ndef test_fn():\n    assert mod.value() == 1\n")
        base_sha = _commit(repo, "base: passing")

        _write(repo, "pkg/mod.py", FAILING_MODULE)
        _commit(repo, "target: regression")

        targets = ["tests/test_mod.py"]
        target_bundle = run_selected_tests(repo, "target", targets)
        base_bundle = BaselineComparisonService().compare_behavior(
            repo_path=repo, base_revision=base_sha, pytest_targets=targets,
        )
        assert base_bundle["status"] == "EXECUTED"
        assert target_bundle["status"] == "EXECUTED"

        result = compare_behavioral_results(
            base_bundle, target_bundle,
            test_files=targets, changed_files=["pkg/mod.py"],
            changed_symbols=["pkg/mod.py::value"],
            selection_provenance="deterministic_changed_test_files",
        )
        regressions = [c for c in result if c.comparison_status == "REGRESSION"]
        assert len(regressions) == 1
        assert regressions[0].regression is True
        assert regressions[0].test_node_id == "tests/test_mod.py::test_fn"

    def test_src_layout_base_worktree_executes_checkout(self, tmp_path):
        repo = str(tmp_path / "repo")
        _init_repo(repo)
        _write(repo, "src/pkg/__init__.py", "")
        _write(repo, "src/pkg/mod.py", PASSING_MODULE)
        _write(repo, "tests/test_mod.py", "from pkg import mod\n\ndef test_fn():\n    assert mod.value() == 1\n")
        base_sha = _commit(repo, "base: src-layout passing")

        base_bundle = BaselineComparisonService().compare_behavior(
            repo_path=repo, base_revision=base_sha,
            pytest_targets=["tests/test_mod.py"],
        )
        assert base_bundle["status"] == "EXECUTED"
        assert base_bundle["node_results"] == {"tests/test_mod.py::test_fn": "passed"}
        assert base_bundle["execution"]["src_layout_pythonpath"] is True

    def test_test_absent_on_base_is_unavailable(self, tmp_path):
        repo = str(tmp_path / "repo")
        _init_repo(repo)
        _write(repo, "pkg/__init__.py", "")
        _write(repo, "pkg/mod.py", PASSING_MODULE)
        base_sha = _commit(repo, "base: no test yet")

        _write(repo, "tests/test_mod.py", "def test_fn():\n    assert True\n")
        _commit(repo, "target: adds test")

        base_bundle = BaselineComparisonService().compare_behavior(
            repo_path=repo, base_revision=base_sha,
            pytest_targets=["tests/test_mod.py"],
        )
        assert base_bundle["status"] == "UNAVAILABLE"
        assert base_bundle["missing_selected_tests"] == ["tests/test_mod.py"]

    def test_active_worktree_remains_untouched(self, tmp_path):
        repo = str(tmp_path / "repo")
        _init_repo(repo)
        _write(repo, "pkg/__init__.py", "")
        _write(repo, "pkg/mod.py", PASSING_MODULE)
        _write(repo, "tests/test_mod.py", "from pkg import mod\n\ndef test_fn():\n    assert mod.value() == 1\n")
        base_sha = _commit(repo, "base")

        _write(repo, "pkg/mod.py", FAILING_MODULE)
        before = Path(repo, "pkg/mod.py").read_text()

        BaselineComparisonService().compare_behavior(
            repo_path=repo, base_revision=base_sha,
            pytest_targets=["tests/test_mod.py"],
        )
        assert Path(repo, "pkg/mod.py").read_text() == before
        worktrees = _git(repo, "worktree", "list")
        assert worktrees.count("\n") == 0

    def test_worktree_cleanup_on_exception(self, tmp_path):
        repo = str(tmp_path / "repo")
        _init_repo(repo)
        _write(repo, "tests/test_mod.py", "def test_fn():\n    assert True\n")
        base_sha = _commit(repo, "base")

        with patch(
            "app.services.verification_execution.run_selected_tests",
            side_effect=RuntimeError("boom"),
        ):
            bundle = BaselineComparisonService().compare_behavior(
                repo_path=repo, base_revision=base_sha,
                pytest_targets=["tests/test_mod.py"],
            )
        assert bundle["status"] == "UNAVAILABLE"
        assert bundle["reason"] == "boom"
        worktrees = _git(repo, "worktree", "list")
        assert worktrees.count("\n") == 0

    def test_missing_base_revision_is_unavailable(self, tmp_path):
        repo = str(tmp_path / "repo")
        _init_repo(repo)
        _write(repo, "tests/test_mod.py", "def test_fn():\n    assert True\n")
        _commit(repo, "base")
        bundle = BaselineComparisonService().compare_behavior(
            repo_path=repo, base_revision=None,
            pytest_targets=["tests/test_mod.py"],
        )
        assert bundle["status"] == "UNAVAILABLE"
        assert bundle["reason"] == "base revision unavailable"


class TestExecutionBoundaryIntegration:
    def test_base_passes_target_hangs_boundary_terminates(self, tmp_path):
        repo = str(tmp_path / "repo")
        _init_repo(repo)
        _write(repo, "tests/test_mod.py", "def test_fn():\n    assert True\n")
        base_sha = _commit(repo, "base: passing")

        _write(
            repo, "tests/test_mod.py",
            "import time\n\ndef test_fn():\n    time.sleep(3600)\n",
        )
        _commit(repo, "target: non-terminating")

        targets = ["tests/test_mod.py"]
        target_bundle = run_selected_tests(repo, "target", targets, timeout_seconds=5)
        base_bundle = BaselineComparisonService().compare_behavior(
            repo_path=repo, base_revision=base_sha, pytest_targets=targets,
        )

        assert base_bundle["status"] == "EXECUTED"
        assert base_bundle["node_results"] == {"tests/test_mod.py::test_fn": "passed"}
        assert base_bundle["execution_outcome"]["status"] == OUTCOME_STATUS_PASSED

        assert target_bundle["status"] == "TIMED_OUT"
        assert target_bundle["execution_outcome"]["status"] == "TIMEOUT"
        assert (
            target_bundle["execution_outcome"]["source"]
            == OUTCOME_SOURCE_EXECUTION_BOUNDARY
        )
        assert target_bundle["execution_outcome"]["executor_terminated_process"] is True
        assert "failed" not in set(target_bundle["node_results"].values())
        assert target_bundle["node_events"]["active"] == ["tests/test_mod.py::test_fn"]

        result = compare_behavioral_results(
            base_bundle, target_bundle,
            test_files=targets, changed_files=["tests/test_mod.py"],
            changed_symbols=["tests/test_mod.py::test_fn"],
            selection_provenance="deterministic_changed_test_files",
        )
        assert len(result) == 1
        assert result[0].comparison_status == "REGRESSION"
        assert result[0].regression is True
        assert result[0].baseline_status == "passed"
        assert result[0].target_status == TARGET_STATUS_EXECUTION_TIMEOUT
        assert result[0].timeout_attribution == "NODE_TIMEOUT_CONFIRMED"
        assert result[0].target_outcome["source"] == OUTCOME_SOURCE_EXECUTION_BOUNDARY

    def test_only_active_node_is_attributed_later_tests_not_executed(self, tmp_path):
        repo = str(tmp_path / "repo")
        _init_repo(repo)
        _write(
            repo, "tests/test_mod.py",
            "def test_a():\n    assert True\n\n"
            "def test_b():\n    assert True\n\n"
            "def test_c():\n    assert True\n\n"
            "def test_d():\n    assert True\n",
        )
        base_sha = _commit(repo, "base: all pass")

        _write(
            repo, "tests/test_mod.py",
            "import time\n\n"
            "def test_a():\n    assert True\n\n"
            "def test_b():\n    assert True\n\n"
            "def test_c():\n    time.sleep(3600)\n\n"
            "def test_d():\n    assert True\n",
        )
        _commit(repo, "target: test_c hangs")

        targets = ["tests/test_mod.py"]
        target_bundle = run_selected_tests(repo, "target", targets, timeout_seconds=6)
        base_bundle = BaselineComparisonService().compare_behavior(
            repo_path=repo, base_revision=base_sha, pytest_targets=targets,
        )
        assert base_bundle["status"] == "EXECUTED"
        assert target_bundle["status"] == "TIMED_OUT"
        assert target_bundle["node_events"]["active"] == ["tests/test_mod.py::test_c"]

        by_node = {
            c.test_node_id: c for c in compare_behavioral_results(
                base_bundle, target_bundle,
                test_files=targets, changed_files=["tests/test_mod.py"],
                changed_symbols=["tests/test_mod.py::test_c"],
                selection_provenance="deterministic_changed_test_files",
            )
        }
        assert by_node["tests/test_mod.py::test_a"].comparison_status == "CONSISTENT"
        assert by_node["tests/test_mod.py::test_b"].comparison_status == "CONSISTENT"
        assert by_node["tests/test_mod.py::test_c"].comparison_status == "REGRESSION"
        assert by_node["tests/test_mod.py::test_c"].timeout_attribution == "NODE_TIMEOUT_CONFIRMED"
        assert by_node["tests/test_mod.py::test_d"].comparison_status == "UNKNOWN"
        assert by_node["tests/test_mod.py::test_d"].regression is None
        assert by_node["tests/test_mod.py::test_d"].target_status == TARGET_STATUS_NOT_EXECUTED
        regressions = [c for c in by_node.values() if c.regression]
        assert [c.test_node_id for c in regressions] == ["tests/test_mod.py::test_c"]
