"""API router for code fixes and PR generation."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.db import get_db
from app.models.analysis_result import AnalysisResult
from app.models.code_fix import CodeFix, FixStatus
from app.tasks import generate_code_fix
from app.security import verify_token

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
