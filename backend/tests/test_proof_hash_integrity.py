"""Deterministic proof-hash integrity: volatile evidence must not leak in."""

import os
import subprocess
import sys

from app.models.change_impact import ChangeImpactReport, ChangedSymbol, Confidence, RiskLevel
from app.services.change_risk_engine import ChangeRiskAssessment
from app.services.verification_engine import (
    PROOF_HASH_SCHEMA,
    PROOF_HASH_VERSION,
    BehavioralTestComparison,
    VerificationEngine,
    VerificationEvidence,
    _canonicalize_for_hash,
)


NODE = "service.py::handle"


def _impact():
    return ChangeImpactReport(
        repository="owner/repo",
        base_revision="base",
        target_revision="target",
        changed_files=["service.py"],
        changed_symbols=[
            ChangedSymbol(
                node_id=NODE,
                node_type="function",
                file_path="service.py",
                name="handle",
                change_kind="modified",
            )
        ],
        directly_affected_symbols=[NODE],
        confidence=Confidence.HIGH,
    ).finalize()


def _risk():
    return ChangeRiskAssessment(risk_level=RiskLevel.LOW, score=20, confidence="high").finalize()


def _command_result(
    *,
    interpreter="/opt/venv-a/bin/python",
    working_directory="/tmp/agi-verification-baseline-aaaa/repo",
    duration_ms=1234,
    stdout="collected 1 item\ntests/test_mod.py::test_fn PASSED\n",
    stderr="",
    node_results=None,
    exit_code=0,
    status="PASSED",
):
    return {
        "check": "pytest",
        "command": [interpreter, "-m", "pytest", "--color=no", "tests/test_mod.py", "-rA"],
        "revision": "target",
        "working_directory": working_directory,
        "discovered": True,
        "executed": True,
        "status": status,
        "exit_code": exit_code,
        "duration_ms": duration_ms,
        "stdout": stdout,
        "stderr": stderr,
        "discovered_test_count": 1,
        "executed_test_count": 1,
        "reason": None,
        "node_results": dict(node_results or {"tests/test_mod.py::test_fn": "passed"}),
        "node_events": {
            "source": "PYTEST_NODE_LIFECYCLE_EVENTS",
            "started": ["tests/test_mod.py::test_fn"],
            "finished": ["tests/test_mod.py::test_fn"],
            "results": {"tests/test_mod.py::test_fn": "passed"},
            "active": [],
        },
    }


def _behavioral(
    *,
    target_status="failed",
    regression=True,
    interpreter="/opt/venv-a/bin/python",
    working_directory="/tmp/agi-verification-baseline-aaaa/repo",
    duration_ms=999,
):
    execution = {
        "command": [interpreter, "-m", "pytest"],
        "working_directory": working_directory,
        "revision": "target",
        "src_layout_pythonpath": False,
        "duration_ms": duration_ms,
        "stdout": "raw pytest output\n",
        "stderr": "",
    }
    return BehavioralTestComparison(
        test_file="tests/test_mod.py",
        test_node_id="tests/test_mod.py::test_fn",
        baseline_status="passed",
        target_status=target_status,
        regression=regression,
        comparison_status="REGRESSION" if regression else "CONSISTENT",
        changed_files=["service.py"],
        changed_symbols=["service.py::handle"],
        selection_provenance="deterministic_changed_test_files",
        baseline_execution={"execution": dict(execution), "node_results": {NODE: "passed"}},
        target_execution={"execution": dict(execution), "node_results": {NODE: target_status}},
        baseline_outcome={"status": "PASSED", "source": "PYTEST_NODE_RESULT"},
        target_outcome={"status": "FAILED", "source": "PYTEST_NODE_RESULT"},
    )


def _proof(evidence):
    return VerificationEngine().assess(_impact(), [], _risk(), evidence)


# --- A: volatile-only differences hash identically -------------------------

def test_volatile_command_differences_hash_identically():
    stable = VerificationEvidence(
        tests_discovered=["tests/test_mod.py"],
        tests_executed=["tests/test_mod.py"],
        test_execution_result="passed",
        relevant_tests=["tests/test_mod.py"],
        command_results=[_command_result()],
    )
    volatile = VerificationEvidence(
        tests_discovered=["tests/test_mod.py"],
        tests_executed=["tests/test_mod.py"],
        test_execution_result="passed",
        relevant_tests=["tests/test_mod.py"],
        command_results=[
            _command_result(
                interpreter="/usr/local/other/bin/python",
                working_directory="/tmp/agi-verification-baseline-zzzz/repo",
                duration_ms=987654,
                stdout="collected 1 item\ntotally different capture\n",
                stderr="a warning on this machine only\n",
            )
        ],
    )
    assert _proof(stable).deterministic_hash == _proof(volatile).deterministic_hash


def test_volatile_behavioral_execution_differences_hash_identically():
    stable = VerificationEvidence(behavioral=[_behavioral()])
    volatile = VerificationEvidence(
        behavioral=[
            _behavioral(
                interpreter="/some/where/else/python3",
                working_directory="/tmp/agi-verification-baseline-9999/repo",
                duration_ms=42,
            )
        ]
    )
    assert _proof(stable).deterministic_hash == _proof(volatile).deterministic_hash


# --- B: meaningful evidence changes the hash -------------------------------

def test_node_outcome_change_changes_hash():
    base = VerificationEvidence(command_results=[_command_result()])
    changed = VerificationEvidence(
        command_results=[
            _command_result(node_results={"tests/test_mod.py::test_fn": "failed"})
        ]
    )
    assert _proof(base).deterministic_hash != _proof(changed).deterministic_hash


def test_behavioral_regression_verdict_changes_hash():
    no_regression = VerificationEvidence(
        behavioral=[_behavioral(target_status="passed", regression=False)]
    )
    regression = VerificationEvidence(behavioral=[_behavioral()])
    assert _proof(no_regression).deterministic_hash != _proof(regression).deterministic_hash


def test_revision_change_changes_hash():
    impact_a = _impact()
    impact_b = ChangeImpactReport(
        repository="owner/repo",
        base_revision="base",
        target_revision="different-target",
        changed_files=["service.py"],
        confidence=Confidence.HIGH,
    ).finalize()
    evidence = VerificationEvidence(command_results=[_command_result()])
    a = VerificationEngine().assess(impact_a, [], _risk(), evidence)
    b = VerificationEngine().assess(impact_b, [], _risk(), evidence)
    assert a.deterministic_hash != b.deterministic_hash


# --- C: display/audit representation keeps runtime evidence ----------------

def test_display_payload_retains_runtime_evidence():
    proof = _proof(
        VerificationEvidence(
            tests_executed=["tests/test_mod.py"],
            test_execution_result="passed",
            command_results=[_command_result(duration_ms=555, stdout="LIVE OUTPUT")],
        )
    )
    payload = proof.to_dict()
    cmd = payload["command_results"][0]
    assert cmd["duration_ms"] == 555
    assert cmd["stdout"] == "LIVE OUTPUT"
    assert cmd["working_directory"].startswith("/tmp/")
    assert cmd["command"][0].startswith("/")
    assert payload["deterministic_hash"] == proof.deterministic_hash
    assert payload["hash_schema_version"] == PROOF_HASH_VERSION


# --- D: optional behavioral fields do not change hash semantics ------------

def test_optional_behavioral_attribution_defaults_are_stable():
    without = _behavioral()
    with_defaults = _behavioral()
    object.__setattr__(with_defaults, "timeout_attribution", None)
    object.__setattr__(with_defaults, "timeout_attribution_source", None)
    a = _proof(VerificationEvidence(behavioral=[without]))
    b = _proof(VerificationEvidence(behavioral=[with_defaults]))
    assert a.deterministic_hash == b.deterministic_hash


def test_behavioral_absent_versus_empty_regression_list():
    absent = _proof(VerificationEvidence())
    present_no_regressions = _proof(
        VerificationEvidence(behavioral=[_behavioral(target_status="passed", regression=False)])
    )
    assert absent.deterministic_hash != present_no_regressions.deterministic_hash
    assert absent.behavioral_comparison_status is None
    assert present_no_regressions.behavioral_comparison_status == "NO_REGRESSIONS"


# --- E: canonicalization is stable across processes ------------------------

def test_hash_is_stable_across_processes():
    script = (
        "from app.models.change_impact import ChangeImpactReport, Confidence\n"
        "from app.services.change_risk_engine import ChangeRiskAssessment, RiskLevel\n"
        "from app.services.verification_engine import VerificationEngine, VerificationEvidence\n"
        "impact = ChangeImpactReport(repository='owner/repo', base_revision='base',"
        " target_revision='target', changed_files=['service.py'], confidence=Confidence.HIGH).finalize()\n"
        "risk = ChangeRiskAssessment(risk_level=RiskLevel.LOW, score=20, confidence='high').finalize()\n"
        "evidence = VerificationEvidence(command_results=[{'check': 'pytest',"
        " 'command': ['/opt/venv/bin/python', '-m', 'pytest', 'tests/test_mod.py'],"
        " 'revision': 'target', 'working_directory': '/tmp/wt/repo', 'duration_ms': 7,"
        " 'stdout': 'x', 'stderr': '', 'node_results': {'tests/test_mod.py::t': 'passed'}}])\n"
        "print(VerificationEngine().assess(impact, [], risk, evidence).deterministic_hash)\n"
    )
    env = dict(os.environ, PYTHONPATH="backend", PYTHONHASHSEED="3")
    first = subprocess.check_output([sys.executable, "-c", script], env=env, text=True).strip()
    env["PYTHONHASHSEED"] = "9001"
    second = subprocess.check_output([sys.executable, "-c", script], env=env, text=True).strip()
    assert first == second


def test_canonical_payload_excludes_volatile_and_wraps_version():
    proof = _proof(VerificationEvidence(command_results=[_command_result()]))
    canonical = proof.canonical_hash_payload()
    assert canonical["schema"] == PROOF_HASH_SCHEMA
    assert canonical["version"] == PROOF_HASH_VERSION
    cmd = canonical["proof"]["command_results"][0]
    assert "duration_ms" not in cmd
    assert "stdout" not in cmd
    assert "stderr" not in cmd
    assert "working_directory" not in cmd
    assert cmd["command"][0] == "<python>"
    assert cmd["node_results"] == {"tests/test_mod.py::test_fn": "passed"}


def test_canonicalize_helper_normalizes_nested_paths():
    raw = {
        "command": ["/abs/python", "-m", "pytest", "/abs/plugin/dir"],
        "duration_ms": 5,
        "working_directory": "/tmp/x",
        "node_results": {"a::b": "passed"},
        "nested": [{"stdout": "drop me", "revision": "keep"}],
    }
    canonical = _canonicalize_for_hash(raw)
    assert canonical["command"] == ["<python>", "-m", "pytest", "dir"]
    assert "duration_ms" not in canonical
    assert "working_directory" not in canonical
    assert canonical["node_results"] == {"a::b": "passed"}
    assert canonical["nested"] == [{"revision": "keep"}]
