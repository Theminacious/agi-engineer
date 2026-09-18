"""PR Analysis Pipeline for Phase 17 — GitHub Intelligence Integration.

Orchestrates end-to-end PR analysis: clone → change impact → analyze →
contextualize findings → persist/generate fixes → score → report.
"""

import logging
import os
import tempfile
import uuid
from dataclasses import replace
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import (
    PRAnalysis,
    PRAnalysisStatus,
    ReliabilityScore,
    AnalysisRun,
    AnalysisResult,
    CodeFix,
    Installation,
    Repository,
)
from app.models.analysis_run import RunStatus
from app.models.analysis_result import IssueCategory
from app.models.change_impact import ChangeImpactReport, ChangeRiskReport
from app.services.github_service import GitHubService
from app.services.cleanup import safe_rmtree
from app.services.change_impact_service import ChangeImpactAnalysis, ChangeImpactService
from app.services.change_risk_service import ChangeRiskService
from app.services.finding_context import build_finding_contexts
from app.services.change_risk_engine import ChangeRiskEngine
from app.services.verification_engine import VerificationEngine
from app.services.verification_execution import VerificationExecutor
from app.services.baseline_comparison import BaselineComparisonService

# Agent imports (orchestrator, fix generation)
from agent.intelligence import IntelligenceOrchestrator, IntelligenceProposal
from agent.intelligence.proposal import BugClass, Severity
from agent.intelligence.registry import ANALYZER_REGISTRY, list_analyzers_for_plan
from agent.intelligence.selection import AnalyzerSelection
from agent.run_ledger import RunLedgerWriter
from app.services.fix_generation import FixGenerationService

logger = logging.getLogger(__name__)

CHANGE_IMPACT_DEPTH = 6


def _line_range_start(line_range: Optional[str]) -> int:
    if not line_range:
        return 0
    try:
        return int(str(line_range).split("-")[0])
    except (TypeError, ValueError):
        return 0


def _reliability_analyzer_ids(plan: str) -> List[str]:
    try:
        available = [aid for aid, _ in list_analyzers_for_plan(plan)]
    except ValueError as e:
        raise ValueError(f"Cannot select reliability analyzers: {e}") from e

    reliability = sorted(
        aid for aid in available
        if ANALYZER_REGISTRY[aid].get("category") == "reliability"
    )
    if not reliability:
        raise ValueError(
            f"No reliability analyzers available for plan '{plan}'; "
            f"cannot produce a reliability review for this PR"
        )
    return reliability


@dataclass(frozen=True)
class _PreparedChangeImpact:
    """PR-local reuse handle for one impact calculation and its evidence."""

    base_revision: Optional[str]
    service: Optional[ChangeImpactService]
    analysis: Optional[ChangeImpactAnalysis]
    error: Optional[str]


class PRAnalysisPipeline:
    """Pipeline for analyzing GitHub PRs with reliability intelligence.

    Workflow:
    1. Clone repository at PR head SHA (with the base branch fetched too)
    2. Build one code graph and one change-impact report
    3. Run orchestrator with reliability analyzers
    4. Attach findings to the existing impact report and assess change risk
    5. Contextualize findings while creating AnalysisResult rows
    6. Generate fix candidates
    7. Calculate reliability score
    8. Post comment with findings
    9. Create status check and record in ledger
    """
    
    def __init__(
        self,
        db_session: Session,
        github_service: Optional[GitHubService] = None
    ):
        """Initialize PR analysis pipeline.
        
        Args:
            db_session: Database session
            github_service: GitHub service instance (optional)
        """
        self.db_session = db_session
        self.github_service = github_service or GitHubService(db_session)
        # Temp roots this pipeline created, so analyze_pr's finally can remove
        # them whatever happened. _clone_repository mkdtemps a root and clones
        # into a subdirectory of it; cleaning only the returned clone path would
        # leave the root behind on every run.
        self._temp_roots: List[str] = []
        self._last_finding_contexts = []

    def _commit(self, description: str) -> None:
        """Commit the session, or roll back and re-raise.

        A commit that fails does not release its transaction: SQLAlchemy marks
        it as needing rollback, and every later operation on the session raises
        PendingRollbackError reporting the *first* error rather than doing the
        work. That matters most here, because the session is owned by the
        background task in github_webhooks._run_pr_analysis and stays open for
        the whole pipeline — so without this rollback a single failed write
        disables every remaining step of the run.

        The exception is re-raised, so analyze_pr's failure path still runs.

        Args:
            description: What was being written, for the log line.
        """
        try:
            self.db_session.commit()
        except Exception as exc:
            self.db_session.rollback()
            logger.error(f"Rolled back after failed commit ({description}): {exc}")
            raise

    def _cleanup_temp_roots(self) -> None:
        """Remove every temp root registered by this pipeline.

        Drains the list either way: a root that could not be removed has already
        been counted by safe_rmtree, and keeping it here would make the next run
        retry a path that is not going to start working.
        """
        roots, self._temp_roots = self._temp_roots, []
        for root in roots:
            safe_rmtree(root, kind="pr_clone")

    async def analyze_pr(
        self,
        pr_analysis_id: int,
        user_plan: str = "team"
    ) -> bool:
        """Run full analysis pipeline for a PR.
        
        Args:
            pr_analysis_id: PRAnalysis record ID
            user_plan: User's subscription plan (for analyzer filtering)
        
        Returns:
            True if successful, False otherwise
        """
        # Load PR analysis record
        pr_analysis = self.db_session.query(PRAnalysis).filter(
            PRAnalysis.id == pr_analysis_id
        ).first()
        
        if not pr_analysis:
            logger.error(f"PRAnalysis {pr_analysis_id} not found")
            return False
        
        # Update status to IN_PROGRESS
        pr_analysis.status = PRAnalysisStatus.IN_PROGRESS
        pr_analysis.started_at = datetime.utcnow()
        self._commit(f"PR analysis {pr_analysis_id} -> IN_PROGRESS")
        
        logger.info(f"Starting analysis for PR {pr_analysis.repository_full_name}#{pr_analysis.pr_number}")
        
        # Create ledger for this run
        run_id = f"pr-{pr_analysis.repository_full_name.replace('/', '-')}-{pr_analysis.pr_number}-{pr_analysis.head_sha[:7]}"
        ledger = RunLedgerWriter(
            run_id=run_id,
            repo_id=pr_analysis.repository_full_name,
            environment="PRODUCTION",
            initiated_by="GITHUB_WEBHOOK"
        )
        ledger.create_ledger()
        pr_analysis.ledger_run_id = run_id
        self._commit(f"ledger run id for PR analysis {pr_analysis_id}")
        
        # Record GitHub event in ledger
        ledger.append_event(
            event_type="GITHUB_PR_ANALYZED",
            summary=f"Analyzing PR #{pr_analysis.pr_number} at {pr_analysis.head_sha[:7]}",
            actor="github-app",
            actor_role="System",
            phase="PHASE_17",
            payload_ref=str(pr_analysis.id)
        )
        
        try:
            # Step 1: Clone repository
            repo_path = await self._clone_repository(pr_analysis, ledger)
            if not repo_path:
                raise Exception("Failed to clone repository")

            # Step 2: Build the graph and change-impact report once. The
            # resulting graph is retained in memory for finding context.
            prepared_impact = self._prepare_change_impact(repo_path, pr_analysis)

            # Step 3: Run intelligence orchestrator
            proposals = await self._run_orchestrator(repo_path, pr_analysis, user_plan, ledger)

            # Step 4: Intersect raw findings with the existing impact report
            # and assess risk without another diff or graph build.
            change_risk_report = self._assess_change_risk(
                repo_path,
                pr_analysis,
                proposals,
                ledger,
                prepared_impact,
            )

            # Step 5: Create AnalysisRun record
            analysis_run = self._create_analysis_run(pr_analysis, proposals)
            pr_analysis.analysis_run_id = analysis_run.id
            self._commit(f"link analysis run {analysis_run.id}")

            # Step 6: Contextualize and persist findings, then generate fixes.
            graph = prepared_impact.analysis.graph if prepared_impact.analysis else None
            impact = prepared_impact.analysis.report if prepared_impact.analysis else None
            fix_count = await self._generate_fixes(
                proposals,
                analysis_run,
                repo_path,
                pr_analysis,
                ledger,
                graph=graph,
                impact=impact,
                change_risk_report=change_risk_report,
                user_plan=user_plan,
            )

            # Step 7: Calculate reliability score
            reliability_score, risk_counts = self._calculate_reliability_score(proposals)
            pr_analysis.reliability_score = reliability_score
            pr_analysis.critical_risks_count = risk_counts["critical"]
            pr_analysis.high_risks_count = risk_counts["high"]
            pr_analysis.medium_risks_count = risk_counts["medium"]
            pr_analysis.fix_candidates_count = fix_count
            self._commit(f"reliability score for PR analysis {pr_analysis_id}")

            # Step 8: Post comment
            comment_posted = await self._post_comment(pr_analysis, proposals, ledger)

            # Step 9: Create status check
            status_posted = await self._create_status_check(pr_analysis, ledger)
            
            # Update status to COMPLETED
            pr_analysis.status = PRAnalysisStatus.COMPLETED
            pr_analysis.completed_at = datetime.utcnow()
            self._commit(f"PR analysis {pr_analysis_id} -> COMPLETED")
            
            # Seal ledger
            ledger.seal("COMPLETE")
            
            logger.info(f"Analysis completed for PR {pr_analysis.repository_full_name}#{pr_analysis.pr_number}: {reliability_score}")
            
            return True
            
        except Exception as e:
            logger.error(f"Analysis failed for PR {pr_analysis_id}: {e}")

            # Discard whatever the failed run left pending before writing the
            # failure. Two reasons: a partially-applied step must not be
            # committed by this handler, and if the failure *was* a commit the
            # session is awaiting rollback, so writing FAILED would raise
            # PendingRollbackError here — losing both the status and the seal
            # below, and masking `e` with the secondary error.
            self.db_session.rollback()

            # Update status to FAILED
            pr_analysis.status = PRAnalysisStatus.FAILED
            pr_analysis.analysis_error = str(e)
            pr_analysis.completed_at = datetime.utcnow()
            try:
                self._commit(f"PR analysis {pr_analysis_id} -> FAILED")
            except Exception as status_error:
                # Recording the failure failed too. Still seal the ledger: an
                # unsealed ledger is indistinguishable from a run still in
                # flight, which is worse than one recorded as INCOMPLETE.
                logger.error(
                    f"Could not record FAILED status for PR analysis "
                    f"{pr_analysis_id}: {status_error}"
                )

            # Seal ledger with failure
            ledger.seal("INCOMPLETE")

            return False
        
        finally:
            # Remove every temp root this run created, not just the clone path.
            # _clone_repository returns "<root>/repo", so removing repo_path
            # alone left the mkdtemp root behind after every analysis — an empty
            # directory per PR, accumulating for the life of the host. Draining
            # the list also covers the case where the clone raised before
            # returning a path at all.
            self._cleanup_temp_roots()
    
    async def _clone_repository(
        self,
        pr_analysis: PRAnalysis,
        ledger: RunLedgerWriter
    ) -> Optional[str]:
        """Clone repository at PR head SHA, with the base branch fetched too."""
        webhook_event = pr_analysis.webhook_event
        if not webhook_event:
            logger.error("No webhook event associated with PR analysis")
            return None

        installation_id = webhook_event.installation_id

        temp_dir = tempfile.mkdtemp(prefix="agi-engineer-pr-")
        # Registered before the clone runs, so analyze_pr's finally removes it
        # even if the clone raises rather than returning False.
        self._temp_roots.append(temp_dir)
        repo_path = os.path.join(temp_dir, "repo")

        logger.info(f"Cloning {pr_analysis.repository_full_name}@{pr_analysis.head_sha[:7]}")

        success = self.github_service.clone_repository(
            installation_id=installation_id,
            repo_full_name=pr_analysis.repository_full_name,
            ref=pr_analysis.head_sha,
            dest_path=repo_path,
            extra_refs=[pr_analysis.base_branch] if pr_analysis.base_branch else None,
        )
        
        if success:
            ledger.append_event(
                event_type="REPO_CLONED",
                summary=f"Cloned {pr_analysis.repository_full_name}@{pr_analysis.head_sha[:7]}",
                actor="github-service",
                actor_role="System",
                phase="PHASE_17"
            )
            return repo_path
        else:
            logger.error(f"Failed to clone repository")
            # Left registered as well: if this removal fails, the finally block
            # retries it and the failure is counted either way.
            safe_rmtree(temp_dir, kind="pr_clone")
            return None
    
    async def _run_orchestrator(
        self,
        repo_path: str,
        pr_analysis: PRAnalysis,
        user_plan: str,
        ledger: RunLedgerWriter
    ) -> List[IntelligenceProposal]:
        """Run intelligence orchestrator on repository.
        
        Args:
            repo_path: Path to cloned repository
            pr_analysis: PR analysis record
            user_plan: User's subscription plan
            ledger: Ledger writer
        
        Returns:
            List of intelligence proposals
        """
        logger.info("Running intelligence orchestrator")

        orchestrator = IntelligenceOrchestrator()
        selection = AnalyzerSelection(
            plan=user_plan,
            enabled_analyzers=_reliability_analyzer_ids(user_plan),
        )

        proposals = orchestrator.analyze(
            repository_path=repo_path,
            repository_url=f"https://github.com/{pr_analysis.repository_full_name}",
            branch=pr_analysis.base_branch or "main",
            ledger=ledger,
            run_id=pr_analysis.ledger_run_id,
            selection=selection,
        )

        logger.info(f"Orchestrator generated {len(proposals)} proposals")
        
        ledger.append_event(
            event_type="INTELLIGENCE_RUN_COMPLETED",
            summary=f"Generated {len(proposals)} intelligence proposals",
            actor="orchestrator",
            actor_role="Agent",
            phase="PHASE_17",
            payload_ref=str(len(proposals))
        )
        
        return proposals
    
    @staticmethod
    def _base_revision(pr_analysis: PRAnalysis) -> Optional[str]:
        webhook_event = pr_analysis.webhook_event
        payload = getattr(webhook_event, "raw_payload", None) if webhook_event else None
        if isinstance(payload, dict):
            pull_request = payload.get("pull_request")
            if isinstance(pull_request, dict):
                base = pull_request.get("base")
                if isinstance(base, dict) and base.get("sha"):
                    return base["sha"]
        if pr_analysis.base_branch:
            return f"origin/{pr_analysis.base_branch}"
        return None

    def _prepare_change_impact(
        self,
        repo_path: str,
        pr_analysis: PRAnalysis,
    ) -> _PreparedChangeImpact:
        """Build one impact report and retain the exact graph behind it."""

        base_revision = self._base_revision(pr_analysis)
        if not base_revision:
            return _PreparedChangeImpact(
                base_revision=None,
                service=None,
                analysis=None,
                error="no base revision available for this PR",
            )

        service = ChangeImpactService()
        try:
            analysis = service.compute_change_impact_with_graph(
                repo_path=repo_path,
                base_revision=base_revision,
                target_revision=pr_analysis.head_sha,
                max_impact_depth=CHANGE_IMPACT_DEPTH,
                repository_label=pr_analysis.repository_full_name,
            )
        except Exception as e:
            logger.warning(
                "Change impact preparation failed for PR analysis %s: %s",
                pr_analysis.id,
                e,
            )
            return _PreparedChangeImpact(
                base_revision=base_revision,
                service=service,
                analysis=None,
                error=str(e),
            )

        return _PreparedChangeImpact(
            base_revision=base_revision,
            service=service,
            analysis=analysis,
            error=None,
        )

    def _assess_change_risk(
        self,
        repo_path: str,
        pr_analysis: PRAnalysis,
        proposals: List[IntelligenceProposal],
        ledger: RunLedgerWriter,
        prepared: _PreparedChangeImpact,
    ) -> Optional[ChangeRiskReport]:
        if prepared.error or prepared.analysis is None or prepared.service is None:
            self._record_risk_unavailable(
                pr_analysis,
                ledger,
                prepared.error or "change impact analysis unavailable",
            )
            return None

        try:
            report = ChangeRiskService(impact_service=prepared.service).assess(
                repo_path=repo_path,
                base_revision=prepared.base_revision or "",
                target_revision=pr_analysis.head_sha,
                findings=proposals,
                ledger=ledger,
                max_impact_depth=CHANGE_IMPACT_DEPTH,
                repository_label=pr_analysis.repository_full_name,
                precomputed_analysis=prepared.analysis,
            )
        except Exception as e:
            logger.warning(
                "Change risk assessment failed for PR analysis %s: %s", pr_analysis.id, e
            )
            self._record_risk_unavailable(pr_analysis, ledger, str(e))
            return None

        pr_analysis.change_risk_level = report.risk_level.value
        pr_analysis.change_risk_recommendation = report.recommendation.value
        pr_analysis.change_risk_base_revision = prepared.base_revision
        pr_analysis.change_risk_hash = report.deterministic_hash
        pr_analysis.change_risk_report = report.to_dict()
        pr_analysis.change_risk_error = None
        self._commit(f"change risk assessment for PR analysis {pr_analysis.id}")

        logger.info(
            "PR %s#%s change risk: %s (%s)",
            pr_analysis.repository_full_name,
            pr_analysis.pr_number,
            report.risk_level.value,
            report.recommendation.value,
        )
        return report

    def _record_risk_unavailable(
        self, pr_analysis: PRAnalysis, ledger: RunLedgerWriter, reason: str
    ) -> None:
        pr_analysis.change_risk_level = None
        pr_analysis.change_risk_recommendation = None
        pr_analysis.change_risk_hash = None
        pr_analysis.change_risk_report = None
        pr_analysis.change_risk_error = reason[:2000]
        self._commit(f"change risk unavailable for PR analysis {pr_analysis.id}")

        ledger.append_event(
            event_type="CHANGE_RISK_UNAVAILABLE",
            summary=f"Change risk assessment unavailable: {reason}"[:1000],
            actor="change-risk-service",
            actor_role="System",
            phase="PHASE_20",
        )

    def _get_or_create_repository(self, pr_analysis: PRAnalysis) -> Repository:
        existing = (
            self.db_session.query(Repository)
            .filter(Repository.repo_full_name == pr_analysis.repository_full_name)
            .first()
        )
        if existing:
            return existing

        webhook_event = pr_analysis.webhook_event
        if not webhook_event:
            raise ValueError(
                f"Cannot create Repository for {pr_analysis.repository_full_name}: "
                f"PR analysis {pr_analysis.id} has no webhook event"
            )
        if webhook_event.repository_id is None:
            raise ValueError(
                f"Cannot create Repository for {pr_analysis.repository_full_name}: "
                f"webhook payload carried no GitHub repository id"
            )

        repository = Repository(
            installation_id=webhook_event.installation_id,
            repo_name=pr_analysis.repository_full_name.split("/")[-1],
            repo_full_name=pr_analysis.repository_full_name,
            github_repo_id=webhook_event.repository_id,
        )
        self.db_session.add(repository)
        self._commit(f"repository row for {pr_analysis.repository_full_name}")
        return repository

    def _create_analysis_run(
        self,
        pr_analysis: PRAnalysis,
        proposals: List[IntelligenceProposal]
    ) -> AnalysisRun:
        repository = self._get_or_create_repository(pr_analysis)

        analysis_run = AnalysisRun(
            repository_id=repository.id,
            github_event="pull_request",
            github_branch=pr_analysis.base_branch or "main",
            github_commit_sha=pr_analysis.head_sha,
            pull_request_number=pr_analysis.pr_number,
            status=RunStatus.COMPLETED,
            started_at=pr_analysis.started_at,
            completed_at=datetime.utcnow(),
        )

        self.db_session.add(analysis_run)
        self._commit(f"analysis run for PR analysis {pr_analysis.id}")

        return analysis_run

    def _create_analysis_results(
        self,
        analysis_run: AnalysisRun,
        proposals: List[IntelligenceProposal],
        repo_root: str,
        graph: Any = None,
        impact: Optional[ChangeImpactReport] = None,
    ) -> List[Tuple[IntelligenceProposal, AnalysisResult]]:
        rows: List[Tuple[IntelligenceProposal, AnalysisResult]] = []

        def sort_key(p: IntelligenceProposal) -> Tuple[str, int, str]:
            first = p.affected_files[0] if p.affected_files else None
            return (
                first.path if first else "",
                _line_range_start(first.line_range if first else None),
                p.bug_class.value if p.bug_class else "",
            )

        ordered = sorted(proposals, key=sort_key)
        persistable = [proposal for proposal in ordered if proposal.affected_files]
        for proposal in ordered:
            if proposal.affected_files:
                continue
            logger.debug(
                "Proposal %s has no affected files; no AnalysisResult row",
                proposal.proposal_id,
            )

        finding_rows = self._finding_rows_from_proposals(persistable)

        contexts = build_finding_contexts(
            finding_rows,
            graph=graph,
            impact=impact,
            repo_root=repo_root,
        )
        self._last_finding_rows = finding_rows
        self._last_finding_contexts = contexts

        for proposal, finding, context in zip(persistable, finding_rows, contexts):
            payload = context.to_dict()
            result = AnalysisResult(
                run_id=analysis_run.id,
                file_path=context.file_path,
                line_number=context.line_number,
                issue_code=finding["issue_code"],
                issue_name=finding["issue_name"],
                category=IssueCategory.REVIEW,
                severity=finding["severity"],
                message=finding["message"],
                suggestion=proposal.root_cause_hypothesis or None,
                file_class=payload["file_class"],
                relevance=payload["relevance"],
                confidence=payload["confidence"],
                recommendation=payload["recommendation"],
                finding_context=payload,
            )
            self.db_session.add(result)
            rows.append((proposal, result))

        if rows:
            self._commit(f"{len(rows)} analysis results for run {analysis_run.id}")
        return rows

    @staticmethod
    def _finding_rows_from_proposals(
        proposals: List[IntelligenceProposal],
    ) -> List[Dict[str, Any]]:
        finding_rows: List[Dict[str, Any]] = []
        for proposal in proposals:
            if not proposal.affected_files:
                continue
            primary = proposal.affected_files[0]
            finding_rows.append(
                {
                    "proposal_id": proposal.proposal_id,
                    "file_path": primary.path,
                    "line_number": _line_range_start(primary.line_range),
                    "issue_code": (
                        proposal.bug_class.value if proposal.bug_class else "unknown"
                    )[:20],
                    "issue_name": (
                        proposal.problem_statement or "Intelligence finding"
                    )[:255],
                    "message": (proposal.problem_statement or "")[:1000],
                    "severity": (
                        proposal.severity.value if proposal.severity else "medium"
                    ),
                }
            )
        return finding_rows

    async def _generate_fixes(
        self,
        proposals: List[IntelligenceProposal],
        analysis_run: AnalysisRun,
        repo_path: str,
        pr_analysis: PRAnalysis,
        ledger: RunLedgerWriter,
        graph: Any = None,
        impact: Optional[ChangeImpactReport] = None,
        change_risk_report: Optional[ChangeRiskReport] = None,
        user_plan: str = "team",
    ) -> int:
        logger.info("Generating fix candidates")

        run_id = pr_analysis.ledger_run_id or f"pr-analysis-{pr_analysis.id}"
        results = self._create_analysis_results(
            analysis_run,
            proposals,
            repo_root=repo_path,
            graph=graph,
            impact=impact,
        )

        if impact is not None and change_risk_report is not None:
            assessment = ChangeRiskEngine().assess(
                impact,
                self._last_finding_contexts,
                existing_report=change_risk_report,
            )
            persisted_report = change_risk_report.to_dict()
            persisted_report["decision"] = assessment.to_dict()
            execution_evidence = VerificationExecutor().execute(
                repo_path=repo_path,
                revision=pr_analysis.head_sha,
                impact=impact,
                risk=assessment,
                contexts=self._last_finding_contexts,
            )
            baseline = BaselineComparisonService().compare(
                repo_path=repo_path,
                base_revision=self._base_revision(pr_analysis),
                target_revision=pr_analysis.head_sha,
                target_findings=self._last_finding_rows,
                analyze=lambda baseline_path: self._run_baseline_analyzers(
                    baseline_path, pr_analysis, user_plan
                ),
                normalize=self._finding_rows_from_proposals,
            )
            execution_evidence = replace(
                execution_evidence,
                findings_before=baseline.findings_before,
                baseline_status=baseline.baseline_status,
                comparison_status=baseline.comparison_status,
                baseline_error=baseline.error,
                comparison_findings_before=baseline.findings_before,
                comparison_findings_after=self._last_finding_rows,
            )
            proof = VerificationEngine().assess(
                impact,
                self._last_finding_contexts,
                assessment,
                evidence=execution_evidence,
            )
            persisted_report["verification"] = proof.to_dict()
            pr_analysis.change_risk_report = persisted_report
            self._commit(f"change risk decision for PR analysis {pr_analysis.id}")
            ledger.append_event(
                event_type="CHANGE_RISK_DECISION_ASSESSED",
                summary=(
                    f"Context-aware change risk decision: "
                    f"{assessment.risk_level.value.upper()}"
                ),
                actor="change-risk-engine",
                actor_role="System",
                phase="PHASE_20",
                payload_ref=assessment.deterministic_hash,
            )
            ledger.append_event(
                event_type="VERIFICATION_PROOF_ASSESSED",
                summary=f"Verification proof: {proof.state.value}",
                actor="verification-engine",
                actor_role="System",
                phase="PHASE_20",
                payload_ref=proof.deterministic_hash,
            )

        fix_service = FixGenerationService(self.db_session)
        fix_count = 0
        for proposal, result in results:
            fixes = fix_service.generate_from_findings(
                run_id=run_id,
                findings=[proposal],
                repository_path=repo_path,
                result_id=result.id,
            )
            fix_count += len(fixes)

        logger.info(f"Generated {fix_count} fix candidates")

        ledger.append_event(
            event_type="FIXES_GENERATED",
            summary=f"Generated {fix_count} fix candidates",
            actor="fix-generation-service",
            actor_role="Agent",
            phase="PHASE_17",
            payload_ref=str(fix_count)
        )

        return fix_count

    def _run_baseline_analyzers(
        self,
        repo_path: str,
        pr_analysis: PRAnalysis,
        user_plan: str,
    ) -> List[IntelligenceProposal]:
        orchestrator = IntelligenceOrchestrator()
        selection = AnalyzerSelection(
            plan=user_plan,
            enabled_analyzers=_reliability_analyzer_ids(user_plan),
        )
        return orchestrator.analyze(
            repository_path=repo_path,
            repository_url=f"https://github.com/{pr_analysis.repository_full_name}",
            branch=pr_analysis.base_branch or "main",
            selection=selection,
        )
    
    def _calculate_reliability_score(
        self,
        proposals: List[IntelligenceProposal]
    ) -> Tuple[ReliabilityScore, Dict[str, int]]:
        """Calculate overall reliability score for PR.
        
        Args:
            proposals: List of intelligence proposals
        
        Returns:
            (reliability_score, risk_counts)
        """
        # Count by severity
        critical_count = sum(1 for p in proposals if p.severity == Severity.CRITICAL)
        high_count = sum(1 for p in proposals if p.severity == Severity.HIGH)
        medium_count = sum(1 for p in proposals if p.severity == Severity.MEDIUM)
        
        # Determine overall score
        if critical_count > 0:
            score = ReliabilityScore.CRITICAL
        elif high_count > 0:
            score = ReliabilityScore.CONCERNING
        elif medium_count > 0:
            score = ReliabilityScore.GOOD
        else:
            score = ReliabilityScore.EXCELLENT
        
        risk_counts = {
            "critical": critical_count,
            "high": high_count,
            "medium": medium_count
        }
        
        return score, risk_counts
    
    async def _post_comment(
        self,
        pr_analysis: PRAnalysis,
        proposals: List[IntelligenceProposal],
        ledger: RunLedgerWriter
    ) -> bool:
        """Post analysis comment on PR.
        
        Args:
            pr_analysis: PR analysis record
            proposals: List of proposals
            ledger: Ledger writer
        
        Returns:
            True if successful, False otherwise
        """
        # Get installation ID
        webhook_event = pr_analysis.webhook_event
        if not webhook_event:
            return False
        
        installation_id = webhook_event.installation_id

        # Generate comment body
        comment_body = self._format_comment(pr_analysis, proposals)

        existing_comment_id = pr_analysis.comment_id
        if existing_comment_id and hasattr(self.github_service, "update_pr_comment"):
            updated = self.github_service.update_pr_comment(
                installation_id=installation_id,
                repo_full_name=pr_analysis.repository_full_name,
                comment_id=existing_comment_id,
                comment_body=comment_body,
            )
            if updated:
                pr_analysis.comment_posted = True
                pr_analysis.comment_posted_at = datetime.utcnow()
                self._commit(f"updated comment {existing_comment_id}")
                ledger.append_event(
                    event_type="GITHUB_COMMENT_UPDATED",
                    summary=f"Updated analysis comment on PR #{pr_analysis.pr_number}",
                    actor="github-service",
                    actor_role="System",
                    phase="PHASE_17",
                    payload_ref=str(existing_comment_id),
                )
                return True
            logger.warning(
                "Could not update comment %s; posting a new one", existing_comment_id
            )

        # Post comment
        comment_id = self.github_service.post_pr_comment(
            installation_id=installation_id,
            repo_full_name=pr_analysis.repository_full_name,
            pr_number=pr_analysis.pr_number,
            comment_body=comment_body
        )
        
        if comment_id:
            pr_analysis.comment_posted = True
            pr_analysis.comment_id = comment_id
            pr_analysis.comment_posted_at = datetime.utcnow()
            self._commit(f"comment {comment_id} on PR #{pr_analysis.pr_number}")
            
            ledger.append_event(
                event_type="GITHUB_COMMENT_POSTED",
                summary=f"Posted analysis comment on PR #{pr_analysis.pr_number}",
                actor="github-service",
                actor_role="System",
                phase="PHASE_17",
                payload_ref=str(comment_id)
            )
            
            return True
        
        return False
    
    def _format_comment(
        self,
        pr_analysis: PRAnalysis,
        proposals: List[IntelligenceProposal]
    ) -> str:
        """Format PR comment with analysis results.
        
        Args:
            pr_analysis: PR analysis record
            proposals: List of proposals
        
        Returns:
            Markdown formatted comment
        """
        # Group proposals by severity
        critical_proposals = [p for p in proposals if p.severity == Severity.CRITICAL]
        high_proposals = [p for p in proposals if p.severity == Severity.HIGH]
        medium_proposals = [p for p in proposals if p.severity == Severity.MEDIUM]
        
        # Build comment
        lines = []
        lines.append("## 🧠 AGI Engineer Reliability Analysis")
        lines.append("")

        lines.extend(self._format_change_risk_section(pr_analysis))

        # Reliability score
        score_emoji = {
            ReliabilityScore.EXCELLENT: "✅",
            ReliabilityScore.GOOD: "👍",
            ReliabilityScore.CONCERNING: "⚠️",
            ReliabilityScore.CRITICAL: "🚨"
        }
        emoji = score_emoji.get(pr_analysis.reliability_score, "❓")
        lines.append(f"**Reliability Score**: {emoji} **{pr_analysis.reliability_score.value.upper()}**")
        lines.append("")
        
        # Summary
        lines.append(f"Found **{len(proposals)} potential reliability issues** in this PR:")
        lines.append(f"- 🚨 {pr_analysis.critical_risks_count} Critical")
        lines.append(f"- ⚠️ {pr_analysis.high_risks_count} High")
        lines.append(f"- ℹ️ {pr_analysis.medium_risks_count} Medium")
        lines.append("")
        
        # Critical risks (show all)
        if critical_proposals:
            lines.append("### 🚨 Critical Risks")
            lines.append("")
            for i, proposal in enumerate(critical_proposals[:5], 1):  # Limit to 5
                lines.append(f"**{i}. {proposal.bug_class.value.replace('_', ' ').title()}**")
                lines.append(f"```")
                lines.append(f"{proposal.problem_statement[:200]}")
                lines.append(f"```")
                lines.append(f"💡 **Fix**: {proposal.suggested_strategies[0].name if proposal.suggested_strategies else 'See detailed report'}")
                lines.append("")
            
            if len(critical_proposals) > 5:
                lines.append(f"*... and {len(critical_proposals) - 5} more critical risks*")
                lines.append("")
        
        # High risks (show top 3)
        if high_proposals:
            lines.append("### ⚠️ High Risks")
            lines.append("")
            for i, proposal in enumerate(high_proposals[:3], 1):
                lines.append(f"**{i}. {proposal.bug_class.value.replace('_', ' ').title()}**")
                lines.append(f"- {proposal.problem_statement[:150]}")
            
            if len(high_proposals) > 3:
                lines.append(f"- *... and {len(high_proposals) - 3} more high risks*")
            lines.append("")
        
        # Fix candidates
        if pr_analysis.fix_candidates_count > 0:
            lines.append("### 🔧 Suggested Fixes")
            lines.append("")
            lines.append(f"✅ **{pr_analysis.fix_candidates_count} fix candidates** generated and ready for review.")
            lines.append("")
        
        # Footer
        lines.append("---")
        lines.append(f"📊 [View Full Governance Report](#) | 🔍 Run ID: `{pr_analysis.ledger_run_id}`")
        lines.append("")
        lines.append("*Powered by AGI Engineer Phase 17 — Reliability Intelligence*")
        
        return "\n".join(lines)
    
    _RISK_EMOJI = {
        "none": "✅",
        "low": "✅",
        "medium": "⚠️",
        "high": "🔶",
        "critical": "🚨",
    }

    _RECOMMENDATION_LABEL = {
        "no_review_required": "No special review required",
        "review_recommended": "Review recommended",
        "requires_human_review": "Human review required",
    }

    _CHANGE_RISK_CONCLUSION = {
        "none": "success",
        "low": "success",
        "medium": "neutral",
        "high": "neutral",
        "critical": "failure",
    }

    _CONCLUSION_SEVERITY = {"success": 0, "neutral": 1, "failure": 2}

    @classmethod
    def _merge_conclusions(cls, first: str, second: str) -> str:
        return max(
            (first, second),
            key=lambda c: cls._CONCLUSION_SEVERITY.get(c, 1),
        )

    def _format_change_risk_section(self, pr_analysis: PRAnalysis) -> List[str]:
        """Change Risk block for the PR comment.

        Describes what the diff touches and which findings sit in that area. It
        is not a claim about what will happen in production.
        """
        report = pr_analysis.change_risk_report
        if not isinstance(report, dict) or not report:
            reason = pr_analysis.change_risk_error or "not available for this PR"
            return [
                "### Change Risk",
                "",
                f"Not assessed — {reason}",
                "",
                "---",
                "",
            ]

        level = str(report.get("risk_level") or "unknown").lower()
        recommendation = str(report.get("recommendation") or "")
        impact = report.get("impact") if isinstance(report.get("impact"), dict) else {}

        lines = ["### Change Risk", ""]
        lines.append(
            f"**{self._RISK_EMOJI.get(level, '❓')} {level.upper()}** — "
            f"{self._RECOMMENDATION_LABEL.get(recommendation, recommendation or 'no recommendation')}"
        )
        lines.append("")

        entrypoints = report.get("affected_entrypoints") or []
        lines.append(
            f"**Blast radius**: {report.get('blast_radius_size', 0)} symbols / "
            f"{report.get('changed_file_count', 0)} changed file(s) / "
            f"{len(entrypoints)} entry point(s)"
        )
        lines.append("")

        changed_symbols = [
            s.get("node_id")
            for s in (impact.get("changed_symbols") or [])
            if isinstance(s, dict) and s.get("node_id")
        ]
        if changed_symbols:
            lines.append("**Changed symbols**")
            for node_id in changed_symbols[:8]:
                lines.append(f"- `{node_id}`")
            if len(changed_symbols) > 8:
                lines.append(f"- *… and {len(changed_symbols) - 8} more*")
            lines.append("")

        factors = [f for f in (report.get("risk_factors") or []) if isinstance(f, dict)]
        if factors:
            lines.append("**Why**")
            for factor in factors:
                lines.append(
                    f"- `{factor.get('level', '?')}` {factor.get('detail', factor.get('kind', ''))}"
                )
            lines.append("")

        lines.append(
            f"**Findings evaluated**: {report.get('findings_evaluated', 0)} "
            f"({report.get('findings_in_blast_radius', 0)} inside the radius, "
            f"{report.get('findings_outside_blast_radius', 0)} outside, "
            f"{report.get('findings_unresolved_location', 0)} unresolved)"
        )
        lines.append("")

        if entrypoints:
            lines.append("**Entry points reaching the change**")
            for node_id in sorted(entrypoints)[:5]:
                lines.append(f"- `{node_id}`")
            lines.append("")

        caveats = report.get("caveats") or []
        if caveats:
            lines.append("**Caveats**")
            for caveat in caveats:
                lines.append(f"- {caveat}")
            lines.append("")

        lines.append("<details><summary>Evidence</summary>")
        lines.append("")
        lines.append(f"- Impact hash: `{report.get('impact_hash', '')}`")
        lines.append(f"- Risk hash: `{report.get('deterministic_hash', '')}`")
        lines.append(f"- Base revision: `{report.get('base_revision', '')}`")
        lines.append(f"- Target revision: `{report.get('target_revision', '')}`")
        lines.append(f"- Confidence: `{report.get('confidence', '')}`")
        lines.append("")
        lines.append(
            "Derived deterministically from the diff, the code graph, and "
            "already-reported reliability findings. Re-running on the same "
            "revisions reproduces these hashes."
        )
        lines.append("</details>")
        lines.append("")
        lines.append("---")
        lines.append("")
        return lines

    async def _create_status_check(
        self,
        pr_analysis: PRAnalysis,
        ledger: RunLedgerWriter
    ) -> bool:
        """Create GitHub status check for PR.
        
        Args:
            pr_analysis: PR analysis record
            ledger: Ledger writer
        
        Returns:
            True if successful, False otherwise
        """
        # Get installation ID
        webhook_event = pr_analysis.webhook_event
        if not webhook_event:
            return False
        
        installation_id = webhook_event.installation_id

        # Determine conclusion based on reliability score
        if pr_analysis.reliability_score == ReliabilityScore.CRITICAL:
            conclusion = "failure"
            summary = f"🚨 Found {pr_analysis.critical_risks_count} critical reliability risks"
        elif pr_analysis.reliability_score == ReliabilityScore.CONCERNING:
            conclusion = "neutral"
            summary = f"⚠️ Found {pr_analysis.high_risks_count} high reliability risks"
        else:
            conclusion = "success"
            summary = f"✅ No critical reliability issues found"

        risk_level = (pr_analysis.change_risk_level or "").lower()
        recommendation = pr_analysis.change_risk_recommendation or ""
        if risk_level:
            conclusion = self._merge_conclusions(
                conclusion, self._CHANGE_RISK_CONCLUSION.get(risk_level, "neutral")
            )
            summary = (
                f"Change risk {risk_level.upper()} — "
                f"{self._RECOMMENDATION_LABEL.get(recommendation, recommendation or 'no recommendation')}. "
                f"{summary}"
            )

        report = pr_analysis.change_risk_report
        risk_text = ""
        if isinstance(report, dict) and report:
            entrypoints = report.get("affected_entrypoints") or []
            factors = [
                f.get("detail") or f.get("kind")
                for f in (report.get("risk_factors") or [])
                if isinstance(f, dict)
            ]
            risk_text = (
                f"Change risk: {risk_level.upper()}\n"
                f"Recommendation: "
                f"{self._RECOMMENDATION_LABEL.get(recommendation, recommendation)}\n"
                f"Blast radius: {report.get('blast_radius_size', 0)} symbols / "
                f"{report.get('changed_file_count', 0)} files / "
                f"{len(entrypoints)} entrypoints\n"
                f"Findings inside radius: {report.get('findings_in_blast_radius', 0)}"
                f" of {report.get('findings_evaluated', 0)}\n"
                + "".join(f"- {detail}\n" for detail in factors)
                + f"Impact hash: {report.get('impact_hash', '')}\n"
                f"Risk hash: {report.get('deterministic_hash', '')}\n\n"
            )
        elif pr_analysis.change_risk_error:
            risk_text = f"Change risk not assessed: {pr_analysis.change_risk_error}\n\n"

        # Create output
        output = {
            "title": "Reliability Analysis Complete",
            "summary": summary,
            "text": risk_text
                    + f"Analyzed {pr_analysis.repository_full_name}#{pr_analysis.pr_number}\n\n"
                    f"- Critical: {pr_analysis.critical_risks_count}\n"
                    f"- High: {pr_analysis.high_risks_count}\n"
                    f"- Medium: {pr_analysis.medium_risks_count}\n\n"
                    f"Fix candidates: {pr_analysis.fix_candidates_count}"
        }
        
        # Create check run
        check_run_id = self.github_service.create_check_run(
            installation_id=installation_id,
            repo_full_name=pr_analysis.repository_full_name,
            head_sha=pr_analysis.head_sha,
            name="AGI Engineer — Reliability",
            status="completed",
            conclusion=conclusion,
            output=output
        )
        
        if check_run_id:
            pr_analysis.status_check_posted = True
            pr_analysis.status_check_id = check_run_id
            pr_analysis.status_check_conclusion = conclusion
            self._commit(f"status check {check_run_id} ({conclusion})")
            
            ledger.append_event(
                event_type="GITHUB_STATUS_REPORTED",
                summary=f"Posted status check: {conclusion}",
                actor="github-service",
                actor_role="System",
                phase="PHASE_17",
                payload_ref=str(check_run_id)
            )
            
            return True
        
        return False
