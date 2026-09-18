"""Deterministic change-risk decision over existing impact and finding evidence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from app.models.change_impact import (
    ChangeImpactReport,
    ChangeRiskReport,
    Confidence,
    RISK_LEVEL_RANK,
    RiskLevel,
    ReviewRecommendation,
)
from app.services.finding_context import FindingContext


_SEVERITY_SCORE = {
    "critical": 90,
    "high": 75,
    "medium": 55,
    "low": 30,
    "unknown": 40,
}
_RELATION_BONUS = {
    "direct": 10,
    "caller": 7,
    "downstream": 4,
}
_LEVEL_FLOOR = {
    RiskLevel.NONE: 0,
    RiskLevel.LOW: 20,
    RiskLevel.MEDIUM: 45,
    RiskLevel.HIGH: 70,
    RiskLevel.CRITICAL: 90,
}
_SCORE_LEVEL = (
    (90, RiskLevel.CRITICAL),
    (70, RiskLevel.HIGH),
    (45, RiskLevel.MEDIUM),
    (1, RiskLevel.LOW),
)


def _stable_context_key(context: FindingContext) -> Tuple[str, str, int, str]:
    return (
        context.finding_ref,
        context.file_path,
        context.line_number,
        context.rule_code,
    )


def _risk_level_for_score(score: int) -> RiskLevel:
    for threshold, level in _SCORE_LEVEL:
        if score >= threshold:
            return level
    return RiskLevel.NONE


def _context_evidence(context: FindingContext) -> Dict[str, Any]:
    return {
        "finding_ref": context.finding_ref,
        "file_path": context.file_path,
        "line_number": context.line_number,
        "rule_code": context.rule_code,
        "severity": context.severity,
        "confidence": context.confidence,
        "symbol": context.symbol,
        "symbol_node_id": context.symbol_node_id,
        "caller_count": context.caller_count,
        "downstream_count": context.downstream_count,
        "change_relation": context.change_relation,
        "correlation_id": context.correlation_id,
        "correlated_count": context.correlated_count,
    }


@dataclass
class ChangeRiskAssessment:
    """Auditable decision derived only from stored graph and finding evidence."""

    risk_level: RiskLevel
    score: int
    confidence: str
    reasons: List[str] = field(default_factory=list)
    supporting_findings: List[Dict[str, Any]] = field(default_factory=list)
    affected_symbols: List[str] = field(default_factory=list)
    affected_files: List[str] = field(default_factory=list)
    caller_count: Optional[int] = None
    downstream_count: Optional[int] = None
    change_relationships: List[str] = field(default_factory=list)
    verification_requirements: List[str] = field(default_factory=list)
    human_review_required: bool = False
    deterministic_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_level": self.risk_level.value,
            "score": self.score,
            "confidence": self.confidence,
            "reasons": list(self.reasons),
            "supporting_findings": list(self.supporting_findings),
            "affected_symbols": list(self.affected_symbols),
            "affected_files": list(self.affected_files),
            "caller_count": self.caller_count,
            "downstream_count": self.downstream_count,
            "change_relationships": list(self.change_relationships),
            "verification_requirements": list(self.verification_requirements),
            "human_review_required": self.human_review_required,
            "deterministic_hash": self.deterministic_hash,
        }

    def finalize(self) -> "ChangeRiskAssessment":
        payload = self.to_dict()
        payload.pop("deterministic_hash")
        self.deterministic_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return self


class ChangeRiskEngine:
    """Turn one existing risk report and its FindingContexts into a decision."""

    def assess(
        self,
        impact: ChangeImpactReport,
        contexts: Sequence[FindingContext],
        existing_report: Optional[ChangeRiskReport] = None,
    ) -> ChangeRiskAssessment:
        report = existing_report
        if report is None:
            from app.services.change_risk_service import assess_change_risk

            report = assess_change_risk(impact)

        ordered = sorted(contexts, key=_stable_context_key)
        supporting = [
            _context_evidence(context)
            for context in ordered
            if context.change_relation in {"direct", "caller", "downstream"}
        ]

        # Correlated findings represent one systemic cause. Only the strongest
        # context in each correlation group contributes to the score.
        groups: Dict[str, List[FindingContext]] = {}
        for context in ordered:
            if context.change_relation not in {"direct", "caller", "downstream"}:
                continue
            group = context.correlation_id or context.finding_ref
            groups.setdefault(group, []).append(context)

        score_candidates = [_LEVEL_FLOOR[report.risk_level]]
        for group in sorted(groups):
            strongest = max(
                groups[group],
                key=lambda context: (
                    _SEVERITY_SCORE.get(context.severity.lower(), 40)
                    + _RELATION_BONUS[context.change_relation or "downstream"],
                    context.finding_ref,
                ),
            )
            severity_score = _SEVERITY_SCORE.get(strongest.severity.lower(), 40)
            score_candidates.append(
                severity_score + _RELATION_BONUS[strongest.change_relation or "downstream"]
            )

        if impact.affected_entrypoints:
            score_candidates.append(45)
        if impact.blast_radius_size() >= 10:
            score_candidates.append(35)
        if impact.confidence == Confidence.LOW:
            score_candidates.append(40)
        if any(
            context.change_relation is None
            and context.file_path in set(impact.changed_files)
            for context in ordered
        ):
            score_candidates.append(50)

        score = max(0, min(100, max(score_candidates)))
        score_level = _risk_level_for_score(score)
        risk_level = max(
            (report.risk_level, score_level),
            key=lambda level: RISK_LEVEL_RANK[level],
        )

        confidence = "low" if impact.confidence == Confidence.LOW else "high"
        if any(context.confidence < 40 for context in ordered):
            confidence = "low"
        elif ordered and any(context.confidence < 70 for context in ordered):
            confidence = "medium"

        affected_symbols = sorted(
            set(impact.directly_affected_symbols)
            | set(impact.callers)
            | set(impact.downstream_symbols)
            | {
                context.symbol_node_id
                for context in ordered
                if context.symbol_node_id and context.change_relation in {"direct", "caller", "downstream"}
            }
        )
        affected_files = sorted(
            set(impact.changed_files)
            | {
                context.file_path
                for context in ordered
                if context.change_relation in {"direct", "caller", "downstream"}
            }
        )
        relationships = sorted(
            {
                context.change_relation
                for context in ordered
                if context.change_relation is not None
            }
        )

        reasons = [
            f"existing change-risk factors establish {report.risk_level.value.upper()} risk",
        ]
        if supporting:
            reasons.append(
                f"{len(supporting)} finding(s) have explicit graph-backed relationships"
            )
        if impact.callers:
            reasons.append(f"{len(set(impact.callers))} caller symbol(s) are affected")
        if impact.downstream_symbols:
            reasons.append(
                f"{len(set(impact.downstream_symbols))} downstream symbol(s) are affected"
            )
        if impact.confidence != Confidence.HIGH:
            reasons.append(
                f"impact evidence confidence is {impact.confidence.value}; coverage is incomplete"
            )
        if not supporting:
            reasons.append("no finding has a resolved relationship to the changed area")

        verification = []
        if impact.confidence != Confidence.HIGH:
            verification.append("verify unresolved changed ranges and impact coverage")
        if any(context.change_relation is None for context in ordered):
            verification.append("verify findings whose symbol relationship is unknown")
        if risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
            verification.append("obtain human review of the affected symbols and files")
        if not verification and impact.changed_symbols:
            verification.append("verify the changed symbols with repository tests")

        human_review = (
            risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}
            or report.recommendation == ReviewRecommendation.REQUIRES_HUMAN_REVIEW
        )
        assessment = ChangeRiskAssessment(
            risk_level=risk_level,
            score=score,
            confidence=confidence,
            reasons=sorted(set(reasons)),
            supporting_findings=supporting,
            affected_symbols=affected_symbols,
            affected_files=affected_files,
            caller_count=(
                None
                if impact.confidence == Confidence.LOW
                else len(set(impact.callers))
            ),
            downstream_count=(
                None
                if impact.confidence == Confidence.LOW
                else len(set(impact.downstream_symbols))
            ),
            change_relationships=relationships,
            verification_requirements=sorted(set(verification)),
            human_review_required=human_review,
        )
        return assessment.finalize()