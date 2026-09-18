"""Read-side view of a persisted ChangeRiskReport.

Shapes PRAnalysis.change_risk_report into a stable response contract so the
router never returns raw column layout, and the frontend never reads the
report's internal nesting.

Reports what the analysis found: which symbols the diff touched, what the graph
says is reachable from them, which reliability findings sit in that area, and
the deterministic hashes proving it. Not a prediction of production impact.
"""

from typing import Any, Dict, List, Optional

RISK_LEVELS = ("none", "low", "medium", "high", "critical")

RECOMMENDATION_LABELS = {
    "no_review_required": "No review required",
    "review_recommended": "Review recommended",
    "requires_human_review": "Human review required",
}


def _as_list(value: Any) -> List[Any]:
    return list(value) if isinstance(value, list) else []


def _as_dict(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _int(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _optional_list(value: Any) -> Optional[List[Any]]:
    return list(value) if isinstance(value, list) else None


def _bounded_text(value: Any, limit: int = 1000) -> str:
    text = str(value or "")
    return text if len(text) <= limit else text[:limit] + "...[truncated]"


def _attribution_summary(attributions: Any) -> Optional[Dict[str, Any]]:
    """Group per-finding attributions into counts by category.

    Returns ``None`` when attributions are unavailable (baseline comparison
    did not run), preserving the None-vs-empty-list distinction.
    """
    if not isinstance(attributions, list):
        return None
    counts: Dict[str, int] = {}
    for item in attributions:
        if isinstance(item, dict):
            cat = item.get("attribution", "UNKNOWN")
            counts[cat] = counts.get(cat, 0) + 1
    return {
        "total": len(attributions),
        "by_attribution": dict(sorted(counts.items())),
        "change_related_count": sum(
            counts.get(cat, 0)
            for cat in ("DIRECT_CHANGE", "CHANGED_FILE", "CALLER_IMPACT", "DOWNSTREAM_IMPACT")
        ),
        "outside_count": counts.get("OUTSIDE_IMPACT", 0),
        "unresolved_count": counts.get("UNRESOLVED", 0) + counts.get("UNKNOWN", 0),
    }


def _command_summaries(value: Any) -> Optional[List[Dict[str, Any]]]:
    if not isinstance(value, list):
        return None
    summaries = []
    for command in value:
        if not isinstance(command, dict):
            continue
        summaries.append({
            "check": command.get("check"),
            "command": command.get("command"),
            "status": command.get("status"),
            "exit_code": command.get("exit_code"),
            "duration_ms": command.get("duration_ms"),
            "reason": command.get("reason"),
            "stdout": _bounded_text(command.get("stdout")),
            "stderr": _bounded_text(command.get("stderr")),
        })
    return summaries


def unavailable_view(reason: Optional[str]) -> Dict[str, Any]:
    return {
        "available": False,
        "unavailable_reason": reason or "No change risk assessment was produced.",
        "risk": None,
        "impact": None,
        "findings": None,
        "risk_factors": [],
        "review_targets": [],
        "finding_impacts": [],
        "caveats": [],
        "evidence": None,
        "decision": None,
        "verification": None,
        "baseline": None,
        "regression": None,
        "proof": None,
        "governance": None,
    }


def change_risk_view(
    report: Optional[Dict[str, Any]],
    error: Optional[str] = None,
) -> Dict[str, Any]:
    if not isinstance(report, dict) or not report:
        return unavailable_view(error)

    impact = _as_dict(report.get("impact"))
    decision = _as_dict(report.get("decision"))
    verification = _as_dict(report.get("verification"))
    proof_hash = verification.get("deterministic_hash")
    requirement = {
        "none": "none",
        "low": "none",
        "medium": "review_recommended",
        "high": "human_review_required",
        "critical": "explicit_approval_required",
    }.get(str(report.get("risk_level") or "").lower())

    return {
        "available": True,
        "unavailable_reason": None,
        "risk": {
            "level": report.get("risk_level"),
            "recommendation": report.get("recommendation"),
            "recommendation_label": RECOMMENDATION_LABELS.get(
                report.get("recommendation") or "", report.get("recommendation")
            ),
            "confidence": report.get("confidence"),
            "summary": report.get("summary"),
        },
        "impact": {
            "repository": report.get("repository"),
            "base_revision": report.get("base_revision"),
            "target_revision": report.get("target_revision"),
            "changed_file_count": _int(report.get("changed_file_count")),
            "changed_symbol_count": _int(report.get("changed_symbol_count")),
            "blast_radius_size": _int(report.get("blast_radius_size")),
            "changed_files": _as_list(impact.get("changed_files")),
            "changed_symbols": [
                {
                    "node_id": s.get("node_id"),
                    "node_type": s.get("node_type"),
                    "file_path": s.get("file_path"),
                    "name": s.get("name"),
                    "change_kind": s.get("change_kind"),
                }
                for s in _as_list(impact.get("changed_symbols"))
                if isinstance(s, dict)
            ],
            "affected_callers": _as_list(impact.get("callers")),
            "downstream_symbols": _as_list(impact.get("downstream_symbols")),
            "affected_entrypoints": _as_list(report.get("affected_entrypoints")),
            "affected_api_surfaces": _as_list(impact.get("affected_api_surfaces")),
            "unresolved_references": [
                {
                    "file_path": reference.get("file_path"),
                    "detail": reference.get("detail"),
                    "reason": reference.get("reason"),
                }
                for reference in _as_list(impact.get("unresolved_references"))
                if isinstance(reference, dict)
            ],
        },
        "findings": {
            "evaluated": _int(report.get("findings_evaluated")),
            "inside_radius": _int(report.get("findings_in_blast_radius")),
            "outside_radius": _int(report.get("findings_outside_blast_radius")),
            "unresolved": _int(report.get("findings_unresolved_location")),
        },
        "risk_factors": [
            {
                "kind": f.get("kind"),
                "level": f.get("level"),
                "detail": f.get("detail"),
                "evidence": _as_list(f.get("evidence")),
            }
            for f in _as_list(report.get("risk_factors"))
            if isinstance(f, dict)
        ],
        "review_targets": [
            {
                "kind": t.get("kind"),
                "location": t.get("location"),
                "detail": t.get("detail"),
            }
            for t in _as_list(report.get("review_targets"))
            if isinstance(t, dict)
        ],
        "finding_impacts": [
            {
                "finding_ref": i.get("finding_ref"),
                "file_path": i.get("file_path"),
                "line_range": i.get("line_range"),
                "severity": i.get("severity"),
                "relation": i.get("relation"),
                "resolved_node_id": i.get("resolved_node_id"),
                "overlapping_symbol_count": _int(i.get("overlapping_symbol_count")),
                "reason": i.get("reason") or "",
            }
            for i in _as_list(impact.get("finding_impacts"))
            if isinstance(i, dict)
        ],
        "caveats": _as_list(report.get("caveats")),
        "evidence": {
            "impact_hash": report.get("impact_hash"),
            "risk_hash": report.get("deterministic_hash"),
        },
        "decision": {
            "risk_level": decision.get("risk_level"),
            "score": decision.get("score"),
            "confidence": decision.get("confidence"),
            "reasons": _as_list(decision.get("reasons")),
            "human_review_required": decision.get("human_review_required"),
            "affected_files": _as_list(decision.get("affected_files")),
            "affected_symbols": _as_list(decision.get("affected_symbols")),
            "caller_count": decision.get("caller_count"),
            "downstream_count": decision.get("downstream_count"),
            "change_relationships": _as_list(decision.get("change_relationships")),
        },
        "verification": {
            "state": verification.get("state"),
            "confidence": verification.get("verification_confidence"),
            "required_checks": _as_list(verification.get("required_checks")),
            "completed_checks": _as_list(verification.get("completed_checks")),
            "missing_checks": _as_list(verification.get("missing_checks")),
            "tests_discovered": _optional_list(verification.get("tests_discovered")),
            "tests_executed": _optional_list(verification.get("tests_executed")),
            "test_execution_result": verification.get("test_execution_result"),
            "static_analysis_executed": verification.get("static_analysis_executed"),
            "static_analysis_result": verification.get("static_analysis_result"),
            "command_results": _command_summaries(verification.get("command_results")),
            "relevant_test_selection": verification.get("relevant_test_selection"),
            "reasons": _as_list(verification.get("reasons")),
        },
        "baseline": {
            "base_revision": report.get("base_revision"),
            "status": verification.get("baseline_status"),
            "comparison_status": verification.get("comparison_status"),
            "error": verification.get("baseline_error"),
            "findings_before": _optional_list(verification.get("findings_before")),
        },
        "regression": {
            "new_findings": _optional_list(verification.get("new_findings")),
            "new_findings_attribution": _optional_list(
                verification.get("new_findings_attribution")
            ),
            "attribution_summary": _attribution_summary(
                _optional_list(verification.get("new_findings_attribution"))
            ),
            "unchanged_findings": _optional_list(verification.get("unchanged_findings")),
            "resolved_findings": _optional_list(verification.get("resolved_findings")),
        },
        "proof": {
            "verification_hash": proof_hash,
            "risk_hash": report.get("deterministic_hash"),
            "impact_hash": report.get("impact_hash"),
            "base_revision": report.get("base_revision"),
            "target_revision": report.get("target_revision"),
        },
        "governance": {
            "review_requirement": requirement,
            "acknowledgement_required": requirement == "explicit_approval_required"
            if requirement is not None
            else None,
            "acknowledged": None,
            "approval_state": None,
            "rejection_state": None,
            "application_state": None,
        },
    }


def pr_analysis_summary(pr_analysis: Any) -> Dict[str, Any]:
    return {
        "id": pr_analysis.id,
        "repository": pr_analysis.repository_full_name,
        "pr_number": pr_analysis.pr_number,
        "head_sha": pr_analysis.head_sha,
        "base_branch": pr_analysis.base_branch,
        "status": pr_analysis.status.value if pr_analysis.status else None,
        "reliability_score": (
            pr_analysis.reliability_score.value if pr_analysis.reliability_score else None
        ),
        "critical_risks_count": pr_analysis.critical_risks_count,
        "high_risks_count": pr_analysis.high_risks_count,
        "medium_risks_count": pr_analysis.medium_risks_count,
        "fix_candidates_count": pr_analysis.fix_candidates_count,
        "comment_posted": pr_analysis.comment_posted,
        "status_check_posted": pr_analysis.status_check_posted,
        "status_check_conclusion": pr_analysis.status_check_conclusion,
        "change_risk_level": pr_analysis.change_risk_level,
        "change_risk_recommendation": pr_analysis.change_risk_recommendation,
        "change_risk_hash": pr_analysis.change_risk_hash,
        "change_risk_available": pr_analysis.change_risk_report is not None,
        "ledger_run_id": pr_analysis.ledger_run_id,
        "created_at": pr_analysis.created_at.isoformat() if pr_analysis.created_at else None,
        "completed_at": (
            pr_analysis.completed_at.isoformat() if pr_analysis.completed_at else None
        ),
    }
