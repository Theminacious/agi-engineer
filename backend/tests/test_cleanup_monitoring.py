"""Temp-resource cleanup and its failure accounting.

Covers P2 #4 of PRODUCTION_READINESS_AUDIT.md ("Add Cleanup Failure
Monitoring"), plus a resource leak found while implementing it that the audit
did not describe.

The audit's concern was that `shutil.rmtree` failures were logged and never
counted. The leak is separate and unconditional: PRAnalysisPipeline._clone_repository
creates a temp root with mkdtemp and clones into `<root>/repo`, but analyze_pr's
cleanup removed only the returned clone path. The root survived every run, so a
worker leaked one directory per analysed PR whether the run succeeded or failed.
`test_clone_then_cleanup_leaves_nothing_behind` is the regression test for it.
"""

import asyncio
import os
import shutil
import tempfile
from unittest.mock import AsyncMock, patch

import pytest

from app.models import (
    GitHubWebhookEvent,
    Installation,
    PRAnalysis,
    Repository,
)
from app.models.github_integration import PRAnalysisStatus, WebhookEventType
from app.services import cleanup as cleanup_module
from app.services.cleanup import (
    MAX_RETAINED_FAILURES,
    CleanupTracker,
    cleanup_stats,
    safe_rmtree,
)
from app.services.pr_analysis import PRAnalysisPipeline
from app.v1_engine import V1AnalysisEngine

PR_TEMP_PREFIX = "agi-engineer-pr-"


@pytest.fixture(autouse=True)
def clean_tracker():
    """Reset the process-wide counters around each test.

    TRACKER is module state shared by every cleanup site, so without this a test
    would see failures recorded by whichever test ran before it.
    """
    cleanup_module.TRACKER.reset()
    yield
    cleanup_module.TRACKER.reset()


@pytest.fixture
def tmp_tree():
    """A populated directory tree, plus its path. Removed if a test leaves it."""
    root = tempfile.mkdtemp(prefix="cleanup-test-")
    os.makedirs(os.path.join(root, "nested", "deeper"))
    with open(os.path.join(root, "nested", "file.txt"), "w") as handle:
        handle.write("content")
    yield root
    shutil.rmtree(root, ignore_errors=True)


def pr_temp_dirs():
    """Paths of PR-clone temp roots currently on disk.

    Compared before/after rather than asserted absolutely, so a directory left
    by an unrelated process (or an earlier crashed run) cannot make the leak
    tests pass or fail spuriously.
    """
    tmp = tempfile.gettempdir()
    try:
        names = os.listdir(tmp)
    except OSError:
        return set()
    return {
        os.path.join(tmp, name) for name in names if name.startswith(PR_TEMP_PREFIX)
    }


class TestSafeRmtree:
    """The primitive every cleanup site now goes through."""

    def test_removes_the_tree_and_counts_an_attempt(self, tmp_tree):
        assert safe_rmtree(tmp_tree, kind="test") is True
        assert not os.path.exists(tmp_tree)

        stats = cleanup_stats()
        assert stats["attempts"] == 1
        assert stats["failures"] == 0

    def test_missing_path_is_not_counted_as_either_outcome(self):
        """Nothing was leaked, so nothing happened worth recording."""
        assert safe_rmtree("/nonexistent/path/xyz", kind="test") is True
        assert safe_rmtree(None, kind="test") is True

        stats = cleanup_stats()
        assert stats["attempts"] == 0
        assert stats["failures"] == 0

    def test_failure_is_counted_and_reported_not_swallowed(self, tmp_tree):
        with patch("app.services.cleanup.shutil.rmtree", side_effect=OSError("device busy")):
            assert safe_rmtree(tmp_tree, kind="pr_clone") is False

        stats = cleanup_stats()
        assert stats["failures"] == 1
        assert stats["failures_by_kind"] == {"pr_clone": 1}
        assert stats["recent_failures"][0]["path"] == tmp_tree
        assert "device busy" in stats["recent_failures"][0]["error"]

    def test_failure_does_not_raise(self, tmp_tree):
        """Callers are in finally blocks: raising here would mask their error."""
        with patch("app.services.cleanup.shutil.rmtree", side_effect=OSError("nope")):
            safe_rmtree(tmp_tree, kind="test")  # must not raise

    def test_failure_is_logged_at_error(self, tmp_tree, caplog):
        """A leaked directory has to be visible to whoever watches logs."""
        with caplog.at_level("ERROR"):
            with patch("app.services.cleanup.shutil.rmtree", side_effect=OSError("locked")):
                safe_rmtree(tmp_tree, kind="pr_clone")

        assert any(
            record.levelname == "ERROR" and tmp_tree in record.message
            for record in caplog.records
        )

    def test_kinds_are_counted_separately(self, tmp_tree):
        """So a failing PR clone is distinguishable from a failing v3 workspace."""
        with patch("app.services.cleanup.shutil.rmtree", side_effect=OSError("x")):
            safe_rmtree(tmp_tree, kind="pr_clone")
            safe_rmtree(tmp_tree, kind="pr_clone")
            safe_rmtree(tmp_tree, kind="v3_analysis")

        assert cleanup_stats()["failures_by_kind"] == {"pr_clone": 2, "v3_analysis": 1}


class TestTrackerBounds:
    """The monitoring must not become the leak it was added to detect."""

    def test_retained_failures_are_capped(self):
        tracker = CleanupTracker()
        for index in range(MAX_RETAINED_FAILURES + 25):
            tracker.record_failure(kind="test", path=f"/tmp/p{index}", error="e")

        snapshot = tracker.snapshot()
        assert snapshot["failures"] == MAX_RETAINED_FAILURES + 25
        assert len(snapshot["recent_failures"]) == MAX_RETAINED_FAILURES

    def test_the_newest_failures_are_the_ones_kept(self):
        tracker = CleanupTracker()
        for index in range(MAX_RETAINED_FAILURES + 5):
            tracker.record_failure(kind="test", path=f"/tmp/p{index}", error="e")

        kept = [entry["path"] for entry in tracker.snapshot()["recent_failures"]]
        assert kept[-1] == f"/tmp/p{MAX_RETAINED_FAILURES + 4}"
        assert "/tmp/p0" not in kept

    def test_snapshot_cannot_mutate_tracker_state(self):
        tracker = CleanupTracker()
        tracker.record_failure(kind="test", path="/tmp/p", error="e")

        snapshot = tracker.snapshot()
        snapshot["failures_by_kind"]["test"] = 999
        snapshot["recent_failures"].clear()

        assert tracker.snapshot()["failures_by_kind"] == {"test": 1}
        assert len(tracker.snapshot()["recent_failures"]) == 1


@pytest.fixture
def installation(db_session):
    record = Installation(installation_id=9101, github_user="owner")
    db_session.add(record)
    db_session.commit()
    return record


@pytest.fixture
def pr_analysis(db_session, installation):
    webhook = GitHubWebhookEvent(
        delivery_id="delivery-cleanup",
        event_type=WebhookEventType.PULL_REQUEST_OPENED,
        signature_verified=True,
        installation_id=installation.id,
        repository_full_name="owner/repo",
        raw_payload={},
    )
    db_session.add(webhook)
    db_session.commit()

    analysis = PRAnalysis(
        repository_full_name="owner/repo",
        pr_number=7,
        head_sha="feed1234beef567",
        base_branch="main",
        status=PRAnalysisStatus.PENDING,
        webhook_event_id=webhook.id,
    )
    db_session.add(analysis)
    db_session.commit()
    return analysis


@pytest.fixture
def ledger_home(monkeypatch):
    """Keep RunLedgerWriter out of the developer's real home directory."""
    home = tempfile.mkdtemp(prefix="ledger-home-")
    monkeypatch.setenv("HOME", home)
    yield home
    shutil.rmtree(home, ignore_errors=True)


def cloning_github_service(succeed=True):
    """A GitHubService stand-in whose clone creates the destination for real.

    A Mock returning True would leave dest_path nonexistent, and the leak under
    test is about which directories survive cleanup — so the clone has to put
    something on disk.
    """
    from unittest.mock import MagicMock

    service = MagicMock()

    def fake_clone(installation_id, repo_full_name, ref, dest_path, extra_refs=None):
        if not succeed:
            return False
        os.makedirs(dest_path, exist_ok=True)
        with open(os.path.join(dest_path, "module.py"), "w") as handle:
            handle.write("x = 1\n")
        return True

    service.clone_repository.side_effect = fake_clone
    return service


class TestPRClonePathIsFullyRemoved:
    """P2 #4 plus the leak: nothing under the temp root may survive a run."""

    def test_clone_then_cleanup_leaves_nothing_behind(
        self, db_session, pr_analysis, ledger_home
    ):
        """The regression test for the leaked mkdtemp root.

        _clone_repository returns `<root>/repo`. Cleanup that removes only the
        returned path leaves `<root>` on disk, which is what the old code did on
        every successful analysis.
        """
        pipeline = PRAnalysisPipeline(
            db_session=db_session, github_service=cloning_github_service()
        )
        before = pr_temp_dirs()

        from agent.run_ledger import RunLedgerWriter

        ledger = RunLedgerWriter(
            run_id="cleanup-test",
            repo_id="owner/repo",
            environment="TEST",
            initiated_by="TEST",
        )
        ledger.create_ledger()

        repo_path = asyncio.run(pipeline._clone_repository(pr_analysis, ledger))
        assert repo_path is not None
        assert os.path.exists(repo_path)

        root = os.path.dirname(repo_path)
        assert pipeline._temp_roots == [root]

        pipeline._cleanup_temp_roots()

        assert not os.path.exists(repo_path)
        assert not os.path.exists(root), "mkdtemp root survived cleanup"
        assert pr_temp_dirs() == before

    def test_failed_clone_removes_its_temp_root(self, db_session, pr_analysis, ledger_home):
        pipeline = PRAnalysisPipeline(
            db_session=db_session, github_service=cloning_github_service(succeed=False)
        )
        before = pr_temp_dirs()

        from agent.run_ledger import RunLedgerWriter

        ledger = RunLedgerWriter(
            run_id="cleanup-test-fail",
            repo_id="owner/repo",
            environment="TEST",
            initiated_by="TEST",
        )
        ledger.create_ledger()

        assert asyncio.run(pipeline._clone_repository(pr_analysis, ledger)) is None
        pipeline._cleanup_temp_roots()

        assert pr_temp_dirs() == before

    def test_full_run_leaves_no_temp_directories(
        self, db_session, pr_analysis, ledger_home
    ):
        """End to end through analyze_pr's finally, on the failure path.

        The orchestrator is made to raise so the run takes the failure path
        *after* a successful clone — the case where a temp root exists and an
        exception is in flight.
        """
        pipeline = PRAnalysisPipeline(
            db_session=db_session, github_service=cloning_github_service()
        )
        before = pr_temp_dirs()

        with patch.object(
            pipeline, "_run_orchestrator", new=AsyncMock(side_effect=RuntimeError("boom"))
        ):
            result = asyncio.run(pipeline.analyze_pr(pr_analysis_id=pr_analysis.id))

        assert result is False
        assert pr_temp_dirs() == before, "analyze_pr leaked a temp directory"

    def test_temp_root_is_registered_before_the_clone_runs(
        self, db_session, pr_analysis, ledger_home
    ):
        """A clone that raises must still leave its root recoverable.

        github_service.clone_repository is documented to return False on error,
        but it reaches subprocess and os paths that can raise; registering the
        root only after a successful clone would leak on that path.
        """
        from unittest.mock import MagicMock

        service = MagicMock()
        service.clone_repository.side_effect = RuntimeError("git blew up")
        pipeline = PRAnalysisPipeline(db_session=db_session, github_service=service)
        before = pr_temp_dirs()

        from agent.run_ledger import RunLedgerWriter

        ledger = RunLedgerWriter(
            run_id="cleanup-test-raise",
            repo_id="owner/repo",
            environment="TEST",
            initiated_by="TEST",
        )
        ledger.create_ledger()

        with pytest.raises(RuntimeError):
            asyncio.run(pipeline._clone_repository(pr_analysis, ledger))

        assert len(pipeline._temp_roots) == 1
        pipeline._cleanup_temp_roots()
        assert pr_temp_dirs() == before

    def test_cleanup_drains_the_list(self, db_session):
        """A root that cannot be removed must not be retried forever."""
        pipeline = PRAnalysisPipeline(db_session=db_session, github_service=None)
        root = tempfile.mkdtemp(prefix=PR_TEMP_PREFIX)
        pipeline._temp_roots.append(root)

        with patch("app.services.cleanup.shutil.rmtree", side_effect=OSError("busy")):
            pipeline._cleanup_temp_roots()

        assert pipeline._temp_roots == []
        assert cleanup_stats()["failures"] == 1
        shutil.rmtree(root, ignore_errors=True)


class TestV1EngineTempTracking:
    """V1AnalysisEngine.temp_dirs grew for the lifetime of the engine."""

    def test_cleanup_removes_the_directory_and_untracks_it(self):
        engine = V1AnalysisEngine()
        temp_dir = tempfile.mkdtemp(prefix="agi-analysis-")
        engine.temp_dirs.append(temp_dir)

        engine._cleanup_temp_dir(temp_dir)

        assert not os.path.exists(temp_dir)
        assert engine.temp_dirs == [], "temp_dirs kept a path that no longer exists"

    def test_repeated_analyses_do_not_accumulate_paths(self):
        """The list is what leaked here, one string per analysis."""
        engine = V1AnalysisEngine()
        for _ in range(5):
            temp_dir = tempfile.mkdtemp(prefix="agi-analysis-")
            engine.temp_dirs.append(temp_dir)
            engine._cleanup_temp_dir(temp_dir)

        assert engine.temp_dirs == []

    def test_cleanup_all_clears_tracking(self):
        engine = V1AnalysisEngine()
        dirs = [tempfile.mkdtemp(prefix="agi-analysis-") for _ in range(3)]
        engine.temp_dirs.extend(dirs)

        engine.cleanup()

        assert engine.temp_dirs == []
        assert not any(os.path.exists(path) for path in dirs)

    def test_cleanup_of_missing_dir_is_harmless(self):
        engine = V1AnalysisEngine()
        engine._cleanup_temp_dir(None)
        engine._cleanup_temp_dir("/nonexistent/xyz")
        assert cleanup_stats()["failures"] == 0


class TestCleanupMonitoringEndpoint:
    """P2 #4: the counters need somewhere an operator can actually read them."""

    def test_reports_healthy_when_nothing_has_failed(self, client):
        response = client.get("/status/cleanup")

        assert response.status_code == 200
        body = response.json()
        assert body["healthy"] is True
        assert body["cleanup"]["failures"] == 0

    def test_reports_unhealthy_after_a_cleanup_failure(self, client, tmp_tree):
        with patch("app.services.cleanup.shutil.rmtree", side_effect=OSError("busy")):
            safe_rmtree(tmp_tree, kind="pr_clone")

        body = client.get("/status/cleanup").json()

        assert body["healthy"] is False
        assert body["cleanup"]["failures"] == 1
        assert body["cleanup"]["failures_by_kind"] == {"pr_clone": 1}

    def test_leaked_paths_are_named_for_triage(self, client, tmp_tree):
        """Knowing a cleanup failed is only actionable with the path."""
        with patch("app.services.cleanup.shutil.rmtree", side_effect=OSError("busy")):
            safe_rmtree(tmp_tree, kind="pr_clone")

        body = client.get("/status/cleanup").json()
        assert body["cleanup"]["recent_failures"][0]["path"] == tmp_tree


class TestCleanupFailuresAreNeverHidden:
    """Structural guard against ignore_errors=True returning.

    `shutil.rmtree(path, ignore_errors=True)` discards the error, the path, and
    the fact that anything went wrong, which is exactly the monitoring gap P2 #4
    describes. A line-number list would rot, so this walks the AST.
    """

    SOURCES = (
        "app/services/cleanup.py",
        "app/services/pr_analysis.py",
        "app/v1_engine.py",
        "app/routers/analysis.py",
    )

    @staticmethod
    def _ignore_errors_calls(relative_path):
        import ast

        backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        tree = ast.parse(open(os.path.join(backend, relative_path)).read())

        offenders = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if name != "rmtree":
                continue
            for keyword in node.keywords:
                if keyword.arg == "ignore_errors" and getattr(
                    keyword.value, "value", False
                ) is True:
                    offenders.append(f"{relative_path}:{node.lineno}")
        return offenders

    @pytest.mark.parametrize("source", SOURCES)
    def test_no_ignore_errors_rmtree(self, source):
        offenders = self._ignore_errors_calls(source)
        assert offenders == [], (
            "rmtree(ignore_errors=True) hides cleanup failures: " + ", ".join(offenders)
        )
