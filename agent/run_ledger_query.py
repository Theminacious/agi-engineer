"""
Run Ledger — Phase 7.3 Query & Inspection API

Read-only helpers for inspecting immutable run ledgers.

Constraints:
- NO writes or mutations
- Deterministic, side-effect free
- Tolerate missing LEGACY ledgers gracefully
- Use only ~/.agi-engineer/ledger/{run_id}/ledger.json and events.jsonl
- Never throw on malformed data; skip bad records

Public APIs:
- get_full_timeline(run_id) -> List[RunEvent]
- get_run_summary(run_id) -> Dict
- get_events_by_phase(run_id, phase) -> List[RunEvent]
- get_events_by_type(run_id, event_type) -> List[RunEvent]
- get_audit_view(run_id) -> List[Dict]
- trace_causality(run_id, payload_ref) -> List[RunEvent]
"""
import os
import json
from typing import List, Dict, Optional, Any
from datetime import datetime

LEDGER_ROOT = os.path.expanduser("~/.agi-engineer/ledger")

# --- Internal helpers (read-only) -------------------------------------------------

def _ledger_dir(run_id: str) -> str:
    # Support both absolute paths and run_id lookups
    if os.path.isabs(run_id) or os.path.exists(run_id):
        return run_id
    return os.path.join(LEDGER_ROOT, run_id)


def _read_ledger(run_id: str) -> Optional[Dict[str, Any]]:
    """Read ledger.json. Return None if missing or malformed."""
    try:
        path = os.path.join(_ledger_dir(run_id), "ledger.json")
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None


def _read_events(run_id: str) -> List[Dict[str, Any]]:
    """Read events.jsonl. Skip malformed lines. Return [] if missing."""
    events_path = os.path.join(_ledger_dir(run_id), "events.jsonl")
    if not os.path.exists(events_path):
        return []
    events: List[Dict[str, Any]] = []
    try:
        with open(events_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    # Ensure minimal shape
                    if isinstance(obj, dict) and "sequence" in obj and "event_type" in obj:
                        events.append(obj)
                except Exception:
                    # Skip malformed line
                    continue
        # Deterministic sort by sequence only (ignore timestamp)
        events.sort(key=lambda e: e.get("sequence", -1))
        return events
    except Exception:
        return []


def _parse_iso(ts: Optional[str]) -> Optional[datetime]:
    if not ts or not isinstance(ts, str):
        return None
    try:
        # Support trailing 'Z' by normalizing to UTC offset
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts)
    except Exception:
        return None


# --- Public query APIs ------------------------------------------------------------

def get_full_timeline(run_id: str) -> List[Dict[str, Any]]:
    """Return all events sorted by sequence. Never raises; returns [] if missing."""
    return _read_events(run_id)


def get_run_summary(run_id: str) -> Dict[str, Any]:
    """Derived summary from ledger + events.
    Includes: start_time, end_time, duration, final_state, total_events,
              total_fixes_applied, human_approvals_count, policies_referenced, edr_id
    """
    ledger = _read_ledger(run_id) or {}
    events = _read_events(run_id)

    start_time = ledger.get("started_at")
    end_time = ledger.get("ended_at")
    final_state = ledger.get("final_state")

    dt_start = _parse_iso(start_time)
    dt_end = _parse_iso(end_time)
    duration = None
    if dt_start and dt_end:
        try:
            duration = (dt_end - dt_start).total_seconds()
        except Exception:
            duration = None

    total_events = len(events)

    # Count FIX_APPLIED occurrences
    total_fixes_applied = sum(1 for e in events if e.get("event_type") == "FIX_APPLIED")

    # Count human approvals
    def _is_human(role: Optional[str]) -> bool:
        return isinstance(role, str) and role.lower() == "human"

    human_approvals_count = sum(
        1 for e in events
        if e.get("event_type") == "PLAN_APPROVED" and _is_human(e.get("actor_role"))
    )

    # Policies referenced: include ledger.run_policy_id (if not LEGACY) and any event payload_ref
    # for safety/policy-related events deterministically.
    policies: List[str] = []
    run_policy_id = ledger.get("run_policy_id")
    if isinstance(run_policy_id, str) and run_policy_id and run_policy_id.upper() != "LEGACY":
        policies.append(run_policy_id)

    for e in events:
        et = e.get("event_type") or ""
        pref = e.get("payload_ref")
        if pref and (
            et == "SAFETY_CHECK_PASSED" or "POLICY" in et
        ):
            policies.append(str(pref))

    # Deduplicate deterministically
    policies_referenced = sorted({p for p in policies if isinstance(p, str) and p})

    # EDR id: payload_ref from the last EDR_FINALIZED event if present
    edr_id = None
    for e in reversed(events):
        if e.get("event_type") == "EDR_FINALIZED":
            edr_id = e.get("payload_ref")
            break

    return {
        "run_id": ledger.get("run_id", run_id),
        "repo_id": ledger.get("repo_id"),
        "start_time": start_time,
        "end_time": end_time,
        "duration": duration,
        "final_state": final_state,
        "total_events": total_events,
        "total_fixes_applied": total_fixes_applied,
        "human_approvals_count": human_approvals_count,
        "policies_referenced": policies_referenced,
        "edr_id": edr_id,
    }


def get_events_by_phase(run_id: str, phase: str) -> List[Dict[str, Any]]:
    """Filter events by phase (exact match, case-insensitive). Returns [] if missing."""
    phase_norm = phase.upper() if isinstance(phase, str) else None
    events = _read_events(run_id)
    if not phase_norm:
        return []
    return [e for e in events if isinstance(e.get("phase"), str) and e.get("phase").upper() == phase_norm]


def get_events_by_type(run_id: str, event_type: str) -> List[Dict[str, Any]]:
    """Filter events by event_type (exact match). Returns [] if missing."""
    events = _read_events(run_id)
    return [e for e in events if e.get("event_type") == event_type]


def get_audit_view(run_id: str) -> List[Dict[str, Any]]:
    """Flattened view for audit: timestamp | sequence | actor | actor_role | event_type | payload_ref | summary."""
    audit: List[Dict[str, Any]] = []
    for e in _read_events(run_id):
        audit.append({
            "timestamp": e.get("timestamp"),
            "sequence": e.get("sequence"),
            "actor": e.get("actor"),
            "actor_role": e.get("actor_role"),
            "event_type": e.get("event_type"),
            "payload_ref": e.get("payload_ref"),
            "summary": e.get("summary"),
        })
    # Ensure deterministic order by sequence
    audit.sort(key=lambda a: a.get("sequence", -1))
    return audit


def trace_causality(run_id: str, payload_ref: Optional[str]) -> List[Dict[str, Any]]:
    """Return all events referencing the given payload_ref, ordered by sequence."""
    if not payload_ref:
        return []
    events = _read_events(run_id)
    return [e for e in events if e.get("payload_ref") == payload_ref]


# --- Inline verifier (unit-test style; read-only) ---------------------------------
if __name__ == "__main__":
    import sys

    # Try to pick run_id from argv or most recent directory
    run_id = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        if not run_id and os.path.exists(LEDGER_ROOT):
            # Choose most recently modified ledger dir deterministically
            dirs = [d for d in os.listdir(LEDGER_ROOT) if os.path.isdir(os.path.join(LEDGER_ROOT, d))]
            if dirs:
                dirs.sort(key=lambda d: os.path.getmtime(os.path.join(LEDGER_ROOT, d)), reverse=True)
                run_id = dirs[0]
    except Exception:
        run_id = None

    if not run_id:
        print("No ledger found. Queries return empty results gracefully.")
        sys.exit(0)

    print("=== Run Ledger Query Verifier ===")
    print(f"run_id: {run_id}")

    events = get_full_timeline(run_id)
    print(f"Timeline events: {len(events)}")

    summary = get_run_summary(run_id)
    print("Summary:")
    for k in [
        "start_time", "end_time", "duration", "final_state",
        "total_events", "total_fixes_applied", "human_approvals_count",
        "policies_referenced", "edr_id"
    ]:
        print(f"  - {k}: {summary.get(k)}")

    # Types
    edr_events = get_events_by_type(run_id, "EDR_FINALIZED")
    print(f"EDR_FINALIZED events: {len(edr_events)}")

    # Phase
    phase6 = get_events_by_phase(run_id, "PHASE_6")
    print(f"PHASE_6 events: {len(phase6)}")

    # Audit view (head)
    audit = get_audit_view(run_id)
    print("Audit head:")
    for row in audit[:5]:
        print(f"  seq={row['sequence']} type={row['event_type']} actor={row['actor_role']} ts={row['timestamp']}")

    # Causality trace using edr_id if available
    if summary.get("edr_id"):
        trace = trace_causality(run_id, summary["edr_id"]) 
        print(f"Causality for edr_id {summary['edr_id']}: {len(trace)} events")
    else:
        print("No EDR id present; skipping causality trace.")
