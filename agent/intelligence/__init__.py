"""
Intelligence Module — Phase 11.2 & 11.3

This module implements proposal-only analysis of source repositories.
All analyzers produce structured proposals WITHOUT modifying code or executing logic.

Phase 11.2: Intelligence analyzers detect complex multi-file issues.
Phase 11.3: Ledger integration records proposals as immutable evidence.

Key invariants:
- All analysis is deterministic and static
- All outputs conform to Phase 11.1 schema
- All proposals are ledger-recordable events
- No side effects, no state mutations, no code generation
- Ledger writes are non-fatal (failures don't crash analysis)
"""

from agent.intelligence.proposal import (
    IntelligenceProposal,
    BugClass,
    Severity,
    EffortEstimate,
    AffectedFile,
    FixStrategy,
)
from agent.intelligence.orchestrator import IntelligenceOrchestrator, run_intelligence_analysis
from agent.intelligence.ledger_adapter import (
    proposal_to_ledger_event,
    proposal_to_runledger_format,
)

__all__ = [
    # Proposal data model
    'IntelligenceProposal',
    'BugClass',
    'Severity',
    'EffortEstimate',
    'AffectedFile',
    'FixStrategy',
    
    # Orchestration
    'IntelligenceOrchestrator',
    'run_intelligence_analysis',
    
    # Ledger integration (Phase 11.3)
    'proposal_to_ledger_event',
    'proposal_to_runledger_format',
]