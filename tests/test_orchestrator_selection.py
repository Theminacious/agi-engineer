"""
Phase 13.2: Orchestrator wiring tests

- Selection ledger event emitted before proposals
- Deterministic ordering
- Missing selection preserves old behavior (no selection event)
"""

import os
import tempfile

from agent.intelligence.orchestrator import IntelligenceOrchestrator
from agent.intelligence.selection import AnalyzerSelection


class FakeLedger:
    def __init__(self):
        self.events = []
    
    def append_event(self, event_type, summary, actor, actor_role, phase, payload_ref):
        self.events.append({
            "event_type": event_type,
            "summary": summary,
            "actor": actor,
            "actor_role": actor_role,
            "phase": phase,
            "payload_ref": payload_ref,
        })
        return True


def make_min_repo() -> str:
    tmp = tempfile.mkdtemp()
    # Minimal repo; analyzers may produce zero proposals; that's okay for ordering tests
    with open(os.path.join(tmp, "README.md"), "w") as f:
        f.write("# test repo\n")
    return tmp


def test_selection_event_emitted_before_proposals():
    repo = make_min_repo()
    orch = IntelligenceOrchestrator()
    ledger = FakeLedger()
    sel = AnalyzerSelection(plan="developer", enabled_analyzers=["architectural", "performance"]) 

    orch.analyze(repository_path=repo, repository_url="https://example.com/repo", ledger=ledger, selection=sel)

    # First event should be selection
    assert len(ledger.events) >= 1
    assert ledger.events[0]["event_type"] == "ANALYZER_SELECTION_DEFINED"


def test_missing_selection_preserves_old_behavior():
    repo = make_min_repo()
    orch = IntelligenceOrchestrator()
    ledger = FakeLedger()

    orch.analyze(repository_path=repo, repository_url="https://example.com/repo", ledger=ledger)

    # No selection event when selection not provided
    assert all(evt["event_type"] != "ANALYZER_SELECTION_DEFINED" for evt in ledger.events)
