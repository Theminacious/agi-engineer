"""Celery tasks for code analysis processing."""

from celery import Task
from sqlalchemy.orm import Session
from datetime import datetime
import subprocess
import json
import asyncio
from pathlib import Path
from typing import Optional

from .celery_app import celery_app
from app.db import SessionLocal
from app.models.analysis_run import AnalysisRun, RunStatus
from app.models.analysis_result import AnalysisResult
from app.config import settings


class DatabaseTask(Task):
    """Base task with database session management."""
    
    _db: Optional[Session] = None

    @property
    def db(self) -> Session:
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def after_return(self, *args, **kwargs):
        if self._db is not None:
            self._db.close()
            self._db = None


@celery_app.task(base=DatabaseTask, bind=True, name="app.tasks.run_code_analysis")
def run_code_analysis(self, run_id: int) -> dict:
    """Run code analysis for a specific analysis run.
    
    This task:
    1. Fetches the repository code from GitHub
    2. Runs the AGI Engineer analysis engine
    3. Stores results in the database
    4. Updates run status in real-time
    
    Args:
        run_id: ID of the AnalysisRun to process
        
    Returns:
        Analysis results summary
    """
    db: Session = self.db
    
    try:
        # Get the run
        run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
        if not run:
            return {"error": f"Run {run_id} not found"}
        
        # Update status to in_progress
        run.status = RunStatus.IN_PROGRESS
        run.started_at = datetime.utcnow()
        db.commit()
        
        # Send WebSocket update
        asyncio.create_task(send_status_update(run.id, {
            "type": "status_change",
            "run_id": run.id,
            "status": "in_progress",
            "started_at": run.started_at.isoformat()
        }))
        
        # Get repository details
        repository = run.repository
        if not repository:
            raise Exception("Repository not found")
        
        # Clone or pull repository
        repo_path = clone_repository(
            repository.github_full_name,
            run.github_branch,
            repository.installation.access_token
        )
        
        # Run analysis using AGI Engineer
        results = run_agi_engineer_analysis(
            repo_path=repo_path,
            branch=run.github_branch,
            commit_sha=run.github_commit_sha
        )
        
        # Store results in database
        total_issues = 0
        for result_data in results:
            result = AnalysisResult(
                run_id=run.id,
                rule_id=result_data.get("rule_id"),
                code=result_data.get("code"),
                name=result_data.get("name"),
                category=result_data.get("category"),
                severity=result_data.get("severity"),
                message=result_data.get("message"),
                file_path=result_data.get("file_path"),
                line_number=result_data.get("line_number"),
                code_snippet=result_data.get("code_snippet"),
                suggestion=result_data.get("suggestion"),
            )
            db.add(result)
            total_issues += 1
        
        # Update run status
        run.status = RunStatus.COMPLETED
        run.completed_at = datetime.utcnow()
        run.total_results = total_issues
        db.commit()
        
        # Send WebSocket update
        asyncio.create_task(send_status_update(run.id, {
            "type": "status_change",
            "run_id": run.id,
            "status": "completed",
            "total_results": total_issues,
            "completed_at": run.completed_at.isoformat()
        }))
        
        return {
            "status": "success",
            "run_id": run_id,
            "total_issues": total_issues,
            "duration": (run.completed_at - run.started_at).total_seconds()
        }
        
    except Exception as e:
        # Update run with error
        run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
        if run:
            run.status = RunStatus.FAILED
            run.completed_at = datetime.utcnow()
            run.error_message = str(e)
            db.commit()
            
            # Send WebSocket update
            asyncio.create_task(send_status_update(run.id, {
                "type": "status_change",
                "run_id": run.id,
                "status": "failed",
                "error": str(e),
                "completed_at": run.completed_at.isoformat()
            }))
        
        return {"status": "failed", "run_id": run_id, "error": str(e)}


async def send_status_update(run_id: int, message: dict):
    """Send WebSocket status update (helper for async calls)."""
    try:
        from app.routers.websockets import manager
        await manager.send_run_update(run_id, message)
    except Exception:
        # Silently fail if WebSocket update fails
        pass


def clone_repository(full_name: str, branch: str, token: str) -> Path:
    """Clone or update repository for analysis.
    
    Args:
        full_name: Repository full name (owner/repo)
        branch: Branch to checkout
        token: GitHub access token
        
    Returns:
        Path to cloned repository
    """
    repos_dir = Path("/tmp/agi_engineer_repos")
    repos_dir.mkdir(exist_ok=True)
    
    repo_name = full_name.replace("/", "_")
    repo_path = repos_dir / repo_name
    
    if repo_path.exists():
        # Pull latest changes
        subprocess.run(
            ["git", "fetch", "origin", branch],
            cwd=repo_path,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "checkout", branch],
            cwd=repo_path,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "pull", "origin", branch],
            cwd=repo_path,
            check=True,
            capture_output=True
        )
    else:
        # Clone repository
        clone_url = f"https://x-access-token:{token}@github.com/{full_name}.git"
        subprocess.run(
            ["git", "clone", "-b", branch, clone_url, str(repo_path)],
            check=True,
            capture_output=True
        )
    
    return repo_path


def run_agi_engineer_analysis(repo_path: Path, branch: str, commit_sha: Optional[str]) -> list[dict]:
    """Run AGI Engineer analysis on repository.
    
    Args:
        repo_path: Path to repository
        branch: Branch name
        commit_sha: Commit SHA (optional)
        
    Returns:
        List of analysis results
    """
    # Run the AGI Engineer analysis
    # This would integrate with the existing agi_engineer_v3.py or v2.py
    cmd = [
        "python",
        str(Path(__file__).parent.parent.parent / "agi_engineer_v3.py"),
        "--repo-path", str(repo_path),
        "--branch", branch,
        "--output-format", "json"
    ]
    
    if commit_sha:
        cmd.extend(["--commit", commit_sha])
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=1800  # 30 minutes max
        )
        
        # Parse JSON output
        if result.stdout:
            return json.loads(result.stdout)
        return []
        
    except subprocess.TimeoutExpired:
        raise Exception("Analysis timed out after 30 minutes")
    except subprocess.CalledProcessError as e:
        raise Exception(f"Analysis failed: {e.stderr}")
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse analysis output: {e}")
