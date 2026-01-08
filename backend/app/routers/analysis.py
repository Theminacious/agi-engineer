"""Analysis API endpoints for running and querying analysis."""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
from app.db import get_db
from app.models.analysis_run import AnalysisRun, RunStatus
from app.models.analysis_result import AnalysisResult
from app.models.repository import Repository
from app.v1_engine import V1AnalysisEngine
from app.config import settings
from app.schemas import AnalysisRunResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["analysis"])


@router.get("/runs/{run_id}")
async def get_analysis_run(
    run_id: int,
    db: Session = Depends(get_db),
):
    """Get analysis run details and results.
    
    Args:
        run_id: Analysis run ID
        db: Database session
        
    Returns:
        Run details with results
        
    Raises:
        HTTPException: If run not found
    """
    run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()

    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    results = db.query(AnalysisResult).filter(
        AnalysisResult.run_id == run_id
    ).all()

    return {
        "id": run.id,
        "repository_id": run.repository_id,
        "event": run.github_event,
        "branch": run.github_branch,
        "commit_sha": run.github_commit_sha,
        "pr_number": run.pull_request_number,
        "status": run.status.value,
        "total_results": len(results),
        "results": [
            {
                "id": r.id,
                "file_path": r.file_path,
                "line_number": r.line_number,
                "code": r.issue_code,
                "name": r.issue_name,
                "category": r.category.value,
                "message": r.message,
                "is_fixed": r.is_fixed,
            }
            for r in results
        ],
        "created_at": run.created_at,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "error": run.error_message,
    }


@router.get("/runs")
async def list_runs(
    repository_id: int = None,
    status: str = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List analysis runs with optional filtering.
    
    Args:
        repository_id: Filter by repository
        status: Filter by status (pending, in_progress, completed, failed)
        limit: Maximum results
        db: Database session
        
    Returns:
        List of runs
    """
    query = db.query(AnalysisRun)

    if repository_id:
        query = query.filter(AnalysisRun.repository_id == repository_id)

    if status:
        try:
            status_enum = RunStatus[status.upper()]
            query = query.filter(AnalysisRun.status == status_enum)
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    runs = query.order_by(AnalysisRun.created_at.desc()).limit(limit).all()

    return [
        {
            "id": r.id,
            "repository_id": r.repository_id,
            "event": r.github_event,
            "status": r.status.value,
            "branch": r.github_branch,
            "results_count": len(r.results),
            "created_at": r.created_at,
        }
        for r in runs
    ]


@router.post("/runs/{run_id}/execute")
async def execute_analysis(
    run_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Execute analysis for a pending run.
    
    This is called internally by webhooks. Runs analysis in background.
    
    Args:
        run_id: Analysis run ID
        background_tasks: FastAPI background tasks
        db: Database session
        
    Returns:
        Status response
        
    Raises:
        HTTPException: If run not found or not pending
    """
    run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()

    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if run.status != RunStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Run status is {run.status.value}, not pending")

    # Queue analysis as background task
    background_tasks.add_task(_execute_analysis_background, run_id)

    return {
        "status": "queued",
        "run_id": run_id,
        "message": "Analysis queued for execution",
    }


async def _execute_analysis_background(run_id: int) -> None:
    """Execute analysis in background.
    
    This function:
    1. Updates run status to in_progress
    2. Clones repository
    3. Runs V1 analysis engine
    4. Stores results in database
    5. Updates run status to completed/failed
    
    Args:
        run_id: Analysis run ID
    """
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        # Get run and repository info
        run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
        if not run:
            logger.error(f"Run {run_id} not found")
            return

        repository = db.query(Repository).filter(
            Repository.id == run.repository_id
        ).first()

        if not repository:
            logger.error(f"Repository {run.repository_id} not found")
            run.status = RunStatus.FAILED
            run.error_message = "Repository not found"
            db.commit()
            return

        # Update status to in_progress
        run.status = RunStatus.IN_PROGRESS
        run.started_at = datetime.utcnow()
        db.commit()
        logger.info(f"Starting analysis for run {run_id}")

        # Initialize V1 engine
        engine = V1AnalysisEngine(groq_api_key=settings.groq_api_key)

        try:
            # Run analysis
            analysis_result = engine.analyze_repository(
                repo_url=f"https://github.com/{repository.repo_full_name}",
                branch=run.github_branch,
                commit_sha=run.github_commit_sha,
            )

            if analysis_result["status"] == "failed":
                run.status = RunStatus.FAILED
                run.error_message = analysis_result.get("error", "Analysis failed")
                run.completed_at = datetime.utcnow()
                db.commit()
                logger.error(f"Analysis failed for run {run_id}: {analysis_result['error']}")
                return

            # Store results
            for issue in analysis_result.get("issues", []):
                result = AnalysisResult(
                    run_id=run_id,
                    file_path=issue.get("file_path", ""),
                    line_number=issue.get("line_number", 0),
                    issue_code=issue.get("issue_code", ""),
                    issue_name=issue.get("issue_name", ""),
                    category=issue.get("category", "suggestion"),
                    severity=issue.get("severity", "info"),
                    message=issue.get("message", ""),
                    is_fixed=0,
                )
                db.add(result)

            # Update run status
            run.status = RunStatus.COMPLETED
            run.completed_at = datetime.utcnow()
            db.commit()

            logger.info(
                f"Analysis completed for run {run_id}: "
                f"{analysis_result['total_issues']} issues found"
            )

        finally:
            engine.cleanup()

    except Exception as e:
        logger.error(f"Error during analysis execution: {str(e)}", exc_info=True)
        try:
            run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
            if run:
                run.status = RunStatus.FAILED
                run.error_message = str(e)
                run.completed_at = datetime.utcnow()
                db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update run status: {str(db_error)}")

    finally:
        db.close()


@router.get("/repositories/{repo_id}/health")
async def repository_health(
    repo_id: int,
    db: Session = Depends(get_db),
):
    """Get repository health metrics.
    
    Shows:
    - Total runs executed
    - Success/failure rate
    - Recent issues
    - Average analysis time
    
    Args:
        repo_id: Repository ID
        db: Database session
        
    Returns:
        Health metrics
        
    Raises:
        HTTPException: If repository not found
    """
    repository = db.query(Repository).filter(Repository.id == repo_id).first()

    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")

    runs = db.query(AnalysisRun).filter(
        AnalysisRun.repository_id == repo_id
    ).all()

    completed_runs = [r for r in runs if r.status == RunStatus.COMPLETED]
    failed_runs = [r for r in runs if r.status == RunStatus.FAILED]

    # Calculate average analysis time
    avg_time = None
    if completed_runs:
        total_time = sum(
            (r.completed_at - r.started_at).total_seconds()
            for r in completed_runs
            if r.started_at and r.completed_at
        )
        avg_time = total_time / len(completed_runs)

    # Get recent issues
    recent_results = db.query(AnalysisResult).join(AnalysisRun).filter(
        AnalysisRun.repository_id == repo_id
    ).order_by(AnalysisResult.created_at.desc()).limit(10).all()

    return {
        "repository_id": repo_id,
        "repository_name": repository.repo_full_name,
        "is_enabled": repository.is_enabled,
        "total_runs": len(runs),
        "completed_runs": len(completed_runs),
        "failed_runs": len(failed_runs),
        "success_rate": len(completed_runs) / len(runs) if runs else 0,
        "average_analysis_time_seconds": avg_time,
        "recent_issues": [
            {
                "file": r.file_path,
                "line": r.line_number,
                "code": r.issue_code,
                "message": r.message,
            }
            for r in recent_results
        ],
    }
