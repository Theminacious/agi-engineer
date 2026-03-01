"""PR Analysis Pipeline for Phase 17 — GitHub Intelligence Integration.

Orchestrates end-to-end PR analysis: clone → analyze → generate fixes → score → report.
"""

import logging
import os
import tempfile
import shutil
import uuid
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import (
    PRAnalysis,
    PRAnalysisStatus,
    ReliabilityScore,
    AnalysisRun,
    CodeFix,
    Installation
)
from app.services.github_service import GitHubService

# Agent imports (orchestrator, fix generation)
from agent.intelligence import IntelligenceOrchestrator, IntelligenceProposal
from agent.intelligence.proposal import BugClass, Severity
from agent.run_ledger import RunLedgerWriter
from app.services.fix_generation import FixGenerationService

logger = logging.getLogger(__name__)


class PRAnalysisPipeline:
    """Pipeline for analyzing GitHub PRs with reliability intelligence.
    
    Workflow:
    1. Clone repository at PR head SHA
    2. Run orchestrator with reliability analyzers
    3. Generate fix candidates
    4. Calculate reliability score
    5. Post comment with findings
    6. Create status check
    7. Record in ledger
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
        self.db_session.commit()
        
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
        self.db_session.commit()
        
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
            
            # Step 2: Run intelligence orchestrator
            proposals = await self._run_orchestrator(repo_path, pr_analysis, user_plan, ledger)
            
            # Step 3: Create AnalysisRun record
            analysis_run = self._create_analysis_run(pr_analysis, proposals)
            pr_analysis.analysis_run_id = analysis_run.id
            self.db_session.commit()
            
            # Step 4: Generate fix candidates
            fix_count = await self._generate_fixes(proposals, analysis_run, ledger)
            
            # Step 5: Calculate reliability score
            reliability_score, risk_counts = self._calculate_reliability_score(proposals)
            pr_analysis.reliability_score = reliability_score
            pr_analysis.critical_risks_count = risk_counts["critical"]
            pr_analysis.high_risks_count = risk_counts["high"]
            pr_analysis.medium_risks_count = risk_counts["medium"]
            pr_analysis.fix_candidates_count = fix_count
            self.db_session.commit()
            
            # Step 6: Post comment
            comment_posted = await self._post_comment(pr_analysis, proposals, ledger)
            
            # Step 7: Create status check
            status_posted = await self._create_status_check(pr_analysis, ledger)
            
            # Update status to COMPLETED
            pr_analysis.status = PRAnalysisStatus.COMPLETED
            pr_analysis.completed_at = datetime.utcnow()
            self.db_session.commit()
            
            # Seal ledger
            ledger.seal("COMPLETE")
            
            logger.info(f"Analysis completed for PR {pr_analysis.repository_full_name}#{pr_analysis.pr_number}: {reliability_score}")
            
            return True
            
        except Exception as e:
            logger.error(f"Analysis failed for PR {pr_analysis_id}: {e}")
            
            # Update status to FAILED
            pr_analysis.status = PRAnalysisStatus.FAILED
            pr_analysis.analysis_error = str(e)
            pr_analysis.completed_at = datetime.utcnow()
            self.db_session.commit()
            
            # Seal ledger with failure
            ledger.seal("INCOMPLETE")
            
            return False
        
        finally:
            # Cleanup: remove cloned repository
            if 'repo_path' in locals() and repo_path and os.path.exists(repo_path):
                try:
                    shutil.rmtree(repo_path)
                    logger.debug(f"Cleaned up repository clone: {repo_path}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup repository: {e}")
    
    async def _clone_repository(
        self,
        pr_analysis: PRAnalysis,
        ledger: RunLedgerWriter
    ) -> Optional[str]:
        """Clone repository at PR head SHA.
        
        Args:
            pr_analysis: PR analysis record
            ledger: Ledger writer
        
        Returns:
            Path to cloned repository if successful, None otherwise
        """
        # Get installation for token
        webhook_event = pr_analysis.webhook_event
        if not webhook_event:
            logger.error("No webhook event associated with PR analysis")
            return None
        
        installation_id = webhook_event.installation_id
        
        # Create temp directory
        temp_dir = tempfile.mkdtemp(prefix="agi-engineer-pr-")
        repo_path = os.path.join(temp_dir, "repo")
        
        logger.info(f"Cloning {pr_analysis.repository_full_name}@{pr_analysis.head_sha[:7]}")
        
        success = self.github_service.clone_repository(
            installation_id=installation_id,
            repo_full_name=pr_analysis.repository_full_name,
            ref=pr_analysis.head_sha,
            dest_path=repo_path
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
            shutil.rmtree(temp_dir)
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
        
        # Initialize orchestrator
        orchestrator = IntelligenceOrchestrator(
            repo_path=repo_path,
            db_session=self.db_session
        )
        
        # Run analysis with reliability focus
        proposals = orchestrator.run_analysis(
            categories=["reliability"],  # Phase 17: Focus on reliability
            user_plan=user_plan,
            emit_ledger=True,
            run_id=pr_analysis.ledger_run_id
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
    
    def _create_analysis_run(
        self,
        pr_analysis: PRAnalysis,
        proposals: List[IntelligenceProposal]
    ) -> AnalysisRun:
        """Create AnalysisRun record for PR analysis.
        
        Args:
            pr_analysis: PR analysis record
            proposals: List of proposals
        
        Returns:
            AnalysisRun record
        """
        analysis_run = AnalysisRun(
            repository_full_name=pr_analysis.repository_full_name,
            commit_sha=pr_analysis.head_sha,
            branch=pr_analysis.base_branch,
            
            # Summary stats
            total_issues=len(proposals),
            critical_count=sum(1 for p in proposals if p.severity == Severity.CRITICAL),
            high_count=sum(1 for p in proposals if p.severity == Severity.HIGH),
            medium_count=sum(1 for p in proposals if p.severity == Severity.MEDIUM),
            low_count=sum(1 for p in proposals if p.severity == Severity.LOW),
            
            # Metadata
            run_metadata={
                "source": "github_pr",
                "pr_number": pr_analysis.pr_number,
                "pr_analysis_id": pr_analysis.id
            },
            
            status="completed",
            completed_at=datetime.utcnow()
        )
        
        self.db_session.add(analysis_run)
        self.db_session.commit()
        
        return analysis_run
    
    async def _generate_fixes(
        self,
        proposals: List[IntelligenceProposal],
        analysis_run: AnalysisRun,
        ledger: RunLedgerWriter
    ) -> int:
        """Generate fix candidates from proposals.
        
        Args:
            proposals: List of intelligence proposals
            analysis_run: Analysis run record
            ledger: Ledger writer
        
        Returns:
            Number of fixes generated
        """
        logger.info("Generating fix candidates")
        
        # Initialize fix generation service
        fix_service = FixGenerationService(
            db_session=self.db_session,
            orchestrator=None  # Not needed for direct proposal input
        )
        
        # Generate fixes
        fixes = await fix_service.generate_fixes_from_proposals(
            proposals=proposals,
            analysis_run_id=analysis_run.id,
            user_plan="team"  # GitHub integration available on team+ plans
        )
        
        fix_count = len(fixes)
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
            self.db_session.commit()
            
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
        
        # Create output
        output = {
            "title": "Reliability Analysis Complete",
            "summary": summary,
            "text": f"Analyzed {pr_analysis.repository_full_name}#{pr_analysis.pr_number}\n\n"
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
            self.db_session.commit()
            
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
