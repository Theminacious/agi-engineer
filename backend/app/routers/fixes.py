"""API router for code fixes and PR generation.

Phase 15.1: Governed Fix Approval & Application
- Approval/rejection endpoints with plan enforcement
- Governed fix application with validation
- Ledger integration for audit trail
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel

from app.db import get_db
from app.models.analysis_result import AnalysisResult
from app.models.code_fix import CodeFix, FixStatus
from app.tasks import generate_code_fix
from app.security import verify_token
from app.plans import UserPlanContext, PlanTier, create_plan_context
from app.services.fix_approval import FixApprovalService
from app.services.fix_application import FixApplicationService

router = APIRouter(prefix="/api/fixes", tags=["fixes"])


@router.post("/generate/{result_id}")
async def generate_fix(
    result_id: int,
    provider: str = Query("groq", description="AI provider: groq or claude"),
    token: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> dict:
    """Generate AI-powered fix for a code issue.
    
    Args:
        result_id: ID of the AnalysisResult to fix
        provider: AI provider ("groq" or "claude")
        token: JWT token
        db: Database session
        
    Returns:
        Fix generation status
    """
    # Get result
    result = db.query(AnalysisResult).filter(AnalysisResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Analysis result not found")
    
    # Check if fix already exists
    existing_fix = db.query(CodeFix).filter(CodeFix.result_id == result_id).first()
    if existing_fix:
        return {
            "status": "already_exists",
            "fix_id": existing_fix.id,
            "fix": existing_fix.to_dict()
        }
    
    # Queue fix generation task
    generate_code_fix.delay(result_id, provider)
    
    return {
        "status": "queued",
        "result_id": result_id,
        "message": f"Fix generation queued using {provider}",
        "check_url": f"/api/fixes/{result_id}"
    }


@router.get("/{result_id}")
async def get_fix(
    result_id: int,
    token: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> dict:
    """Get generated fix for a result.
    
    Args:
        result_id: ID of the AnalysisResult
        token: JWT token
        db: Database session
        
    Returns:
        Fix details or 404 if not found
    """
    fix = db.query(CodeFix).filter(CodeFix.result_id == result_id).first()
    if not fix:
        raise HTTPException(status_code=404, detail="Fix not found")
    
    return fix.to_dict()


@router.post("/{fix_id}/apply")
async def apply_fix(
    fix_id: int,
    token: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> dict:
    """Mark fix as applied (used for tracking).
    
    Args:
        fix_id: ID of the CodeFix
        token: JWT token
        db: Database session
        
    Returns:
        Updated fix details
    """
    fix = db.query(CodeFix).filter(CodeFix.id == fix_id).first()
    if not fix:
        raise HTTPException(status_code=404, detail="Fix not found")
    
    fix.status = FixStatus.APPLIED
    db.commit()
    db.refresh(fix)
    
    return fix.to_dict()


@router.post("/{fix_id}/create-pr")
async def create_pr_from_fix(
    fix_id: int,
    branch_name: Optional[str] = None,
    token: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> dict:
    """Create a GitHub PR from the fix.
    
    Args:
        fix_id: ID of the CodeFix
        branch_name: Optional custom branch name
        token: JWT token
        db: Database session
        
    Returns:
        PR creation status
    """
    fix = db.query(CodeFix).filter(CodeFix.id == fix_id).first()
    if not fix:
        raise HTTPException(status_code=404, detail="Fix not found")
    
    if fix.pr_url:
        return {
            "status": "already_exists",
            "pr_url": fix.pr_url,
            "message": "PR already created for this fix"
        }
    
    # Queue PR creation task
    from app.tasks import create_github_pr
    create_github_pr.delay(fix_id, branch_name)
    
    return {
        "status": "queued",
        "fix_id": fix_id,
        "message": "PR creation queued"
    }


@router.get("/result/{result_id}/all")
async def get_result_with_fix(
    result_id: int,
    token: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> dict:
    """Get analysis result with any associated fixes.
    
    Args:
        result_id: ID of the AnalysisResult
        token: JWT token
        db: Database session
        
    Returns:
        Result with fixes array
    """
    result = db.query(AnalysisResult).filter(AnalysisResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Analysis result not found")
    
    fixes = db.query(CodeFix).filter(CodeFix.result_id == result_id).all()
    
    return {
        "result": result.to_dict() if hasattr(result, 'to_dict') else {
            "id": result.id,
            "rule_id": result.rule_id,
            "message": result.message,
            "file_path": result.file_path,
            "line_number": result.line_number,
        },
        "fixes": [fix.to_dict() for fix in fixes],
        "has_fix": len(fixes) > 0,
        "fix_status": fixes[0].status.value if fixes else None
    }

# ----------------------------------------------------------------------
# Phase 15.1: Governed Fix Approval & Application
# ----------------------------------------------------------------------

class ApprovalRequest(BaseModel):
    """Request model for fix approval."""
    plan_tier: str = "developer"  # Plan tier (developer/team/enterprise)
    approved_by: str = "user@example.com"  # User identifier


class RejectionRequest(BaseModel):
    """Request model for fix rejection."""
    plan_tier: str = "developer"
    rejected_by: str = "user@example.com"
    reason: Optional[str] = None


class ApplicationRequest(BaseModel):
    """Request model for fix application."""
    plan_tier: str = "developer"
    applied_by: str = "user@example.com"
    repo_path: Optional[str] = None
    dry_run: bool = False


@router.post("/{fix_id}/approve")
async def approve_fix(
    fix_id: int,
    request: ApprovalRequest,
    token: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> dict:
    """
    Approve a proposed fix for application.
    
    Phase 15.1: Governed approval with plan enforcement.
    
    Workflow:
    1. Verify plan capabilities (Advanced+ only)
    2. Validate fix is in PROPOSED state
    3. Update fix status to APPROVED
    4. Record approval in ledger
    5. Return success/error
    
    Args:
        fix_id: ID of fix to approve
        request: Approval request with plan context
        token: JWT token
        db: Database session
        
    Returns:
        Approval result with fix data or error
    """
    # Create plan context
    try:
        plan_tier = PlanTier(request.plan_tier)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid plan tier: {request.plan_tier}")
    
    plan_context = create_plan_context(plan_tier)
    
    # Execute approval
    service = FixApprovalService(db)
    result = service.approve_fix(
        fix_id=fix_id,
        plan_context=plan_context,
        approved_by=request.approved_by,
        ledger_writer=None  # TODO: Integrate with RunLedgerWriter
    )
    
    if not result["success"]:
        status_code = 400
        if result.get("error") == "plan_restriction":
            status_code = 403
        elif result.get("error") == "not_found":
            status_code = 404
        raise HTTPException(status_code=status_code, detail=result["message"])
    
    return result


@router.post("/{fix_id}/reject")
async def reject_fix(
    fix_id: int,
    request: RejectionRequest,
    token: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> dict:
    """
    Reject a proposed fix.
    
    Phase 15.1: Governed rejection with plan enforcement.
    
    Args:
        fix_id: ID of fix to reject
        request: Rejection request with reason
        token: JWT token
        db: Database session
        
    Returns:
        Rejection result with fix data or error
    """
    # Create plan context
    try:
        plan_tier = PlanTier(request.plan_tier)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid plan tier: {request.plan_tier}")
    
    plan_context = create_plan_context(plan_tier)
    
    # Execute rejection
    service = FixApprovalService(db)
    result = service.reject_fix(
        fix_id=fix_id,
        plan_context=plan_context,
        rejected_by=request.rejected_by,
        reason=request.reason,
        ledger_writer=None
    )
    
    if not result["success"]:
        status_code = 400
        if result.get("error") == "plan_restriction":
            status_code = 403
        elif result.get("error") == "not_found":
            status_code = 404
        raise HTTPException(status_code=status_code, detail=result["message"])
    
    return result


@router.post("/{fix_id}/apply-governed")
async def apply_fix_governed(
    fix_id: int,
    request: ApplicationRequest,
    token: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> dict:
    """
    Apply an approved fix to codebase (governed workflow).
    
    Phase 15.1: Governed application with validation, rollback, and ledger recording.
    
    Workflow:
    1. Verify plan capabilities (Advanced+ only)
    2. Validate fix is in APPROVED state
    3. Validate file hasn't changed
    4. Generate and apply patch
    5. Record outcome in ledger
    6. Update fix status
    
    Args:
        fix_id: ID of fix to apply
        request: Application request with plan context
        token: JWT token
        db: Database session
        
    Returns:
        Application result with patch or error
    """
    # Create plan context
    try:
        plan_tier = PlanTier(request.plan_tier)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid plan tier: {request.plan_tier}")
    
    plan_context = create_plan_context(plan_tier)
    
    # Execute application
    service = FixApplicationService(db)
    result = service.apply_fix(
        fix_id=fix_id,
        plan_context=plan_context,
        applied_by=request.applied_by,
        repo_path=request.repo_path,
        ledger_writer=None,  # TODO: Integrate with RunLedgerWriter
        dry_run=request.dry_run
    )
    
    if not result["success"]:
        status_code = 400
        if result.get("error") == "plan_restriction":
            status_code = 403
        elif result.get("error") == "not_found":
            status_code = 404
        elif result.get("error") == "validation_failed":
            status_code = 422
        raise HTTPException(status_code=status_code, detail=result["message"])
    
    return result


@router.get("/run/{run_id}")
async def get_fixes_for_run(
    run_id: str,
    token: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> dict:
    """
    Get all fixes for a run.
    
    Phase 15.1: List all fixes with their states.
    
    Args:
        run_id: Run ID (ledger run ID)
        token: JWT token
        db: Database session
        
    Returns:
        List of fixes with counts by status
    """
    service = FixApprovalService(db)
    fixes = service.get_fixes_for_run(run_id)
    
    # Count by status
    status_counts = {
        "proposed": 0,
        "approved": 0,
        "rejected": 0,
        "applied": 0,
        "failed": 0,
    }
    
    for fix in fixes:
        status = fix.status.value.lower()
        if status in status_counts:
            status_counts[status] += 1
        elif status in ["pending", "generated"]:
            status_counts["proposed"] += 1
    
    return {
        "run_id": run_id,
        "fixes": [fix.to_dict() for fix in fixes],
        "total": len(fixes),
        "status_counts": status_counts,
    }