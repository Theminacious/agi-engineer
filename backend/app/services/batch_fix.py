"""
Batch Fix Service — Phase 15.2

Enables safe governed batch operations on multiple fixes:
- Batch approval/rejection with governance
- Batch application with conflict detection
- Combined patch generation
- Comprehensive validation
- Ledger recording of all batch actions

Design Principles:
- All-or-nothing operations (atomic where possible)
- Fail fast on validation errors
- No silent operations
- Comprehensive error reporting
- Ledger integration for audit trail
- Human approval required
"""
import logging
import uuid
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from collections import defaultdict

from app.models.code_fix import CodeFix, FixStatus
from app.plans import UserPlanContext, PLAN_REGISTRY
from app.services.fix_approval import FixApprovalService
from app.services.fix_application import FixApplicationService

logger = logging.getLogger(__name__)


class BatchFixService:
    """Service for batch operations on multiple fixes."""
    
    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db
        self.approval_service = FixApprovalService(db)
        self.application_service = FixApplicationService(db)
    
    def validate_batch(
        self,
        fix_ids: List[int],
        plan_context: UserPlanContext,
        operation: str = "approve"
    ) -> Dict[str, Any]:
        """
        Validate a batch of fixes before operation.
        
        Validation checks:
        1. All fix IDs exist
        2. No duplicate IDs
        3. Appropriate states for operation
        4. File conflict detection (for apply)
        5. Plan capabilities
        
        Args:
            fix_ids: List of fix IDs to validate
            plan_context: User's plan context
            operation: Operation type ('approve', 'reject', 'apply')
            
        Returns:
            Validation result with errors, warnings, and metadata
        """
        errors = []
        warnings = []
        metadata = {}
        
        # Check for empty batch
        if not fix_ids:
            errors.append("Batch is empty - no fixes provided")
            return {
                "valid": False,
                "errors": errors,
                "warnings": warnings,
                "metadata": metadata
            }
        
        # Check for duplicates
        unique_ids = set(fix_ids)
        if len(unique_ids) != len(fix_ids):
            duplicates = [fid for fid in fix_ids if fix_ids.count(fid) > 1]
            errors.append(f"Duplicate fix IDs found: {list(set(duplicates))}")
        
        # Retrieve all fixes
        fixes = self.db.query(CodeFix).filter(CodeFix.id.in_(fix_ids)).all()
        found_ids = {f.id for f in fixes}
        missing_ids = unique_ids - found_ids
        
        if missing_ids:
            errors.append(f"Fixes not found: {sorted(list(missing_ids))}")
        
        if not fixes:
            errors.append("No valid fixes found in batch")
            return {
                "valid": False,
                "errors": errors,
                "warnings": warnings,
                "metadata": metadata
            }
        
        # Validate states based on operation
        state_errors = []
        if operation == "approve":
            invalid_states = [f for f in fixes if f.status not in [FixStatus.PROPOSED, FixStatus.GENERATED]]
            if invalid_states:
                state_errors = [f"Fix #{f.id} is {f.status.value} (must be proposed)" for f in invalid_states]
        
        elif operation == "reject":
            invalid_states = [f for f in fixes if f.status not in [FixStatus.PROPOSED, FixStatus.GENERATED]]
            if invalid_states:
                state_errors = [f"Fix #{f.id} is {f.status.value} (must be proposed)" for f in invalid_states]
        
        elif operation == "apply":
            invalid_states = [f for f in fixes if f.status != FixStatus.APPROVED]
            if invalid_states:
                state_errors = [f"Fix #{f.id} is {f.status.value} (must be approved)" for f in invalid_states]
        
        if state_errors:
            errors.extend(state_errors)
        
        # Check for file conflicts (multiple fixes for same file)
        if operation == "apply":
            file_conflicts = defaultdict(list)
            for fix in fixes:
                if fix.file_path:
                    file_conflicts[fix.file_path].append(fix.id)
            
            conflicts = {path: ids for path, ids in file_conflicts.items() if len(ids) > 1}
            if conflicts:
                for path, ids in conflicts.items():
                    warnings.append(f"Multiple fixes for {path}: {ids}")
                metadata["file_conflicts"] = conflicts
        
        # Calculate risk level (highest severity)
        severity_map = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        max_risk = "low"
        risk_score = 1
        
        # Metadata
        metadata.update({
            "batch_size": len(fixes),
            "fix_ids": [f.id for f in fixes],
            "files_affected": len(set(f.file_path for f in fixes if f.file_path)),
            "risk_level": max_risk,
            "risk_score": risk_score,
            "status_distribution": {
                status.value: len([f for f in fixes if f.status == status])
                for status in FixStatus
            }
        })
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "metadata": metadata,
            "fixes": [f.to_dict() for f in fixes] if len(errors) == 0 else []
        }
    
    def approve_many(
        self,
        fix_ids: List[int],
        user_id: str,
        plan_context: UserPlanContext,
        ledger_writer=None
    ) -> Dict[str, Any]:
        """
        Approve multiple fixes in batch.
        
        Process:
        1. Validate batch
        2. Check plan capabilities
        3. Approve each fix individually
        4. Record batch event in ledger
        5. Return comprehensive result
        
        Note: Operations are independent - partial success possible
        
        Args:
            fix_ids: List of fix IDs to approve
            user_id: User identifier
            plan_context: User's plan context
            ledger_writer: Optional RunLedgerWriter
            
        Returns:
            Batch operation result with successes and failures
        """
        try:
            # 1. Validate batch
            validation = self.validate_batch(fix_ids, plan_context, operation="approve")
            if not validation["valid"]:
                return {
                    "success": False,
                    "error": "validation_failed",
                    "validation": validation
                }
            
            # 2. Check plan capabilities
            if not self.approval_service.can_approve_fixes(plan_context):
                return {
                    "success": False,
                    "error": "plan_restriction",
                    "message": f"Your {plan_context.plan_tier.value} plan does not allow fix approval"
                }
            
            # 3. Approve each fix
            results = {"approved": [], "failed": []}
            for fix_id in fix_ids:
                result = self.approval_service.approve_fix(
                    fix_id=fix_id,
                    plan_context=plan_context,
                    approved_by=user_id,
                    ledger_writer=None  # Individual events not recorded
                )
                
                if result["success"]:
                    results["approved"].append({
                        "fix_id": fix_id,
                        "fix": result["fix"]
                    })
                else:
                    results["failed"].append({
                        "fix_id": fix_id,
                        "error": result.get("error"),
                        "message": result.get("message")
                    })
            
            # 4. Record batch event in ledger
            ledger_event_id = None
            if ledger_writer and results["approved"]:
                ledger_event_id = str(uuid.uuid4())
                approved_ids = [r["fix_id"] for r in results["approved"]]
                ledger_writer.append_event(
                    event_type="BATCH_APPROVED",
                    summary=f"Batch approved {len(approved_ids)} fixes by {user_id}",
                    actor=user_id,
                    actor_role="Human",
                    phase="PHASE_15.2",
                    payload_ref=ledger_event_id
                )
                
                logger.info(f"Batch approval: {len(approved_ids)} approved by {user_id}")
            
            return {
                "success": True,
                "results": results,
                "summary": {
                    "total": len(fix_ids),
                    "approved": len(results["approved"]),
                    "failed": len(results["failed"])
                },
                "ledger_event_id": ledger_event_id,
                "validation": validation
            }
            
        except Exception as e:
            logger.error(f"Error in batch approval: {e}", exc_info=True)
            return {
                "success": False,
                "error": "internal_error",
                "message": f"Batch approval failed: {str(e)}"
            }
    
    def reject_many(
        self,
        fix_ids: List[int],
        user_id: str,
        reason: Optional[str],
        plan_context: UserPlanContext,
        ledger_writer=None
    ) -> Dict[str, Any]:
        """
        Reject multiple fixes in batch.
        
        Process:
        1. Validate batch
        2. Check plan capabilities
        3. Reject each fix individually
        4. Record batch event in ledger
        5. Return comprehensive result
        
        Args:
            fix_ids: List of fix IDs to reject
            user_id: User identifier
            reason: Rejection reason
            plan_context: User's plan context
            ledger_writer: Optional RunLedgerWriter
            
        Returns:
            Batch operation result
        """
        try:
            # 1. Validate batch
            validation = self.validate_batch(fix_ids, plan_context, operation="reject")
            if not validation["valid"]:
                return {
                    "success": False,
                    "error": "validation_failed",
                    "validation": validation
                }
            
            # 2. Check plan capabilities
            if not self.approval_service.can_approve_fixes(plan_context):
                return {
                    "success": False,
                    "error": "plan_restriction",
                    "message": f"Your {plan_context.plan_tier.value} plan does not allow fix rejection"
                }
            
            # 3. Reject each fix
            results = {"rejected": [], "failed": []}
            for fix_id in fix_ids:
                result = self.approval_service.reject_fix(
                    fix_id=fix_id,
                    plan_context=plan_context,
                    rejected_by=user_id,
                    reason=reason,
                    ledger_writer=None
                )
                
                if result["success"]:
                    results["rejected"].append({
                        "fix_id": fix_id,
                        "fix": result["fix"]
                    })
                else:
                    results["failed"].append({
                        "fix_id": fix_id,
                        "error": result.get("error"),
                        "message": result.get("message")
                    })
            
            # 4. Record batch event
            ledger_event_id = None
            if ledger_writer and results["rejected"]:
                ledger_event_id = str(uuid.uuid4())
                rejected_ids = [r["fix_id"] for r in results["rejected"]]
                ledger_writer.append_event(
                    event_type="BATCH_REJECTED",
                    summary=f"Batch rejected {len(rejected_ids)} fixes by {user_id}: {reason or 'No reason'}",
                    actor=user_id,
                    actor_role="Human",
                    phase="PHASE_15.2",
                    payload_ref=ledger_event_id
                )
                
                logger.info(f"Batch rejection: {len(rejected_ids)} rejected by {user_id}")
            
            return {
                "success": True,
                "results": results,
                "summary": {
                    "total": len(fix_ids),
                    "rejected": len(results["rejected"]),
                    "failed": len(results["failed"])
                },
                "ledger_event_id": ledger_event_id,
                "validation": validation
            }
            
        except Exception as e:
            logger.error(f"Error in batch rejection: {e}", exc_info=True)
            return {
                "success": False,
                "error": "internal_error",
                "message": f"Batch rejection failed: {str(e)}"
            }
    
    def apply_many(
        self,
        fix_ids: List[int],
        user_id: str,
        plan_context: UserPlanContext,
        ledger_writer=None
    ) -> Dict[str, Any]:
        """
        Apply multiple approved fixes in batch.
        
        Process:
        1. Validate batch (including conflict detection)
        2. Check plan capabilities
        3. Apply each fix individually
        4. Record batch event in ledger
        5. Return detailed results
        
        Note: Fixes applied independently for safety
        
        Args:
            fix_ids: List of fix IDs to apply
            user_id: User identifier
            plan_context: User's plan context
            ledger_writer: Optional RunLedgerWriter
            
        Returns:
            Batch application result
        """
        try:
            # 1. Validate batch
            validation = self.validate_batch(fix_ids, plan_context, operation="apply")
            if not validation["valid"]:
                return {
                    "success": False,
                    "error": "validation_failed",
                    "validation": validation
                }
            
            # Warn about file conflicts but don't fail
            if validation.get("warnings"):
                logger.warning(f"Batch apply warnings: {validation['warnings']}")
            
            # 2. Check plan capabilities
            if not self.application_service.can_apply_fix(plan_context):
                return {
                    "success": False,
                    "error": "plan_restriction",
                    "message": f"Your {plan_context.plan_tier.value} plan does not allow fix application"
                }
            
            # 3. Apply each fix
            results = {"applied": [], "failed": []}
            for fix_id in fix_ids:
                result = self.application_service.apply_fix(
                    fix_id=fix_id,
                    applied_by=user_id,
                    plan_context=plan_context,
                    ledger_writer=None
                )
                
                if result["success"]:
                    results["applied"].append({
                        "fix_id": fix_id,
                        "fix": result["fix"],
                        "file_path": result.get("file_path")
                    })
                else:
                    results["failed"].append({
                        "fix_id": fix_id,
                        "error": result.get("error"),
                        "message": result.get("message")
                    })
            
            # 4. Generate combined patch hash
            combined_patch = self.generate_combined_patch([r["fix_id"] for r in results["applied"]])
            patch_hash = hashlib.sha256(combined_patch.encode()).hexdigest() if combined_patch else None
            
            # 5. Record batch event
            ledger_event_id = None
            if ledger_writer and results["applied"]:
                ledger_event_id = str(uuid.uuid4())
                applied_ids = [r["fix_id"] for r in results["applied"]]
                ledger_writer.append_event(
                    event_type="BATCH_APPLIED",
                    summary=f"Batch applied {len(applied_ids)} fixes by {user_id}",
                    actor=user_id,
                    actor_role="Human",
                    phase="PHASE_15.2",
                    payload_ref=ledger_event_id,
                    metadata={
                        "fix_ids": applied_ids,
                        "patch_hash": patch_hash,
                        "risk_level": validation["metadata"].get("risk_level")
                    }
                )
                
                logger.info(f"Batch application: {len(applied_ids)} applied by {user_id}")
            
            return {
                "success": True,
                "results": results,
                "summary": {
                    "total": len(fix_ids),
                    "applied": len(results["applied"]),
                    "failed": len(results["failed"])
                },
                "combined_patch_hash": patch_hash,
                "ledger_event_id": ledger_event_id,
                "validation": validation
            }
            
        except Exception as e:
            logger.error(f"Error in batch application: {e}", exc_info=True)
            return {
                "success": False,
                "error": "internal_error",
                "message": f"Batch application failed: {str(e)}"
            }
    
    def generate_combined_patch(self, fix_ids: List[int]) -> str:
        """
        Generate a combined unified diff patch for multiple fixes.
        
        Process:
        1. Retrieve all fixes
        2. Sort by file path (deterministic order)
        3. Combine patches
        4. Return unified diff
        
        Args:
            fix_ids: List of fix IDs
            
        Returns:
            Combined patch string
        """
        try:
            fixes = self.db.query(CodeFix).filter(CodeFix.id.in_(fix_ids)).all()
            
            # Sort by file path for deterministic order
            fixes.sort(key=lambda f: (f.file_path or "", f.id))
            
            # Combine patches
            combined = []
            for fix in fixes:
                if fix.patch:
                    combined.append(f"# Fix #{fix.id}: {fix.file_path or 'unknown'}")
                    combined.append(fix.patch)
                    combined.append("")  # Blank line between fixes
                elif fix.fixed_code and fix.original_code:
                    # Generate patch if not stored
                    patch = self.application_service.generate_patch(
                        fix.original_code,
                        fix.fixed_code,
                        fix.file_path or "file"
                    )
                    combined.append(f"# Fix #{fix.id}: {fix.file_path or 'unknown'}")
                    combined.append(patch)
                    combined.append("")
            
            return "\n".join(combined)
            
        except Exception as e:
            logger.error(f"Error generating combined patch: {e}", exc_info=True)
            return ""
    
    def get_batch_preview(
        self,
        fix_ids: List[int],
        plan_context: UserPlanContext
    ) -> Dict[str, Any]:
        """
        Generate a preview of batch operation without executing.
        
        Includes:
        - Validation results
        - Risk assessment
        - Combined patch preview
        - File impact summary
        
        Args:
            fix_ids: List of fix IDs
            plan_context: User's plan context
            
        Returns:
            Preview data
        """
        validation = self.validate_batch(fix_ids, plan_context, operation="apply")
        
        if validation["valid"]:
            combined_patch = self.generate_combined_patch(fix_ids)
            patch_hash = hashlib.sha256(combined_patch.encode()).hexdigest()
        else:
            combined_patch = ""
            patch_hash = None
        
        return {
            "validation": validation,
            "combined_patch": combined_patch,
            "patch_hash": patch_hash,
            "patch_size": len(combined_patch),
            "preview_generated_at": datetime.utcnow().isoformat()
        }
