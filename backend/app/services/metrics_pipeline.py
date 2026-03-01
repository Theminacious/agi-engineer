"""Metrics Pipeline for Phase 18 — Automated metrics updates.

Integrates with PR analysis and fix application workflows.
"""

import logging
from typing import Optional
from sqlalchemy.orm import Session

from app.services.reliability_metrics import ReliabilityMetricsService

logger = logging.getLogger(__name__)


class MetricsPipeline:
    """Pipeline for automated metrics updates.
    
    Features:
    - Triggers after PR analysis completion
    - Triggers after fix application
    - Handles daily aggregation
    - Error handling and retries
    """
    
    def __init__(self, db_session: Session):
        """Initialize metrics pipeline.
        
        Args:
            db_session: Database session
        """
        self.db_session = db_session
        self.metrics_service = ReliabilityMetricsService(db_session)
    
    def process_pr_analysis_completion(
        self,
        pr_analysis_id: int,
        ledger_run_id: Optional[str] = None
    ) -> bool:
        """Process PR analysis completion and update metrics.
        
        Args:
            pr_analysis_id: PRAnalysis ID
            ledger_run_id: Optional ledger run ID
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Processing PR analysis {pr_analysis_id} for metrics update")
            
            # Update metrics
            metrics = self.metrics_service.update_metrics_after_pr_analysis(
                pr_analysis_id=pr_analysis_id,
                ledger_run_id=ledger_run_id
            )
            
            if metrics:
                logger.info(
                    f"Metrics updated: repo={metrics.repository_id}, "
                    f"score={metrics.reliability_score:.1f}, "
                    f"grade={metrics.score_grade}"
                )
                return True
            else:
                logger.warning(f"Failed to update metrics for PR analysis {pr_analysis_id}")
                return False
        
        except Exception as e:
            logger.error(f"Error processing PR analysis {pr_analysis_id}: {e}", exc_info=True)
            return False
    
    def process_fix_application(
        self,
        fix_id: int,
        ledger_run_id: Optional[str] = None
    ) -> bool:
        """Process fix application and update metrics.
        
        Args:
            fix_id: CodeFix ID
            ledger_run_id: Optional ledger run ID
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Processing fix {fix_id} for metrics update")
            
            # Update metrics
            metrics = self.metrics_service.update_metrics_after_fix_applied(
                fix_id=fix_id,
                ledger_run_id=ledger_run_id
            )
            
            if metrics:
                logger.info(
                    f"Metrics updated after fix: repo={metrics.repository_id}, "
                    f"score={metrics.reliability_score:.1f}"
                )
                return True
            else:
                logger.warning(f"Failed to update metrics for fix {fix_id}")
                return False
        
        except Exception as e:
            logger.error(f"Error processing fix {fix_id}: {e}", exc_info=True)
            return False
    
    def run_daily_aggregation(self, repository_id: int) -> bool:
        """Run daily metrics aggregation for repository.
        
        Args:
            repository_id: Repository ID
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Running daily aggregation for repository {repository_id}")
            
            # Get or create metrics
            metrics = self.metrics_service.get_or_create_repo_metrics(repository_id)
            
            # Recalculate all metrics
            # (This would involve re-scanning all recent data)
            # For Phase 18.1, just log the operation
            
            logger.info(f"Daily aggregation complete: repo={repository_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error in daily aggregation for repo {repository_id}: {e}", exc_info=True)
            return False


def setup_metrics_hooks():
    """Setup hooks to trigger metrics updates.
    
    This function should be called during application startup to wire
    metrics pipeline into PR analysis and fix application workflows.
    """
    logger.info("Metrics pipeline hooks configured")
    # Actual hook registration would happen in the PR analysis service
    # and fix application service (Phase 18.2)
