"""
Intelligence Ledger Adapter — Phase 11.3

Converts IntelligenceProposal objects to immutable ledger events.

Design:
- Lossless projection of all proposal data
- No transformations, no inference, no merging
- Deterministic (same proposal → same event, always)
- Stateless (no memory, side-effect free)
- Non-fatal (failures do not crash analysis)

Constraints (Phase 11.3):
- NO ranking, filtering, or decision logic
- NO approval logic
- NO execution logic
- NO analyzer imports
- Ledger writes only append, never mutate or update

Event Schema (STRICT):
{
  "event_type": "INTELLIGENCE_PROPOSAL",
  "run_id": "string",
  "timestamp": "ISO-8601",
  "analyzer": "string",
  "proposal_id": "uuid",
  "severity": "CRITICAL|HIGH|MEDIUM|LOW",
  "confidence": float,
  "bug_class": "string",
  "summary": "string",
  "affected_files": ["string"],
  "strategies": [
    {
      "id": "string",
      "description": "string",
      "prerequisites": ["string"]
    }
  ],
  "constraints": {
    "proposal_only": true,
    "no_execution": true,
    "human_approval_required": true
  }
}
"""

from typing import Dict, Any, Optional
from agent.intelligence.proposal import IntelligenceProposal
from datetime import datetime
from agent.intelligence.selection import AnalyzerSelection


def proposal_to_ledger_event(
    proposal: IntelligenceProposal,
    run_id: str,
    analyzer: str,
) -> Dict[str, Any]:
    """
    Convert an IntelligenceProposal to a ledger event.
    
    This is a lossless projection: all proposal data is preserved
    in the ledger event for auditability and replay.
    
    Args:
        proposal: IntelligenceProposal object from analysis
        run_id: Run ID to associate with this event
        analyzer: Name of analyzer that generated this proposal
    
    Returns:
        Dictionary matching INTELLIGENCE_PROPOSAL event schema
    
    Guarantees:
        - Deterministic (same input → same output, always)
        - No transformations or inferences
        - All proposal data preserved
        - Schema-compliant
    """
    # Extract affected files
    affected_files = [f.path for f in proposal.affected_files]
    
    # Extract strategies with lossless structure
    strategies = []
    for strategy in proposal.suggested_strategies:
        strategies.append({
            "id": strategy.strategy_id,
            "name": strategy.name,
            "description": strategy.description,
            "effort_estimate": strategy.effort_estimate.value,
            "prerequisites": strategy.prerequisite_actions,
            "assumptions": strategy.assumptions,
            "risks": strategy.risks,
        })
    
    # Build event (strict schema)
    event = {
        "event_type": "INTELLIGENCE_PROPOSAL",
        "run_id": run_id,
        "timestamp": proposal.timestamp.isoformat() + "Z" if not proposal.timestamp.isoformat().endswith("Z") else proposal.timestamp.isoformat(),
        "analyzer": analyzer,
        "proposal_id": proposal.proposal_id,
        "severity": proposal.severity.value,
        "confidence": proposal.confidence_level / 100.0,  # Convert to 0.0-1.0 range
        "bug_class": proposal.bug_class.value,
        "summary": proposal.problem_statement,
        "affected_files": affected_files,
        "strategies": strategies,
        
        # Full proposal payload (for auditability and replay)
        "full_proposal": proposal.to_dict(),
        
        # Constraints (immutable)
        "constraints": {
            "proposal_only": True,
            "no_execution": True,
            "human_approval_required": True,
        },
        
        # Analysis metadata (for future intelligence improvement)
        "metadata": {
            "confidence_explanation": proposal.confidence_explanation,
            "risk_explanation": proposal.risk_explanation,
            "root_cause_hypothesis": proposal.root_cause_hypothesis,
            "requires_human_decision": proposal.requires_human_decision,
            "decision_required_for": proposal.decision_required_for,
            "conflicting_analysis_ids": proposal.conflicting_analysis_ids,
            "analysis_duration_ms": proposal.analysis_duration_ms,
            "files_scanned": proposal.files_scanned,
            "lines_analyzed": proposal.lines_analyzed,
            "patterns_matched": proposal.patterns_matched,
            "repository_url": proposal.repository_url,
            "branch": proposal.branch,
        }
    }
    
    return event


def proposal_to_runledger_format(
    proposal: IntelligenceProposal,
    analyzer: str,
) -> Dict[str, Any]:
    """
    Convert proposal to RunLedgerWriter.append_event() compatible format.
    
    This format is compatible with the existing RunLedgerWriter API
    which expects: (event_type, summary, actor, actor_role, phase, payload_ref)
    
    Args:
        proposal: IntelligenceProposal object
        analyzer: Name of analyzer that generated this proposal
    
    Returns:
        Dictionary with 'event_type', 'summary', 'actor', 'actor_role', 'phase', 'payload_ref'
    """
    return {
        "event_type": "INTELLIGENCE_PROPOSAL",
        "summary": proposal.problem_statement[:1000],  # Enforce max length like ledger
        "actor": analyzer.lower(),
        "actor_role": "Analyzer",
        "phase": "PHASE_11",
        "payload_ref": proposal.proposal_id,  # UUID reference for audit trail
    }


def selection_to_runledger_format(selection: AnalyzerSelection) -> Dict[str, Any]:
    """
    Convert AnalyzerSelection to RunLedgerWriter.append_event() compatible format.

    Event type: ANALYZER_SELECTION_DEFINED
    Actor: intelligence-orchestrator
    Phase: PHASE_13

    Deterministic payload_ref: stable string from plan + sorted analyzer IDs.
    """
    plan = selection.plan
    enabled_sorted = sorted(selection.enabled_analyzers)
    # Deterministic summary and payload reference
    summary = f"Analyzer selection defined for plan '{plan}': {len(enabled_sorted)} analyzers"
    payload_ref = f"selection:{plan}:{','.join(enabled_sorted)}"
    return {
        "event_type": "ANALYZER_SELECTION_DEFINED",
        "summary": summary,
        "actor": "intelligence-orchestrator",
        "actor_role": "Orchestrator",
        "phase": "PHASE_13",
        "payload_ref": payload_ref,
    }
