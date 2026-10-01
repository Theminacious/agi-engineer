"""Regression tests for deterministic verification and proof semantics."""

import os
import subprocess
import sys

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
        confidence=confidence,
    ).finalize()


def _context():
    return FindingContext(
        finding_ref="finding-1",
        file_path="service.py",
        line_number=10,
        rule_code="reliability",
        symbol="handle",
        symbol_node_id=NODE,
        change_relation="direct",
        confidence=85,
    )


def _risk(level=RiskLevel.LOW):
    return ChangeRiskAssessment(
        risk_level=level,
        score=20 if level == RiskLevel.LOW else 90,
        confidence="high",
    ).finalize()


def _proof(evidence=None, confidence=Confidence.HIGH, risk=RiskLevel.LOW):
    impact = _impact(confidence)
    return VerificationEngine().assess(
        impact,
        [_context()],
        _risk(risk),
        evidence,
    )


def test_no_verification_evidence_is_unverified_and_explicitly_unknown():
    proof = _proof()

    assert proof.state is VerificationState.UNVERIFIED
    assert proof.tests_discovered is None
    assert proof.tests_executed is None
    assert proof.static_analysis_executed is None
    assert proof.verification_confidence == "unknown"
    assert "test_execution" in proof.missing_checks


def test_discovered_tests_without_execution_are_not_verified():
    proof = _proof(VerificationEvidence(tests_discovered=["tests/test_service.py"]))

    assert proof.state is VerificationState.UNVERIFIED
    assert proof.tests_discovered == ["tests/test_service.py"]
    assert proof.tests_executed is None
    assert any("discovered but no test execution" in reason for reason in proof.reasons)


def test_static_analysis_execution_without_tests_is_partial():
    proof = _proof(
        VerificationEvidence(
            static_analysis_executed=True,
            static_analysis_result="passed",
        )
    )

    assert proof.state is VerificationState.PARTIALLY_VERIFIED
    assert proof.completed_checks == ["impact_confidence", "static_analysis_execution"]
    assert proof.test_execution_result is None


def test_tests_executed_and_passed_still_need_other_required_evidence():
    proof = _proof(
        VerificationEvidence(
            tests_discovered=["tests/test_service.py"],
            tests_executed=["tests/test_service.py"],
            test_execution_result="passed",
        )
    )

    assert proof.state is VerificationState.PARTIALLY_VERIFIED
    assert "static_analysis_execution" in proof.missing_checks


def test_failed_test_execution_blocks_verification():
    proof = _proof(
        VerificationEvidence(
            tests_discovered=["tests/test_service.py"],
            tests_executed=["tests/test_service.py"],
            test_execution_result="failed",
        )
    )

    assert proof.state is VerificationState.BLOCKED
    assert proof.test_execution_result == "failed"


def test_new_finding_blocks_even_when_execution_passes():
    proof = _proof(
        VerificationEvidence(
            tests_discovered=["tests/test_service.py"],
            tests_executed=["tests/test_service.py"],
            test_execution_result="passed",
            static_analysis_executed=True,
            static_analysis_result="passed",
            findings_before=[],
            findings_after=["finding-1"],
            relevant_tests=["tests/test_service.py"],
        )
    )

    assert proof.state is VerificationState.BLOCKED
    assert proof.new_findings == ["finding-1"]


def test_new_finding_attribution_uses_existing_impact_relationships():
    impact = ChangeImpactReport(
        repository="owner/repo",
        base_revision="base",
        target_revision="target",
        changed_files=["service.py", "changed.py"],
        directly_affected_symbols=["service.py::handle"],
        callers=["caller.py::call"],
        downstream_symbols=["downstream.py::finish"],
        confidence=Confidence.HIGH,
    ).finalize()
    findings = [
        {"file_path": "service.py", "issue_code": "R", "symbol_id": "service.py::handle"},
        {"file_path": "changed.py", "issue_code": "R", "message": "module finding"},
        {"file_path": "caller.py", "issue_code": "R", "symbol_id": "caller.py::call"},
        {"file_path": "downstream.py", "issue_code": "R", "symbol_id": "downstream.py::finish"},
        {"file_path": "unrelated.py", "issue_code": "R", "message": "unrelated"},
        {"issue_code": "R", "message": "no location"},
    ]
    proof = VerificationEngine().assess(
        impact,
        [],
        _risk(),
        VerificationEvidence(findings_before=[], findings_after=findings),
    )

    by_file = {item["file_path"]: item["attribution"] for item in proof.new_findings_attribution}
    assert by_file["service.py"] == "DIRECT_CHANGE"
    assert by_file["changed.py"] == "CHANGED_FILE"
    assert by_file["caller.py"] == "CALLER_IMPACT"
    assert by_file["downstream.py"] == "DOWNSTREAM_IMPACT"
    assert by_file["unrelated.py"] == "OUTSIDE_IMPACT"
    assert by_file[None] == "UNRESOLVED"


def test_attribution_preserves_empty_and_unavailable_comparison_semantics():
    empty = _proof(VerificationEvidence(findings_before=[], findings_after=[]))
    unavailable = _proof(VerificationEvidence())

    assert empty.new_findings == []
    assert empty.new_findings_attribution == []
    assert unavailable.new_findings is None
    assert unavailable.new_findings_attribution is None


def test_attribution_does_not_change_risk_or_verification_state():
    impact = _impact()
    risk = _risk()
    evidence = VerificationEvidence(
        findings_before=[],
        findings_after=[{"file_path": "outside.py", "issue_code": "R", "message": "new"}],
    )
    proof = VerificationEngine().assess(impact, [], risk, evidence)

    assert proof.state is VerificationState.BLOCKED
    assert proof.change_risk == risk.risk_level.value
    assert proof.new_findings_attribution[0]["attribution"] == "OUTSIDE_IMPACT"


def test_unchanged_and_resolved_findings_are_distinguished():
    evidence = VerificationEvidence(
        tests_discovered=["tests/test_service.py"],
        tests_executed=["tests/test_service.py"],
        test_execution_result="passed",
        static_analysis_executed=True,
        static_analysis_result="passed",
        findings_before=["finding-1", "finding-2"],
        findings_after=["finding-1"],
        relevant_tests=["tests/test_service.py"],
    )
    proof = _proof(evidence)

    assert proof.state is VerificationState.VERIFIED
    assert proof.new_findings == []
    assert proof.unchanged_findings == ["finding-1"]
    assert proof.resolved_findings == ["finding-2"]


def test_high_risk_requires_relevant_test_evidence_and_impact_confidence():
    proof = _proof(
        VerificationEvidence(
            tests_discovered=["tests/test_service.py"],
            tests_executed=["tests/test_service.py"],
            test_execution_result="passed",
            static_analysis_executed=True,
            static_analysis_result="passed",
            findings_before=[],
            findings_after=[],
        ),
        risk=RiskLevel.HIGH,
    )

    assert proof.state is VerificationState.PARTIALLY_VERIFIED
    assert "relevant_test_evidence" in proof.missing_checks
    assert "impact_confidence" not in proof.missing_checks


def test_relevant_test_evidence_can_complete_high_risk_verification():
    proof = _proof(
        VerificationEvidence(
            tests_discovered=["tests/test_service.py"],
            tests_executed=["tests/test_service.py"],
            test_execution_result="passed",
            relevant_tests=["tests/test_service.py"],
            static_analysis_executed=True,
            static_analysis_result="passed",
            findings_before=[],
            findings_after=[],
        ),
        risk=RiskLevel.HIGH,
    )

    assert proof.state is VerificationState.VERIFIED
    assert proof.verification_confidence == "high"


def test_low_impact_confidence_remains_explicitly_incomplete():
    proof = _proof(
        VerificationEvidence(
            static_analysis_executed=True,
            static_analysis_result="passed",
        ),
        confidence=Confidence.LOW,
    )

    assert proof.state is VerificationState.PARTIALLY_VERIFIED
    assert proof.verification_confidence == "low"
    assert "impact_confidence" in proof.missing_checks


def test_empty_test_discovery_is_not_test_success():
    proof = _proof(VerificationEvidence(tests_discovered=[]))

    assert proof.state is VerificationState.UNVERIFIED
    assert proof.tests_discovered == []
    assert proof.test_execution_result is None


def test_ordering_and_hash_are_independent_of_input_order():
    first = _proof(
        VerificationEvidence(
            tests_discovered=["b.py", "a.py"],
            tests_executed=["b.py", "a.py"],
            test_execution_result="passed",
            static_analysis_executed=True,
            static_analysis_result="passed",
            findings_before=["z", "a"],
            findings_after=["a", "z"],
        )
    )
    second = _proof(
        VerificationEvidence(
            tests_discovered=["a.py", "b.py"],
            tests_executed=["a.py", "b.py"],
            test_execution_result="passed",
            static_analysis_executed=True,
            static_analysis_result="passed",
            findings_before=["a", "z"],
            findings_after=["z", "a"],
        )
    )

    assert first.to_dict() == second.to_dict()
    assert first.deterministic_hash == second.deterministic_hash


def test_proof_hash_is_stable_across_python_hash_seeds():
    script = """
from app.models.change_impact import ChangeImpactReport, Confidence, RiskLevel
from app.services.change_risk_engine import ChangeRiskAssessment
from app.services.verification_engine import VerificationEngine, VerificationEvidence
impact = ChangeImpactReport(repository='r', base_revision='b', target_revision='t', changed_files=['b.py', 'a.py'], confidence=Confidence.HIGH).finalize()
risk = ChangeRiskAssessment(risk_level=RiskLevel.LOW, score=20, confidence='high').finalize()
evidence = VerificationEvidence(tests_discovered=['b.py', 'a.py'], findings_before=['z', 'a'], findings_after=['a', 'z'])
print(VerificationEngine().assess(impact, [], risk, evidence).deterministic_hash)
"""
    env = dict(os.environ, PYTHONPATH="backend", PYTHONHASHSEED="1")
    first = subprocess.check_output([sys.executable, "-c", script], env=env, text=True).strip()
    env["PYTHONHASHSEED"] = "777"
    second = subprocess.check_output([sys.executable, "-c", script], env=env, text=True).strip()

    assert first == second

def test_unavailable_test_execution_does_not_block():
    proof = _proof(
        VerificationEvidence(
            tests_discovered=["tests/test_service.py"],
            tests_executed=["tests/test_service.py"],
            test_execution_result="unavailable",
        )
    )

    assert proof.state is not VerificationState.BLOCKED
    assert "test_execution" in proof.missing_checks
    assert proof.test_execution_result == "unavailable"
    assert any("test execution evidence is unavailable" in reason for reason in proof.reasons)


def test_unavailable_static_analysis_does_not_block():
    proof = _proof(
        VerificationEvidence(
            static_analysis_executed=False,
            static_analysis_result="unavailable",
        )
    )

    assert proof.state is not VerificationState.BLOCKED
    assert "static_analysis_execution" in proof.missing_checks
    assert any("static analysis evidence is unavailable" in reason for reason in proof.reasons)


def test_genuine_static_findings_still_block():
    proof = _proof(
        VerificationEvidence(
            tests_discovered=["tests/test_service.py"],
            tests_executed=["tests/test_service.py"],
            test_execution_result="passed",
            static_analysis_executed=True,
            static_analysis_result="failed",
        )
    )

    assert proof.state is VerificationState.BLOCKED
    assert proof.static_analysis_result == "failed"


def test_unavailable_evidence_preserves_check_accounting():
    proof = _proof(
        VerificationEvidence(
            tests_discovered=["tests/test_service.py"],
            tests_executed=["tests/test_service.py"],
            test_execution_result="unavailable",
            static_analysis_executed=False,
            static_analysis_result="unavailable",
            findings_before=[],
            findings_after=[],
        )
    )

    assert "test_execution" in proof.required_checks
    assert "static_analysis_execution" in proof.required_checks
    assert "test_execution" in proof.missing_checks
    assert "static_analysis_execution" in proof.missing_checks
    assert "finding_comparison" in proof.completed_checks
