"""
Fix Approval Service — Phase 15.1

Governs the approval workflow for AI-generated fixes:
- Approve/reject proposals with human oversight
- Record all decisions in ledger
- Enforce plan-based capabilities
- Maintain immutable audit trail

Design Principles:
- No silent approvals
- All actions ledger-recorded
- Plan capabilities enforced
- Human-in-the-loop required
"""
import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.code_fix import CodeFix, FixStatus
from app.plans import UserPlanContext, PLAN_REGISTRY

logger = logging.getLogger(__name__)


class FixApprovalService:
    """Service for governing fix approval workflow."""
    
    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db
    
    def can_approve_fixes(self, plan_context: UserPlanContext) -> bool:
        """
        Check if user's plan allows fix approval.
        
        Phase 15.1 Capabilities:
        - Core (developer): View-only, no approval
        - Advanced (team): Can approve & apply fixes
        - Autonomous (enterprise): Can approve & apply fixes (+ batch future)
        
        Args:
            plan_context: User's plan context
            
        Returns:
            True if user can approve fixes
        """
        plan_def = PLAN_REGISTRY.get(plan_context.plan_id)
        if not plan_def:
            return False
        
        # Check if plan includes fix approval capability
        # Phase 15.1: Only Advanced and Autonomous can approve
        return plan_context.plan_id in ["team", "enterprise"]
    
    def can_apply_fixes(self, plan_context: UserPlanContext) -> bool:
        """
        Check if user's plan allows fix application.
        
        Same rules as approval (for Phase 15.1).
        
        Args:
            plan_context: User's plan context
            
        Returns:
            True if user can apply fixes
        """
        return self.can_approve_fixes(plan_context)
    
    def approve_fix(
        self,
        fix_id: int,
        plan_context: UserPlanContext,
        approved_by: str,
        ledger_writer=None
    ) -> Dict[str, Any]:
        """
        Approve a proposed fix for application.
        
        Workflow:
        1. Verify plan capabilities
        2. Check fix is in PROPOSED state
        3. Update fix status to APPROVED
        4. Record approval in ledger
        5. Return success/error
        
        Args:
            fix_id: ID of fix to approve
            plan_context: User's plan context
            approved_by: User identifier (email/ID)
            ledger_writer: Optional RunLedgerWriter for recording
            
        Returns:
            Result dict with status, fix data, or error
        """
        try:
            # 1. Check plan capabilities
            if not self.can_approve_fixes(plan_context):
                return {
                    "success": False,
                    "error": "plan_restriction",
                    "message": f"Your {plan_context.plan_id} plan does not allow fix approval. Upgrade to Advanced Engineer to approve and apply fixes.",
                    "required_plan": "team"
                }
            
            # 2. Get fix
            fix = self.db.query(CodeFix).filter(CodeFix.id == fix_id).first()
            if not fix:
                return {
                    "success": False,
                    "error": "not_found",
                    "message": f"Fix {fix_id} not found"
                }
            
            # 3. Check state
            if fix.status not in [FixStatus.PROPOSED, FixStatus.GENERATED]:
                return {
                    "success": False,
                    "error": "invalid_state",
                    "message": f"Fix is in {fix.status.value} state, cannot approve. Only PROPOSED fixes can be approved.",
                    "current_status": fix.status.value
                }
            
            # 4. Update fix
            now = datetime.utcnow()
            fix.status = FixStatus.APPROVED
            fix.approved_by = approved_by
            fix.approved_at = now
            fix.approval_plan = plan_context.plan_id
            fix.updated_at = now
            
            # 5. Record in ledger
            ledger_event_id = None
            if ledger_writer and fix.ledger_run_id:
                ledger_event_id = str(uuid.uuid4())
                ledger_writer.append_event(
                    event_type="FIX_APPROVED",
                    summary=f"Fix #{fix_id} approved for application by {approved_by}",
                    actor=approved_by,
                    actor_role="Human",
                    phase="PHASE_15.1",
                    payload_ref=ledger_event_id
                )
                fix.approval_ledger_event_id = ledger_event_id
            
            # 6. Commit
            self.db.commit()
            self.db.refresh(fix)
            
            logger.info(f"Fix {fix_id} approved by {approved_by} (plan={plan_context.plan_id})")
            
            return {
                "success": True,
                "fix": fix.to_dict(),
                "ledger_event_id": ledger_event_id,
                "message": "Fix approved successfully. Ready to apply."
            }
            
        except Exception as e:
            logger.error(f"Error approving fix {fix_id}: {e}", exc_info=True)
            self.db.rollback()
            return {
                "success": False,
                "error": "internal_error",
                "message": f"Failed to approve fix: {str(e)}"
            }
    
    def reject_fix(
        self,
        fix_id: int,
        plan_context: UserPlanContext,
        rejected_by: str,
        reason: Optional[str] = None,
        ledger_writer=None
    ) -> Dict[str, Any]:
        """
        Reject a proposed fix.
        
        Workflow:
        1. Verify plan capabilities (same as approve)
        2. Check fix is in PROPOSED state
        3. Update fix status to REJECTED
        4. Record rejection in ledger
        5. Return success/error
        
        Args:
            fix_id: ID of fix to reject
            plan_context: User's plan context
            rejected_by: User identifier
            reason: Optional rejection reason
            ledger_writer: Optional RunLedgerWriter
            
        Returns:
            Result dict with status, fix data, or error
        """
        try:
            # 1. Check plan capabilities
            if not self.can_approve_fixes(plan_context):
                return {
                    "success": False,
                    "error": "plan_restriction",
                    "message": f"Your {plan_context.plan_id} plan does not allow fix rejection.",
                    "required_plan": "team"
                }
            
            # 2. Get fix
            fix = self.db.query(CodeFix).filter(CodeFix.id == fix_id).first()
            if not fix:
                return {
                    "success": False,
                    "error": "not_found",
                    "message": f"Fix {fix_id} not found"
                }
            
            # 3. Check state
            if fix.status not in [FixStatus.PROPOSED, FixStatus.GENERATED]:
                return {
                    "success": False,
                    "error": "invalid_state",
                    "message": f"Fix is in {fix.status.value} state, cannot reject.",
                    "current_status": fix.status.value
                }
            
            # 4. Update fix
            now = datetime.utcnow()
            fix.status = FixStatus.REJECTED
            fix.rejected_by = rejected_by
            fix.rejected_at = now
            fix.rejection_reason = reason
            fix.updated_at = now
            
            # 5. Record in ledger
            if ledger_writer and fix.ledger_run_id:
                ledger_writer.append_event(
                    event_type="FIX_REJECTED",
                    summary=f"Fix #{fix_id} rejected by {rejected_by}: {reason or 'No reason provided'}",
                    actor=rejected_by,
                    actor_role="Human",
                    phase="PHASE_15.1",
                    payload_ref=None
                )
            
            # 6. Commit
            self.db.commit()
            self.db.refresh(fix)
            
            logger.info(f"Fix {fix_id} rejected by {rejected_by} (reason={reason})")
            
            return {
                "success": True,
                "fix": fix.to_dict(),
                "message": "Fix rejected successfully."
            }
            
        except Exception as e:
            logger.error(f"Error rejecting fix {fix_id}: {e}", exc_info=True)
            self.db.rollback()
            return {
                "success": False,
                "error": "internal_error",
                "message": f"Failed to reject fix: {str(e)}"
            }
    
    def get_fix_by_id(self, fix_id: int) -> Optional[CodeFix]:
        """Get fix by ID."""
        return self.db.query(CodeFix).filter(CodeFix.id == fix_id).first()
    
    def get_fixes_for_run(self, run_id: str) -> list[CodeFix]:
        """Get all fixes for a run."""
        return self.db.query(CodeFix).filter(
            CodeFix.ledger_run_id == run_id
        ).order_by(CodeFix.created_at.desc()).all()
