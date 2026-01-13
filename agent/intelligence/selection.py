"""
Phase 13.2: Analyzer Selection (Pure Data Model)

- Represents which analyzers are enabled for a run
- Records the user's subscription plan
- Pure data: no behavior, no validation logic
- Deterministic and JSON-serializable
- Ledger-recordable via adapter (no direct ledger logic here)
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any


@dataclass(frozen=True)
class AnalyzerSelection:
    """Pure data model for analyzer selection.
    
    Fields:
    - plan: 'developer' | 'team' | 'enterprise'
    - enabled_analyzers: list of stable analyzer IDs (from registry)
    
    No behavior or validation included to keep the model pure and replayable.
    """
    plan: str
    enabled_analyzers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Deterministic JSON-serializable representation."""
        # Sort analyzers for deterministic serialization only (does not imply execution order)
        return {
            "plan": self.plan,
            "enabled_analyzers": sorted(self.enabled_analyzers),
        }

    def to_json_ready(self) -> Dict[str, Any]:
        """Alias for clarity when preparing ledger payloads."""
        return self.to_dict()
