"""Regression tests for deterministic regression finding attribution."""

import pytest

from app.models.change_impact import ChangeImpactReport, ChangedSymbol, Confidence, RiskLevel
from app.services.change_risk_engine import ChangeRiskAssessment
from app.services.verification_engine import (
    VerificationEngine,
    VerificationEvidence,
    VerificationState,
)
from app.services.finding_context import FindingContext


NODE = "service.py::handle"


def _impact(confidence=Confidence.HIGH):
    return ChangeImpactReport(
        repository="owner/repo",
        base_revision="base",
        target_revision="target",
        changed_files=["service.py", "changed.py"],
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
        callers=["caller.py::call"],
        downstream_symbols=["downstream.py::finish"],
        confidence=confidence,
    ).finalize()


def _risk(level=RiskLevel.LOW):
    return ChangeRiskAssessment(
        risk_level=level,
        score=20 if level == RiskLevel.LOW else 90,
        confidence="high",
    ).finalize()


def _proof(findings, confidence=Confidence.HIGH, risk=RiskLevel.LOW):
    impact = _impact(confidence)
    evidence = VerificationEvidence(
        findings_before=[],
        findings_after=findings,
    )
    return VerificationEngine().assess(
        impact,
        [],
        _risk(risk),
        evidence,
    )


def _assert_attribution(findings, expected_attribution):
    proof = _proof(findings)
    assert len(proof.new_findings_attribution) == 1
    assert proof.new_findings_attribution[0]["attribution"] == expected_attribution
    return proof


def test_finding_directly_on_changed_symbol():
    _assert_attribution(
        [{"file_path": "service.py", "issue_code": "R", "symbol_id": NODE}],
        "DIRECT_CHANGE",
    )


def test_finding_in_changed_file_without_symbol():
    _assert_attribution(
        [{"file_path": "changed.py", "issue_code": "R", "message": "module level"}],
        "CHANGED_FILE",
    )


def test_finding_on_caller():
    _assert_attribution(
        [{"file_path": "caller.py", "issue_code": "R", "symbol_id": "caller.py::call"}],
        "CALLER_IMPACT",
    )


def test_finding_downstream():
    _assert_attribution(
        [{"file_path": "downstream.py", "issue_code": "R", "symbol_id": "downstream.py::finish"}],
        "DOWNSTREAM_IMPACT",
    )


def test_finding_in_unrelated_file():
    _assert_attribution(
        [{"file_path": "outside.py", "issue_code": "R", "symbol_id": "outside.py::func"}],
        "OUTSIDE_IMPACT",
    )


def test_unresolved_impact():
    _assert_attribution(
        [{"issue_code": "R", "message": "no location evidence"}],
        "UNRESOLVED",
    )


def test_empty_new_findings_produces_empty_attribution():
    proof = _proof([])
    assert proof.new_findings == []
    assert proof.new_findings_attribution == []


def test_none_evidence_produces_none_attribution():
    impact = _impact()
    evidence = VerificationEvidence()
    proof = VerificationEngine().assess(impact, [], _risk(), evidence)
    assert proof.new_findings is None
    assert proof.new_findings_attribution is None


def test_deterministic_ordering():
    findings_a = [
        {"file_path": "service.py", "issue_code": "R", "symbol_id": NODE},
        {"file_path": "outside.py", "issue_code": "R", "symbol_id": "outside.py::func"},
    ]
    findings_b = [
        {"file_path": "outside.py", "issue_code": "R", "symbol_id": "outside.py::func"},
        {"file_path": "service.py", "issue_code": "R", "symbol_id": NODE},
    ]
    proof_a = _proof(findings_a)
    proof_b = _proof(findings_b)

    assert proof_a.new_findings_attribution == proof_b.new_findings_attribution


def test_idempotency_same_input_same_attribution():
    findings = [{"file_path": "service.py", "issue_code": "R", "symbol_id": NODE}]
    proof_1 = _proof(findings)
    proof_2 = _proof(findings)

    assert proof_1.new_findings_attribution == proof_2.new_findings_attribution


def test_attribution_does_not_modify_existing_risk_score():
    findings = [{"file_path": "outside.py", "issue_code": "R", "symbol_id": "outside.py::func"}]
    risk = _risk(RiskLevel.MEDIUM)
    impact = _impact()
    evidence = VerificationEvidence(findings_before=[], findings_after=findings)
    proof = VerificationEngine().assess(impact, [], risk, evidence)

    assert proof.change_risk == "medium"


def test_attribution_does_not_modify_existing_verification_state():
    findings = [{"file_path": "outside.py", "issue_code": "R", "symbol_id": "outside.py::func"}]
    risk = _risk()
    impact = _impact()
    # Provide all necessary checks so the only thing blocking is the new finding itself
    evidence = VerificationEvidence(
        tests_discovered=["tests/test_service.py"],
        tests_executed=["tests/test_service.py"],
        test_execution_result="passed",
        static_analysis_executed=True,
        static_analysis_result="passed",
        relevant_tests=["tests/test_service.py"],
        findings_before=[],
        findings_after=findings,
    )
    proof = VerificationEngine().assess(impact, [], risk, evidence)

    assert proof.state == VerificationState.BLOCKED


def test_flask_module_level_scenario():
    # Flask scenario: changed_symbols=[], confidence=LOW
    impact = ChangeImpactReport(
        repository="pallets/flask",
        base_revision="base",
        target_revision="target",
        changed_files=["src/flask/app.py"],
        changed_symbols=[],
        confidence=Confidence.LOW,
    ).finalize()

    evidence = VerificationEvidence(
        findings_before=[],
        findings_after=[{"file_path": "src/flask/app.py", "issue_code": "R", "message": "unresolved"}],
    )

    proof = VerificationEngine().assess(impact, [], _risk(), evidence)

    # Finding in changed file but no symbol mapped should be CHANGED_FILE, not DIRECT_CHANGE
    assert len(proof.new_findings_attribution) == 1
    assert proof.new_findings_attribution[0]["attribution"] == "CHANGED_FILE"


def test_real_repository_outside_impact_scenario():
    # Simulate an unrelated finding that appeared in the target run
    # (e.g. from a different file not modified in this PR)
    impact = ChangeImpactReport(
        repository="owner/repo",
        base_revision="base",
        target_revision="target",
        changed_files=["src/main.py"],
        changed_symbols=[
            ChangedSymbol(
                node_id="src/main.py::main",
                node_type="function",
                file_path="src/main.py",
                name="main",
                change_kind="modified",
            )
        ],
        directly_affected_symbols=["src/main.py::main"],
        confidence=Confidence.HIGH,
    ).finalize()

    evidence = VerificationEvidence(
        findings_before=[],
        findings_after=[
            {"file_path": "src/utils.py", "issue_code": "flake8", "message": "line too long"}
        ],
    )

    proof = VerificationEngine().assess(impact, [], _risk(), evidence)

    assert len(proof.new_findings_attribution) == 1
    assert proof.new_findings_attribution[0]["attribution"] == "OUTSIDE_IMPACT"
