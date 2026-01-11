"""
Run Ledger — Phase 7.1 Implementation

Immutable, append-only execution timeline for AGI Engineer runs.

Design Principles (from Phase 6.3):
- Append-only (no deletes, no edits)
- Sequence-based ordering (0, 1, 2, ...)
- One RunLedger per run_id
- JSON persistence (no database)
- Failure-tolerant (LEGACY mode fallback)

Directory Structure:
  ~/.agi-engineer/ledger/{run_id}/
    ├── ledger.json       (run metadata)
    └── events.jsonl      (append-only event stream)
"""
import os
import json
import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class RunLedgerWriter:
    """
    Write-only ledger for recording immutable run execution timeline.
    
    Usage:
        ledger = RunLedgerWriter(run_id="run-123", repo_id="owner/repo")
        ledger.create_ledger()
        ledger.append_event("RUN_STARTED", "Execution began")
        ledger.append_event("FIX_APPLIED", "Fixed F401 in utils.py")
        ledger.seal("COMPLETE")
    """
    
    def __init__(
        self,
        run_id: str,
        repo_id: str,
        environment: str = "DEV",
        initiated_by: str = "CLI"
    ):
        """
        Initialize ledger writer.
        
        Args:
            run_id: Unique run identifier (from Phase 1)
            repo_id: Repository identifier (owner/repo or path hash)
            environment: Execution environment (DEV|STAGING|PROD)
            initiated_by: How run was triggered (CLI|DASHBOARD|API|SYSTEM)
        """
        self.run_id = run_id
        self.repo_id = repo_id
        self.environment = environment
        self.initiated_by = initiated_by
        
        # Ledger directory
        self.ledger_dir = os.path.expanduser(f"~/.agi-engineer/ledger/{run_id}")
        self.ledger_file = os.path.join(self.ledger_dir, "ledger.json")
        self.events_file = os.path.join(self.ledger_dir, "events.jsonl")
        
        # State tracking
        self.next_sequence = 0
        self.sealed = False
        self.started_at = None
        self.ended_at = None
        
        # Error tracking (non-fatal)
        self.enabled = True
    
    def create_ledger(self) -> bool:
        """
        Create RunLedger and initialize with RUN_CREATED event.
        
        Returns:
            True if successful, False if failed (non-fatal)
        """
        try:
            # Create directory
            os.makedirs(self.ledger_dir, exist_ok=True)
            
            # Initialize ledger metadata
            self.started_at = datetime.utcnow().isoformat() + "Z"
            
            ledger = {
                "run_id": self.run_id,
                "repo_id": self.repo_id,
                "environment": self.environment,
                "run_policy_id": "LEGACY",  # Phase 7.1: no policy resolution yet
                "started_at": self.started_at,
                "ended_at": None,
                "final_state": None,
                "initiated_by": self.initiated_by,
                "ledger_version": 1,
                "immutable": True
            }
            
            # Write ledger.json
            with open(self.ledger_file, 'w') as f:
                json.dump(ledger, f, indent=2)
            
            # Initialize events.jsonl (empty for now)
            with open(self.events_file, 'w') as f:
                pass  # Create empty file
            
            # Append first event: RUN_CREATED (sequence=0)
            self.append_event(
                event_type="RUN_CREATED",
                summary=f"Run initialized for {self.repo_id}",
                actor="system",
                actor_role="System",
                phase="PHASE_6",
                payload_ref=None
            )
            
            logger.info(f"RunLedger created: {self.ledger_dir}")
            return True
            
        except Exception as e:
            # Non-fatal: log error and disable ledger
            logger.warning(f"Failed to create ledger for {self.run_id}: {e}")
            self.enabled = False
            return False
    
    def append_event(
        self,
        event_type: str,
        summary: str,
        actor: str = "system",
        actor_role: str = "System",
        phase: str = "PHASE_6",
        payload_ref: Optional[str] = None
    ) -> bool:
        """
        Append immutable event to timeline.
        
        Args:
            event_type: Event type from Phase 6.3 taxonomy
            summary: Human-readable description (max 1000 chars)
            actor: Who caused this event (system, agent name, user email)
            actor_role: System|Agent|Human
            phase: PHASE_1 through PHASE_6
            payload_ref: Reference to external immutable record (UUID or string)
        
        Returns:
            True if successful, False if failed (non-fatal)
        """
        # Skip if ledger disabled
        if not self.enabled:
            return False
        
        # Prevent writes after seal
        if self.sealed:
            logger.warning(f"Cannot append event to sealed ledger: {self.run_id}")
            return False
        
        try:
            # Build event
            event = {
                "id": str(uuid.uuid4()),
                "run_id": self.run_id,
                "sequence": self.next_sequence,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "event_type": event_type,
                "actor": actor,
                "actor_role": actor_role,
                "phase": phase,
                "payload_ref": payload_ref,
                "summary": summary[:1000]  # Enforce max length
            }
            
            # Append to events.jsonl (one JSON object per line)
            with open(self.events_file, 'a') as f:
                f.write(json.dumps(event) + '\n')
            
            # Increment sequence
            self.next_sequence += 1
            
            logger.debug(f"Event appended: {event_type} (seq={event['sequence']})")
            return True
            
        except Exception as e:
            # Non-fatal: log error but continue execution
            logger.warning(f"Failed to append event {event_type} to ledger {self.run_id}: {e}")
            return False
    
    def seal(self, final_state: str) -> bool:
        """
        Seal ledger with terminal state.
        
        Args:
            final_state: COMPLETE|INCOMPLETE|ABORTED|REJECTED
        
        Returns:
            True if successful, False if failed (non-fatal)
        """
        # Skip if ledger disabled
        if not self.enabled:
            return False
        
        # Already sealed
        if self.sealed:
            logger.warning(f"Ledger already sealed: {self.run_id}")
            return False
        
        try:
            # Append terminal event
            terminal_event_map = {
                "COMPLETE": "RUN_COMPLETED",
                "INCOMPLETE": "RUN_ABORTED",  # Operational failure
                "ABORTED": "RUN_ABORTED",
                "REJECTED": "RUN_REJECTED"
            }
            
            terminal_event = terminal_event_map.get(final_state, "RUN_COMPLETED")
            
            self.append_event(
                event_type=terminal_event,
                summary=f"Run finished with state: {final_state}",
                actor="system",
                actor_role="System",
                phase="PHASE_6",
                payload_ref=None
            )
            
            # Update ledger.json with final state
            self.ended_at = datetime.utcnow().isoformat() + "Z"
            
            with open(self.ledger_file, 'r') as f:
                ledger = json.load(f)
            
            ledger['ended_at'] = self.ended_at
            ledger['final_state'] = final_state
            
            with open(self.ledger_file, 'w') as f:
                json.dump(ledger, f, indent=2)
            
            # Mark sealed
            self.sealed = True
            
            logger.info(f"RunLedger sealed: {self.run_id} (state={final_state})")
            return True
            
        except Exception as e:
            # Non-fatal: log error but continue
            logger.warning(f"Failed to seal ledger {self.run_id}: {e}")
            return False
    
    def get_event_count(self) -> int:
        """
        Get total number of events recorded.
        
        Returns:
            Event count (equals next_sequence)
        """
        return self.next_sequence
    
    def is_enabled(self) -> bool:
        """
        Check if ledger is enabled (not disabled due to errors).
        
        Returns:
            True if ledger is operational
        """
        return self.enabled
    
    def get_ledger_path(self) -> str:
        """
        Get absolute path to ledger directory.
        
        Returns:
            Path string
        """
        return self.ledger_dir


# Convenience factory function
def create_run_ledger(
    run_id: str,
    repo_id: str,
    environment: str = "DEV",
    initiated_by: str = "CLI"
) -> Optional[RunLedgerWriter]:
    """
    Factory function to create and initialize a RunLedger.
    
    Args:
        run_id: Unique run identifier
        repo_id: Repository identifier
        environment: DEV|STAGING|PROD
        initiated_by: CLI|DASHBOARD|API|SYSTEM
    
    Returns:
        RunLedgerWriter instance, or None if creation failed (LEGACY mode)
    """
    try:
        ledger = RunLedgerWriter(
            run_id=run_id,
            repo_id=repo_id,
            environment=environment,
            initiated_by=initiated_by
        )
        
        if ledger.create_ledger():
            return ledger
        else:
            # Creation failed; return None (LEGACY mode)
            logger.warning(f"Ledger creation failed for {run_id}; operating in LEGACY mode")
            return None
    
    except Exception as e:
        # Non-fatal: log and return None
        logger.warning(f"Exception during ledger creation: {e}")
        return None


# Helper: Read ledger (read-only, for future query support)
def read_ledger(run_id: str) -> Optional[Dict[str, Any]]:
    """
    Read RunLedger metadata (read-only).
    
    Args:
        run_id: Run identifier
    
    Returns:
        Ledger dict, or None if not found
    """
    try:
        ledger_file = os.path.expanduser(f"~/.agi-engineer/ledger/{run_id}/ledger.json")
        
        if not os.path.exists(ledger_file):
            return None
        
        with open(ledger_file, 'r') as f:
            return json.load(f)
    
    except Exception as e:
        logger.warning(f"Failed to read ledger {run_id}: {e}")
        return None


# Helper: Read events (read-only, for future query support)
def read_events(run_id: str) -> list:
    """
    Read all RunEvents for a run (read-only).
    
    Args:
        run_id: Run identifier
    
    Returns:
        List of event dicts, sorted by sequence
    """
    try:
        events_file = os.path.expanduser(f"~/.agi-engineer/ledger/{run_id}/events.jsonl")
        
        if not os.path.exists(events_file):
            return []
        
        events = []
        with open(events_file, 'r') as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))
        
        # Sort by sequence (should already be ordered, but ensure)
        events.sort(key=lambda e: e['sequence'])
        
        return events
    
    except Exception as e:
        logger.warning(f"Failed to read events for {run_id}: {e}")
        return []
