"""Celery tasks for AI-powered code fixing."""

from .celery_app import celery_app
from app.db import SessionLocal
from app.models.analysis_result import AnalysisResult
from app.models.code_fix import CodeFix, FixStatus
from app.ai.code_fixer import get_ai_provider
from datetime import datetime


@celery_app.task(name="app.tasks.generate_code_fix", bind=True)
def generate_code_fix(self, result_id: int, provider: str = "groq") -> dict:
    """Generate AI fix for a code issue.
    
    Args:
        result_id: ID of AnalysisResult to fix
        provider: AI provider ("groq" or "claude")
        
    Returns:
        Fix generation result
    """
    db = SessionLocal()
    
    try:
        # Get result
        result = db.query(AnalysisResult).filter(AnalysisResult.id == result_id).first()
        if not result:
            return {"error": f"Result {result_id} not found"}
        
        # Get AI provider
        ai = get_ai_provider(provider)
        
        # Prepare issue info
        issue_info = {
            "rule_id": result.rule_id,
            "name": result.name or result.code,
            "message": result.message,
            "category": result.category,
            "severity": result.severity,
        }
        
        # Generate fix
        fixed_code = ai.generate_fix(issue_info, result.code_snippet or "")
        
        # Generate explanation
        explanation = ai.generate_explanation(issue_info, fixed_code)
        
        # Save to database
        code_fix = CodeFix(
            result_id=result_id,
            original_code=result.code_snippet or "",
            fixed_code=fixed_code,
            explanation=explanation,
            status=FixStatus.GENERATED,
            ai_provider=provider,
        )
        
        db.add(code_fix)
        db.commit()
        db.refresh(code_fix)
        
        return {
            "status": "success",
            "fix_id": code_fix.id,
            "result_id": result_id,
            "explanation": explanation
        }
        
    except Exception as e:
        print(f"Error generating fix: {e}")
        
        # Try to save error fix
        try:
            code_fix = CodeFix(
                result_id=result_id,
                original_code=result.code_snippet or "",
                fixed_code="",
                explanation=f"Error: {str(e)}",
                status=FixStatus.FAILED,
                ai_provider=provider,
            )
            db.add(code_fix)
            db.commit()
        except:
            pass
        
        return {"status": "failed", "error": str(e)}
        
    finally:
        db.close()


@celery_app.task(name="app.tasks.create_github_pr")
def create_github_pr(fix_id: int, branch_name: str = None) -> dict:
    """Create GitHub PR from generated fix.
    
    Args:
        fix_id: ID of CodeFix
        branch_name: Optional custom branch name
        
    Returns:
        PR creation result
    """
    db = SessionLocal()
    
    try:
        # Get fix
        code_fix = db.query(CodeFix).filter(CodeFix.id == fix_id).first()
        if not code_fix:
            return {"error": f"Fix {fix_id} not found"}
        
        # Get result and run for context
        result = code_fix.result
        run = result.run if hasattr(result, 'run') else None
        
        if not run:
            return {"error": "Associated run not found"}
        
        # TODO: Implement GitHub PR creation
        # This would involve:
        # 1. Clone repo to temp dir
        # 2. Checkout new branch
        # 3. Apply fix
        # 4. Commit changes
        # 5. Push to GitHub
        # 6. Create PR via GitHub API
        
        # For now, just mark as pending
        code_fix.pr_url = f"https://github.com/{result.repository.github_full_name if hasattr(result, 'repository') else 'user/repo'}/pull/TBD"
        db.commit()
        
        return {
            "status": "pending",
            "fix_id": fix_id,
            "message": "PR creation implementation in progress"
        }
        
    except Exception as e:
        return {"status": "failed", "error": str(e)}
        
    finally:
        db.close()
