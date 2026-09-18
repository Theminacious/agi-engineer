"""Phase 20 — Change Impact -> Risk Intelligence.

Composes existing systems only:

    git diff / PR head
       -> ChangeImpactService          (changed symbols + blast radius)
       -> existing reliability findings (intersected, not re-run)
       -> assess_change_risk()         (deterministic scoring, this file)
       -> ChangeRiskReport             (structured change decision)
       -> existing RunLedgerWriter     (CHANGE_RISK_ASSESSED event)

No new graph, no new analyzers, no LLM, no new approval path. The scoring
is a pure function of the impact report, so it is testable without git and
identical on every run.

What this does NOT do
---------------------
It does not predict whether a change will cause a production incident, and
nothing here is evidence for such a claim. It answers four mechanical
questions — which symbols the diff touched, what the graph says is reachable
from them, which already-reported reliability findings sit in that area, and
how much of that could actually be resolved — and turns the answers into a
review recommendation. Every contributing factor is named in
``risk_factors`` so a human can disagree with any single one of them.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence

from app.models.change_impact import (
    RISK_LEVEL_RANK,
    ChangeImpactReport,
    ChangeRiskReport,
    Confidence,
    FindingImpact,
    ReviewRecommendation,
    ReviewTarget,
    RiskFactor,
    RiskLevel,
)
from app.services.change_impact_service import ChangeImpactAnalysis, ChangeImpactService

logger = logging.getLogger(__name__)


# A finding's severity string maps onto the risk level it contributes when it
# sits inside the blast radius. An unrecognised severity contributes MEDIUM
# rather than nothing — an unreadable severity is not evidence of safety.
_SEVERITY_TO_RISK: Dict[str, RiskLevel] = {
    "critical": RiskLevel.CRITICAL,
    "high": RiskLevel.HIGH,
    "medium": RiskLevel.MEDIUM,
    "low": RiskLevel.LOW,
}
_UNKNOWN_SEVERITY_RISK = RiskLevel.MEDIUM

# Blast radius at or above this many symbols is reported as wide. Chosen as a
# reporting threshold, not a calibrated one — see the module docstring.
WIDE_BLAST_RADIUS_THRESHOLD = 10

_RECOMMENDATION_BY_LEVEL: Dict[RiskLevel, ReviewRecommendation] = {
    RiskLevel.NONE: ReviewRecommendation.NO_REVIEW_REQUIRED,
    RiskLevel.LOW: ReviewRecommendation.NO_REVIEW_REQUIRED,
    RiskLevel.MEDIUM: ReviewRecommendation.REVIEW_RECOMMENDED,
    RiskLevel.HIGH: ReviewRecommendation.REQUIRES_HUMAN_REVIEW,
    RiskLevel.CRITICAL: ReviewRecommendation.REQUIRES_HUMAN_REVIEW,
}


def _severity_risk(severity: str) -> RiskLevel:
    return _SEVERITY_TO_RISK.get(severity.strip().lower(), _UNKNOWN_SEVERITY_RISK)


def _max_level(levels: Sequence[RiskLevel]) -> RiskLevel:
    if not levels:
        return RiskLevel.NONE
    return max(levels, key=lambda level: RISK_LEVEL_RANK[level])


def assess_change_risk(impact: ChangeImpactReport) -> ChangeRiskReport:
    """Score a finalized ``ChangeImpactReport`` into a change decision.

    Pure: same impact report in, byte-identical report out.
    """
    report = ChangeRiskReport(
        repository=impact.repository,
        base_revision=impact.base_revision,
        target_revision=impact.target_revision,
        confidence=impact.confidence,
        impact=impact,
        impact_hash=impact.deterministic_hash,
        changed_file_count=len(impact.changed_files),
        changed_symbol_count=len(impact.changed_symbols),
        blast_radius_size=impact.blast_radius_size(),
        affected_entrypoints=list(impact.affected_entrypoints),
    )

    in_radius = [f for f in impact.finding_impacts if f.is_in_blast_radius()]
    outside = [f for f in impact.finding_impacts if f.relation == "outside"]
    unresolved = [f for f in impact.finding_impacts if f.relation == "unresolved"]

    report.findings_evaluated = len(impact.finding_impacts)
    report.findings_in_blast_radius = len(in_radius)
    report.findings_outside_blast_radius = len(outside)
    report.findings_unresolved_location = len(unresolved)

    if not impact.changed_files:
        report.risk_level = RiskLevel.NONE
        report.recommendation = ReviewRecommendation.NO_REVIEW_REQUIRED
        report.summary = "No changes detected between revisions; nothing to assess."
        return report.finalize()

    _add_finding_factors(report, in_radius, bool(impact.affected_entrypoints))
    _add_entrypoint_factor(report, impact)
    _add_blast_radius_factor(report, impact)
    _add_unresolved_factors(report, impact, unresolved)
    _add_confidence_factor(report, impact)
    _add_baseline_factor(report, impact)

    report.risk_level = _max_level([f.level for f in report.risk_factors])
    report.recommendation = _RECOMMENDATION_BY_LEVEL[report.risk_level]

    _add_review_targets(report, impact, in_radius, unresolved)
    _add_caveats(report, impact, in_radius, outside)
    report.summary = _build_summary(report)

    return report.finalize()


# ── Factors ─────────────────────────────────────────────────────────


def _add_finding_factors(
    report: ChangeRiskReport,
    in_radius: List[FindingImpact],
    has_entrypoints: bool,
) -> None:
    """One factor per severity present inside the radius.

    Grouped by severity rather than one factor per finding so the factor list
    stays readable on a change that touches a hot file; the individual
    findings are listed as evidence and as review targets.
    """
    by_severity: Dict[str, List[FindingImpact]] = {}
    for impact in in_radius:
        by_severity.setdefault(impact.severity.strip().lower() or "unknown", []).append(impact)

    for severity, impacts in by_severity.items():
        level = _severity_risk(severity)
        report.risk_factors.append(
            RiskFactor(
                kind="reliability_finding_in_blast_radius",
                level=level,
                detail=(
                    f"{len(impacts)} {severity}-severity reliability finding(s) "
                    f"resolve to symbols inside the affected area"
                ),
                evidence=[
                    f"{i.file_path}:{i.line_range} -> {i.resolved_node_id} ({i.relation})"
                    for i in impacts
                ],
            )
        )

        # A medium finding on code reachable from a request handler is worse
        # than the same finding on an internal helper, because the entry point
        # is how it gets reached. Recorded as its own factor so the escalation
        # is visible rather than folded into the severity mapping.
        if has_entrypoints and level == RiskLevel.MEDIUM:
            report.risk_factors.append(
                RiskFactor(
                    kind="finding_reachable_from_entrypoint",
                    level=RiskLevel.HIGH,
                    detail=(
                        "medium-severity finding(s) sit in an affected area that "
                        "an API entry point reaches"
                    ),
                    evidence=sorted(report.affected_entrypoints),
                )
            )


def _add_entrypoint_factor(report: ChangeRiskReport, impact: ChangeImpactReport) -> None:
    if not impact.affected_entrypoints:
        return
    report.risk_factors.append(
        RiskFactor(
            kind="entrypoint_reachable",
            level=RiskLevel.MEDIUM,
            detail=(
                f"{len(set(impact.affected_entrypoints))} API entry point(s) reach the "
                f"changed code"
            ),
            evidence=sorted(set(impact.affected_api_surfaces or impact.affected_entrypoints)),
        )
    )


def _add_blast_radius_factor(report: ChangeRiskReport, impact: ChangeImpactReport) -> None:
    size = impact.blast_radius_size()
    if size < WIDE_BLAST_RADIUS_THRESHOLD:
        return
    report.risk_factors.append(
        RiskFactor(
            kind="wide_blast_radius",
            level=RiskLevel.MEDIUM,
            detail=(
                f"{size} symbols are reachable from the change "
                f"(threshold {WIDE_BLAST_RADIUS_THRESHOLD})"
            ),
        )
    )


def _add_unresolved_factors(
    report: ChangeRiskReport,
    impact: ChangeImpactReport,
    unresolved: List[FindingImpact],
) -> None:
    """Uncertainty about a finding's position is reported, never resolved.

    A finding whose location could not be mapped to a symbol is not counted as
    inside the radius — there is no evidence for that — but neither is it
    treated as outside. When it sits in a file the diff touched it raises the
    floor to MEDIUM, because it may well be in the changed code.
    """
    changed_files = set(impact.changed_files)
    in_changed_file = sorted(
        {f"{u.file_path}:{u.line_range}" for u in unresolved if u.file_path in changed_files}
    )
    if in_changed_file:
        report.risk_factors.append(
            RiskFactor(
                kind="unresolved_finding_location_in_changed_file",
                level=RiskLevel.MEDIUM,
                detail=(
                    f"{len(in_changed_file)} reliability finding location(s) in changed "
                    f"files could not be mapped to a symbol, so whether they are inside "
                    f"the affected area is unknown"
                ),
                evidence=in_changed_file,
            )
        )

    if impact.unresolved_references:
        report.risk_factors.append(
            RiskFactor(
                kind="unresolved_changed_lines",
                level=RiskLevel.LOW,
                detail=(
                    f"{len(impact.unresolved_references)} changed range(s) could not be "
                    f"attributed to a symbol, so their downstream impact is not covered"
                ),
                evidence=[
                    f"{u.file_path}:{u.detail} ({u.reason})"
                    for u in impact.unresolved_references
                ],
            )
        )


def _add_confidence_factor(report: ChangeRiskReport, impact: ChangeImpactReport) -> None:
    if impact.confidence != Confidence.LOW:
        return
    report.risk_factors.append(
        RiskFactor(
            kind="low_impact_confidence",
            level=RiskLevel.MEDIUM,
            detail=(
                "impact resolution confidence is low, so the blast radius is likely "
                "incomplete and the finding intersection under-reports"
            ),
        )
    )


def _add_baseline_factor(report: ChangeRiskReport, impact: ChangeImpactReport) -> None:
    """Floor for a change with no other factor: code changed, nothing known against it."""
    if report.risk_factors:
        return
    report.risk_factors.append(
        RiskFactor(
            kind="code_changed_no_known_risk",
            level=RiskLevel.LOW,
            detail=(
                f"{len(impact.changed_symbols)} symbol(s) changed with no reliability "
                f"finding, entry point, or wide blast radius in the affected area"
            ),
        )
    )


# ── Review targets, caveats, summary ────────────────────────────────


def _add_review_targets(
    report: ChangeRiskReport,
    impact: ChangeImpactReport,
    in_radius: List[FindingImpact],
    unresolved: List[FindingImpact],
) -> None:
    for finding in in_radius:
        report.review_targets.append(
            ReviewTarget(
                kind="finding",
                location=f"{finding.file_path}:{finding.line_range}",
                detail=(
                    f"{finding.severity} finding on {finding.resolved_node_id} "
                    f"({finding.relation} to the change)"
                ),
            )
        )

    for node_id in set(impact.affected_entrypoints):
        report.review_targets.append(
            ReviewTarget(
                kind="entrypoint",
                location=node_id,
                detail="API entry point reaching the changed code",
            )
        )

    changed_files = set(impact.changed_files)
    for finding in unresolved:
        if finding.file_path not in changed_files:
            continue
        report.review_targets.append(
            ReviewTarget(
                kind="unresolved_location",
                location=f"{finding.file_path}:{finding.line_range}",
                detail=(
                    f"{finding.severity} finding in a changed file whose position "
                    f"could not be resolved ({finding.reason})"
                ),
            )
        )


def _add_caveats(
    report: ChangeRiskReport,
    impact: ChangeImpactReport,
    in_radius: List[FindingImpact],
    outside: List[FindingImpact],
) -> None:
    if outside:
        report.caveats.append(
            f"{len(outside)} reliability finding location(s) resolved outside the blast "
            f"radius and did not contribute to this risk level."
        )
    if any(f.overlapping_symbol_count > 1 for f in in_radius):
        report.caveats.append(
            "Some findings report a line range spanning several symbols, so their "
            "attribution to a specific symbol is approximate."
        )
    if impact.confidence != Confidence.HIGH:
        report.caveats.append(
            f"Impact resolution confidence is {impact.confidence.value}; the blast "
            f"radius may be incomplete."
        )
    if any(not path.endswith(".py") for path in impact.changed_files):
        report.caveats.append(
            "Non-Python changed files are not covered by symbol extraction and were "
            "not analysed for impact."
        )


def _build_summary(report: ChangeRiskReport) -> str:
    return (
        f"{report.risk_level.value.upper()} risk: {report.changed_symbol_count} changed "
        f"symbol(s), {report.blast_radius_size} symbol(s) in the blast radius, "
        f"{report.findings_in_blast_radius} of {report.findings_evaluated} finding "
        f"location(s) inside it, {len(set(report.affected_entrypoints))} entry point(s) "
        f"affected. Recommendation: {report.recommendation.value}."
    )


# ── Service ─────────────────────────────────────────────────────────


class ChangeRiskService:
    """End-to-end change analysis: diff -> blast radius -> risk decision.

    Thin composition over ``ChangeImpactService`` and ``assess_change_risk``.
    """

    def __init__(self, impact_service: Optional[ChangeImpactService] = None) -> None:
        self._impact_service = impact_service or ChangeImpactService()

    def assess(
        self,
        repo_path: str,
        base_revision: str,
        target_revision: str,
        findings: Optional[Sequence[Any]] = None,
        ledger: Optional[Any] = None,
        max_impact_depth: int = 3,
        repository_label: Optional[str] = None,
        precomputed_analysis: Optional[ChangeImpactAnalysis] = None,
    ) -> ChangeRiskReport:
        """Analyse ``base..target`` and return the change decision.

        Parameters
        ----------
        findings:
            Existing reliability findings — ``IntelligenceProposal`` objects
            or the dicts they serialise to. Never re-analysed here.
        ledger:
            Optional ``RunLedgerWriter``. When given, the impact service
            records ``CHANGE_IMPACT_ANALYZED`` and this method records
            ``CHANGE_RISK_ASSESSED`` after it.
        repository_label:
            Stable repository identity for the report, in place of the local
            clone path. Keeps the deterministic hash stable across clones.
        precomputed_analysis:
            Optional impact report plus its exact graph. When supplied, this
            method only intersects findings and scores risk; it does not rerun
            the diff or rebuild the graph.
        """
        finding_dicts = _normalise_findings(findings)

        analysis = precomputed_analysis
        if analysis is None:
            analysis = self._impact_service.compute_change_impact_with_graph(
                repo_path=repo_path,
                base_revision=base_revision,
                target_revision=target_revision,
                max_impact_depth=max_impact_depth,
                repository_label=repository_label,
            )

        return self.assess_precomputed(
            analysis,
            findings=finding_dicts,
            ledger=ledger,
        )

    def assess_precomputed(
        self,
        analysis: ChangeImpactAnalysis,
        findings: Optional[Sequence[Any]] = None,
        ledger: Optional[Any] = None,
    ) -> ChangeRiskReport:
        """Score findings against one existing impact calculation.

        The report and graph in ``analysis`` are reused directly: no diff is
        recomputed and no second graph is built.
        """

        finding_dicts = _normalise_findings(findings)
        impact = self._impact_service.intersect_findings(
            analysis,
            finding_dicts or None,
        )
        self._impact_service.record(impact, ledger)

        report = assess_change_risk(impact)
        self._record(report, ledger)
        return report

    @staticmethod
    def _record(report: ChangeRiskReport, ledger: Optional[Any]) -> None:
        if ledger is None or not hasattr(ledger, "append_event"):
            return
        try:
            ledger.append_event(
                "CHANGE_RISK_ASSESSED",
                summary=report.summary or "Change risk assessment completed",
                actor="system",
                actor_role="System",
                phase="PHASE_20",
                payload_ref=report.deterministic_hash,
            )
        except Exception as e:  # non-fatal, matches the ledger's own failure policy
            logger.warning("Failed to record CHANGE_RISK_ASSESSED event: %s", e)


def _normalise_findings(findings: Optional[Sequence[Any]]) -> List[Dict[str, Any]]:
    """Accept ``IntelligenceProposal`` objects or plain dicts.

    Kept here rather than in ``ChangeImpactService`` so the backend impact
    service stays free of ``agent.intelligence`` imports.
    """
    if not findings:
        return []
    out: List[Dict[str, Any]] = []
    for finding in findings:
        if isinstance(finding, dict):
            out.append(finding)
        elif hasattr(finding, "to_dict"):
            out.append(finding.to_dict())
        else:
            logger.warning("Skipping finding of unsupported type %s", type(finding).__name__)
    return out
