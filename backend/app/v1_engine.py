"""V1 Core Engine wrapper for V2 backend.

This module provides integration between V1 analysis engine and V2 FastAPI backend.
It handles:
- Repository cloning and setup
- V1 analysis execution (Ruff + ESLint)
- Result mapping to V2 database models
- Error handling and cleanup
"""

import subprocess
import tempfile
import shutil
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from app.models.analysis_result import AnalysisResult, IssueCategory
import logging

logger = logging.getLogger(__name__)


class V1AnalysisEngine:
    """Wrapper for V1 analysis engine."""

    def __init__(self, groq_api_key: Optional[str] = None):
        """Initialize analysis engine.
        
        Args:
            groq_api_key: Optional Groq API key for AI analysis
        """
        self.groq_api_key = groq_api_key
        self.temp_dirs: List[str] = []

    def analyze_repository(
        self,
        repo_url: str,
        branch: str = "main",
        commit_sha: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyze a repository using V1 engine.
        
        Args:
            repo_url: GitHub repository URL
            branch: Branch to analyze (default: main)
            commit_sha: Specific commit SHA to analyze
            
        Returns:
            Dict with analysis results, statistics, errors
            
        Raises:
            Exception: If analysis fails
        """
        temp_dir = None
        try:
            # Create temporary directory
            temp_dir = tempfile.mkdtemp(prefix="agi-analysis-")
            self.temp_dirs.append(temp_dir)
            logger.info(f"Created temp directory: {temp_dir}")

            # Clone repository
            self._clone_repository(repo_url, temp_dir, branch)
            logger.info(f"Cloned repository to {temp_dir}")

            # Checkout specific commit if provided
            if commit_sha:
                self._checkout_commit(temp_dir, commit_sha)
                logger.info(f"Checked out commit: {commit_sha}")

            # Run Ruff analysis (Python)
            ruff_results = self._run_ruff_analysis(temp_dir)
            logger.info(f"Ruff analysis found {len(ruff_results)} issues")

            # Run ESLint analysis (JavaScript/TypeScript)
            eslint_results = self._run_eslint_analysis(temp_dir)
            logger.info(f"ESLint analysis found {len(eslint_results)} issues")

            # Combine results
            all_issues = ruff_results + eslint_results

            return {
                "status": "completed",
                "repository": repo_url,
                "branch": branch,
                "commit_sha": commit_sha,
                "total_issues": len(all_issues),
                "issues": all_issues,
                "ruff_count": len(ruff_results),
                "eslint_count": len(eslint_results),
                "analyzed_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}", exc_info=True)
            return {
                "status": "failed",
                "repository": repo_url,
                "error": str(e),
                "analyzed_at": datetime.utcnow().isoformat(),
            }

        finally:
            # Cleanup temp directory
            if temp_dir and Path(temp_dir).exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
                logger.info(f"Cleaned up temp directory: {temp_dir}")

    def _clone_repository(self, repo_url: str, target_dir: str, branch: str) -> None:
        """Clone repository to target directory.
        
        Args:
            repo_url: Repository URL
            target_dir: Target directory
            branch: Branch to clone
            
        Raises:
            subprocess.CalledProcessError: If clone fails
        """
        cmd = [
            "git",
            "clone",
            "--depth=1",
            "--branch",
            branch,
            repo_url,
            target_dir,
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=60)

    def _checkout_commit(self, repo_dir: str, commit_sha: str) -> None:
        """Checkout specific commit.
        
        Args:
            repo_dir: Repository directory
            commit_sha: Commit SHA to checkout
            
        Raises:
            subprocess.CalledProcessError: If checkout fails
        """
        cmd = ["git", "-C", repo_dir, "checkout", commit_sha]
        subprocess.run(cmd, check=True, capture_output=True, timeout=30)

    def _run_ruff_analysis(self, repo_dir: str) -> List[Dict[str, Any]]:
        """Run Ruff analysis on Python code.
        
        Args:
            repo_dir: Repository directory
            
        Returns:
            List of issues found
        """
        try:
            cmd = ["ruff", "check", repo_dir, "--output-format=json"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=120,
                text=True,
            )

            # Ruff returns exit code 1 if issues found
            if result.returncode in [0, 1]:
                try:
                    issues = json.loads(result.stdout) if result.stdout else []
                    return self._normalize_ruff_issues(issues)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse Ruff JSON output")
                    return []
            else:
                logger.error(f"Ruff failed: {result.stderr}")
                return []

        except subprocess.TimeoutExpired:
            logger.error("Ruff analysis timed out")
            return []
        except FileNotFoundError:
            logger.warning("Ruff not installed, skipping Python analysis")
            return []

    def _run_eslint_analysis(self, repo_dir: str) -> List[Dict[str, Any]]:
        """Run ESLint analysis on JavaScript/TypeScript code.
        
        Args:
            repo_dir: Repository directory
            
        Returns:
            List of issues found
        """
        try:
            cmd = [
                "npx",
                "eslint",
                repo_dir,
                "--format=json",
                "--ext=.js,.jsx,.ts,.tsx",
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=120,
                text=True,
                cwd=repo_dir,
            )

            # ESLint returns exit code 1 if issues found
            if result.returncode in [0, 1]:
                try:
                    issues = json.loads(result.stdout) if result.stdout else []
                    return self._normalize_eslint_issues(issues)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse ESLint JSON output")
                    return []
            else:
                logger.error(f"ESLint failed: {result.stderr}")
                return []

        except subprocess.TimeoutExpired:
            logger.error("ESLint analysis timed out")
            return []
        except FileNotFoundError:
            logger.warning("ESLint not installed, skipping JavaScript analysis")
            return []

    def _normalize_ruff_issues(self, issues: List[Dict]) -> List[Dict[str, Any]]:
        """Normalize Ruff issues to V2 format.
        
        Args:
            issues: Raw Ruff issues
            
        Returns:
            Normalized issues
        """
        normalized = []
        for issue in issues:
            normalized.append({
                "file_path": issue.get("filename", ""),
                "line_number": issue.get("location", {}).get("row", 0),
                "issue_code": issue.get("code", ""),
                "issue_name": issue.get("message", ""),
                "category": self._categorize_issue("python", issue.get("code", "")),
                "severity": "error" if issue.get("code", "").startswith("E") else "warning",
                "message": issue.get("message", ""),
                "language": "python",
            })
        return normalized

    def _normalize_eslint_issues(self, files: List[Dict]) -> List[Dict[str, Any]]:
        """Normalize ESLint issues to V2 format.
        
        Args:
            files: ESLint report with messages
            
        Returns:
            Normalized issues
        """
        normalized = []
        for file_data in files:
            file_path = file_data.get("filePath", "")
            for message in file_data.get("messages", []):
                normalized.append({
                    "file_path": file_path,
                    "line_number": message.get("line", 0),
                    "issue_code": message.get("ruleId", ""),
                    "issue_name": message.get("ruleId", ""),
                    "category": self._categorize_issue("javascript", message.get("ruleId", "")),
                    "severity": message.get("severity", 1),  # 1=warning, 2=error
                    "message": message.get("message", ""),
                    "language": "javascript",
                })
        return normalized

    def _categorize_issue(self, language: str, code: str) -> str:
        """Categorize issue as safe, review, or suggestion.
        
        Args:
            language: Language (python, javascript)
            code: Issue code/rule ID
            
        Returns:
            Category: safe, review, or suggestion
        """
        # Simple heuristic: prefix-based categorization
        if language == "python":
            if code.startswith("E"):  # PEP 8 errors
                return IssueCategory.SAFE.value
            elif code.startswith("W"):  # Warnings
                return IssueCategory.REVIEW.value
            else:
                return IssueCategory.SUGGESTION.value
        else:  # javascript
            if code in ["no-console", "no-unused-vars", "semi"]:
                return IssueCategory.SAFE.value
            elif code in ["require-jsdoc", "indent"]:
                return IssueCategory.REVIEW.value
            else:
                return IssueCategory.SUGGESTION.value

    def cleanup(self) -> None:
        """Cleanup all temporary directories."""
        for temp_dir in self.temp_dirs:
            if Path(temp_dir).exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
                logger.info(f"Cleaned up: {temp_dir}")
        self.temp_dirs.clear()
