"""V1 Core Engine wrapper for V2 backend."""

import subprocess
import tempfile
import shutil
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from app.models.analysis_result import AnalysisResult, IssueCategory
import logging

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from agent.rule_classifier import RuleClassifier, RuleCategory

logger = logging.getLogger(__name__)


class V1AnalysisEngine:
    def __init__(self, groq_api_key: Optional[str] = None):
        self.groq_api_key = groq_api_key
        self.temp_dirs: List[str] = []

    def analyze_repository(self, repo_url: str, branch: str = "main", commit_sha: Optional[str] = None) -> Dict[str, Any]:
        temp_dir = None
        try:
            temp_dir = tempfile.mkdtemp(prefix="agi-analysis-")
            self.temp_dirs.append(temp_dir)
            logger.info(f"Created temp directory: {temp_dir}")

            self._clone_repository(repo_url, temp_dir, branch)
            logger.info(f"Cloned repository to {temp_dir}")

            if commit_sha:
                self._checkout_commit(temp_dir, commit_sha)

            ruff_results = self._run_ruff_analysis(temp_dir)
            logger.info(f"Ruff analysis found {len(ruff_results)} issues")

            eslint_results = self._run_eslint_analysis(temp_dir)
            logger.info(f"ESLint analysis found {len(eslint_results)} issues")

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
            if temp_dir and Path(temp_dir).exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    def _clone_repository(self, repo_url: str, target_dir: str, branch: str) -> None:
        cmd = ["git", "clone", "--depth=1", "--branch", branch, repo_url, target_dir]
        subprocess.run(cmd, check=True, capture_output=True, timeout=60)

    def _checkout_commit(self, repo_dir: str, commit_sha: str) -> None:
        cmd = ["git", "-C", repo_dir, "checkout", commit_sha]
        subprocess.run(cmd, check=True, capture_output=True, timeout=30)

    def _run_ruff_analysis(self, repo_dir: str) -> List[Dict[str, Any]]:
        try:
            cmd = ["ruff", "check", repo_dir, "--output-format=json"]
            result = subprocess.run(cmd, capture_output=True, timeout=120, text=True)
            if result.returncode in [0, 1]:
                try:
                    issues = json.loads(result.stdout) if result.stdout else []
                    return self._normalize_ruff_issues(issues)
                except json.JSONDecodeError:
                    return []
            else:
                logger.error(f"Ruff failed: {result.stderr}")
                return []
        except subprocess.TimeoutExpired:
            return []
        except FileNotFoundError:
            logger.warning("Ruff not installed")
            return []

    def _run_eslint_analysis(self, repo_dir: str) -> List[Dict[str, Any]]:
        try:
            # Create a temporary eslint config for the analysis
            eslint_config = {
                "env": {"browser": True, "es2021": True, "node": True},
                "parser": "@typescript-eslint/parser",
                "plugins": ["@typescript-eslint"],
                "rules": {
                    "no-unused-vars": "warn",
                    "no-console": "warn",
                    "no-undef": "warn",
                    "prefer-const": "warn",
                    "no-var": "warn",
                    "@typescript-eslint/no-unused-vars": "warn",
                    "@typescript-eslint/no-explicit-any": "warn",
                }
            }
            
            config_path = Path(repo_dir) / ".eslintrc.json"
            with open(config_path, "w") as f:
                json.dump(eslint_config, f)

            cmd = [
                "eslint",
                ".",
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

            # Cleanup config
            config_path.unlink(missing_ok=True)

            if result.returncode in [0, 1]:
                try:
                    issues = json.loads(result.stdout) if result.stdout else []
                    return self._normalize_eslint_issues(issues)
                except json.JSONDecodeError:
                    return []
            else:
                logger.error(f"ESLint failed: {result.stderr}")
                return []

        except subprocess.TimeoutExpired:
            return []
        except FileNotFoundError:
            logger.warning("ESLint not installed")
            return []

    def _normalize_ruff_issues(self, issues: List[Dict]) -> List[Dict[str, Any]]:
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
                    "severity": "error" if message.get("severity") == 2 else "warning",
                    "message": message.get("message", ""),
                    "language": "javascript",
                })
        return normalized

    def _categorize_issue(self, language: str, code: str) -> str:
        if language == "python":
            classifier = RuleClassifier()
            classification = classifier.classify(code)
            if classification.get('category') == RuleCategory.SAFE:
                return IssueCategory.SAFE.value
            elif classification.get('category') == RuleCategory.RISKY:
                return IssueCategory.REVIEW.value
            else:
                return IssueCategory.SUGGESTION.value
        else:
            if code in ["no-console", "no-unused-vars", "prefer-const", "no-var"]:
                return IssueCategory.SAFE.value
            elif code in ["@typescript-eslint/no-unused-vars", "@typescript-eslint/no-explicit-any"]:
                return IssueCategory.REVIEW.value
            else:
                return IssueCategory.SUGGESTION.value

    def cleanup(self) -> None:
        for temp_dir in self.temp_dirs:
            if Path(temp_dir).exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
        self.temp_dirs.clear()
