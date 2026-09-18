"""Transaction safety for ReliabilityMetricsService and PRAnalysisPipeline.

Covers P1 items #2 and #3 of PRODUCTION_READINESS_AUDIT.md: 13 `commit()` calls
across the two services with no `rollback()` between them.

Why a failed commit matters. SQLAlchemy does not discard a transaction that
failed to flush; it marks it as needing rollback and raises PendingRollbackError
on *every* subsequent operation until someone rolls back:

    IntegrityError on commit -> session.query(...) -> PendingRollbackError

So one failed commit does not fail one operation, it fails every operation that
follows on that session. In PRAnalysisPipeline the session outlives the request
(github_webhooks._run_pr_analysis holds it for the whole background task), which
is what turns a single constraint violation into a dead pipeline.

These tests drive real SQLite sessions rather than mocks, because the behaviour
under test *is* the session's — a Mock would happily accept commit() and prove
nothing.
"""

import asyncio
import os
import shutil
import tempfile
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.exc import IntegrityError, PendingRollbackError

from app.models import (
    GitHubWebhookEvent,
    Installation,
    PRAnalysis,
    RepoMetrics,
    Repository,
)
from app.models.github_integration import PRAnalysisStatus, WebhookEventType
from app.services.pr_analysis import PRAnalysisPipeline
from app.services.reliability_metrics import ReliabilityMetricsService


@pytest.fixture
def installation(db_session):
    """A persisted Installation — Repository and webhook events both need one."""
    record = Installation(installation_id=9001, github_user="owner")
    db_session.add(record)
    db_session.commit()
    return record


@pytest.fixture
def repository(db_session, installation):
    """A persisted Repository, needed for RepoMetrics' foreign key."""
    repo = Repository(
        installation_id=installation.id,
        repo_name="repo",
        repo_full_name="owner/repo",
        github_repo_id=555001,
    )
    db_session.add(repo)
    db_session.commit()
    return repo


@pytest.fixture
def pr_analysis(db_session, installation):
    """A persisted PRAnalysis in PENDING, with its webhook event."""
    webhook = GitHubWebhookEvent(
        delivery_id="delivery-transaction-safety",
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
        pr_number=42,
        head_sha="abc1234def5678",
        base_branch="main",
        status=PRAnalysisStatus.PENDING,
        webhook_event_id=webhook.id,
    )
    db_session.add(analysis)
    db_session.commit()
    return analysis


@pytest.fixture
def ledger_home(monkeypatch):
    """Redirect RunLedgerWriter's ~/.agi-engineer tree into a temp dir.

    run_ledger builds its path with os.path.expanduser at __init__ time, so
    pointing HOME elsewhere keeps test ledgers out of the developer's home.
    """
    home = tempfile.mkdtemp(prefix="ledger-home-")
    monkeypatch.setenv("HOME", home)
    yield home
    shutil.rmtree(home, ignore_errors=True)


def queue_bad_row(session):
    """Queue a row that cannot be inserted, so the next commit fails for real.

    RepoMetrics.repository_id is NOT NULL, so flushing this raises IntegrityError.
    Nothing is committed here — the failure lands on whichever commit runs next,
    which is how a genuine bad write reaches a service's own commit call.
    """
    session.add(RepoMetrics(repository_id=None, reliability_score=100.0, score_grade="A"))


def poison(session):
    """Put `session` into the failed-flush state a real bad commit produces.

    After this the transaction is awaiting rollback: every operation raises
    PendingRollbackError until someone rolls back — the same state a constraint
    violation or lost connection leaves behind in production.
    """
    queue_bad_row(session)
    with pytest.raises(IntegrityError):
        session.commit()


class TestSessionPoisoningIsReal:
    """The premise: a failed commit disables the session until rollback."""

    def test_failed_commit_blocks_every_later_operation(self, db_session):
        poison(db_session)
        with pytest.raises(PendingRollbackError):
            db_session.query(RepoMetrics).count()

    def test_rollback_restores_the_session(self, db_session):
        poison(db_session)
        db_session.rollback()
        assert db_session.query(RepoMetrics).count() == 0


class TestReliabilityMetricsCommitSafety:
    """P1 #2 — reliability_metrics.py lines 70, 222, 328, 593."""

    def test_commit_helper_rolls_back_and_reraises(self, db_session):
        """The failure is reported, not swallowed, and the session survives it."""
        service = ReliabilityMetricsService(db_session=db_session)
        queue_bad_row(db_session)

        with pytest.raises(IntegrityError):
            service._commit("unit test")

        assert db_session.query(RepoMetrics).count() == 0

    def test_get_or_create_leaves_session_usable_after_failure(self, db_session, repository):
        """Line 70: a failed create must not strand the caller's session.

        The bad row is queued rather than mocked, so the service's own commit is
        the one that fails and the session really does end up awaiting rollback.
        """
        service = ReliabilityMetricsService(db_session=db_session)
        queue_bad_row(db_session)

        with pytest.raises(IntegrityError):
            service.get_or_create_repo_metrics(repository_id=repository.id)

        # Without the rollback this raises PendingRollbackError instead.
        assert db_session.query(RepoMetrics).count() == 0

    def test_successful_path_still_commits(self, db_session, repository):
        """Rollback handling must not disturb the normal path."""
        service = ReliabilityMetricsService(db_session=db_session)
        metrics = service.get_or_create_repo_metrics(repository_id=repository.id)

        assert metrics.id is not None
        assert metrics.reliability_score == 100.0
        assert db_session.query(RepoMetrics).count() == 1

    def test_get_or_create_is_idempotent(self, db_session, repository):
        service = ReliabilityMetricsService(db_session=db_session)
        first = service.get_or_create_repo_metrics(repository_id=repository.id)
        second = service.get_or_create_repo_metrics(repository_id=repository.id)

        assert first.id == second.id
        assert db_session.query(RepoMetrics).count() == 1

    def test_create_risk_snapshot_rolls_back_on_failure(self, db_session, repository):
        """Line 593: _create_risk_snapshot is called after other commits."""
        service = ReliabilityMetricsService(db_session=db_session)
        metrics = service.get_or_create_repo_metrics(repository_id=repository.id)
        queue_bad_row(db_session)

        with pytest.raises(IntegrityError):
            service._create_risk_snapshot(
                repo_metrics_id=metrics.id,
                snapshot_type="pr_analysis",
                snapshot_reason="unit test",
                critical_risks=1,
                high_risks=0,
                medium_risks=0,
                low_risks=0,
                reliability_score=90.0,
            )

        assert db_session.query(RepoMetrics).count() == 1


class TestPRAnalysisCommitSafety:
    """P1 #3 — pr_analysis.py lines 88, 102, 126, 138, 149, 165, 315, 437, 595."""

    def test_commit_helper_rolls_back_and_reraises(self, db_session):
        pipeline = PRAnalysisPipeline(db_session=db_session)
        queue_bad_row(db_session)

        with pytest.raises(IntegrityError):
            pipeline._commit("unit test")

        assert db_session.query(RepoMetrics).count() == 0

    def test_failed_analysis_marks_record_failed(self, db_session, pr_analysis, ledger_home):
        """The ordinary failure path still records FAILED and seals the ledger."""
        pipeline = PRAnalysisPipeline(db_session=db_session)

        with patch.object(pipeline, "_clone_repository", new=AsyncMock(return_value=None)):
            result = asyncio.run(pipeline.analyze_pr(pr_analysis_id=pr_analysis.id))

        assert result is False
        db_session.refresh(pr_analysis)
        assert pr_analysis.status == PRAnalysisStatus.FAILED
        assert "clone" in (pr_analysis.analysis_error or "").lower()
        assert pr_analysis.completed_at is not None

    def test_failure_handler_survives_a_poisoned_session(self, db_session, pr_analysis, ledger_home):
        """The regression this task exists for.

        When the pipeline fails *because* a commit failed, the session is already
        awaiting rollback. The handler at line 165 then commits into that dead
        session, so it raises too — the record is never marked FAILED, the ledger
        is never sealed, and the caller sees the secondary error rather than the
        real cause.
        """
        pipeline = PRAnalysisPipeline(db_session=db_session)

        async def poisoning_clone(*args, **kwargs):
            poison(db_session)
            raise RuntimeError("clone exploded after a bad commit")

        with patch.object(pipeline, "_clone_repository", new=poisoning_clone):
            result = asyncio.run(pipeline.analyze_pr(pr_analysis_id=pr_analysis.id))

        assert result is False
        db_session.refresh(pr_analysis)
        assert pr_analysis.status == PRAnalysisStatus.FAILED
        assert "clone exploded" in (pr_analysis.analysis_error or "")

    def test_failure_handler_reports_the_original_cause(self, db_session, pr_analysis, ledger_home):
        """The recorded error is the real failure, not the rollback fallout."""
        pipeline = PRAnalysisPipeline(db_session=db_session)

        async def poisoning_clone(*args, **kwargs):
            poison(db_session)
            raise RuntimeError("original cause")

        with patch.object(pipeline, "_clone_repository", new=poisoning_clone):
            asyncio.run(pipeline.analyze_pr(pr_analysis_id=pr_analysis.id))

        db_session.refresh(pr_analysis)
        assert pr_analysis.analysis_error == "original cause"
        assert "PendingRollbackError" not in (pr_analysis.analysis_error or "")

    def test_session_is_usable_after_a_failed_analysis(self, db_session, pr_analysis, ledger_home):
        """A dead session would break the next PR, not just this one."""
        pipeline = PRAnalysisPipeline(db_session=db_session)

        async def poisoning_clone(*args, **kwargs):
            poison(db_session)
            raise RuntimeError("boom")

        with patch.object(pipeline, "_clone_repository", new=poisoning_clone):
            asyncio.run(pipeline.analyze_pr(pr_analysis_id=pr_analysis.id))

        assert db_session.query(PRAnalysis).count() == 1

    def test_missing_record_returns_false(self, db_session):
        """Guard clause before any commit — unchanged by this work."""
        pipeline = PRAnalysisPipeline(db_session=db_session)
        assert asyncio.run(pipeline.analyze_pr(pr_analysis_id=999999)) is False


class TestLedgerIsAlwaysSealed:
    """PRODUCTION_READINESS_AUDIT.md Area 6 records "Always seals
    (COMPLETE/INCOMPLETE)" as a held invariant. It did not hold: the FAILED
    commit sat before `ledger.seal("INCOMPLETE")` with nothing between them, so
    any error from that commit skipped the seal and left the run looking as
    though it were still in flight.
    """

    @staticmethod
    def _run_failing_analysis(pipeline, analysis_id, break_commit):
        """Drive analyze_pr into its failure path with RunLedgerWriter mocked.

        `break_commit` breaks commits only from the third call onward. The first
        two (IN_PROGRESS, then the ledger run id) run before the try block, so
        breaking them would propagate out of analyze_pr before a ledger exists
        — a different path, with nothing to seal.
        """
        session = pipeline.db_session
        real_commit = session.commit
        calls = {"count": 0}

        def flaky_commit():
            calls["count"] += 1
            if calls["count"] <= 2:
                return real_commit()
            raise IntegrityError("stmt", {}, Exception())

        with patch("app.services.pr_analysis.RunLedgerWriter") as ledger_class:
            ledger = ledger_class.return_value
            with patch.object(
                pipeline, "_clone_repository", new=AsyncMock(return_value=None)
            ):
                if break_commit:
                    with patch.object(session, "commit", new=flaky_commit):
                        result = asyncio.run(pipeline.analyze_pr(pr_analysis_id=analysis_id))
                else:
                    result = asyncio.run(pipeline.analyze_pr(pr_analysis_id=analysis_id))
        return result, ledger

    def test_ledger_seals_incomplete_on_failure(self, db_session, pr_analysis):
        pipeline = PRAnalysisPipeline(db_session=db_session)
        result, ledger = self._run_failing_analysis(pipeline, pr_analysis.id, break_commit=False)

        assert result is False
        ledger.seal.assert_called_once_with("INCOMPLETE")

    def test_ledger_seals_even_when_the_failed_status_cannot_be_written(
        self, db_session, pr_analysis
    ):
        """Every commit is broken, so recording FAILED cannot succeed.

        The run must still be sealed and still report False rather than raising.
        """
        pipeline = PRAnalysisPipeline(db_session=db_session)
        result, ledger = self._run_failing_analysis(pipeline, pr_analysis.id, break_commit=True)

        assert result is False
        ledger.seal.assert_called_once_with("INCOMPLETE")


class TestNoBareCommitsRemain:
    """Structural guard: every commit in these services goes through _commit.

    A line-number list would rot on the next edit, so this walks the AST instead
    and fails on any `self.db_session.commit()` that reappears outside the helper.
    """

    SERVICES = (
        "app/services/reliability_metrics.py",
        "app/services/pr_analysis.py",
    )

    @staticmethod
    def _bare_commits(relative_path):
        import ast

        backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(backend, relative_path)
        tree = ast.parse(open(path).read())

        offenders = []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name == "_commit":
                continue  # the helper is the one place allowed to commit
            for call in ast.walk(node):
                if (
                    isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Attribute)
                    and call.func.attr == "commit"
                ):
                    offenders.append(f"{relative_path}:{call.lineno} in {node.name}()")
        return offenders

    @pytest.mark.parametrize("service", SERVICES)
    def test_service_has_no_unguarded_commit(self, service):
        offenders = self._bare_commits(service)
        assert offenders == [], "commit() outside _commit(): " + ", ".join(offenders)

    @pytest.mark.parametrize("service", SERVICES)
    def test_service_defines_the_commit_helper(self, service):
        import ast

        backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        tree = ast.parse(open(os.path.join(backend, service)).read())
        helpers = [
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "_commit"
        ]
        assert helpers == ["_commit"]
