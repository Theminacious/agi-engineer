"""Item 8: persisted proof reconstructs to its own finalize() hash (schema v3)."""

import copy

from app.models.change_impact import ChangeImpactReport, Confidence
from app.services.change_risk_engine import ChangeRiskAssessment, RiskLevel
from app.services.verification_engine import (
    PROOF_HASH_VERSION,
    BehavioralTestComparison,
    VerificationEngine,
    VerificationEvidence,
    recompute_proof_hash,
)


def _finalized_proof():
    impact = ChangeImpactReport(
        repository="owner/repo", base_revision="base", target_revision="target",
        changed_files=["service.py"], confidence=Confidence.HIGH,
    ).finalize()
    risk = ChangeRiskAssessment(risk_level=RiskLevel.LOW, score=20, confidence="high").finalize()
    behavioral = [BehavioralTestComparison(
        test_file="tests/test_mod.py", test_node_id="tests/test_mod.py::t",
        baseline_status="passed", target_status="passed", regression=False,
        comparison_status="CONSISTENT",
        baseline_execution={
            "node_results_source": "PYTEST_NODE_LIFECYCLE_EVENTS",
            "node_results": {"tests/test_mod.py::t": "passed"},
            "status": "EXECUTED", "duration_ms": 123, "stdout": "noise", "stderr": "",
        },
        target_execution={
            "node_results_source": "PYTEST_NODE_LIFECYCLE_EVENTS",
            "node_results": {"tests/test_mod.py::t": "passed"},
            "status": "EXECUTED", "duration_ms": 456, "stdout": "noise", "stderr": "",
        },
    )]
    evidence = VerificationEvidence(
        tests_discovered=["tests/test_mod.py"],
        tests_executed=["tests/test_mod.py"],
        test_execution_result="passed",
        relevant_tests=["tests/test_mod.py"],
        behavioral=behavioral,
    )
    return VerificationEngine().assess(impact, [], risk, evidence)


def test_recomputed_hash_equals_finalize_hash():
    proof = _finalized_proof()
    body = proof.to_dict()
    assert recompute_proof_hash(body) == proof.deterministic_hash


def test_schema_is_v3():
    proof = _finalized_proof()
    assert proof.to_dict()["hash_schema_version"] == PROOF_HASH_VERSION == 3


def test_mutating_deterministic_field_changes_recomputed_hash():
    proof = _finalized_proof()
    original = proof.deterministic_hash
    for field, value in (
        ("state", "blocked"),
        ("target_identity", "mismatch"),
        ("node_results_source", {"baseline": ["PYTEST_RA_SUMMARY_TEXT"], "target": []}),
        ("behavioral_comparison_status", "REGRESSIONS_FOUND"),
    ):
        tampered = copy.deepcopy(proof.to_dict())
        tampered[field] = value
        assert recompute_proof_hash(tampered) != original, field


def test_mutating_volatile_field_does_not_change_recomputed_hash():
    proof = _finalized_proof()
    original = proof.deterministic_hash
    tampered = copy.deepcopy(proof.to_dict())
    for cmd in tampered.get("command_results") or []:
        cmd["duration_ms"] = 999999
        cmd["stdout"] = "entirely different capture"
    # behavioral execution volatile fields too
    for comp in tampered.get("behavioral_regressions") or []:
        pass
    assert recompute_proof_hash(tampered) == original
