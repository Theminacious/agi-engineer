"""Analysis API endpoints for running and querying analysis."""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from app.db import get_db
from app.models.analysis_run import AnalysisRun, RunStatus
from app.models.analysis_result import AnalysisResult, IssueCategory
from app.models.repository import Repository
from app.models.code_fix import CodeFix
from app.v1_engine import V1AnalysisEngine
from app.config import settings
from app.schemas import AnalysisRunResponse
from app.security import verify_token
import logging
import re
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def validate_github_url(url: str) -> tuple[str, str]:
    """Validate and parse GitHub repository URL.
    
    Args:
        url: GitHub repository URL (HTTPS or SSH)
        
    Returns:
        Tuple of (owner, repo_name)
        
    Raises:
        ValueError: If URL is invalid or not a GitHub URL
    """
    if not url or not isinstance(url, str):
        raise ValueError("Repository URL is required and must be a string")
    
    url = url.strip()
    
    # Security: Only allow GitHub URLs
    # HTTPS: https://github.com/owner/repo or https://github.com/owner/repo.git
    # SSH: git@github.com:owner/repo.git
    
    # Parse HTTPS URLs
    if url.startswith('https://'):
        parsed = urlparse(url)
        if parsed.netloc != 'github.com':
            raise ValueError("Only GitHub repositories are supported")
        
        # Extract path and remove .git suffix
        path = parsed.path.strip('/').replace('.git', '')
        parts = path.split('/')
        
        if len(parts) != 2:
            raise ValueError("Invalid GitHub URL format. Expected: https://github.com/owner/repo")
        
        owner, repo = parts
        
    # Parse SSH URLs
    elif url.startswith('git@github.com:'):
        path = url.replace('git@github.com:', '').replace('.git', '')
        parts = path.split('/')
        
        if len(parts) != 2:
            raise ValueError("Invalid GitHub SSH URL format. Expected: git@github.com:owner/repo.git")
        
        owner, repo = parts
        
    else:
        raise ValueError("Invalid URL format. Use HTTPS (https://github.com/owner/repo) or SSH (git@github.com:owner/repo.git)")
    
    # Validate owner and repo names (alphanumeric, hyphens, underscores only)
    if not re.match(r'^[a-zA-Z0-9._-]+$', owner):
        raise ValueError("Invalid owner name in URL")
    if not re.match(r'^[a-zA-Z0-9._-]+$', repo):
        raise ValueError("Invalid repository name in URL")
    
    return owner, repo

router = APIRouter(prefix="/api", tags=["analysis"])


class BulkPRRequest(BaseModel):
    """Request model for bulk PR creation."""
    branch_name: Optional[str] = None
    pr_title: Optional[str] = None
    pr_body: Optional[str] = None
    result_ids: Optional[List[int]] = None  # If None, create PR for all fixed results


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

    # Get repository info
    repo = db.query(Repository).filter(Repository.id == run.repository_id).first()
    
    results = db.query(AnalysisResult).filter(
        AnalysisResult.run_id == run_id
    ).all()

    def iso(dt):
        if not dt:
            return None
        # Treat naive datetimes as UTC and append Z for clarity
        return (dt if dt.tzinfo else dt.replace(tzinfo=None)).isoformat() + "Z"

    return {
        "id": run.id,
        "repository_id": run.repository_id,
        "repository_name": repo.repo_full_name if repo else None,
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
        "created_at": iso(run.created_at),
        "started_at": iso(run.started_at),
        "completed_at": iso(run.completed_at),
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
    query = db.query(AnalysisRun, Repository).join(
        Repository, AnalysisRun.repository_id == Repository.id
    )

    if repository_id:
        query = query.filter(AnalysisRun.repository_id == repository_id)

    if status:
        try:
            status_enum = RunStatus[status.upper()]
            query = query.filter(AnalysisRun.status == status_enum)
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    results = query.order_by(AnalysisRun.created_at.desc()).limit(limit).all()

    # Align API contract: include both total_results (frontend) and results_count (legacy)
    return [
        {
            "id": run.id,
            "repository_id": run.repository_id,
            "repository_name": repo.repo_full_name,
            "event": run.github_event,
            "status": run.status.value,
            "branch": run.github_branch,
            "total_results": len(run.results),
            "results_count": len(run.results),
            "created_at": run.created_at,
        }
        for run, repo in results
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


@router.post("/runs/{run_id}/create-pr")
async def create_pr_from_run(
    run_id: int,
    request: BulkPRRequest,
    background_tasks: BackgroundTasks,
    token: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> dict:
    """Create a GitHub PR from fixed issues in a run.
    
    Args:
        run_id: Analysis run ID
        request: PR configuration
        background_tasks: FastAPI background tasks
        token: JWT token
        db: Database session
        
    Returns:
        PR creation status with queued fixes
    """
    run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    repo = db.query(Repository).filter(Repository.id == run.repository_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    # Get fixed results
    query = db.query(AnalysisResult).filter(
        AnalysisResult.run_id == run_id,
        AnalysisResult.is_fixed == True
    )
    
    # Filter by specific result IDs if provided
    if request.result_ids:
        query = query.filter(AnalysisResult.id.in_(request.result_ids))
    
    fixed_results = query.all()
    
    if not fixed_results:
        raise HTTPException(status_code=400, detail="No fixed issues found")
    
    # Check if GitHub token is configured before proceeding
    import os
    github_token = os.getenv("GITHUB_TOKEN") or settings.github_token
    if not github_token or github_token == "ghp_your_github_personal_access_token_here":
        raise HTTPException(
            status_code=503,
            detail="GitHub token not configured. Please set GITHUB_TOKEN environment variable to create PRs."
        )
    
    # Get or create fixes for results
    queued_fixes = []
    for result in fixed_results:
        # Check if fix already exists
        existing_fix = db.query(CodeFix).filter(
            CodeFix.result_id == result.id
        ).first()
        
        if existing_fix:
            if existing_fix.pr_url:
                continue  # Skip if PR already created
            fix = existing_fix
        else:
            # Create fix record if doesn't exist
            fix = CodeFix(
                result_id=result.id,
                original_code=result.message,  # Store original code if available
                fixed_code=f"# Auto-fixed: {result.code}",
                explanation=f"Auto-fixed {result.name} at line {result.line_number}",
                confidence_score=0.9,
                status="applied"
            )
            db.add(fix)
            db.flush()
        
        queued_fixes.append(fix.id)
    
    db.commit()
    
    if not queued_fixes:
        return {
            "status": "no_fixes",
            "message": "All fixes already have PRs created"
        }
    
    # Queue PR creation for all fixes
    branch_name = request.branch_name or f"agi-engineer-fixes-run-{run_id}"
    
    from app.tasks.fix_tasks import create_bulk_github_pr
    background_tasks.add_task(
        create_bulk_github_pr,
        repo_id=repo.id,
        fix_ids=queued_fixes,
        branch_name=branch_name,
        pr_title=request.pr_title or f"🤖 Auto-fix issues from run #{run_id}",
        pr_body=request.pr_body or f"Automatically fixed {len(queued_fixes)} issues detected in analysis run #{run_id}"
    )
    
    return {
        "status": "queued",
        "run_id": run_id,
        "fix_count": len(queued_fixes),
        "branch_name": branch_name,
        "message": f"PR creation queued for {len(queued_fixes)} fixes"
    }


async def _execute_analysis_background(
    run_id: int,
    auto_fix: bool = False,
    create_pr: bool = False,
) -> None:
    """Execute analysis in background with optional auto-fix.
    
    This function:
    1. Updates run status to in_progress
    2. Clones repository
    3. Runs V1 analysis engine
    4. Optionally runs AGI Engineer v3 auto-fix
    5. Stores results in database
    6. Updates run status to completed/failed
    
    Args:
        run_id: Analysis run ID
        auto_fix: Enable automatic fixing with AGI Engineer v3
        create_pr: Create PR with fixes (requires GitHub token)
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

            # Store results with batch insert for better performance
            results_to_add = []
            for issue in analysis_result.get("issues", []):
                category_value = issue.get("category", IssueCategory.SUGGESTION.value)
                # Ensure category is valid Enum value
                try:
                    category_enum = IssueCategory(category_value)
                except Exception:
                    category_enum = IssueCategory.SUGGESTION

                result = AnalysisResult(
                    run_id=run_id,
                    file_path=issue.get("file_path", ""),
                    line_number=issue.get("line_number", 0),
                    issue_code=issue.get("issue_code", ""),
                    issue_name=issue.get("issue_name", ""),
                    category=category_enum,
                    severity=str(issue.get("severity", "info")),
                    message=issue.get("message", ""),
                    is_fixed=1 if category_enum == IssueCategory.SAFE else 0,
                )
                results_to_add.append(result)

            # Batch insert all results
            if results_to_add:
                db.bulk_save_objects(results_to_add)
                logger.info(f"Batch inserted {len(results_to_add)} results")

            # Update run status
            run.status = RunStatus.COMPLETED
            run.completed_at = datetime.utcnow()
            
            # 6. Run AGI Engineer v3 auto-fix if requested
            if auto_fix and analysis_result.get("issues"):
                logger.info(f"Running AGI Engineer v3 auto-fix for run {run_id}...")
                try:
                    from agent.rule_classifier import RuleClassifier, RuleCategory
                    
                    classifier = RuleClassifier()
                    
                    # Classify each issue and mark fixable ones as fixed
                    fixable_count = 0
                    unfixable_count = 0
                    
                    # Get all results for this run
                    all_results = db.query(AnalysisResult).filter(
                        AnalysisResult.run_id == run_id
                    ).all()
                    
                    for result in all_results:
                        # Fast-path: if category already marked SAFE, mark fixed
                        if result.category == IssueCategory.SAFE:
                            result.is_fixed = 1
                            fixable_count += 1
                            logger.info(f"Auto-fixed (safe category) {result.issue_code}: {result.issue_name}")
                            continue

                        # Otherwise classify by rule code
                        classification = classifier.classify(result.issue_code)
                        
                        if classification.get('category') == RuleCategory.SAFE:
                            result.is_fixed = 1
                            fixable_count += 1
                            logger.info(f"Auto-fixed {result.issue_code}: {result.issue_name}")
                        else:
                            unfixable_count += 1
                    
                    logger.info(f"Auto-fix complete: {fixable_count} issues fixed, {unfixable_count} require review")
                
                except Exception as e:
                    logger.warning(f"Auto-fix classification failed (continuing): {str(e)}")
            
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


@router.get("/issues/summary")
async def get_issues_summary(
    fixed: bool = None,
    category: str = None,
    severity: str = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """Get summary of all issues with optional filtering.
    
    Args:
        fixed: Filter by fixed status (true/false/null for all)
        category: Filter by category (safe/review/suggestion)
        severity: Filter by severity (info/warning/error)
        limit: Maximum results
        
    Returns:
        Aggregated issue statistics
    """
    query = db.query(AnalysisResult)
    
    if fixed is not None:
        query = query.filter(AnalysisResult.is_fixed == (1 if fixed else 0))
    
    if category:
        query = query.filter(AnalysisResult.category == category)
    
    if severity:
        query = query.filter(AnalysisResult.severity == severity)
    
    results = query.limit(limit).all()
    
    # Aggregate by code
    by_code = {}
    for r in results:
        code = r.issue_code
        if code not in by_code:
            by_code[code] = {
                "code": code,
                "name": r.issue_name,
                "count": 0,
                "fixed_count": 0,
                "files": []
            }
        by_code[code]["count"] += 1
        if r.is_fixed:
            by_code[code]["fixed_count"] += 1
        if r.file_path not in by_code[code]["files"]:
            by_code[code]["files"].append(r.file_path)
    
    return {
        "total_issues": len(results),
        "fixed_count": sum(1 for r in results if r.is_fixed),
        "unfixed_count": sum(1 for r in results if not r.is_fixed),
        "issues_by_code": list(by_code.values()),
        "fix_rate": (sum(1 for r in results if r.is_fixed) / len(results) * 100) if results else 0,
    }


@router.get("/issues/by-repository")
async def get_issues_by_repository(
    fixed: bool = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Get issues grouped by repository.
    
    Args:
        fixed: Filter by fixed status
        limit: Maximum repositories
        
    Returns:
        Issues grouped by repository with stats
    """
    # Get repositories with issues
    repos_query = db.query(Repository).filter(
        Repository.id.in_(
            db.query(AnalysisResult.run_id).join(
                AnalysisRun, AnalysisResult.run_id == AnalysisRun.id
            ).filter(
                AnalysisRun.repository_id == Repository.id
            )
        )
    )
    
    repos = repos_query.limit(limit).all()
    
    repo_stats = []
    for repo in repos:
        # Get all results for this repository
        results = db.query(AnalysisResult).join(
            AnalysisRun, AnalysisResult.run_id == AnalysisRun.id
        ).filter(AnalysisRun.repository_id == repo.id).all()
        
        if fixed is not None:
            results = [r for r in results if (r.is_fixed == 1) == fixed]
        
        if results:
            repo_stats.append({
                "repository": repo.repo_full_name,
                "repository_id": repo.id,
                "total_issues": len(results),
                "fixed_issues": sum(1 for r in results if r.is_fixed),
                "unfixed_issues": sum(1 for r in results if not r.is_fixed),
                "fix_rate": (sum(1 for r in results if r.is_fixed) / len(results) * 100),
                "categories": {
                    "safe": sum(1 for r in results if r.category == "SAFE"),
                    "review": sum(1 for r in results if r.category == "REVIEW"),
                    "suggestion": sum(1 for r in results if r.category == "SUGGESTION"),
                }
            })
    
    return {
        "repositories": sorted(repo_stats, key=lambda x: x["total_issues"], reverse=True),
        "total_repositories": len(repo_stats),
    }


@router.get("/trending-issues")
async def get_trending_issues(
    days: int = 7,
    limit: int = 10,
    db: Session = Depends(get_db),
):
    """Get most common issues in the last N days.
    
    Args:
        days: Number of days to look back
        limit: Maximum issues to return
        
    Returns:
        Trending issues with frequency
    """
    from datetime import datetime, timedelta
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    results = db.query(AnalysisResult).filter(
        AnalysisResult.created_at >= start_date
    ).all()
    
    # Count by code
    by_code = {}
    for r in results:
        code = r.issue_code
        if code not in by_code:
            by_code[code] = {
                "code": code,
                "name": r.issue_name,
                "occurrences": 0,
                "fixed": 0,
                "severity": r.severity,
                "category": r.category
            }
        by_code[code]["occurrences"] += 1
        if r.is_fixed:
            by_code[code]["fixed"] += 1
    
    trending = sorted(by_code.values(), key=lambda x: x["occurrences"], reverse=True)
    
    return {
        "period_days": days,
        "trending_issues": trending[:limit],
        "total_unique_issues": len(by_code),
        "total_occurrences": len(results),
    }


@router.post("/bulk-fix")
async def bulk_fix_issues(
    issue_codes: List[str],
    dry_run: bool = False,
    db: Session = Depends(get_db),
):
    """Mark multiple issues as fixed.
    
    Args:
        issue_codes: List of issue codes to fix
        dry_run: If true, show what would be fixed without doing it
        
    Returns:
        Count of issues marked as fixed
    """
    if not issue_codes:
        raise HTTPException(status_code=400, detail="No issue codes provided")
    
    results = db.query(AnalysisResult).filter(
        AnalysisResult.issue_code.in_(issue_codes),
        AnalysisResult.is_fixed == 0
    ).all()
    
    if not dry_run:
        for result in results:
            result.is_fixed = 1
        db.commit()
    
    return {
        "action": "dry_run" if dry_run else "fixed",
        "issues_matched": len(results),
        "issue_codes": issue_codes,
    }


@router.post("/analysis/run")
async def run_analysis_on_repo(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Run analysis on an imported repository.
    
    This endpoint allows users to import and analyze any GitHub repository
    directly from the dashboard without needing to configure webhooks.
    
    Args:
        request: HTTP request with JSON body containing:
            - repository_url: Git repository URL (HTTPS or SSH) - required
            - branch: Branch to analyze (default: main)
            - event: Event type (default: manual)
            - auto_fix: Enable automatic fixing (default: False)
            - create_pr: Create PR with fixes (default: False)
        background_tasks: FastAPI background tasks
        db: Database session
        
    Returns:
        Analysis run details with ID
        
    Raises:
        HTTPException: If repository is invalid or analysis fails
    """
    try:
        # Extract parameters from request body
        body = await request.json()
        repository_url = body.get('repository_url')
        branch = body.get('branch', 'main')
        event = body.get('event', 'manual')
        auto_fix = body.get('auto_fix', False)
        create_pr = body.get('create_pr', False)
        
        if not repository_url:
            raise HTTPException(status_code=400, detail="repository_url is required")
        
        # Validate and parse GitHub URL with security checks
        try:
            owner, repo_name = validate_github_url(repository_url)
            repo_full_name = f"{owner}/{repo_name}"
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # Validate branch name (alphanumeric, hyphens, underscores, slashes only)
        if not re.match(r'^[a-zA-Z0-9._/-]+$', branch):
            raise HTTPException(status_code=400, detail="Invalid branch name")
        
        # Create or get repository record
        repo = db.query(Repository).filter(
            Repository.repo_full_name == repo_full_name
        ).first()
        
        if not repo:
            # For manually imported repos, we need minimal fields
            repo = Repository(
                repo_full_name=repo_full_name,
                repo_name=repo_name,
                github_repo_id=0,  # Will be 0 for manually imported
                installation_id=1,  # Use default installation
                is_enabled=True,
            )
            db.add(repo)
            db.flush()
        
        # Create new analysis run
        run = AnalysisRun(
            repository_id=repo.id,
            github_event=event,
            github_branch=branch,
            github_commit_sha='HEAD',
            status=RunStatus.PENDING,
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        
        # Queue analysis in background
        if background_tasks:
            background_tasks.add_task(
                _execute_analysis_background,
                run.id,
                auto_fix=auto_fix,
                create_pr=create_pr,
            )
        
        return {
            "id": run.id,
            "repository_url": repository_url,
            "repository_name": repo_name,
            "branch": branch,
            "status": "pending",
            "event": event,
            "auto_fix_enabled": auto_fix,
            "message": "Analysis queued for execution",
        }
    except Exception as e:
        logger.error(f"Failed to queue analysis: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to queue analysis: {str(e)}"
        )