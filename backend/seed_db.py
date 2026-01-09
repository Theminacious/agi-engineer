"""Seed the database with demo data for testing."""

import sys
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db import SessionLocal, engine
from app.models.installation import Installation
from app.models.repository import Repository
from app.models.analysis_run import AnalysisRun, RunStatus
from app.models.analysis_result import AnalysisResult, IssueCategory

def seed_database():
    """Create demo data for testing."""
    db = SessionLocal()
    
    try:
        print("🌱 Seeding database with demo data...")
        
        # Create demo installation
        installation = db.query(Installation).filter(
            Installation.github_user == "demo_user"
        ).first()
        
        if not installation:
            installation = Installation(
                installation_id=999999,
                github_user="demo_user",
                github_org="demo_org",
                access_token="demo_token",
                is_active=True
            )
            db.add(installation)
            db.commit()
            db.refresh(installation)
            print(f"✓ Created demo installation (ID: {installation.id})")
        
        # Create demo repositories
        repos_data = [
            {"name": "api-backend", "full_name": "demo_user/api-backend", "github_id": 100001},
            {"name": "web-frontend", "full_name": "demo_user/web-frontend", "github_id": 100002},
            {"name": "mobile-app", "full_name": "demo_user/mobile-app", "github_id": 100003},
        ]
        
        repos = []
        for repo_data in repos_data:
            repo = db.query(Repository).filter(
                Repository.repo_full_name == repo_data["full_name"]
            ).first()
            
            if not repo:
                repo = Repository(
                    installation_id=installation.id,
                    repo_name=repo_data["name"],
                    repo_full_name=repo_data["full_name"],
                    github_repo_id=repo_data["github_id"],
                    is_enabled=True
                )
                db.add(repo)
                db.commit()
                db.refresh(repo)
                print(f"✓ Created repository: {repo.repo_full_name}")
            repos.append(repo)
        
        # Create demo analysis runs
        now = datetime.utcnow()
        runs_data = [
            {
                "repo": repos[0],
                "event": "push",
                "branch": "main",
                "commit": "a1b2c3d",
                "status": RunStatus.COMPLETED,
                "created": now - timedelta(hours=2),
                "started": now - timedelta(hours=2, minutes=1),
                "completed": now - timedelta(hours=2, minutes=5),
                "issues": 8
            },
            {
                "repo": repos[0],
                "event": "pull_request",
                "branch": "feature/auth-fixes",
                "commit": "e4f5g6h",
                "status": RunStatus.COMPLETED,
                "created": now - timedelta(hours=5),
                "started": now - timedelta(hours=5, minutes=1),
                "completed": now - timedelta(hours=5, minutes=3),
                "issues": 3
            },
            {
                "repo": repos[1],
                "event": "push",
                "branch": "develop",
                "commit": "i7j8k9l",
                "status": RunStatus.COMPLETED,
                "created": now - timedelta(hours=8),
                "started": now - timedelta(hours=8, minutes=1),
                "completed": now - timedelta(hours=8, minutes=4),
                "issues": 12
            },
            {
                "repo": repos[1],
                "event": "pull_request",
                "branch": "feature/ui-redesign",
                "commit": "m0n1o2p",
                "status": RunStatus.IN_PROGRESS,
                "created": now - timedelta(minutes=15),
                "started": now - timedelta(minutes=14),
                "completed": None,
                "issues": 0
            },
            {
                "repo": repos[2],
                "event": "push",
                "branch": "main",
                "commit": "q3r4s5t",
                "status": RunStatus.COMPLETED,
                "created": now - timedelta(days=1),
                "started": now - timedelta(days=1, seconds=30),
                "completed": now - timedelta(days=1, seconds=-120),
                "issues": 5
            },
            {
                "repo": repos[0],
                "event": "push",
                "branch": "hotfix/security-patch",
                "commit": "u6v7w8x",
                "status": RunStatus.FAILED,
                "created": now - timedelta(hours=12),
                "started": now - timedelta(hours=12, minutes=1),
                "completed": now - timedelta(hours=12, minutes=2),
                "error": "Repository clone failed: timeout",
                "issues": 0
            },
            {
                "repo": repos[2],
                "event": "pull_request",
                "branch": "feature/offline-mode",
                "commit": "y9z0a1b",
                "status": RunStatus.PENDING,
                "created": now - timedelta(minutes=5),
                "started": None,
                "completed": None,
                "issues": 0
            },
        ]
        
        for run_data in runs_data:
            run = AnalysisRun(
                repository_id=run_data["repo"].id,
                github_event=run_data["event"],
                github_branch=run_data["branch"],
                github_commit_sha=run_data["commit"],
                pull_request_number=None,
                status=run_data["status"],
                error_message=run_data.get("error"),
                created_at=run_data["created"],
                started_at=run_data["started"],
                completed_at=run_data["completed"]
            )
            db.add(run)
            db.commit()
            db.refresh(run)
            
            # Add demo issues for completed runs
            if run_data["status"] == RunStatus.COMPLETED and run_data["issues"] > 0:
                issues_templates = [
                    {
                        "file": "src/auth/login.py",
                        "line": 45,
                        "code": "SEC101",
                        "name": "Hardcoded credentials",
                        "category": IssueCategory.REVIEW,
                        "severity": "high",
                        "message": "Potential hardcoded password found in authentication module"
                    },
                    {
                        "file": "src/api/routes.py",
                        "line": 128,
                        "code": "PERF201",
                        "name": "N+1 query pattern",
                        "category": IssueCategory.SUGGESTION,
                        "severity": "medium",
                        "message": "Database query inside loop detected, consider using bulk fetch"
                    },
                    {
                        "file": "src/utils/helpers.py",
                        "line": 67,
                        "code": "CODE301",
                        "name": "Unused variable",
                        "category": IssueCategory.SAFE,
                        "severity": "low",
                        "message": "Variable 'temp_result' is assigned but never used"
                    },
                    {
                        "file": "src/models/user.py",
                        "line": 23,
                        "code": "TYPE401",
                        "name": "Missing type annotation",
                        "category": IssueCategory.SUGGESTION,
                        "severity": "low",
                        "message": "Function parameter lacks type hint, add for better code clarity"
                    },
                    {
                        "file": "src/config/settings.py",
                        "line": 12,
                        "code": "SEC102",
                        "name": "Debug mode enabled",
                        "category": IssueCategory.REVIEW,
                        "severity": "high",
                        "message": "DEBUG=True should not be used in production"
                    },
                ]
                
                for i in range(min(run_data["issues"], len(issues_templates))):
                    template = issues_templates[i % len(issues_templates)]
                    result = AnalysisResult(
                        run_id=run.id,
                        file_path=template["file"],
                        line_number=template["line"] + i,
                        issue_code=template["code"],
                        issue_name=template["name"],
                        category=template["category"],
                        severity=template["severity"],
                        message=template["message"],
                        is_fixed=0
                    )
                    db.add(result)
                
                db.commit()
            
            status_icon = "✓" if run_data["status"] == RunStatus.COMPLETED else "⏳" if run_data["status"] == RunStatus.IN_PROGRESS else "⚠" if run_data["status"] == RunStatus.FAILED else "⏸"
            print(f"{status_icon} Created run #{run.id}: {run_data['repo'].repo_name} / {run_data['branch']} ({run_data['status'].value})")
        
        print(f"\n✅ Database seeded successfully!")
        print(f"📊 Created:")
        print(f"   - 1 installation")
        print(f"   - {len(repos)} repositories")
        print(f"   - {len(runs_data)} analysis runs")
        print(f"   - {sum(r['issues'] for r in runs_data)} issues")
        
    except Exception as e:
        print(f"❌ Error seeding database: {str(e)}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
