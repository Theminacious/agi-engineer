"""Regression tests for the deterministic context-aware change decision."""

import os
import subprocess
import sys

from app.models.change_impact import (
    ChangeImpactReport,
    ChangedSymbol,
    Confidence,
    FindingImpact,
    RiskLevel,
)
from app.services.change_risk_engine import ChangeRiskEngine
from app.services.change_risk_service import assess_change_risk
from app.services.finding_context import FindingContext


NODE = "service.py::handle"


def _context(
    ref="finding-1",
    relation="direct",
    severity="high",
    confidence=85,
    correlation_id=None,
    symbol_node_id=NODE,
):
    return FindingContext(
        finding_ref=ref,
        file_path="service.py",
        line_number=10,
        rule_code="reliability",
        symbol="handle" if symbol_node_id else None,
        symbol_node_id=symbol_node_id,
        caller_count=1 if symbol_node_id else None,
        downstream_count=2 if symbol_node_id else None,
        change_relation=relation,
        severity=severity,
        confidence=confidence,
        correlation_id=correlation_id,
    )


def _impact(
    *,
    callers=(),
    downstream=(),
    confidence=Confidence.HIGH,
    changed=True,
):
    report = ChangeImpactReport(
        repository="owner/repo",
        base_revision="base",
        target_revision="target",
        changed_files=["service.py"] if changed else [],
        changed_symbols=(
            [
                ChangedSymbol(
                    node_id=NODE,
                    node_type="function",
                    file_path="service.py",
                    name="handle",
                    change_kind="modified",
                )
            ]
            if changed
            else []
        ),
        directly_affected_symbols=[NODE] if changed else [],
        callers=list(callers),
        downstream_symbols=list(downstream),
        confidence=confidence,
    )
    return report.finalize()


def _report(impact):
    return assess_change_risk(impact)


def test_no_finding_is_low_bounded_and_requires_no_human_review():
    impact = _impact()
    assessment = ChangeRiskEngine().assess(impact, [], _report(impact))

    assert assessment.risk_level == RiskLevel.LOW
    assert assessment.score == 20
    assert 0 <= assessment.score <= 100
    assert assessment.human_review_required is False
    assert assessment.supporting_findings == []


def test_direct_finding_is_stronger_than_unrelated_finding():
    impact = _impact()
    engine = ChangeRiskEngine()
    direct = engine.assess(impact, [_context()], _report(impact))
    unrelated = engine.assess(
        impact,
        [_context(relation="outside", symbol_node_id=None)],
        _report(impact),
    )

    assert direct.score > unrelated.score
    assert direct.human_review_required is True
    assert unrelated.supporting_findings == []


def test_high_severity_and_relationship_are_explicit_score_evidence():
    impact = _impact()
    assessment = ChangeRiskEngine().assess(impact, [_context(severity="critical")], _report(impact))

    assert assessment.score == 100
    assert any("explicit graph-backed" in reason for reason in assessment.reasons)
    assert assessment.change_relationships == ["direct"]


def test_low_confidence_evidence_requires_verification_without_claiming_reachability():
    impact = _impact(confidence=Confidence.LOW)
    assessment = ChangeRiskEngine().assess(
        impact, [_context(confidence=20)], _report(impact)
    )

    assert assessment.confidence == "low"
    assert "verify unresolved changed ranges and impact coverage" in assessment.verification_requirements
    assert assessment.human_review_required is True


def test_many_callers_do_not_automatically_create_high_risk():
    impact = _impact(callers=[f"caller.py::f{i}" for i in range(100)])
    assessment = ChangeRiskEngine().assess(impact, [], _report(impact))

    assert assessment.caller_count == 100
    assert assessment.risk_level == RiskLevel.MEDIUM
    assert assessment.score == 45


def test_correlated_findings_are_scored_once():
    impact = _impact()
    contexts = [
        _context(ref="one", severity="high", correlation_id="same"),
        _context(ref="two", severity="critical", correlation_id="same"),
    ]
    assessment = ChangeRiskEngine().assess(impact, contexts, _report(impact))

    assert assessment.score == 100
    assert len(assessment.supporting_findings) == 2


def test_missing_relationship_evidence_remains_unknown():
    impact = _impact()
    assessment = ChangeRiskEngine().assess(
        impact,
        [_context(relation=None, symbol_node_id=None, confidence=50)],
        _report(impact),
    )

    assert assessment.supporting_findings == []
    assert assessment.change_relationships == []
    assert assessment.verification_requirements == [
        "verify findings whose symbol relationship is unknown"
    ]


def test_large_blast_radius_is_a_separate_bounded_contribution():
    impact = _impact(downstream=[f"module.py::f{i}" for i in range(10)])
    assessment = ChangeRiskEngine().assess(impact, [], _report(impact))

    assert assessment.score == 45
    assert assessment.downstream_count == 10
    assert assessment.risk_level == RiskLevel.MEDIUM


def test_ordering_and_reasons_are_deterministic():
    impact = _impact(callers=("b.py::b", "a.py::a"), downstream=("z.py::z",))
    contexts = [_context(ref="b"), _context(ref="a", relation="caller")]
    engine = ChangeRiskEngine()
    first = engine.assess(impact, contexts, _report(impact)).to_dict()
    second = engine.assess(impact, list(reversed(contexts)), _report(impact)).to_dict()

    assert first == second
    assert first["reasons"] == sorted(first["reasons"])
    assert first["deterministic_hash"] == second["deterministic_hash"]


def test_serialized_result_is_stable_across_hash_seeds():
    script = """
from app.models.change_impact import ChangeImpactReport, Confidence
from app.services.change_risk_engine import ChangeRiskEngine
from app.services.change_risk_service import assess_change_risk
impact = ChangeImpactReport(repository='r', base_revision='b', target_revision='t', changed_files=['b.py', 'a.py'], confidence=Confidence.HIGH).finalize()
assessment = ChangeRiskEngine().assess(impact, [], assess_change_risk(impact))
print(assessment.deterministic_hash)
"""
    env = dict(os.environ, PYTHONPATH="backend", PYTHONHASHSEED="1")
    first = subprocess.check_output([sys.executable, "-c", script], env=env, text=True).strip()
    env["PYTHONHASHSEED"] = "777"
    second = subprocess.check_output([sys.executable, "-c", script], env=env, text=True).strip()

    assert first == second