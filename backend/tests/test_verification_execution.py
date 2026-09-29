"""Tests for safe deterministic verification command execution."""

import subprocess
from pathlib import Path
from unittest.mock import patch

from app.models.change_impact import ChangeImpactReport, Confidence, RiskLevel
from app.services.change_risk_engine import ChangeRiskAssessment
from app.services.verification_execution import VerificationExecutor


def _impact(changed_files=("tests/test_sample.py",)):
    return ChangeImpactReport(
        repository="owner/repo",
        base_revision="base",
        target_revision="target",
        changed_files=list(changed_files),
        confidence=Confidence.HIGH,
    ).finalize()


def _risk(level=RiskLevel.LOW):
    return ChangeRiskAssessment(
        risk_level=level,
        score=20 if level == RiskLevel.LOW else 90,
        confidence="high",
    ).finalize()


def _repo(tmp_path: Path, *, pytest_file=True, ruff=False, package=False):
    if pytest_file:
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_sample.py").write_text("def test_sample():\n    assert 1 == 1\n")
    if ruff:
        (tmp_path / "pyproject.toml").write_text("[tool.ruff]\nline-length = 88\n")
    if package:
        (tmp_path / "package.json").write_text('{"scripts":{"test":"echo unsafe"}}')
    return tmp_path


def test_pytest_is_discovered_selected_and_passed(tmp_path):
    result = VerificationExecutor(timeout_seconds=30).execute(
        str(_repo(tmp_path)), "target", _impact(), _risk(), []
    )

    command = next(item for item in result.command_results if item["check"] == "pytest")
    assert command["discovered"] is True
    assert command["executed"] is True
    assert command["status"] == "PASSED"
    assert command["exit_code"] == 0
    assert command["executed_test_count"] == 1
    assert result.test_execution_result == "passed"


def test_pytest_failure_becomes_structured_evidence(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_sample.py").write_text("def test_sample():\n    assert False\n")
    result = VerificationExecutor(timeout_seconds=30).execute(
        str(tmp_path), "target", _impact(), _risk(), []
    )

    command = result.command_results[0]
    assert command["status"] == "FAILED"
    assert command["executed"] is True
    assert result.test_execution_result == "failed"


def test_pytest_is_discovered_but_not_executed_without_deterministic_target(tmp_path):
    result = VerificationExecutor().execute(
        str(_repo(tmp_path)), "target", _impact(("src/service.py",)), _risk(), []
    )

    command = result.command_results[0]
    assert command["check"] == "pytest"
    assert command["discovered"] is True
    assert command["executed"] is False
    assert result.relevant_test_selection == "unavailable"
    assert result.test_execution_result is None


def test_pytest_unavailable_is_not_installed_or_executed(tmp_path):
    with patch("app.services.verification_execution.importlib.util.find_spec", return_value=None):
        result = VerificationExecutor().execute(
            str(_repo(tmp_path)), "target", _impact(), _risk(), []
        )

    command = result.command_results[0]
    assert command["executed"] is False
    assert "unavailable" in command["reason"]


def test_timeout_becomes_structured_evidence(tmp_path):
    timeout = subprocess.TimeoutExpired(["pytest"], 1, output=b"partial", stderr=b"late")
    with patch(
        "app.services.verification_execution.subprocess.run",
        side_effect=timeout,
    ):
        result = VerificationExecutor(timeout_seconds=1).execute(
            str(_repo(tmp_path)), "target", _impact(), _risk(), []
        )

    command = result.command_results[0]
    assert command["status"] == "TIMEOUT"
    assert command["executed"] is True
    assert command["exit_code"] is None
    assert result.test_execution_result == "blocked"


def test_ruff_pass_and_failure_are_structured(tmp_path):
    repository = _repo(tmp_path, pytest_file=False, ruff=True)
    passing = VerificationExecutor(timeout_seconds=30).execute(
        str(repository), "target", _impact(("service.py",)), _risk(), []
    )
    ruff = next(item for item in passing.command_results if item["check"] == "ruff")
    assert ruff["executed"] is True
    assert ruff["status"] == "PASSED"

    (repository / "service.py").write_text("import os\n")
    failing = VerificationExecutor(timeout_seconds=30).execute(
        str(repository), "target", _impact(("service.py",)), _risk(), []
    )
    ruff = next(item for item in failing.command_results if item["check"] == "ruff")
    assert ruff["status"] == "FAILED"
    assert failing.static_analysis_result == "failed"


def test_npm_scripts_are_discovered_but_never_executed(tmp_path):
    with patch("app.services.verification_execution.subprocess.run") as run:
        result = VerificationExecutor().execute(
            str(_repo(tmp_path, pytest_file=False, package=True)),
            "target",
            _impact(("service.js",)),
            _risk(),
            [],
        )

    command = next(item for item in result.command_results if item["check"] == "javascript_tests")
    assert command["discovered"] is True
    assert command["executed"] is False
    assert "not executed" in command["reason"]
    run.assert_not_called()


def test_command_order_and_identity_are_stable(tmp_path):
    repository = _repo(tmp_path, ruff=True, package=True)
    first = VerificationExecutor().execute(
        str(repository), "target", _impact(), _risk(), []
    )
    second = VerificationExecutor().execute(
        str(repository), "target", _impact(), _risk(), []
    )

    stable_fields = (
        "check",
        "command",
        "revision",
        "working_directory",
        "discovered",
        "executed",
        "status",
        "exit_code",
        "discovered_test_count",
        "executed_test_count",
        "reason",
    )
    assert [
        tuple(item[field] for field in stable_fields) for item in first.command_results
    ] == [
        tuple(item[field] for field in stable_fields) for item in second.command_results
    ]
    assert [item["check"] for item in first.command_results] == ["javascript_tests", "pytest", "ruff"]


# ---------------------------------------------------------------------------
# deterministic evidence-backed source-to-test mapping (spec: option C)
# ---------------------------------------------------------------------------

import os
import sys

from app.services import verification_execution  # noqa: E402
from app.services.verification_execution import _command_env, _test_targets  # noqa: E402

SHIM = (
    "import os\n"
    "import sys\n"
    "sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))\n"
)


def _mirror_repo(tmp_path: Path, test_path: str, body: str = "def test_mirror():\n    assert 1 == 1\n") -> Path:
    test_file = tmp_path / test_path
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text(body)
    return tmp_path


def _package_repo(tmp_path: Path, test_body: str) -> Path:
    """Repo with a real importable package src/service/client.py (TEST 1/5/6 shape)."""
    pkg = tmp_path / "src" / "service"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "client.py").write_text("VALUE = 1\n")
    test_file = tmp_path / "tests" / "service" / "test_client.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text(test_body)
    return tmp_path


# --- selection rules (unit level, via _test_targets) ------------------------

def test_selected_when_test_imports_changed_module(tmp_path):
    """TEST A: starlette/routing.py + test importing starlette.routing -> selected."""
    repository = _mirror_repo(
        tmp_path, "tests/test_routing.py", "from starlette.routing import Route\n"
    )
    (repository / "starlette").mkdir()
    (repository / "starlette" / "routing.py").write_text("")
    assert _test_targets(repository, ["starlette/routing.py"]) == ["tests/test_routing.py"]


def test_same_stem_foreign_import_is_not_selected(tmp_path):
    """TEST B: benchmarks/_utils.py vs tests/test__utils.py importing starlette._utils."""
    repository = _mirror_repo(
        tmp_path, "tests/test__utils.py", "from starlette._utils import get_route_path\n"
    )
    (repository / "benchmarks").mkdir()
    (repository / "benchmarks" / "_utils.py").write_text("")
    assert _test_targets(repository, ["benchmarks/_utils.py"]) == []


def test_same_stem_example_collision_is_not_selected(tmp_path):
    """TEST C: examples/termui/termui.py vs tests/test_termui.py of the core package."""
    repository = _mirror_repo(
        tmp_path, "tests/test_termui.py", "import click\nfrom click._compat import WIN\n"
    )
    (repository / "examples" / "termui").mkdir(parents=True)
    (repository / "examples" / "termui" / "termui.py").write_text("")
    assert _test_targets(repository, ["examples/termui/termui.py"]) == []


def test_package_namespace_import_alone_is_not_evidence(tmp_path):
    """TEST D: flask/config.py + tests/test_config.py with only `import flask`."""
    repository = _mirror_repo(tmp_path, "tests/test_config.py", "import flask\n")
    (repository / "src" / "flask").mkdir(parents=True)
    (repository / "src" / "flask" / "config.py").write_text("")
    assert _test_targets(repository, ["src/flask/config.py"]) == []


def test_explicit_module_import_is_evidence(tmp_path):
    """TEST E: flask/config.py + test importing flask.config -> selected."""
    repository = _mirror_repo(
        tmp_path, "tests/test_config.py", "from flask.config import Config\n"
    )
    (repository / "src" / "flask").mkdir(parents=True)
    (repository / "src" / "flask" / "config.py").write_text("")
    assert _test_targets(repository, ["src/flask/config.py"]) == ["tests/test_config.py"]


def test_from_parent_import_of_submodule_is_evidence(tmp_path):
    """TEST F: `from starlette import routing` -> selected for starlette/routing.py."""
    repository = _mirror_repo(
        tmp_path, "tests/test_routing.py", "from starlette import routing\n"
    )
    (repository / "starlette").mkdir()
    (repository / "starlette" / "routing.py").write_text("")
    assert _test_targets(repository, ["starlette/routing.py"]) == ["tests/test_routing.py"]


def test_from_parent_import_of_other_name_is_not_evidence(tmp_path):
    """`from service import other` does not prove service/client.py."""
    repository = _mirror_repo(
        tmp_path, "tests/service/test_client.py", "from service import other\n"
    )
    (repository / "src" / "service").mkdir(parents=True)
    (repository / "src" / "service" / "client.py").write_text("")
    assert _test_targets(repository, ["src/service/client.py"]) == []


def test_ancestor_package_import_is_not_evidence(tmp_path):
    """TEST G: `import starlette` does not prove starlette/routing.py."""
    repository = _mirror_repo(tmp_path, "tests/test_routing.py", "import starlette\n")
    (repository / "starlette").mkdir()
    (repository / "starlette" / "routing.py").write_text("")
    assert _test_targets(repository, ["starlette/routing.py"]) == []


def test_import_as_alias_is_evidence(tmp_path):
    """`import starlette.routing as routing` -> selected."""
    repository = _mirror_repo(
        tmp_path, "tests/test_routing.py", "import starlette.routing as routing\n"
    )
    (repository / "starlette").mkdir()
    (repository / "starlette" / "routing.py").write_text("")
    assert _test_targets(repository, ["starlette/routing.py"]) == ["tests/test_routing.py"]


def test_unparsable_candidate_is_rejected(tmp_path):
    """AST parse failure fabricates no relationship; candidate is conservatively rejected."""
    repository = _mirror_repo(
        tmp_path, "tests/test_routing.py", "def broken(:\n"
    )
    (repository / "starlette").mkdir()
    (repository / "starlette" / "routing.py").write_text("")
    assert _test_targets(repository, ["starlette/routing.py"]) == []


def test_all_evidenced_candidates_are_selected_without_ranking(tmp_path):
    """Multiple deterministically-related candidates are all selected, never ranked."""
    repository = _mirror_repo(
        tmp_path, "tests/test_routing.py", "from starlette.routing import Route\n"
    )
    nested = repository / "tests" / "starlette"
    nested.mkdir()
    (nested / "test_routing.py").write_text("from starlette.routing import Route\n")
    (repository / "starlette").mkdir()
    (repository / "starlette" / "routing.py").write_text("")
    assert _test_targets(repository, ["starlette/routing.py"]) == [
        "tests/starlette/test_routing.py",
        "tests/test_routing.py",
    ]


def test_relative_import_is_not_evidence(tmp_path):
    """Relative imports are not resolved (conservative under-approximation)."""
    repository = _mirror_repo(
        tmp_path, "tests/test_routing.py", "from .routing import Route\n"
    )
    (repository / "starlette").mkdir()
    (repository / "starlette" / "routing.py").write_text("")
    assert _test_targets(repository, ["starlette/routing.py"]) == []


# --- selection V2: non-mirror recall + provenance ---------------------------

def test_non_mirror_test_with_direct_import_is_selected(tmp_path):
    repository = _mirror_repo(
        tmp_path, "tests/test_requests.py", "from requests.models import Response\n"
    )
    (repository / "src" / "requests").mkdir(parents=True)
    (repository / "src" / "requests" / "models.py").write_text("")
    assert _test_targets(repository, ["src/requests/models.py"]) == [
        "tests/test_requests.py"
    ]


def test_mirror_test_with_direct_import_is_still_selected(tmp_path):
    repository = _mirror_repo(
        tmp_path, "tests/test_models.py", "from requests.models import Response\n"
    )
    (repository / "src" / "requests").mkdir(parents=True)
    (repository / "src" / "requests" / "models.py").write_text("")
    assert _test_targets(repository, ["src/requests/models.py"]) == [
        "tests/test_models.py"
    ]


def test_same_stem_unrelated_test_is_not_selected(tmp_path):
    repository = _mirror_repo(
        tmp_path, "tests/test_models.py", "from other.models import Thing\n"
    )
    (repository / "src" / "requests").mkdir(parents=True)
    (repository / "src" / "requests" / "models.py").write_text("")
    assert _test_targets(repository, ["src/requests/models.py"]) == []


def test_package_import_only_is_not_selected_v2(tmp_path):
    repository = _mirror_repo(
        tmp_path,
        "tests/test_status.py",
        "import httpx\n\ndef test_codes():\n    assert httpx.codes.OK == 200\n",
    )
    (repository / "httpx").mkdir()
    (repository / "httpx" / "_status_codes.py").write_text("")
    assert _test_targets(repository, ["httpx/_status_codes.py"]) == []


def test_urllib3_style_test_directory_is_selected(tmp_path):
    repository = _mirror_repo(
        tmp_path,
        "test/test_connectionpool.py",
        "from urllib3.connectionpool import HTTPConnectionPool\n",
    )
    (repository / "src" / "urllib3").mkdir(parents=True)
    (repository / "src" / "urllib3" / "connectionpool.py").write_text("")
    assert _test_targets(repository, ["src/urllib3/connectionpool.py"]) == [
        "test/test_connectionpool.py"
    ]


def test_multiple_evidenced_non_mirror_candidates_all_selected(tmp_path):
    repository = _mirror_repo(
        tmp_path, "tests/test_context.py", "from click.core import Context\n"
    )
    (repository / "tests" / "test_commands.py").write_text(
        "from click.core import Command\n"
    )
    (repository / "src" / "click").mkdir(parents=True)
    (repository / "src" / "click" / "core.py").write_text("")
    assert _test_targets(repository, ["src/click/core.py"]) == [
        "tests/test_commands.py",
        "tests/test_context.py",
    ]


def test_changed_symbol_reference_strengthens_provenance(tmp_path):
    from app.models.change_impact import ChangedSymbol
    from app.services.verification_execution import _select_tests

    repository = _mirror_repo(
        tmp_path,
        "tests/test_requests.py",
        "from requests.models import Response\n\n"
        "def test_it():\n    Response().raise_for_status()\n",
    )
    (repository / "src" / "requests").mkdir(parents=True)
    (repository / "src" / "requests" / "models.py").write_text("")
    symbol = ChangedSymbol(
        node_id="requests.models.Response.raise_for_status",
        node_type="method",
        file_path="src/requests/models.py",
        name="Response.raise_for_status",
        change_kind="modified",
    )
    records = _select_tests(
        repository, ["src/requests/models.py"], [symbol]
    )
    assert len(records) == 1
    assert records[0].test_file == "tests/test_requests.py"
    assert records[0].evidence == "DIRECT_IMPORT_AND_SYMBOL"
    assert records[0].symbols == ("raise_for_status",)


def test_unrelated_symbol_does_not_establish_symbol_evidence(tmp_path):
    from app.models.change_impact import ChangedSymbol
    from app.services.verification_execution import _select_tests

    repository = _mirror_repo(
        tmp_path,
        "tests/test_requests.py",
        "from requests.models import Response\n\n"
        "def test_it():\n    Response().json()\n",
    )
    (repository / "src" / "requests").mkdir(parents=True)
    (repository / "src" / "requests" / "models.py").write_text("")
    symbol = ChangedSymbol(
        node_id="requests.models.Response.raise_for_status",
        node_type="method",
        file_path="src/requests/models.py",
        name="Response.raise_for_status",
        change_kind="modified",
    )
    records = _select_tests(
        repository, ["src/requests/models.py"], [symbol]
    )
    assert len(records) == 1
    assert records[0].evidence == "DIRECT_IMPORT"
    assert records[0].symbols == ()


def test_no_evidence_yields_no_selection_and_unavailable_provenance(tmp_path):
    from app.services.verification_execution import (
        _select_tests, format_selection_provenance,
    )

    repository = _mirror_repo(tmp_path, "tests/test_config.py", "import flask\n")
    (repository / "src" / "flask").mkdir(parents=True)
    (repository / "src" / "flask" / "config.py").write_text("")
    records = _select_tests(repository, ["src/flask/config.py"])
    assert records == []
    assert format_selection_provenance(records) == "unavailable"


def test_selection_provenance_is_deterministic_across_runs(tmp_path):
    from app.services.verification_execution import (
        _select_tests, format_selection_provenance,
    )

    repository = _mirror_repo(
        tmp_path, "tests/test_context.py", "from click.core import Context\n"
    )
    (repository / "tests" / "test_commands.py").write_text(
        "from click.core import Command\n"
    )
    (repository / "src" / "click").mkdir(parents=True)
    (repository / "src" / "click" / "core.py").write_text("")
    first = format_selection_provenance(
        _select_tests(repository, ["src/click/core.py"])
    )
    second = format_selection_provenance(
        _select_tests(repository, ["src/click/core.py"])
    )
    assert first == second
    assert '"evidence":"DIRECT_IMPORT"' in first


# --- executor-level integration ---------------------------------------------

def test_mirror_source_to_test_is_selected_and_executed(tmp_path):
    """TEST 1 + TEST 5: evidence-backed mirror target is selected and executed."""
    repository = _package_repo(
        tmp_path,
        SHIM + "import service.client\n\ndef test_mirror():\n    assert service.client.VALUE == 1\n",
    )
    result = VerificationExecutor(timeout_seconds=30).execute(
        str(repository), "target", _impact(("src/service/client.py",)), _risk(), []
    )

    command = next(item for item in result.command_results if item["check"] == "pytest")
    assert command["executed"] is True
    assert command["status"] == "PASSED"
    assert command["exit_code"] == 0
    assert command["executed_test_count"] == 1
    assert result.relevant_tests == ["tests/service/test_client.py"]
    assert result.relevant_test_selection == "deterministic_changed_test_files"
    assert result.test_execution_result == "passed"


def test_no_deterministic_mapping_stays_unavailable(tmp_path):
    """TEST 2 + TEST I: no mirror, no evidence -> nothing selected, pytest not invoked."""
    repository = _mirror_repo(tmp_path, "tests/test_other.py")
    result = VerificationExecutor().execute(
        str(repository), "target", _impact(("src/service.py",)), _risk(), []
    )

    command = next(item for item in result.command_results if item["check"] == "pytest")
    assert command["executed"] is False
    assert command["reason"] == "relevant_test_selection=unavailable"
    assert result.relevant_test_selection == "unavailable"
    assert result.test_execution_result is None


def test_existing_candidate_without_evidence_is_not_executed(tmp_path):
    """Candidate exists, same stem, but the test never imports the module."""
    repository = _mirror_repo(tmp_path, "tests/service/test_client.py")
    result = VerificationExecutor().execute(
        str(repository), "target", _impact(("src/service/client.py",)), _risk(), []
    )

    command = next(item for item in result.command_results if item["check"] == "pytest")
    assert command["executed"] is False
    assert command["reason"] == "relevant_test_selection=unavailable"
    assert result.relevant_test_selection == "unavailable"


def test_changed_test_file_behavior_is_unchanged(tmp_path):
    """TEST 4 + TEST H: changed test files keep the pre-existing selection path."""
    repository = _repo(tmp_path)
    result = VerificationExecutor(timeout_seconds=30).execute(
        str(repository), "target", _impact(("tests/test_sample.py",)), _risk(), []
    )

    command = next(item for item in result.command_results if item["check"] == "pytest")
    assert command["executed"] is True
    assert command["status"] == "PASSED"
    assert result.relevant_tests == ["tests/test_sample.py"]


def test_mirror_target_failure_is_structured_evidence(tmp_path):
    """TEST 6: a failing evidence-backed mirror target produces honest failed evidence."""
    repository = _package_repo(
        tmp_path,
        SHIM + "import service.client\n\ndef test_mirror():\n    assert False\n",
    )
    result = VerificationExecutor(timeout_seconds=30).execute(
        str(repository), "target", _impact(("src/service/client.py",)), _risk(), []
    )

    command = next(item for item in result.command_results if item["check"] == "pytest")
    assert command["executed"] is True
    assert command["status"] == "FAILED"
    assert result.test_execution_result == "failed"


def test_pytest_unavailable_with_selected_target_is_not_executed(tmp_path):
    """TEST 7: selection succeeds but pytest is missing -> safe NOT_EXECUTED."""
    repository = _mirror_repo(
        tmp_path, "tests/service/test_client.py", "import service.client\n"
    )
    (repository / "src" / "service").mkdir(parents=True)
    (repository / "src" / "service" / "client.py").write_text("")
    with patch(
        "app.services.verification_execution.importlib.util.find_spec", return_value=None
    ):
        result = VerificationExecutor().execute(
            str(repository), "target", _impact(("src/service/client.py",)), _risk(), []
        )

    command = next(item for item in result.command_results if item["check"] == "pytest")
    assert command["executed"] is False
    assert "pytest is unavailable" in command["reason"]
    # the selection itself is still deterministic and recorded
    assert result.relevant_test_selection == "deterministic_changed_test_files"
    assert result.test_execution_result is None


# ---------------------------------------------------------------------------
# subprocess-local PYTHONPATH for src-layout import integrity
# ---------------------------------------------------------------------------

from app.services.verification_execution import _command_env  # noqa: E402


def test_flat_repository_environment_unchanged(tmp_path):
    """TEST 1: no src directory -> PYTHONPATH behavior is unchanged."""
    base = _command_env(tmp_path, include_src=False)
    flat = _command_env(tmp_path, include_src=True)  # no src/ exists
    assert base.get("PYTHONPATH") == flat.get("PYTHONPATH")
    assert "PYTHONPATH" not in flat or "src" not in flat["PYTHONPATH"]


def test_src_layout_prepends_absolute_src(tmp_path):
    """TEST 2: repo/src exists -> subprocess env contains the absolute src dir."""
    (tmp_path / "src" / "example_pkg").mkdir(parents=True)
    env = _command_env(tmp_path, include_src=True)
    assert env["PYTHONPATH"] == str((tmp_path / "src").resolve())


def test_existing_pythonpath_is_preserved_and_prepended(tmp_path, monkeypatch):
    """TEST 3: existing PYTHONPATH entries remain; src is prepended, not replaced."""
    (tmp_path / "src").mkdir()
    monkeypatch.setenv("PYTHONPATH", "/existing/entry")
    env = _command_env(tmp_path, include_src=True)
    assert env["PYTHONPATH"] == f"{(tmp_path / 'src').resolve()}{os.pathsep}/existing/entry"


def test_missing_src_directory_is_not_added(tmp_path):
    """TEST 4: a nonexistent src path is never added."""
    assert not (tmp_path / "src").exists()
    env = _command_env(tmp_path, include_src=True)
    assert "PYTHONPATH" not in env or str(tmp_path / "src") not in env["PYTHONPATH"]


def test_pytest_command_itself_is_unchanged(tmp_path):
    """TEST 5: the pytest argv is identical with the src adjustment in place."""
    (tmp_path / "src").mkdir()
    repository = _mirror_repo(tmp_path, "tests/test_sample.py")
    result = VerificationExecutor(timeout_seconds=30).execute(
        str(repository), "target", _impact(("tests/test_sample.py",)), _risk(), []
    )
    command = next(item for item in result.command_results if item["check"] == "pytest")
    assert command["command"] == [
        sys.executable, "-m", "pytest", "--color=no", "tests/test_sample.py",
    ]


def test_ruff_environment_is_unchanged(tmp_path):
    """TEST 6: ruff does not receive the src PYTHONPATH adjustment."""
    (tmp_path / "src").mkdir()
    repository = _repo(tmp_path, ruff=True)
    captured = []

    real_run = verification_execution.subprocess.run

    def recording_run(*args, **kwargs):
        captured.append(kwargs.get("env"))
        return real_run(*args, **kwargs)

    with patch.object(verification_execution.subprocess, "run", side_effect=recording_run):
        VerificationExecutor(timeout_seconds=30).execute(
            str(repository), "target", _impact(("service.py",)), _risk(), []
        )

    assert len(captured) == 1  # only the ruff command ran
    src_path = str((tmp_path / "src").resolve())
    assert src_path not in (captured[0].get("PYTHONPATH") or "")


def test_environment_modification_is_subprocess_local(tmp_path, monkeypatch):
    """TEST 7: os.environ is never mutated; the env dict is a private copy."""
    (tmp_path / "src").mkdir()
    monkeypatch.setenv("PYTHONPATH", "/sentinel")
    before = dict(os.environ)
    env = _command_env(tmp_path, include_src=True)
    assert env is not os.environ
    assert env["PYTHONPATH"].startswith(str((tmp_path / "src").resolve()))
    assert os.environ == before
    assert os.environ["PYTHONPATH"] == "/sentinel"


def test_src_layout_test_executes_the_checkout_package(tmp_path):
    """TEST 8: integration — pytest imports the package from temp_repo/src, not elsewhere.

    The executed test asserts example_pkg.__file__ resolves inside temp_repo/src,
    so a PASSED result proves import integrity, not merely a PYTHONPATH string.
    """
    pkg_dir = tmp_path / "src" / "example_pkg"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "__init__.py").write_text("PACKAGE_DIR = __file__\n")
    test_file = tmp_path / "tests" / "test_import.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text(
        "import example_pkg\n"
        "\n"
        "def test_import_resolves_inside_checkout_src():\n"
        f"    assert example_pkg.__file__.startswith({str((tmp_path / 'src').resolve())!r})\n"
    )
    result = VerificationExecutor(timeout_seconds=30).execute(
        str(tmp_path), "target", _impact(("tests/test_import.py",)), _risk(), []
    )

    command = next(item for item in result.command_results if item["check"] == "pytest")
    assert command["executed"] is True
    assert command["status"] == "PASSED"
    assert command["exit_code"] == 0
    assert command["executed_test_count"] == 1
    assert result.test_execution_result == "passed"
