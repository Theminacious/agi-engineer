"""
Run logger for tracking analysis execution, fixes, and errors.
Stores metrics in ~/.agi-engineer/runs.json
"""
import os
import json
import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

DEFAULT_RUNS_FILE = os.path.expanduser("~/.agi-engineer/runs.json")


class RunLogger:
    """Track and log each analysis run"""
    
    def __init__(self, runs_file: str = DEFAULT_RUNS_FILE):
        self.runs_file = runs_file
        self.current_run: Optional[Dict[str, Any]] = None
    
    def start_run(self, repo_path: str, repo_name: str) -> None:
        """Start a new run"""
        self.current_run = {
            "timestamp": datetime.now().isoformat(),
            "repo_path": repo_path,
            "repo_name": repo_name,
            "start_time": time.time(),
            "issues_found": 0,
            "fixes_applied": 0,
            "errors": [],
            "status": "running"
        }
    
    def add_issue(self, code: str, filename: str) -> None:
        """Log an issue found"""
        if self.current_run:
            self.current_run["issues_found"] = self.current_run.get("issues_found", 0) + 1
    
    def add_fix(self, code: str, filename: str) -> None:
        """Log a fix applied"""
        if self.current_run:
            self.current_run["fixes_applied"] = self.current_run.get("fixes_applied", 0) + 1
    
    def add_error(self, error_msg: str, error_type: str = "unknown") -> None:
        """Log an error"""
        if self.current_run:
            self.current_run["errors"].append({
                "type": error_type,
                "message": error_msg,
                "timestamp": datetime.now().isoformat()
            })
    
    def end_run(self, status: str = "completed") -> Dict[str, Any]:
        """End the current run and save"""
        if not self.current_run:
            return {}
        
        self.current_run["status"] = status
        self.current_run["end_time"] = time.time()
        self.current_run["duration"] = self.current_run["end_time"] - self.current_run["start_time"]
        
        # Save to file
        self._save_run(self.current_run)
        
        result = self.current_run.copy()
        self.current_run = None
        return result
    
    def _save_run(self, run: Dict[str, Any]) -> None:
        """Save run to file"""
        try:
            runs = self._load_runs()
            runs.append(run)
            
            os.makedirs(os.path.dirname(self.runs_file), exist_ok=True)
            with open(self.runs_file, "w") as f:
                json.dump(runs, f, indent=2)
            
            logger.info(f"Saved run to {self.runs_file}")
        except Exception as e:
            logger.error(f"Failed to save run: {e}")
    
    def _load_runs(self) -> list:
        """Load all runs from file"""
        try:
            if os.path.exists(self.runs_file):
                with open(self.runs_file, "r") as f:
                    return json.load(f) or []
        except Exception as e:
            logger.warning(f"Failed to load runs: {e}")
        return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get aggregate statistics"""
        runs = self._load_runs()
        
        if not runs:
            return {
                "total_runs": 0,
                "total_issues_found": 0,
                "total_fixes_applied": 0,
                "total_errors": 0,
                "avg_duration": 0
            }
        
        total_issues = sum(r.get("issues_found", 0) for r in runs)
        total_fixes = sum(r.get("fixes_applied", 0) for r in runs)
        total_errors = sum(len(r.get("errors", [])) for r in runs)
        avg_duration = sum(r.get("duration", 0) for r in runs) / len(runs) if runs else 0
        
        return {
            "total_runs": len(runs),
            "total_issues_found": total_issues,
            "total_fixes_applied": total_fixes,
            "total_errors": total_errors,
            "avg_duration": round(avg_duration, 2),
            "success_rate": round((len([r for r in runs if r["status"] == "completed"]) / len(runs)) * 100, 1) if runs else 0
        }
