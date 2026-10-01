"""Execution-sandbox security: customer code cannot observe application secrets.

Exercises the real VerificationExecutor subprocess boundary against disposable
git repositories. A sentinel secret placed in the parent process environment
must never be visible to executed repository test code.
"""

import os
import subprocess

from app.models.change_impact import ChangeImpactReport
from app.services.change_risk_engine import ChangeRiskAssessment, RiskLevel
from app.services.verification_execution import (
    _ENV_ALLOWLIST,
    _command_env,
    VerificationExecutor,
)


SECRET_NAMES = (
    "GITHUB_APP_PRIVATE_KEY",
    "GITHUB_CLIENT_SECRET",
    "GITHUB_TOKEN",
    "JWT_SECRET_KEY",
    "WEBHOOK_SECRET",
    "GROQ_API_KEY",
    "DATABASE_URL",
    "REDIS_URL",
    "AGI_SECRET_SENTINEL",
)


def _git(repo, *args):
    return subprocess.run(
        ["git", "-C", repo, *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def _repo(tmp_path, test_body):
    repo = str(tmp_path / "repo")
    subprocess.run(["git", "init", "--quiet", "-b", "main", repo], check=True)
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Sandbox Test")
    _git(repo, "config", "commit.gpgsign", "false")
    os.makedirs(os.path.join(repo, "tests"))
    with open(os.path.join(repo, "tests", "test_leak.py"), "w") as fh:
        fh.write(test_body)
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "c")
    return repo, _git(repo, "rev-parse", "HEAD")


def _impact():
    return ChangeImpactReport(
        repository="r", base_revision="base", target_revision="target",
        changed_files=["tests/test_leak.py"],
    )


def _risk():
    return ChangeRiskAssessment(risk_level=RiskLevel.LOW, score=10, confidence="high")


def _execute(repo, sha):
    return VerificationExecutor().execute(
        repo_path=repo, revision=sha, impact=_impact(), risk=_risk(),
        contexts=[], capture_node_results=True, expected_target_sha=sha,
    )


def test_command_env_excludes_secret_names(monkeypatch):
    for name in SECRET_NAMES:
        monkeypatch.setenv(name, "LEAK-" + name)
    env = _command_env(tmp_path_env(), include_src=False)
    for name in SECRET_NAMES:
        assert name not in env, f"{name} leaked into customer environment"
    assert env.get("PYTHONHASHSEED") == "0"
    assert "PATH" in env


def test_command_env_only_passes_allowlisted_names(monkeypatch):
    monkeypatch.setenv("TOTALLY_ARBITRARY_APP_VAR", "x")
    env = _command_env(tmp_path_env(), include_src=False)
    allowed = _ENV_ALLOWLIST | {"PYTHONHASHSEED"}
    assert set(env).issubset(allowed), f"non-allowlisted vars present: {set(env) - allowed}"


def test_sentinel_secret_not_observable_by_customer_test(tmp_path, monkeypatch):
    monkeypatch.setenv("AGI_SECRET_SENTINEL", "super-secret-value")
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", "-----BEGIN PRIVATE KEY-----leak")
    body = (
        "import os\n"
        "def test_no_app_secret():\n"
        "    assert os.environ.get('AGI_SECRET_SENTINEL') is None\n"
        "    assert os.environ.get('GITHUB_APP_PRIVATE_KEY') is None\n"
    )
    repo, sha = _repo(tmp_path, body)
    ev = _execute(repo, sha)
    assert ev.tests_executed == ["tests/test_leak.py"]
    assert ev.test_execution_result == "passed"


def test_leaked_secret_would_fail_the_guard_test(tmp_path, monkeypatch):
    monkeypatch.setenv("AGI_SECRET_SENTINEL", "super-secret-value")
    body = (
        "import os\n"
        "def test_secret_absent():\n"
        "    assert os.environ.get('AGI_SECRET_SENTINEL') is None\n"
    )
    repo, sha = _repo(tmp_path, body)
    ev = _execute(repo, sha)
    assert ev.test_execution_result == "passed"
    node = (ev.command_results[0].get("node_results") or {}) if ev.command_results else {}
    assert node.get("tests/test_leak.py::test_secret_absent") == "passed"


def tmp_path_env():
    from pathlib import Path
    import tempfile
    return Path(tempfile.gettempdir())
