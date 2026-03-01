"""GitHub Webhook Router for Phase 17 — GitHub Intelligence Integration.

Handles incoming webhooks from GitHub App.
"""

import logging
import json
from typing import Dict, Any

from fastapi import APIRouter, Request, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from app.db import get_db, SessionLocal
from app.models import (
    GitHubWebhookEvent,
    PRAnalysis,
    PRAnalysisStatus,
    WebhookEventType,
    Installation
)
from app.services.github_service import GitHubService
from app.services.pr_analysis import PRAnalysisPipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/github", tags=["github"])


@router.post("/webhook")
async def handle_github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Handle incoming GitHub webhook events.
    
    Supports:
    - pull_request (opened, synchronize, reopened)
    - push
    
    Idempotent: Uses delivery_id to prevent duplicate processing.
    """
    # Get headers
    event_type = request.headers.get("X-GitHub-Event")
    delivery_id = request.headers.get("X-GitHub-Delivery")
    signature = request.headers.get("X-Hub-Signature-256")
    
    if not delivery_id:
        raise HTTPException(status_code=400, detail="Missing X-GitHub-Delivery header")
    
    # Check for duplicate delivery (idempotent)
    existing = db.query(GitHubWebhookEvent).filter(
        GitHubWebhookEvent.delivery_id == delivery_id
    ).first()
    
    if existing:
        logger.info(f"Webhook {delivery_id} already processed, skipping")
        return {"status": "already_processed", "delivery_id": delivery_id}
    
    # Read raw body
    raw_body = await request.body()
    
    # Parse JSON payload
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    # Verify signature
    github_service = GitHubService(db)
    signature_valid = github_service.verify_webhook_signature(raw_body, signature)
    
    if not signature_valid:
        logger.warning(f"Invalid webhook signature for delivery {delivery_id}")
        # Continue processing but log warning (some test webhooks may not have signature)
    
    # Route based on event type
    if event_type == "pull_request":
        return await _handle_pull_request_event(
            delivery_id=delivery_id,
            signature_valid=signature_valid,
            payload=payload,
            db=db,
            background_tasks=background_tasks
        )
    
    elif event_type == "push":
        return await _handle_push_event(
            delivery_id=delivery_id,
            signature_valid=signature_valid,
            payload=payload,
            db=db,
            background_tasks=background_tasks
        )
    
    else:
        logger.info(f"Ignoring unsupported event type: {event_type}")
        return {"status": "ignored", "event_type": event_type}


async def _handle_pull_request_event(
    delivery_id: str,
    signature_valid: bool,
    payload: Dict[str, Any],
    db: Session,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Handle pull_request webhook event.
    
    Actions:
    - opened: Start new analysis
    - synchronize: Re-analyze with new commits
    - reopened: Re-analyze
    """
    action = payload.get("action")
    
    # Only process specific actions
    if action not in ["opened", "synchronize", "reopened"]:
        logger.info(f"Ignoring PR action: {action}")
        return {"status": "ignored", "action": action}
    
    # Extract PR data
    pr_data = payload.get("pull_request", {})
    repo_data = payload.get("repository", {})
    installation_data = payload.get("installation", {})
    
    pr_number = pr_data.get("number")
    head_sha = pr_data.get("head", {}).get("sha")
    base_branch = pr_data.get("base", {}).get("ref")
    head_branch = pr_data.get("head", {}).get("ref")
    repo_full_name = repo_data.get("full_name")
    repo_id = repo_data.get("id")
    installation_id_github = installation_data.get("id")
    
    if not all([pr_number, head_sha, repo_full_name, installation_id_github]):
        raise HTTPException(status_code=400, detail="Missing required PR data")
    
    # Get or create Installation record
    installation = db.query(Installation).filter(
        Installation.installation_id == installation_id_github
    ).first()
    
    if not installation:
        # Create new installation record
        installation = Installation(
            installation_id=installation_id_github,
            github_user=repo_data.get("owner", {}).get("login", "unknown"),
            github_org=repo_data.get("owner", {}).get("type") == "Organization" and repo_data.get("owner", {}).get("login") or None,
            is_active=True
        )
        db.add(installation)
        db.commit()
        logger.info(f"Created new installation {installation_id_github}")
    
    # Map action to event type
    event_type_map = {
        "opened": WebhookEventType.PULL_REQUEST_OPENED,
        "synchronize": WebhookEventType.PULL_REQUEST_SYNCHRONIZE,
        "reopened": WebhookEventType.PULL_REQUEST_REOPENED
    }
    event_type = event_type_map[action]
    
    # Create webhook event record
    webhook_event = GitHubWebhookEvent(
        delivery_id=delivery_id,
        event_type=event_type,
        signature_verified=signature_valid,
        installation_id=installation.id,
        repository_full_name=repo_full_name,
        repository_id=repo_id,
        pr_number=pr_number,
        pr_head_sha=head_sha,
        pr_base_branch=base_branch,
        pr_head_branch=head_branch,
        raw_payload=payload
    )
    db.add(webhook_event)
    db.commit()
    
    logger.info(f"Recorded webhook event: {event_type} for PR {repo_full_name}#{pr_number}")
    
    # Check if we should auto-analyze (integration config)
    # For Phase 17, default to auto-analyze for all PRs
    should_analyze = True
    
    if should_analyze:
        # Create PR analysis record
        pr_analysis = PRAnalysis(
            repository_full_name=repo_full_name,
            pr_number=pr_number,
            head_sha=head_sha,
            base_branch=base_branch,
            status=PRAnalysisStatus.PENDING,
            webhook_event_id=webhook_event.id
        )
        db.add(pr_analysis)
        db.commit()
        
        logger.info(f"Created PR analysis {pr_analysis.id} for PR {repo_full_name}#{pr_number}")
        
        # Queue analysis in background
        background_tasks.add_task(
            _run_pr_analysis,
            pr_analysis_id=pr_analysis.id
        )
        
        return {
            "status": "queued",
            "pr_analysis_id": pr_analysis.id,
            "repository": repo_full_name,
            "pr_number": pr_number,
            "head_sha": head_sha[:7]
        }
    
    else:
        return {
            "status": "skipped",
            "reason": "auto_analysis_disabled"
        }


async def _handle_push_event(
    delivery_id: str,
    signature_valid: bool,
    payload: Dict[str, Any],
    db: Session,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Handle push webhook event.
    
    Phase 17.1: Basic support (record event, don't analyze)
    Future: Could trigger branch/commit analysis
    """
    repo_data = payload.get("repository", {})
    installation_data = payload.get("installation", {})
    
    ref = payload.get("ref")  # refs/heads/main
    before_sha = payload.get("before")
    after_sha = payload.get("after")
    repo_full_name = repo_data.get("full_name")
    repo_id = repo_data.get("id")
    installation_id_github = installation_data.get("id")
    
    # Get installation
    installation = db.query(Installation).filter(
        Installation.installation_id == installation_id_github
    ).first()
    
    if not installation:
        raise HTTPException(status_code=400, detail="Installation not found")
    
    # Create webhook event record
    webhook_event = GitHubWebhookEvent(
        delivery_id=delivery_id,
        event_type=WebhookEventType.PUSH,
        signature_verified=signature_valid,
        installation_id=installation.id,
        repository_full_name=repo_full_name,
        repository_id=repo_id,
        push_ref=ref,
        push_before_sha=before_sha,
        push_after_sha=after_sha,
        raw_payload=payload
    )
    db.add(webhook_event)
    db.commit()
    
    logger.info(f"Recorded push event for {repo_full_name}: {ref}")
    
    # Phase 17.1: Don't auto-analyze pushes yet
    return {
        "status": "recorded",
        "event_type": "push",
        "repository": repo_full_name,
        "ref": ref
    }


async def _run_pr_analysis(pr_analysis_id: int):
    """Background task to run PR analysis pipeline.
    
    Creates its own database session to avoid lifecycle issues with
    the request session being closed before background task executes.
    
    Args:
        pr_analysis_id: PRAnalysis record ID
    """
    logger.info(f"Starting background analysis for PR analysis {pr_analysis_id}")
    
    # Create new database session for background task
    db = SessionLocal()
    try:
        pipeline = PRAnalysisPipeline(db_session=db)
        success = await pipeline.analyze_pr(
            pr_analysis_id=pr_analysis_id,
            user_plan="team"  # Default to team plan for GitHub integrations
        )
        
        if success:
            logger.info(f"PR analysis {pr_analysis_id} completed successfully")
        else:
            logger.error(f"PR analysis {pr_analysis_id} failed")
            
    except Exception as e:
        db.rollback()
        logger.error(f"Error in background PR analysis {pr_analysis_id}: {e}")
        raise
    finally:
        db.close()


@router.get("/webhook-events")
async def list_webhook_events(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List recent webhook events (for debugging/monitoring)."""
    events = db.query(GitHubWebhookEvent).order_by(
        GitHubWebhookEvent.created_at.desc()
    ).limit(limit).all()
    
    return {
        "events": [
            {
                "id": event.id,
                "delivery_id": event.delivery_id,
                "event_type": event.event_type.value,
                "repository": event.repository_full_name,
                "pr_number": event.pr_number,
                "processed_at": event.processed_at.isoformat() if event.processed_at else None,
                "created_at": event.created_at.isoformat()
            }
            for event in events
        ]
    }


@router.get("/pr-analyses/{pr_analysis_id}")
async def get_pr_analysis(
    pr_analysis_id: int,
    db: Session = Depends(get_db)
):
    """Get PR analysis details."""
    pr_analysis = db.query(PRAnalysis).filter(
        PRAnalysis.id == pr_analysis_id
    ).first()
    
    if not pr_analysis:
        raise HTTPException(status_code=404, detail="PR analysis not found")
    
    return {
        "id": pr_analysis.id,
        "repository": pr_analysis.repository_full_name,
        "pr_number": pr_analysis.pr_number,
        "head_sha": pr_analysis.head_sha,
        "status": pr_analysis.status.value,
        "reliability_score": pr_analysis.reliability_score.value if pr_analysis.reliability_score else None,
        "critical_risks_count": pr_analysis.critical_risks_count,
        "high_risks_count": pr_analysis.high_risks_count,
        "medium_risks_count": pr_analysis.medium_risks_count,
        "fix_candidates_count": pr_analysis.fix_candidates_count,
        "comment_posted": pr_analysis.comment_posted,
        "status_check_posted": pr_analysis.status_check_posted,
        "status_check_conclusion": pr_analysis.status_check_conclusion,
        "started_at": pr_analysis.started_at.isoformat() if pr_analysis.started_at else None,
        "completed_at": pr_analysis.completed_at.isoformat() if pr_analysis.completed_at else None,
        "analysis_error": pr_analysis.analysis_error,
        "ledger_run_id": pr_analysis.ledger_run_id
    }
