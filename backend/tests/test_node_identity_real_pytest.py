"""H1/H2 end-to-end: real pytest + agi_node_tracker prove lossless node identity.

These tests run actual pytest subprocesses through the real AGI Engineer
execution path (run_selected_tests -> _run -> agi_node_tracker -> node_events
-> _authoritative_node_results -> behavioral bundle). They are the integration
counterpart to the synthetic-dictionary unit tests and deliberately avoid
re-covering helper logic already unit-tested.
"""

import os
import subprocess

from app.services.baseline_comparison import BaselineComparisonService
from app.services.verification_execution import (
    NODE_RESULTS_SOURCE_LIFECYCLE,
    NODE_RESULTS_SOURCE_TEXT_SUMMARY,
    compare_behavioral_results,
    parse_pytest_node_results,
    run_selected_tests,
)


NODE_X = "tests/test_mod.py::test_fn[a - x]"
NODE_Y = "tests/test_mod.py::test_fn[a - y]"
TARGETS = ["tests/test_mod.py"]

_BASE_BODY = (
    "import pytest\n\n"
    '@pytest.mark.parametrize("val", ["a - x", "a - y"])\n'
    "def test_fn(val):\n"
    "    assert True\n"
)
# Target: the "a - x" variant passes, the "a - y" variant fails.
_TARGET_BODY = (
    "import pytest\n\n"
    '@pytest.mark.parametrize("val", ["a - x", "a - y"])\n'
    "def test_fn(val):\n"
    "    assert val == \"a - x\"\n"
)


def _git(repo, *args):
    return subprocess.run(
        ["git", "-C", repo, *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def _init_repo(repo):
    subprocess.run(["git", "init", "--quiet", "-b", "main", repo], check=True)
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Node Identity Test")
    _git(repo, "config", "commit.gpgsign", "false")


def _write(repo, rel, body):
    full = os.path.join(repo, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as fh:
        fh.write(body)


def _commit(repo, message):
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _project(tmp_path, body):
    repo = str(tmp_path / "repo")
    os.makedirs(repo, exist_ok=True)
    _write(repo, "tests/test_mod.py", body)
    return repo


# 1. REAL PARAMETRIZED NODE ID -------------------------------------------------

def test_real_parametrized_node_id_is_lossless(tmp_path):
    repo = _project(tmp_path, _BASE_BODY)
    bundle = run_selected_tests(repo, "target", TARGETS)

    assert bundle["status"] == "EXECUTED"
    stdout = bundle["execution"]["stdout"]
    # pytest itself emitted the full parametrized ids in its -rA summary.
    assert "test_fn[a - x]" in stdout
    assert "test_fn[a - y]" in stdout
    # The lifecycle tracker captured the complete ids.
    assert set(bundle["node_events"]["results"]) == {NODE_X, NODE_Y}
    # Authoritative provenance is the lossless lifecycle source.
    assert bundle["node_results_source"] == NODE_RESULTS_SOURCE_LIFECYCLE
    # Final node_results retains complete parametrized ids, un-truncated.
    assert set(bundle["node_results"]) == {NODE_X, NODE_Y}
    assert all(" - " in nid for nid in bundle["node_results"])


# 2. COLLISION CASE ------------------------------------------------------------

def test_real_colliding_ids_stay_independent(tmp_path):
    repo = _project(tmp_path, _TARGET_BODY)
    bundle = run_selected_tests(repo, "target", TARGETS)

    assert bundle["node_results_source"] == NODE_RESULTS_SOURCE_LIFECYCLE
    # Independent, distinct outcomes for the two variants.
    assert bundle["node_results"] == {NODE_X: "passed", NODE_Y: "failed"}

    # Prove the premise on the REAL pytest output: the -rA text parser
    # collapses both dashed ids onto one truncated key.
    text = parse_pytest_node_results(bundle["execution"]["stdout"])
    assert len(text) < 2
    assert NODE_X not in text or NODE_Y not in text


# 3. REGRESSION SAFETY ---------------------------------------------------------

def test_real_regression_not_hidden_by_collision(tmp_path):
    repo = str(tmp_path / "repo")
    _init_repo(repo)
    _write(repo, "tests/test_mod.py", _BASE_BODY)
    base_sha = _commit(repo, "base: both variants pass")

    _write(repo, "tests/test_mod.py", _TARGET_BODY)
    _commit(repo, "target: a - y variant fails")

    target_bundle = run_selected_tests(repo, "target", TARGETS)
    base_bundle = BaselineComparisonService().compare_behavior(
        repo_path=repo, base_revision=base_sha, pytest_targets=TARGETS
    )
    assert base_bundle["status"] == "EXECUTED"
    assert target_bundle["status"] == "EXECUTED"
    assert base_bundle["node_results"] == {NODE_X: "passed", NODE_Y: "passed"}

    by_node = {
        c.test_node_id: c for c in compare_behavioral_results(
            base_bundle, target_bundle,
            test_files=TARGETS, changed_files=["tests/test_mod.py"],
            changed_symbols=["tests/test_mod.py::test_fn"],
            selection_provenance="deterministic_changed_test_files",
        )
    }
    assert by_node[NODE_X].comparison_status == "CONSISTENT"
    assert by_node[NODE_X].regression is False
    assert by_node[NODE_Y].comparison_status == "REGRESSION"
    assert by_node[NODE_Y].regression is True
    regressions = [nid for nid, c in by_node.items() if c.regression]
    assert regressions == [NODE_Y]


# 4. FALLBACK SAFETY -----------------------------------------------------------

def test_real_output_without_lifecycle_falls_back_to_text_summary(tmp_path):
    from app.services.verification_execution import behavioral_bundle_from_command_result

    repo = _project(tmp_path, _TARGET_BODY)
    live = run_selected_tests(repo, "target", TARGETS)
    real_stdout = live["execution"]["stdout"]

    # Same real pytest output, but the lifecycle tracker evidence is absent.
    cmd = {
        "check": "pytest",
        "command": live["execution"]["command"],
        "revision": "target",
        "working_directory": repo,
        "status": "FAILED",
        "exit_code": live["exit_code"],
        "duration_ms": 1,
        "stdout": real_stdout,
        "stderr": "",
        "node_results": parse_pytest_node_results(real_stdout),
        "node_events": None,
    }
    bundle = behavioral_bundle_from_command_result(cmd, revision="target")
    assert bundle["node_results_source"] == NODE_RESULTS_SOURCE_TEXT_SUMMARY
    # No lifecycle claim; only the weaker (truncatable) text evidence remains.
    assert bundle["node_results"] == parse_pytest_node_results(real_stdout)
