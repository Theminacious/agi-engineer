"""Change-risk context for fix governance.

Connects a CodeFix back to the PR analysis it came from so an approval decision
is recorded against the change risk that stood at the time, and so a CRITICAL
change requires an explicit acknowledgement rather than an ordinary approval.

Governance events are written to a ledger run of their own,
``{analysis_ledger_run_id}-governance``. The analysis ledger is sealed when the
PR run completes and is immutable; appending decisions taken afterwards belongs
in a separate append-only record that cross-references it.
"""

import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from agent.run_ledger import RunLedgerWriter
from app.models import AnalysisResult, CodeFix, PRAnalysis

logger = logging.getLogger(__name__)

REVIEW_REQUIREMENT = {
    "none": "none",
    "low": "none",
    "medium": "review_recommended",
    "high": "human_review_required",
    "critical": "explicit_approval_required",
}

REQUIREMENT_MESSAGE = {
    "review_recommended": "Change risk is MEDIUM; review of the affected area is recommended.",
    "human_review_required": "Change risk is HIGH; a human must review the affected area.",
    "explicit_approval_required": (
        "Change risk is CRITICAL. Approving this fix requires explicitly "
        "acknowledging the change risk assessment."
    ),
}

GOVERNANCE_LEDGER_SUFFIX = "-governance"


def pr_analysis_for_fix(db: Session, fix: CodeFix) -> Optional[PRAnalysis]:
    """The PR analysis a fix belongs to, or None if it did not come from a PR."""
    if fix.result_id is None:
        return None

    result = db.query(AnalysisResult).filter(AnalysisResult.id == fix.result_id).first()
    if result is None or result.run_id is None:
        return None

    return (
        db.query(PRAnalysis)
        .filter(PRAnalysis.analysis_run_id == result.run_id)
        .first()
    )


def change_risk_context(db: Session, fix: CodeFix) -> Dict[str, Any]:
    """What the change-risk assessment says about the change this fix sits in.

    ``requirement`` is derived from the persisted risk level only. A fix with no
    PR analysis, or a PR whose assessment could not run, carries requirement
    "unknown" — absence of an assessment is not evidence the change is safe.
    """
    pr_analysis = pr_analysis_for_fix(db, fix)
    if pr_analysis is None:
        return {
            "available": False,
            "reason": "fix is not linked to a PR analysis",
            "requirement": "unknown",
            "level": None,
            "recommendation": None,
            "risk_hash": None,
            "pr_analysis_id": None,
            "ledger_run_id": fix.ledger_run_id,
        }

    level = (pr_analysis.change_risk_level or "").lower()
    if not level:
        return {
            "available": False,
            "reason": pr_analysis.change_risk_error
            or "no change risk assessment for this PR",
            "requirement": "unknown",
            "level": None,
            "recommendation": None,
            "risk_hash": None,
            "pr_analysis_id": pr_analysis.id,
            "ledger_run_id": pr_analysis.ledger_run_id,
        }

    return {
        "available": True,
        "reason": None,
        "requirement": REVIEW_REQUIREMENT.get(level, "human_review_required"),
        "level": level,
        "recommendation": pr_analysis.change_risk_recommendation,
        "risk_hash": pr_analysis.change_risk_hash,
        "pr_analysis_id": pr_analysis.id,
        "ledger_run_id": pr_analysis.ledger_run_id,
    }


def blocks_approval(context: Dict[str, Any], acknowledged: bool) -> Optional[str]:
    """Why this approval cannot proceed, or None if it can.

    Only CRITICAL blocks, and only until acknowledged. MEDIUM and HIGH are
    surfaced and recorded, not enforced: nothing here knows whether a human
    already reviewed the change, so refusing would be a claim it cannot make.
    """
    if context.get("requirement") != "explicit_approval_required":
        return None
    if acknowledged:
        return None
    return REQUIREMENT_MESSAGE["explicit_approval_required"]


def governance_ledger(context: Dict[str, Any], repo_id: str) -> Optional[RunLedgerWriter]:
    """Append-only ledger for decisions taken after the analysis run sealed."""
    run_id = context.get("ledger_run_id")
    if not run_id:
        return None
    try:
        return RunLedgerWriter.open_or_create(
            run_id=f"{run_id}{GOVERNANCE_LEDGER_SUFFIX}",
            repo_id=repo_id,
            environment="PRODUCTION",
            initiated_by="API",
        )
    except Exception as e:
        logger.warning("Could not open governance ledger for %s: %s", run_id, e)
        return None


def record_review_requested(
    ledger: Optional[RunLedgerWriter],
    context: Dict[str, Any],
    fix_id: int,
    actor: str,
) -> None:
    """Record that a decision was gated on the change risk."""
    if ledger is None:
        return
    try:
        ledger.append_event(
            event_type="REVIEW_REQUESTED",
            summary=(
                f"Fix #{fix_id} approval gated: change risk "
                f"{(context.get('level') or 'unknown').upper()} requires "
                f"{context.get('requirement')}"
            ),
            actor=actor,
            actor_role="System",
            phase="PHASE_20",
            payload_ref=context.get("risk_hash"),
        )
    except Exception as e:
        logger.warning("Could not record REVIEW_REQUESTED for fix %s: %s", fix_id, e)
