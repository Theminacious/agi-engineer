"""GitHub webhook event handlers."""

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from app.db import get_db
from app.models.repository import Repository
from app.models.analysis_run import AnalysisRun, RunStatus
from app.security import validate_webhook_signature
from app.config import settings
from app.tasks import run_code_analysis
import json

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/github")
async def github_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """Handle GitHub webhook events.
    
    Supported events:
    - push: Trigger analysis on code push
    - pull_request: Trigger analysis on PR opened/synchronize
    - pull_request_review: Trigger analysis on review requested
    
    Args:
        request: FastAPI request object
        db: Database session
        
    Returns:
        Webhook processing status
        
    Raises:
        HTTPException: If signature validation fails or event processing fails
    """
    # Validate webhook signature
    signature = request.headers.get("X-Hub-Signature-256")
    if not signature:
        raise HTTPException(status_code=401, detail="Missing signature")

    body = await request.body()
    if not validate_webhook_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse payload
    payload = json.loads(body)
    event_type = request.headers.get("X-GitHub-Event")
    action = payload.get("action")

    try:
        if event_type == "push":
            return await handle_push_event(payload, db)
        elif event_type == "pull_request":
            return await handle_pull_request_event(payload, action, db)
        elif event_type == "pull_request_review":
            return await handle_review_event(payload, db)
        else:
            return {"status": "ignored", "event": event_type}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")


async def handle_push_event(payload: dict, db: Session) -> dict:
    """Handle push event - trigger analysis on code push.
    
    Args:
        payload: GitHub push event payload
        db: Database session
        
    Returns:
        Processing status
    """
    repo_full_name = payload.get("repository", {}).get("full_name")
    repo_id = payload.get("repository", {}).get("id")
    ref = payload.get("ref", "").split("/")[-1]  # Get branch name
    commit_sha = payload.get("after")

    if not all([repo_full_name, commit_sha]):
        return {"status": "skipped", "reason": "Missing required fields"}

    # Find repository
    repository = db.query(Repository).filter(
        Repository.github_repo_id == repo_id
    ).first()

    if not repository:
        return {"status": "skipped", "reason": "Repository not tracked"}

    if not repository.is_enabled:
        return {"status": "skipped", "reason": "Repository analysis disabled"}

    # Create analysis run
    run = AnalysisRun(
        repository_id=repository.id,
        github_event="push",
        github_branch=ref,
        github_commit_sha=commit_sha,
        status=RunStatus.PENDING,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    # Queue background task for analysis
    run_code_analysis.delay(run.id)

    return {
        "status": "queued",
        "event": "push",
        "repository": repo_full_name,
        "branch": ref,
        "run_id": run.id,
    }


async def handle_pull_request_event(payload: dict, action: str, db: Session) -> dict:
    """Handle pull request event.
    
    Args:
        payload: GitHub PR event payload
        action: PR action (opened, synchronize, etc.)
        db: Database session
        
    Returns:
        Processing status
    """
    # Only trigger on these actions
    if action not in ["opened", "synchronize", "reopened"]:
        return {"status": "ignored", "reason": f"Action '{action}' not configured"}

    repo_full_name = payload.get("repository", {}).get("full_name")
    repo_id = payload.get("repository", {}).get("id")
    pr_number = payload.get("pull_request", {}).get("number")
    branch = payload.get("pull_request", {}).get("head", {}).get("ref")
    commit_sha = payload.get("pull_request", {}).get("head", {}).get("sha")

    if not all([repo_full_name, pr_number, commit_sha]):
        return {"status": "skipped", "reason": "Missing required fields"}

    # Find repository
    repository = db.query(Repository).filter(
        Repository.github_repo_id == repo_id
    ).first()

    if not repository or not repository.is_enabled:
        return {"status": "skipped", "reason": "Repository not tracked or disabled"}

    # Create analysis run
    run = AnalysisRun(
        repository_id=repository.id,
        github_event="pull_request",
        github_branch=branch,
        github_commit_sha=commit_sha,
        pull_request_number=pr_number,
        status=RunStatus.PENDING,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    # Queue background task for analysis
    run_code_analysis.delay(run.id)

    return {
        "status": "queued",
        "event": "pull_request",
        "action": action,
        "repository": repo_full_name,
        "pr": pr_number,
        "run_id": run.id,
    }


async def handle_review_event(payload: dict, db: Session) -> dict:
    """Handle pull request review event.
    
    Args:
        payload: GitHub review event payload
        db: Database session
        
    Returns:
        Processing status
    """
    action = payload.get("action")

    # Only trigger on review request
    if action not in ["requested_reviewer", "submitted"]:
        return {"status": "ignored", "reason": f"Action '{action}' not configured"}

    repo_full_name = payload.get("repository", {}).get("full_name")
    repo_id = payload.get("repository", {}).get("id")
    pr_number = payload.get("pull_request", {}).get("number")
    branch = payload.get("pull_request", {}).get("head", {}).get("ref")
    commit_sha = payload.get("pull_request", {}).get("head", {}).get("sha")

    if not all([repo_full_name, pr_number, commit_sha]):
        return {"status": "skipped", "reason": "Missing required fields"}

    # Find repository
    repository = db.query(Repository).filter(
        Repository.github_repo_id == repo_id
    ).first()

    if not repository or not repository.is_enabled:
        return {"status": "skipped", "reason": "Repository not tracked or disabled"}

    # Create analysis run
    run = AnalysisRun(
        repository_id=repository.id,
        github_event="pull_request_review",
        github_branch=branch,
        github_commit_sha=commit_sha,
        pull_request_number=pr_number,
        status=RunStatus.PENDING,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    # Queue background task for analysis
    run_code_analysis.delay(run.id)

    return {
        "status": "queued",
        "event": "pull_request_review",
        "action": action,
        "repository": repo_full_name,
        "pr": pr_number,
        "run_id": run.id,
    }
