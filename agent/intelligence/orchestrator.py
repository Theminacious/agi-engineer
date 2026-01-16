"""
Intelligence orchestrator.

Coordinates all analyzers, aggregates proposals, and emits ledger events.

Phase 11.3: Ledger Integration
- Accepts optional ledger and run_id for recording proposals
- Ledger writes are NON-FATAL (failures do not crash analysis)
- Proposals are deterministic and replay-safe

Phase 14.2: Plan Enforcement
- Accepts optional plan_context for subscription-based execution
- Filters analyzers based on plan entitlements
- Records skipped analyzers with reasons
- Maintains determinism and auditability
"""

from typing import List, Dict, Set, Optional, Any, Tuple
import os
import uuid
from datetime import datetime
import logging

from agent.intelligence.proposal import IntelligenceProposal
from agent.intelligence.ledger_adapter import proposal_to_ledger_event, proposal_to_runledger_format, selection_to_runledger_format
from agent.intelligence.selection import AnalyzerSelection
from agent.intelligence.selection_validation import validate_selection, compute_execution_order, SelectionValidationError
from agent.intelligence.registry import ANALYZER_REGISTRY, list_all_analyzers, list_analyzers_for_plan

logger = logging.getLogger(__name__)

# Import all analyzers
# Analyzer classes are imported via registry entries (ANALYZER_REGISTRY) to avoid hardcoding.


class IntelligenceOrchestrator:
    """
    Orchestrates all intelligence analyzers.
    
    Responsibilities:
    - Run all analyzers on a repository
    - Aggregate proposals
    - Detect conflicts between analyses
    - Emit proposals as immutable ledger events
    - Track analysis timing and metrics
    - Enforce subscription plan entitlements (Phase 14.2)
    """
    
    def __init__(self):
        """Initialize orchestrator with registry-driven analyzers (developer plan by default for backward compatibility)."""
        self.analyzers = self._instantiate_from_registry_default()
        
        self.run_id = str(uuid.uuid4())
        self.start_time = None
        self.end_time = None
        self.total_proposals = 0
        self.proposals_by_severity = {}
        self.proposals_by_bug_class = {}
        self.conflicting_proposals = []
        
        # Phase 14.2: Track skipped analyzers due to plan restrictions
        self.skipped_analyzers: List[Dict[str, str]] = []
    
    def analyze(
        self,
        repository_path: str,
        repository_url: str,
        branch: str = "main",
        ledger: Optional[Any] = None,
        run_id: Optional[str] = None,
        selection: Optional[AnalyzerSelection] = None,
        plan: Optional[str] = None,
        plan_context: Optional[Any] = None,  # UserPlanContext from backend.app.plans
    ) -> List[IntelligenceProposal]:
        """
        Analyze repository with all analyzers.
        
        Phase 11.3: Optional ledger integration.
        Phase 14.2: Optional plan_context for subscription enforcement.
        
        Args:
            repository_path: Path to repository root
            repository_url: Repository URL (for ledger)
            branch: Git branch being analyzed
            ledger: Optional RunLedgerWriter instance for recording proposals
            run_id: Optional run_id for ledger events (uses self.run_id if not provided)
            selection: Optional analyzer selection
            plan: Optional plan tier string (deprecated in favor of plan_context)
            plan_context: Optional UserPlanContext for plan enforcement
        
        Returns:
            List of intelligence proposals
        
        Guarantees:
            - Proposals are generated deterministically regardless of ledger
            - Ledger failures are non-fatal and never crash analysis
            - Intelligence remains stateless and replayable
            - Plan enforcement is deterministic and auditable
        """
        import time
        self.start_time = time.time()
        
        all_proposals = []
        analyzer_results = {}
        ledger_run_id = run_id or self.run_id
        
        # Phase 14.2: Resolve analyzers with plan enforcement
        analyzers_to_run, skipped_analyzers = self._resolve_analyzers_with_enforcement(
            selection=selection,
            plan=plan,
            plan_context=plan_context
        )
        self.skipped_analyzers = skipped_analyzers
        
        # Track actual analyzers used for this run (for summary/backward compatibility expectations)
        self.analyzers = analyzers_to_run

        # Phase 14.2: Record plan context to ledger if provided (non-fatal)
        if ledger is not None and plan_context is not None:
            try:
                ledger.append_event(
                    event_type="PLAN_CONTEXT_CAPTURED",
                    summary=f"Plan context: {plan_context.plan_tier.value}",
                    actor="SYSTEM",
                    actor_role="SUBSCRIPTION",
                    phase="INTELLIGENCE",
                    payload_ref=plan_context.to_dict(),
                )
            except Exception as e:
                logger.warning(f"Failed to record plan context to ledger: {e}")
        
        # Phase 14.2: Record skipped analyzers to ledger if any (non-fatal)
        if ledger is not None and skipped_analyzers:
            try:
                ledger.append_event(
                    event_type="ANALYZERS_SKIPPED",
                    summary=f"{len(skipped_analyzers)} analyzer(s) skipped due to plan restrictions",
                    actor="SYSTEM",
                    actor_role="SUBSCRIPTION",
                    phase="INTELLIGENCE",
                    payload_ref={'skipped': skipped_analyzers},
                )
            except Exception as e:
                logger.warning(f"Failed to record skipped analyzers to ledger: {e}")

        # If ledger present and selection provided, record selection event (non-fatal)
        if ledger is not None and selection is not None:
            try:
                sel_evt = selection_to_runledger_format(selection)
                ledger.append_event(
                    event_type=sel_evt["event_type"],
                    summary=sel_evt["summary"],
                    actor=sel_evt["actor"],
                    actor_role=sel_evt["actor_role"],
                    phase=sel_evt["phase"],
                    payload_ref=sel_evt["payload_ref"],
                )
            except Exception as e:
                logger.warning(f"Failed to record analyzer selection to ledger: {e}")

        # Run each analyzer (either all, or filtered by selection)
        for analyzer in analyzers_to_run:
            try:
                proposals = analyzer.analyze(
                    repository_path=repository_path,
                    repository_url=repository_url,
                    branch=branch,
                )
                all_proposals.extend(proposals)
                analyzer_results[analyzer.__class__.__name__] = len(proposals)
            except Exception as e:
                # Log error but continue with other analyzers
                print(f"Error in {analyzer.__class__.__name__}: {e}")
                analyzer_results[analyzer.__class__.__name__] = f"ERROR: {str(e)}"
        
        # Finalize run
        self.end_time = time.time()
        
        # Detect conflicts
        self._detect_conflicts(all_proposals)
        
        # Track metrics
        self.total_proposals = len(all_proposals)
        self._track_metrics(all_proposals)
        
        # Add run metadata to proposals
        for proposal in all_proposals:
            proposal.analysis_run_id = self.run_id
        
        # ======== PHASE 11.3: LEDGER INTEGRATION (NON-FATAL) ========
        # Record proposals in ledger if provided
        # Failures do NOT crash analysis - ledger is optional
        if ledger is not None:
            self._record_proposals_to_ledger(
                proposals=all_proposals,
                ledger=ledger,
                run_id=ledger_run_id,
            )
        
        return all_proposals
    
    def _detect_conflicts(self, proposals: List[IntelligenceProposal]) -> None:
        """
        Detect conflicting proposals (same issue detected by multiple analyzers).
        
        Marks conflicting proposals so they can be deduped by governance.
        """
        # Group by file + problem description (simple dedup)
        issues_seen: Dict[str, List[IntelligenceProposal]] = {}
        
        for proposal in proposals:
            # Key: (file, first line of problem statement)
            files_str = ','.join(f.path for f in proposal.affected_files[:3])
            key = f"{files_str}|{proposal.problem_statement[:50]}"
            
            if key not in issues_seen:
                issues_seen[key] = []
            issues_seen[key].append(proposal)
        
        # Mark conflicts
        for key, group in issues_seen.items():
            if len(group) > 1:
                # Multiple analyzers detected similar issue
                for i, proposal in enumerate(group):
                    proposal.conflicting_analysis_ids.extend([
                        p.proposal_id for p in group if p is not proposal
                    ])
                self.conflicting_proposals.extend(group)
    
    def _track_metrics(self, proposals: List[IntelligenceProposal]) -> None:
        """Track proposal metrics."""
        from agent.intelligence.proposal import Severity, BugClass
        
        # By severity
        for severity in Severity:
            count = sum(1 for p in proposals if p.severity == severity)
            if count > 0:
                self.proposals_by_severity[severity.name] = count
        
        # By bug class
        for bug_class in BugClass:
            count = sum(1 for p in proposals if p.bug_class == bug_class)
            if count > 0:
                self.proposals_by_bug_class[bug_class.name] = count
    
    def _record_proposals_to_ledger(
        self,
        proposals: List[IntelligenceProposal],
        ledger: Any,
        run_id: str,
    ) -> None:
        """
        Record proposals to immutable ledger.
        
        Phase 11.3 Implementation: Non-fatal ledger writes.
        
        Args:
            proposals: List of IntelligenceProposal objects
            ledger: RunLedgerWriter instance
            run_id: Run ID for ledger association
        
        Guarantees:
            - Failures do NOT crash analysis
            - Each proposal becomes one INTELLIGENCE_PROPOSAL event
            - Ledger is append-only (no updates or deletes)
            - All proposal data preserved for auditability
        """
        if not ledger or not hasattr(ledger, 'append_event'):
            # Ledger is None or invalid; skip silently
            logger.warning("Ledger not available; skipping proposal recording")
            return
        
        recorded_count = 0
        failed_count = 0
        
        for proposal in proposals:
            try:
                # Get analyzer name from proposal (set by analyzer)
                analyzer_name = getattr(
                    proposal,
                    'analyzer_name',
                    'unknown-analyzer'
                )
                
                # Convert proposal to RunLedger format
                ledger_args = proposal_to_runledger_format(proposal, analyzer_name)
                
                # Append to ledger (non-fatal if it fails)
                success = ledger.append_event(
                    event_type=ledger_args['event_type'],
                    summary=ledger_args['summary'],
                    actor=ledger_args['actor'],
                    actor_role=ledger_args['actor_role'],
                    phase=ledger_args['phase'],
                    payload_ref=ledger_args['payload_ref'],
                )
                
                if success:
                    recorded_count += 1
                else:
                    failed_count += 1
                    logger.warning(f"Failed to record proposal {proposal.proposal_id} to ledger")
                    
            except Exception as e:
                # Ledger write failed; log but continue
                failed_count += 1
                logger.warning(
                    f"Error recording proposal {proposal.proposal_id} to ledger: {e}",
                    exc_info=True
                )
        
        logger.info(
            f"Proposals recorded: {recorded_count}/{len(proposals)} "
            f"(failed: {failed_count})"
        )
    
    def get_summary(self) -> Dict:
        """Get analysis summary."""
        summary = {
            'run_id': self.run_id,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration_seconds': self.end_time - self.start_time if self.end_time else None,
            'total_proposals': self.total_proposals,
            'proposals_by_severity': self.proposals_by_severity,
            'proposals_by_bug_class': self.proposals_by_bug_class,
            'conflicting_proposals_count': len(self.conflicting_proposals),
        }
        
        # Phase 14.2: Include skipped analyzers in summary
        if self.skipped_analyzers:
            summary['skipped_analyzers'] = self.skipped_analyzers
            summary['skipped_count'] = len(self.skipped_analyzers)
        
        return summary

    # ===== Registry-driven helpers =====
    def _instantiate_from_registry_default(self) -> List[Any]:
        """Instantiate analyzers using registry for developer plan to preserve backward compatibility."""
        ids = [aid for aid, _ in list_analyzers_for_plan("developer")]
        return [ANALYZER_REGISTRY[aid]["class"]() for aid in ids]

    def _resolve_analyzers_with_enforcement(
        self,
        selection: Optional[AnalyzerSelection],
        plan: Optional[str],
        plan_context: Optional[Any],  # UserPlanContext
    ) -> Tuple[List[Any], List[Dict[str, str]]]:
        """
        Determine analyzers to run with plan enforcement.
        
        Phase 14.2: Plan context enforcement.
        
        Priority:
        1. selection (if provided) → validate and filter by plan
        2. plan_context (if provided) → filter by allowed analyzers
        3. plan (if provided) → use plan-based filtering
        4. default → developer plan (backward compatibility)
        
        Returns:
            Tuple of (analyzers_to_run, skipped_analyzers)
            
        Skipped analyzers format:
            [{'analyzer_id': str, 'reason': str}, ...]
        """
        skipped = []
        
        # Priority 1: selection
        if selection is not None:
            validate_selection(selection.plan, selection.enabled_analyzers)
            ordered_ids = compute_execution_order(selection.enabled_analyzers)
            
            # Phase 14.2: Filter by plan_context if provided
            if plan_context is not None:
                allowed_ids = plan_context.filter_allowed_analyzers(ordered_ids)
                skipped_ids = [aid for aid in ordered_ids if aid not in allowed_ids]
                
                for aid in skipped_ids:
                    skipped.append({
                        'analyzer_id': aid,
                        'reason': plan_context.get_disallowed_reason(aid),
                    })
                
                return [ANALYZER_REGISTRY[aid]["class"]() for aid in allowed_ids], skipped
            
            return [ANALYZER_REGISTRY[aid]["class"]() for aid in ordered_ids], skipped
        
        # Priority 2: plan_context (Phase 14.2)
        if plan_context is not None:
            # Get all analyzers that could run
            all_ids = [aid for aid, _ in list_all_analyzers()]
            allowed_ids = plan_context.filter_allowed_analyzers(all_ids)
            skipped_ids = [aid for aid in all_ids if aid not in allowed_ids]
            
            for aid in skipped_ids:
                skipped.append({
                    'analyzer_id': aid,
                    'reason': plan_context.get_disallowed_reason(aid),
                })
            
            # Return allowed analyzers in deterministic order
            allowed_ids_sorted = sorted(allowed_ids)
            return [ANALYZER_REGISTRY[aid]["class"]() for aid in allowed_ids_sorted], skipped

        # Priority 3: explicit plan (backward compatibility)
        if plan is not None:
            ids = [aid for aid, _ in list_analyzers_for_plan(plan)]
            return [ANALYZER_REGISTRY[aid]["class"]() for aid in ids], skipped

        # Priority 4: backward-compatible default (developer plan)
        ids = [aid for aid, _ in list_analyzers_for_plan("developer")]
        return [ANALYZER_REGISTRY[aid]["class"]() for aid in ids], skipped
    
    def to_ledger_events(self, proposals: List[IntelligenceProposal]) -> List[Dict]:
        """
        Convert proposals to immutable ledger events.
        
        Args:
            proposals: List of proposals from analysis
        
        Returns:
            List of ledger events ready for recording
        """
        events = []
        
        # Add run start event
        events.append({
            'event_id': str(uuid.uuid4()),
            'event_type': 'INTELLIGENCE_RUN_STARTED',
            'timestamp': datetime.utcnow().isoformat(),
            'data': {
                'run_id': self.run_id,
                'analyzer_count': len(self.analyzers),
            }
        })
        
        # Add proposal events
        for proposal in proposals:
            events.append(proposal.to_ledger_event())
        
        # Add run summary event
        events.append({
            'event_id': str(uuid.uuid4()),
            'event_type': 'INTELLIGENCE_RUN_COMPLETED',
            'timestamp': datetime.utcnow().isoformat(),
            'data': {
                'run_id': self.run_id,
                'total_proposals': len(proposals),
                'summary': self.get_summary(),
            }
        })
        
        return events


def run_intelligence_analysis(
    repository_path: str,
    repository_url: str,
    branch: str = "main",
) -> tuple[List[IntelligenceProposal], Dict]:
    """
    Convenience function to run intelligence analysis.
    
    Args:
        repository_path: Path to repository root
        repository_url: Repository URL
        branch: Git branch to analyze
    
    Returns:
        Tuple of (proposals, summary)
    """
    orchestrator = IntelligenceOrchestrator()
    proposals = orchestrator.analyze(
        repository_path=repository_path,
        repository_url=repository_url,
        branch=branch,
    )
    return proposals, orchestrator.get_summary()
