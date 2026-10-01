"""Read-time verification-proof integrity: persisted body vs ledger-anchored hash."""

import copy

from app.models.change_impact import ChangeImpactReport, Confidence
from app.services.change_risk_engine import ChangeRiskAssessment, RiskLevel
from app.services.change_risk_view import (
    INTEGRITY_MISMATCH,
    INTEGRITY_UNAVAILABLE,
    INTEGRITY_VERIFIED,
    change_risk_view,
    proof_hash_from_ledger,
)
from app.services.verification_engine import (
    VerificationEngine,
    VerificationEvidence,
)


def _proof_dict():
    impact = ChangeImpactReport(
        repository="owner/repo",
        base_revision="base",
        target_revision="target",
        changed_files=["service.py"],
        confidence=Confidence.HIGH,
    ).finalize()
    risk = ChangeRiskAssessment(risk_level=RiskLevel.LOW, score=20, confidence="high").finalize()
    evidence = VerificationEvidence(
        tests_discovered=["tests/test_mod.py"],
        tests_executed=["tests/test_mod.py"],
        test_execution_result="passed",
        relevant_tests=["tests/test_mod.py"],
    )
    proof = VerificationEngine().assess(impact, [], risk, evidence)
    return proof.to_dict(), proof.deterministic_hash


def _report(proof_dict):
    return {"risk_level": "low", "verification": proof_dict}


def test_matching_proof_and_ledger_hash_is_verified():
    proof_dict, digest = _proof_dict()
    view = change_risk_view(_report(proof_dict), expected_proof_hash=digest)
    integrity = view["verification"]["proof_integrity"]
    assert integrity["status"] == INTEGRITY_VERIFIED
    assert integrity["expected_hash"] == digest
    assert integrity["actual_hash"] == digest


def test_mutated_persisted_proof_is_mismatch():
    proof_dict, digest = _proof_dict()
    tampered = copy.deepcopy(proof_dict)
    tampered["reasons"] = list(tampered.get("reasons") or []) + ["injected"]
    view = change_risk_view(_report(tampered), expected_proof_hash=digest)
    integrity = view["verification"]["proof_integrity"]
    assert integrity["status"] == INTEGRITY_MISMATCH
    assert integrity["expected_hash"] == digest
    assert integrity["actual_hash"] != digest


def test_missing_proof_is_unavailable():
    view = change_risk_view({"risk_level": "low"}, expected_proof_hash="a" * 64)
    integrity = view["verification"]["proof_integrity"]
    assert integrity["status"] == INTEGRITY_UNAVAILABLE
    assert integrity["actual_hash"] is None


def test_missing_ledger_reference_is_unavailable():
    proof_dict, _digest = _proof_dict()
    view = change_risk_view(_report(proof_dict), expected_proof_hash=None)
    integrity = view["verification"]["proof_integrity"]
    assert integrity["status"] == INTEGRITY_UNAVAILABLE
    assert integrity["expected_hash"] is None
    assert integrity["actual_hash"] is None


def test_malformed_proof_is_unavailable():
    malformed = {"state": "verified", "weird": {1, 2, 3}}
    view = change_risk_view(_report(malformed), expected_proof_hash="a" * 64)
    integrity = view["verification"]["proof_integrity"]
    assert integrity["status"] == INTEGRITY_UNAVAILABLE
    assert integrity["actual_hash"] is None


def test_mismatch_never_becomes_a_successful_verification():
    proof_dict, digest = _proof_dict()
    forged = copy.deepcopy(proof_dict)
    forged["state"] = "verified"
    forged["test_execution_result"] = "passed"
    forged["new_findings"] = []
    view = change_risk_view(_report(forged), expected_proof_hash=digest)
    integrity = view["verification"]["proof_integrity"]
    assert integrity["status"] == INTEGRITY_MISMATCH
    assert integrity["status"] not in (INTEGRITY_VERIFIED, "verified", "passed")
    assert view["verification"]["state"] == "verified"


def test_normal_response_is_backward_compatible_with_additive_integrity():
    proof_dict, _digest = _proof_dict()
    view = change_risk_view(_report(proof_dict))
    verification = view["verification"]
    assert set(
        ["state", "required_checks", "completed_checks", "missing_checks", "reasons"]
    ).issubset(verification.keys())
    assert "proof_integrity" in verification
    assert verification["proof_integrity"]["status"] == INTEGRITY_UNAVAILABLE


def test_proof_hash_from_ledger_returns_latest_assessment(monkeypatch):
    events = [
        {"event_type": "RUN_STARTED", "payload_ref": None, "sequence": 0},
        {"event_type": "VERIFICATION_PROOF_ASSESSED", "payload_ref": "hash-old", "sequence": 1},
        {"event_type": "CHANGE_RISK_DECISION_ASSESSED", "payload_ref": "risk", "sequence": 2},
        {"event_type": "VERIFICATION_PROOF_ASSESSED", "payload_ref": "hash-new", "sequence": 3},
    ]
    import agent.run_ledger as run_ledger

    monkeypatch.setattr(run_ledger, "read_events", lambda run_id: events)
    assert proof_hash_from_ledger("run-1") == "hash-new"


def test_proof_hash_from_ledger_none_when_absent(monkeypatch):
    import agent.run_ledger as run_ledger

    monkeypatch.setattr(run_ledger, "read_events", lambda run_id: [
        {"event_type": "RUN_STARTED", "payload_ref": None, "sequence": 0},
    ])
    assert proof_hash_from_ledger("run-1") is None
    assert proof_hash_from_ledger(None) is None
