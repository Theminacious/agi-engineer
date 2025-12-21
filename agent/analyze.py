import subprocess
import os
import json

def run_ruff(repo_root):
    """
    Run Ruff from repo root and return ABSOLUTE file paths.
    """
    result = subprocess.run(
        ["ruff", "check", ".", "--output-format", "json", "--exit-zero"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    issues = []

    if not result.stdout.strip():
        return issues

    data = json.loads(result.stdout)

    for item in data:
        filename = os.path.abspath(
            os.path.join(repo_root, item["filename"])
        )

        issues.append({
            "filename": filename,   # ✅ ABSOLUTE PATH
            "line": item["location"]["row"],
            "code": item["code"],
            "message": item["message"],
        })

    return issues
