"""
Run Ledger — Phase 7.5 Run Inspection & Visualization (Read-Only)

Constraints:
- Read-only
- No writes
- No execution
- No AI calls
- No ledger mutation

Task:
- Combine replay_run() and query helpers into comprehensive JSON report
- Provide CLI: python3 agent/run_inspect.py <run_id>
"""
import os
import sys
import json
from typing import Dict, Any

# Import Phase 7.3 & 7.4 modules
from run_replay import replay_run, LEDGER_ROOT
from run_ledger_query import (
    get_full_timeline,
    get_run_summary,
    get_events_by_phase,
    get_events_by_type,
    get_audit_view,
    trace_causality,
)


def inspect_run(run_id: str) -> Dict[str, Any]:
    """
    Comprehensive read-only inspection of a run ledger.
    
    Combines:
    - replay_run(run_id): deterministic state reconstruction
    - query helpers: timeline, summary, audit
    
    Returns JSON-safe dict.
    """
    # Phase 7.4: Replay state
    replay_state = replay_run(run_id)
    
    # Phase 7.3: Query helpers
    summary = get_run_summary(run_id)
    timeline = get_full_timeline(run_id)
    audit = get_audit_view(run_id)
    
    # Timeline aggregations (deterministic)
    phases_histogram = {}
    for e in timeline:
        phase = e.get("phase")
        if isinstance(phase, str):
            phases_histogram[phase] = phases_histogram.get(phase, 0) + 1
    
    event_types_histogram = {}
    for e in timeline:
        et = e.get("event_type")
        if isinstance(et, str):
            event_types_histogram[et] = event_types_histogram.get(et, 0) + 1
    
    # Build report (JSON-safe)
    report = {
        "run_id": replay_state.run_id,
        "repo_id": replay_state.repo_id,
        
        # Metadata
        "metadata": {
            "started_at": replay_state.started_at,
            "ended_at": replay_state.ended_at,
            "duration_seconds": replay_state.duration,
            "final_state": replay_state.final_state,
            "event_count": replay_state.event_count,
        },
        
        # Timeline summary
        "timeline": {
            "total_events": len(timeline),
            "phases": phases_histogram,
            "event_types": event_types_histogram,
            "first_event": timeline[0] if timeline else None,
            "last_event": timeline[-1] if timeline else None,
        },
        
        # Decisions
        "decisions": {
            "plan_approved": replay_state.decisions["plan_approved"],
            "approvals_count": len(replay_state.decisions.get("approvals", [])),
            "approvals": replay_state.decisions.get("approvals", []),
        },
        
        # Fixes
        "fixes": {
            "count": replay_state.fixes["count"],
            "items": replay_state.fixes.get("items", []),
        },
        
        # Safety
        "safety": {
            "passed": replay_state.safety["passed"],
            "policy_refs": replay_state.safety.get("policy_refs", []),
            "events_count": replay_state.safety.get("events", 0),
        },
        
        # EDR
        "edr": {
            "id": replay_state.edr.get("id"),
            "finalized": bool(replay_state.edr.get("id")),
        },
        
        # Overrides
        "overrides": {
            "rejected": replay_state.overrides.get("rejected", False),
            "aborted": replay_state.overrides.get("aborted", False),
            "events": replay_state.overrides.get("events", []),
        },
        
        # Issues
        "issues": {
            "detected": replay_state.issues_detected,
        },
        
        # Invariants
        "invariants": {
            "violations": replay_state.invariant_violations,
            "violation_count": len(replay_state.invariant_violations),
        },
        
        # Audit (flattened; limit to first 50 for JSON size)
        "audit_preview": audit[:50],
        
        # Query summary (from Phase 7.3)
        "query_summary": {
            "total_fixes_applied": summary.get("total_fixes_applied", 0),
            "human_approvals_count": summary.get("human_approvals_count", 0),
            "policies_referenced": summary.get("policies_referenced", []),
            "edr_id": summary.get("edr_id"),
        },
    }
    
    # Causality trace (if EDR present)
    edr_id = replay_state.edr.get("id")
    if edr_id:
        trace = trace_causality(run_id, edr_id)
        report["causality_trace"] = {
            "payload_ref": edr_id,
            "events_count": len(trace),
            "events": trace,
        }
    
    return report


# --- CLI usage --------------------------------------------------------------------
if __name__ == "__main__":
    run_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Auto-detect most recent if not provided
    try:
        if not run_id and os.path.exists(LEDGER_ROOT):
            dirs = [d for d in os.listdir(LEDGER_ROOT) if os.path.isdir(os.path.join(LEDGER_ROOT, d))]
            if dirs:
                dirs.sort(key=lambda d: os.path.getmtime(os.path.join(LEDGER_ROOT, d)), reverse=True)
                run_id = dirs[0]
    except Exception:
        run_id = None
    
    if not run_id:
        print("Usage: python3 agent/run_inspect.py <run_id>")
        print("No ledgers found in ~/.agi-engineer/ledger/")
        sys.exit(1)
    
    # Generate report
    report = inspect_run(run_id)
    
    # JSON output
    print(json.dumps(report, indent=2, default=str))
