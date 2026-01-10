"""Analytics API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List

from app.db import get_db
from app.models.analysis_run import AnalysisRun, RunStatus
from app.models.analysis_result import AnalysisResult
from app.security import verify_token

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/runs/stats")
async def get_run_statistics(
    days: int = Query(30, ge=1, le=365),
    token: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> dict:
    """Get aggregated run statistics over time.
    
    Args:
        days: Number of days to analyze (default 30)
        token: JWT token
        db: Database session
        
    Returns:
        Statistics dict with daily breakdown
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Get runs in date range
    runs = db.query(AnalysisRun).filter(AnalysisRun.created_at >= cutoff_date).all()
    
    # Aggregate by day
    daily_stats = {}
    for run in runs:
        day = run.created_at.date().isoformat()
        if day not in daily_stats:
            daily_stats[day] = {
                "date": day,
                "total": 0,
                "completed": 0,
                "failed": 0,
                "issues": 0
            }
        
        daily_stats[day]["total"] += 1
        if run.status == RunStatus.COMPLETED:
            daily_stats[day]["completed"] += 1
        elif run.status == RunStatus.FAILED:
            daily_stats[day]["failed"] += 1
        daily_stats[day]["issues"] += run.total_results or 0
    
    # Get fix counts from results
    results = db.query(AnalysisResult).filter(
        AnalysisResult.created_at >= cutoff_date
    ).all()
    fixed_count = sum(1 for r in results if r.is_fixed == 1)
    unfixed_count = sum(1 for r in results if r.is_fixed == 0)

    return {
        "period_days": days,
        "daily_breakdown": [daily_stats[day] for day in sorted(daily_stats.keys())],
        "summary": {
            "total_runs": len(runs),
            "completed": len([r for r in runs if r.status == RunStatus.COMPLETED]),
            "failed": len([r for r in runs if r.status == RunStatus.FAILED]),
            "total_issues": sum(r.total_results or 0 for r in runs),
            "fixed_issues": fixed_count,
            "unfixed_issues": unfixed_count,
            "average_issues_per_run": sum(r.total_results or 0 for r in runs) / len(runs) if runs else 0
        }
    }


@router.get("/issues/categories")
async def get_issue_categories(
    days: int = Query(30, ge=1, le=365),
    token: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> dict:
    """Get breakdown of issues by category.
    
    Args:
        days: Number of days to analyze
        token: JWT token
        db: Database session
        
    Returns:
        Category breakdown
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    results = db.query(AnalysisResult).filter(
        AnalysisResult.created_at >= cutoff_date
    ).all()
    
    categories = {}
    for result in results:
        cat = result.category.value if hasattr(result.category, "value") else (result.category or "unknown")
        if cat not in categories:
            categories[cat] = {
                "name": cat,
                "count": 0,
                "severity_breakdown": {}
            }
        
        categories[cat]["count"] += 1
        sev = result.severity or "unknown"
        categories[cat]["severity_breakdown"][sev] = categories[cat]["severity_breakdown"].get(sev, 0) + 1
    
    return {
        "categories": list(categories.values()),
        "total_issues": len(results)
    }


@router.get("/issues/severity")
async def get_issues_by_severity(
    days: int = Query(30, ge=1, le=365),
    token: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> dict:
    """Get breakdown of issues by severity.
    
    Args:
        days: Number of days to analyze
        token: JWT token
        db: Database session
        
    Returns:
        Severity breakdown
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    results = db.query(AnalysisResult).filter(
        AnalysisResult.created_at >= cutoff_date
    ).all()
    
    severity_counts = {}
    for result in results:
        sev = result.severity or "unknown"
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
    
    return {
        "severity_breakdown": severity_counts,
        "total_issues": len(results),
        "high_severity": severity_counts.get("high", 0),
        "medium_severity": severity_counts.get("medium", 0),
        "low_severity": severity_counts.get("low", 0),
    }


@router.get("/repository-health")
async def get_repository_health(
    repository_id: int = Query(...),
    days: int = Query(30, ge=1, le=365),
    token: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> dict:
    """Get health score for a repository.
    
    Args:
        repository_id: ID of repository
        days: Number of days to analyze
        token: JWT token
        db: Database session
        
    Returns:
        Health score and metrics
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Get runs for repository
    runs = db.query(AnalysisRun).filter(
        AnalysisRun.repository_id == repository_id,
        AnalysisRun.created_at >= cutoff_date
    ).all()
    
    if not runs:
        return {
            "repository_id": repository_id,
            "health_score": 100,
            "message": "No analysis data available"
        }
    
    # Calculate metrics
    completed_runs = len([r for r in runs if r.status == RunStatus.COMPLETED])
    total_issues = sum(r.total_results or 0 for r in runs)
    success_rate = (completed_runs / len(runs) * 100) if runs else 0
    
    # Calculate health score (0-100)
    # Higher success rate is better, fewer issues is better
    issue_impact = min(total_issues / max(1, total_issues), 1.0) * 20  # Max 20 points for issues
    success_impact = success_rate  # Up to 80 points
    health_score = int(success_impact + (20 - issue_impact))
    health_score = max(0, min(100, health_score))  # Clamp 0-100
    
    return {
        "repository_id": repository_id,
        "health_score": health_score,
        "metrics": {
            "total_runs": len(runs),
            "completed_runs": completed_runs,
            "success_rate": success_rate,
            "total_issues": total_issues,
            "average_issues_per_run": total_issues / len(runs) if runs else 0,
        },
        "trend": "improving" if success_rate > 70 else "needs_attention"
    }


@router.get("/top-issues")
async def get_top_issues(
    limit: int = Query(10, ge=1, le=100),
    days: int = Query(30, ge=1, le=365),
    token: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> dict:
    """Get most common issues across all runs.
    
    Args:
        limit: Number of issues to return
        days: Number of days to analyze
        token: JWT token
        db: Database session
        
    Returns:
        Top issues list
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Group by rule_id and count occurrences
    top_rules = db.query(
        AnalysisResult.issue_code,
        AnalysisResult.issue_name,
        func.count(AnalysisResult.id).label('count')
    ).filter(
        AnalysisResult.created_at >= cutoff_date
    ).group_by(
        AnalysisResult.issue_code,
        AnalysisResult.issue_name
    ).order_by(
        func.count(AnalysisResult.id).desc()
    ).limit(limit).all()
    
    return {
        "top_issues": [
            {
                "issue_code": rule[0],
                "issue_name": rule[1],
                "occurrence_count": rule[2]
            }
            for rule in top_rules
        ],
        "total_unique_issues": len(top_rules)
    }
