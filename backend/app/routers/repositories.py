"""Repository import and management endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import requests
import re
from concurrent.futures import ThreadPoolExecutor

from app.db import SessionLocal
from app.models.analysis_run import AnalysisRun, RunStatus
from app.models.analysis_result import AnalysisResult, IssueCategory
from app.tasks.analysis_tasks import clone_repository, run_agi_engineer_analysis
from datetime import datetime

from app.db import get_db
from app.models.repository import Repository
from app.models.installation import Installation
from app.models.analysis_run import AnalysisRun, RunStatus
from app.security import verify_token
from app.tasks import run_code_analysis

router = APIRouter(prefix="/api/repositories", tags=["repositories"])

# Lightweight executor to fall back to in-process analysis when Celery isn't running
_fallback_executor = ThreadPoolExecutor(max_workers=1)


class ImportRepoRequest(BaseModel):
    full_name: str  # owner/repo
    branch: str = "main"


def _normalize_full_name(raw: str) -> str:
    """Normalize user input to owner/repo."""
    cleaned = raw.strip()
    cleaned = cleaned.replace("git@github.com:", "https://github.com/")
    if cleaned.startswith("http://") or cleaned.startswith("https://"):
        cleaned = re.sub(r"^https?://github.com/", "", cleaned)
    if cleaned.endswith(".git"):
        cleaned = cleaned[:-4]
    return cleaned


def _run_analysis_sync(run_id: int):
    """Minimal synchronous runner to ensure analysis executes if Celery is down."""
    db = SessionLocal()
    try:
        run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
        if not run:
            return
        repo = run.repository
        if not repo or not repo.installation:
            run.status = RunStatus.FAILED
            run.error_message = "Repository or installation missing"
            db.commit()
            return

        # Mark in progress
        run.status = RunStatus.IN_PROGRESS
        run.started_at = datetime.utcnow()
        db.commit()

        # Clone and analyze
        repo_path = clone_repository(
            repo.github_repo_id and repo.repo_full_name or repo.repo_full_name,
            run.github_branch,
            repo.installation.access_token,
        )

        results = run_agi_engineer_analysis(
            repo_path=repo_path,
            branch=run.github_branch,
            commit_sha=run.github_commit_sha,
        )

        total_issues = 0
        for result_data in results:
            category_value = result_data.get("category") or IssueCategory.SUGGESTION
            if isinstance(category_value, str):
                category_value = IssueCategory(category_value)

            issue = AnalysisResult(
                run_id=run.id,
                file_path=result_data.get("file_path", ""),
                line_number=result_data.get("line_number", 0),
                issue_code=result_data.get("issue_code", ""),
                issue_name=result_data.get("issue_name", result_data.get("issue_code", "")),
                category=category_value,
                severity=result_data.get("severity", "warning"),
                message=result_data.get("message", ""),
                suggestion=result_data.get("suggestion"),
                before_code=result_data.get("before_code"),
                after_code=result_data.get("after_code"),
                is_fixed=result_data.get("is_fixed", 0),
            )
            db.add(issue)
            total_issues += 1

        run.status = RunStatus.COMPLETED
        run.completed_at = datetime.utcnow()
        run.total_results = total_issues
        db.commit()
    except Exception as e:
        run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
        if run:
            run.status = RunStatus.FAILED
            run.error_message = str(e)
            run.completed_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


@router.post("/import")
async def import_repository(
    data: ImportRepoRequest,
    claims: dict = Depends(verify_token),
    db: Session = Depends(get_db),
) -> dict:
    """Import a GitHub repository and create an initial analysis run.
    
    Args:
        data: Repository full name and branch
        claims: JWT claims (must include installation_id)
        db: Database session
        
    Returns:
        Created repository and queued run info
    """
    full_name = _normalize_full_name(data.full_name)
    if "/" not in full_name:
        raise HTTPException(status_code=400, detail="full_name must be in 'owner/repo' format")

    # Resolve installation
    installation_id = claims.get("installation_id")
    if not installation_id:
        raise HTTPException(status_code=401, detail="Missing installation_id in token")

    installation = db.query(Installation).filter(Installation.id == installation_id).first()
    if not installation:
        raise HTTPException(status_code=404, detail="Installation not found")

    # Check if repository already exists
    existing = db.query(Repository).filter(Repository.repo_full_name == full_name).first()
    if existing:
        repo = existing
    else:
        # Try to fetch repo info from GitHub to get numeric id
        github_repo_id = None
        try:
            headers = {"Authorization": f"Bearer {installation.access_token}", "Accept": "application/vnd.github+json"}
            resp = requests.get(f"https://api.github.com/repos/{full_name}", headers=headers, timeout=10)
            if resp.status_code == 200:
                github_repo_id = resp.json().get("id")
        except Exception:
            github_repo_id = None

        # Fallback pseudo id if GitHub call fails (demo mode)
        if github_repo_id is None:
            github_repo_id = abs(hash(full_name)) % (2**31)

        repo_name = full_name.split("/")[-1]
        repo = Repository(
            installation_id=installation.id,
            repo_name=repo_name,
            repo_full_name=full_name,
            github_repo_id=github_repo_id,
            is_enabled=True,
        )
        db.add(repo)
        db.commit()
        db.refresh(repo)

    # Create an analysis run
    run = AnalysisRun(
        repository_id=repo.id,
        github_event="import",
        github_branch=data.branch,
        github_commit_sha="0" * 40,
        status=RunStatus.PENDING,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    # Run analysis immediately via in-process thread (avoids pending if Celery is unavailable)
    _fallback_executor.submit(_run_analysis_sync, run.id)

    return {
        "status": "in_progress",
        "repository": {
            "id": repo.id,
            "full_name": repo.repo_full_name,
            "is_enabled": repo.is_enabled,
        },
        "run": {
            "id": run.id,
            "branch": run.github_branch,
            "status": run.status.value,
        },
        "message": "Analysis started",
    }
