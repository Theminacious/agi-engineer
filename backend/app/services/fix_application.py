"""
Fix Application Service — Phase 15.1

Safely applies approved AI-generated fixes to codebase:
- Deterministic patch generation
- Pre-application validation
- Safe execution with rollback
- Comprehensive error handling
- Ledger recording of outcomes

Design Principles:
- No silent application
- Validate before apply
- Rollback on error
- All outcomes ledger-recorded
- Human approval required
"""
import logging
import os
import uuid
import difflib
import subprocess
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.code_fix import CodeFix, FixStatus
from app.plans import UserPlanContext

logger = logging.getLogger(__name__)


class FixApplicationService:
    """Service for safely applying approved fixes to codebase."""
    
    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db
    
    def can_apply_fix(self, plan_context: UserPlanContext) -> bool:
        """
        Check if user's plan allows fix application.
        
        Phase 15.1 Capabilities:
        - Core (developer): No fix application
        - Advanced (team): Can apply approved fixes
        - Autonomous (enterprise): Can apply approved fixes
        
        Args:
            plan_context: User's plan context
            
        Returns:
            True if user can apply fixes
        """
        return plan_context.plan_id in ["team", "enterprise"]
    
    def generate_patch(self, original_code: str, fixed_code: str, file_path: str = "file") -> str:
        """
        Generate unified diff patch.
        
        Args:
            original_code: Original code content
            fixed_code: Fixed code content
            file_path: File path for patch header
            
        Returns:
            Unified diff patch string
        """
        original_lines = original_code.splitlines(keepends=True)
        fixed_lines = fixed_code.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            original_lines,
            fixed_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm=""
        )
        
        return "".join(diff)
    
    def validate_fix(self, fix: CodeFix) -> Dict[str, Any]:
        """
        Validate fix before application.
        
        Checks:
        1. Fix is in APPROVED state
        2. File path exists
        3. Original code matches current file content
        4. Patch can be generated
        
        Args:
            fix: CodeFix to validate
            
        Returns:
            Validation result dict
        """
        errors = []
        warnings = []
        
        # 1. Check status
        if fix.status != FixStatus.APPROVED:
            errors.append(f"Fix is not approved (status={fix.status.value})")
        
        # 2. Check file path
        if not fix.file_path:
            errors.append("Fix has no file path specified")
        elif not os.path.exists(fix.file_path):
            errors.append(f"File does not exist: {fix.file_path}")
        else:
            # 3. Check original code matches
            try:
                with open(fix.file_path, 'r') as f:
                    current_content = f.read()
                
                if current_content != fix.original_code:
                    # Check if it's close (maybe whitespace differences)
                    if current_content.strip() == fix.original_code.strip():
                        warnings.append("File content differs in whitespace only")
                    else:
                        errors.append("File content has changed since fix was generated. Cannot safely apply.")
            except Exception as e:
                errors.append(f"Failed to read file: {str(e)}")
        
        # 4. Try generating patch
        if not errors:
            try:
                patch = self.generate_patch(
                    fix.original_code,
                    fix.fixed_code,
                    fix.file_path or "file"
                )
                if not patch:
                    warnings.append("Patch is empty (no changes detected)")
            except Exception as e:
                errors.append(f"Failed to generate patch: {str(e)}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def apply_fix(
        self,
        fix_id: int,
        plan_context: UserPlanContext,
        applied_by: str,
        repo_path: Optional[str] = None,
        ledger_writer=None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Apply approved fix to codebase.
        
        Workflow:
        1. Verify plan capabilities
        2. Get fix and validate
        3. Generate patch
        4. Apply patch to file
        5. Record outcome in ledger
        6. Update fix status
        
        Args:
            fix_id: ID of fix to apply
            plan_context: User's plan context
            applied_by: User identifier
            repo_path: Optional repository root path
            ledger_writer: Optional RunLedgerWriter
            dry_run: If True, validate but don't apply
            
        Returns:
            Result dict with status, fix data, patch, or error
        """
        try:
            # 1. Check plan capabilities
            if not self.can_apply_fix(plan_context):
                return {
                    "success": False,
                    "error": "plan_restriction",
                    "message": f"Your {plan_context.plan_id} plan does not allow fix application. Upgrade to Advanced Engineer.",
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
            
            # 3. Validate fix
            validation = self.validate_fix(fix)
            if not validation["valid"]:
                return {
                    "success": False,
                    "error": "validation_failed",
                    "message": "Fix validation failed",
                    "validation": validation
                }
            
            # 4. Generate patch
            patch = self.generate_patch(
                fix.original_code,
                fix.fixed_code,
                fix.file_path or "file"
            )
            
            # Store patch on fix object
            fix.patch = patch
            
            # Dry run: return validation + patch without applying
            if dry_run:
                return {
                    "success": True,
                    "dry_run": True,
                    "message": "Validation successful (dry run)",
                    "patch": patch,
                    "validation": validation,
                    "fix": fix.to_dict()
                }
            
            # 5. Apply fix to file
            try:
                if fix.file_path and os.path.exists(fix.file_path):
                    # Create backup
                    backup_path = f"{fix.file_path}.backup"
                    with open(fix.file_path, 'r') as f:
                        backup_content = f.read()
                    with open(backup_path, 'w') as f:
                        f.write(backup_content)
                    
                    try:
                        # Write fixed code
                        with open(fix.file_path, 'w') as f:
                            f.write(fix.fixed_code)
                        
                        logger.info(f"Fix {fix_id} applied to {fix.file_path}")
                        
                        # Remove backup on success
                        os.remove(backup_path)
                        
                    except Exception as write_error:
                        # Rollback from backup
                        logger.error(f"Failed to write fix, rolling back: {write_error}")
                        with open(backup_path, 'r') as f:
                            original = f.read()
                        with open(fix.file_path, 'w') as f:
                            f.write(original)
                        os.remove(backup_path)
                        raise write_error
                else:
                    raise ValueError("File path not specified or file does not exist")
                
            except Exception as apply_error:
                # Record failure
                now = datetime.utcnow()
                fix.status = FixStatus.FAILED
                fix.application_error = str(apply_error)
                fix.updated_at = now
                
                # Record in ledger
                if ledger_writer and fix.ledger_run_id:
                    ledger_writer.append_event(
                        event_type="FIX_APPLICATION_FAILED",
                        summary=f"Fix #{fix_id} application failed: {str(apply_error)}",
                        actor=applied_by,
                        actor_role="Human",
                        phase="PHASE_15.1",
                        payload_ref=None
                    )
                
                self.db.commit()
                
                return {
                    "success": False,
                    "error": "application_failed",
                    "message": f"Failed to apply fix: {str(apply_error)}",
                    "fix": fix.to_dict()
                }
            
            # 6. Update fix status
            now = datetime.utcnow()
            fix.status = FixStatus.APPLIED
            fix.applied_by = applied_by
            fix.applied_at = now
            fix.application_plan = plan_context.plan_id
            fix.application_metadata = {
                "repo_path": repo_path,
                "file_modified": fix.file_path,
                "applied_at": now.isoformat()
            }
            fix.updated_at = now
            
            # 7. Record success in ledger
            ledger_event_id = None
            if ledger_writer and fix.ledger_run_id:
                ledger_event_id = str(uuid.uuid4())
                ledger_writer.append_event(
                    event_type="FIX_APPLIED",
                    summary=f"Fix #{fix_id} successfully applied to {fix.file_path} by {applied_by}",
                    actor=applied_by,
                    actor_role="Human",
                    phase="PHASE_15.1",
                    payload_ref=ledger_event_id
                )
                fix.application_ledger_event_id = ledger_event_id
            
            # 8. Commit
            self.db.commit()
            self.db.refresh(fix)
            
            logger.info(f"Fix {fix_id} applied successfully by {applied_by}")
            
            return {
                "success": True,
                "fix": fix.to_dict(),
                "patch": patch,
                "ledger_event_id": ledger_event_id,
                "message": f"Fix applied successfully to {fix.file_path}"
            }
            
        except Exception as e:
            logger.error(f"Error applying fix {fix_id}: {e}", exc_info=True)
            self.db.rollback()
            return {
                "success": False,
                "error": "internal_error",
                "message": f"Failed to apply fix: {str(e)}"
            }
