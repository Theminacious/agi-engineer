"""
Run Ledger — Phase 7.4 Deterministic Replay Engine

Constraints:
- Read-only implementation
- No side effects, no disk writes
- No AI calls
- Do not modify existing files or event types
- Deterministic and idempotent: same inputs => same outputs

Task:
- Implement `replay_run(run_id) -> ReplayRunState`
- Load ledger.json and events.jsonl
- Apply event handlers strictly by sequence
- Reconstruct decisions, fixes, EDR, approvals, overrides
- Detect invariant violations (record, do not fix)
"""
import os
import json
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

LEDGER_ROOT = os.path.expanduser("~/.agi-engineer/ledger")

# --- Utilities (read-only) --------------------------------------------------------

def _ledger_dir(run_id: str) -> str:
    # Support both absolute paths and run_id lookups
    if os.path.isabs(run_id) or os.path.exists(run_id):
        return run_id
    return os.path.join(LEDGER_ROOT, run_id)


def _read_ledger(run_id: str) -> Dict[str, Any]:
    try:
        path = os.path.join(_ledger_dir(run_id), "ledger.json")
        if not os.path.exists(path):
            return {}
        with open(path, "r") as f:
            obj = json.load(f)
            return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _read_events(run_id: str) -> List[Dict[str, Any]]:
    events_path = os.path.join(_ledger_dir(run_id), "events.jsonl")
    if not os.path.exists(events_path):
        return []
    out: List[Dict[str, Any]] = []
    try:
        with open(events_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict) and "sequence" in obj and "event_type" in obj:
                        out.append(obj)
                except Exception:
                    # Skip malformed
                    continue
        # Deterministic order by sequence only
        out.sort(key=lambda e: e.get("sequence", -1))
        return out
    except Exception:
        return []


def _parse_iso(ts: Optional[str]) -> Optional[datetime]:
    if not ts or not isinstance(ts, str):
        return None
    try:
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts)
    except Exception:
        return None


# --- Replay state ----------------------------------------------------------------

@dataclass
class ReplayRunState:
    run_id: str
    repo_id: Optional[str] = None
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    duration: Optional[float] = None
    final_state: Optional[str] = None
    event_count: int = 0

    # Derived domains
    issues_detected: int = 0
    decisions: Dict[str, Any] = field(default_factory=lambda: {
        "plan_approved": False,
        "approvals": [],  # List[Dict]: {sequence, actor, actor_role, timestamp}
    })
    safety: Dict[str, Any] = field(default_factory=lambda: {
        "passed": False,
        "policy_refs": [],  # List[str]
        "events": 0,
    })
    fixes: Dict[str, Any] = field(default_factory=lambda: {
        "count": 0,
        "items": [],  # List[Dict]: {sequence, actor, summary}
    })
    edr: Dict[str, Any] = field(default_factory=lambda: {
        "id": None,
    })
    overrides: Dict[str, Any] = field(default_factory=lambda: {
        "rejected": False,
        "aborted": False,
        "events": [],  # List[Dict]: {sequence, event_type, summary}
    })

    phases: Dict[str, int] = field(default_factory=dict)  # counts per phase

    # Invariants
    invariant_violations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# --- Replay Engine (read-only) ---------------------------------------------------

def replay_run(run_id: str) -> ReplayRunState:
    """Deterministic, read-only reconstruction of run state.
    Does not modify files, does not execute side effects.
    """
    ledger = _read_ledger(run_id)
    events = _read_events(run_id)

    state = ReplayRunState(
        run_id=ledger.get("run_id", run_id),
        repo_id=ledger.get("repo_id"),
        started_at=ledger.get("started_at"),
        ended_at=ledger.get("ended_at"),
        final_state=ledger.get("final_state"),
    )

    # Duration
    dt_start = _parse_iso(state.started_at)
    dt_end = _parse_iso(state.ended_at)
    if dt_start and dt_end:
        try:
            state.duration = (dt_end - dt_start).total_seconds()
        except Exception:
            state.duration = None

    # Sequence invariants
    expected_seq = 0
    for idx, e in enumerate(events):
        seq = e.get("sequence")
        if not isinstance(seq, int):
            state.invariant_violations.append(f"non-integer-sequence at index {idx}")
        elif seq != expected_seq:
            state.invariant_violations.append(f"sequence-gap-or-out-of-order: expected {expected_seq}, found {seq}")
            expected_seq = seq  # resync deterministically
        expected_seq = expected_seq + 1

    state.event_count = len(events)

    # Handlers by event_type (deterministic; sequence-driven)
    for e in events:
        et = e.get("event_type")
        role = e.get("actor_role")
        actor = e.get("actor")
        seq = e.get("sequence")
        phase = e.get("phase")
        summary = e.get("summary")
        pref = e.get("payload_ref")

        # Phase counts
        if isinstance(phase, str):
            pkey = phase.upper()
            state.phases[pkey] = state.phases.get(pkey, 0) + 1

        if et == "RUN_CREATED":
            # Nothing to derive; ledger has started_at
            pass
        elif et == "RUN_STARTED":
            # No-op; could mark started flag if needed
            pass
        elif et == "ISSUE_DETECTED":
            state.issues_detected += 1
        elif et == "PLAN_APPROVED":
            state.decisions["plan_approved"] = True
            state.decisions["approvals"].append({
                "sequence": seq,
                "actor": actor,
                "actor_role": role,
                "timestamp": e.get("timestamp"),
            })
        elif et == "SAFETY_CHECK_PASSED":
            state.safety["passed"] = True
            state.safety["events"] = state.safety.get("events", 0) + 1
            if pref:
                state.safety["policy_refs"].append(str(pref))
        elif et == "FIX_APPLIED":
            state.fixes["count"] += 1
            state.fixes["items"].append({
                "sequence": seq,
                "actor": role or actor,
                "summary": summary,
            })
        elif et == "EDR_FINALIZED":
            # Last one wins deterministically
            state.edr["id"] = pref
        elif et == "RUN_COMPLETED":
            # Terminal consistency check
            if state.final_state and state.final_state not in ("COMPLETE", "COMPLETED"):
                state.invariant_violations.append(
                    f"terminal-mismatch: ledger={state.final_state} event=RUN_COMPLETED"
                )
        elif et == "RUN_ABORTED":
            state.overrides["aborted"] = True
            if state.final_state and state.final_state not in ("ABORTED", "INCOMPLETE"):
                state.invariant_violations.append(
                    f"terminal-mismatch: ledger={state.final_state} event=RUN_ABORTED"
                )
            state.overrides["events"].append({
                "sequence": seq,
                "event_type": et,
                "summary": summary,
            })
        elif et == "RUN_REJECTED":
            state.overrides["rejected"] = True
            if state.final_state and state.final_state != "REJECTED":
                state.invariant_violations.append(
                    f"terminal-mismatch: ledger={state.final_state} event=RUN_REJECTED"
                )
            state.overrides["events"].append({
                "sequence": seq,
                "event_type": et,
                "summary": summary,
            })
        else:
            # Unknown event types are tolerated; deterministic no-op
            pass

    # Terminal event presence
    if events:
        last_et = events[-1].get("event_type")
        if last_et not in ("RUN_COMPLETED", "RUN_ABORTED", "RUN_REJECTED"):
            state.invariant_violations.append("no-terminal-event")
    else:
        # No events: LEGACY or failure to create; tolerated
        pass

    # Deduplicate policy refs deterministically
    if isinstance(state.safety.get("policy_refs"), list):
        state.safety["policy_refs"] = sorted({p for p in state.safety["policy_refs"] if p})

    return state


# --- Inline verifier --------------------------------------------------------------
if __name__ == "__main__":
    import sys

    run_id = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        if not run_id and os.path.exists(LEDGER_ROOT):
            dirs = [d for d in os.listdir(LEDGER_ROOT) if os.path.isdir(os.path.join(LEDGER_ROOT, d))]
            if dirs:
                dirs.sort(key=lambda d: os.path.getmtime(os.path.join(LEDGER_ROOT, d)), reverse=True)
                run_id = dirs[0]
    except Exception:
        run_id = None

    if not run_id:
        print("No ledger found. Replay returns default state gracefully.")
        sys.exit(0)

    state = replay_run(run_id)
    print("=== Replay Summary ===")
    print(f"run_id: {state.run_id}")
    print(f"repo_id: {state.repo_id}")
    print(f"final_state: {state.final_state}")
    print(f"events: {state.event_count}")
    print(f"fixes: {state.fixes['count']}")
    print(f"plan_approved: {state.decisions['plan_approved']}")
    print(f"safety_passed: {state.safety['passed']}")
    print(f"edr_id: {state.edr['id']}")
    print(f"invariants: {len(state.invariant_violations)}")
    for v in state.invariant_violations[:5]:
        print(f" - {v}")
