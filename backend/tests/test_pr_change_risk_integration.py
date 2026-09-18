"""Phase 20 integration: the real PR pipeline produces a ChangeRiskReport."""

import asyncio
import os
import subprocess
from typing import List, Optional
from unittest.mock import AsyncMock, patch

import pytest

from agent.intelligence.proposal import (
    AffectedFile,
    BugClass,
    FixStrategy,
    IntelligenceProposal,
    Severity,
)
from agent.run_ledger import read_events
from app.models import (
    AnalysisResult,
    AnalysisRun,
    CodeFix,
    GitHubWebhookEvent,
    Installation,
    PRAnalysis,
    Repository,
)
from app.models.analysis_run import RunStatus
from app.models.code_fix import FixStatus
from app.models.github_integration import PRAnalysisStatus, WebhookEventType
from app.intelligence.code_graph.code_graph_builder import CodeGraphBuilder
from app.services.change_impact_service import ChangeImpactService
from app.services.finding_context import build_finding_contexts as real_build_finding_contexts
from app.services.github_service import GitHubService
from app.services.pr_analysis import PRAnalysisPipeline
from app.services.verification_engine import VerificationEngine

def _git(repo: str, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", repo, *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def _init_repo(path: str) -> None:
    subprocess.run(["git", "init", "--quiet", "-b", "main", path], check=True)
    _git(path, "config", "user.email", "test@example.invalid")
    _git(path, "config", "user.name", "Phase 20 Test")
    _git(path, "config", "commit.gpgsign", "false")


def _write(repo: str, rel_path: str, body: str) -> None:
    full = os.path.join(repo, rel_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as fh:
        fh.write(body)


def _commit(repo: str, message: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


USER_REPO_BASE = '''
class UserRepository:
    """Owns user lookups."""

    def get_user(self, user_id):
        return {"id": user_id}
'''

USER_REPO_HEAD = '''
class UserRepository:
    """Owns user lookups."""

    def get_user(self, user_id):
        record = {"id": user_id}
        return record["id"] and record
'''

AUTH_SERVICE = '''
from user_repo import UserRepository


class AuthorizationService:
    def __init__(self):
        self.repo = UserRepository()

    def authorize(self, user_id):
        user = self.repo.get_user(user_id)
        return user is not None
'''

PAYMENTS = '''
from auth_service import AuthorizationService


class PaymentService:
    def __init__(self):
        self.auth = AuthorizationService()

    def process_payment(self, user_id, amount):
        if not self.auth.authorize(user_id):
            raise PermissionError("not authorized")
        return {"charged": amount}
'''

API = '''
from payments import PaymentService

app = None


@app.post("/payments")
def create_payment(user_id, amount):
    return PaymentService().process_payment(user_id, amount)
'''

REPORTING_BASE = '''
class ReportBuilder:
    """Unrelated to the payment chain."""

    def build(self, rows):
        return len(rows)
'''

REPORTING_HEAD = '''
class ReportBuilder:
    """Unrelated to the payment chain. Docstring extended."""

    def build(self, rows):
        return len(rows)
'''

GET_USER_LINES = "5-7"
AUTHORIZE_LINES = "9-11"
PROCESS_PAYMENT_LINES = "9-12"
REPORT_BUILD_LINES = "5-6"

class Revisions:
    def __init__(self, remote_root: str, repo_path: str) -> None:
        self.remote_root = remote_root
        self.repo_path = repo_path
        self.base: str = ""
        self.chain_head: str = ""
        self.unrelated_head: str = ""


@pytest.fixture
def revisions(tmp_path) -> Revisions:
    remote_root = str(tmp_path / "remotes")
    repo_path = os.path.join(remote_root, "owner", "repo")
    os.makedirs(repo_path)
    _init_repo(repo_path)

    _write(repo_path, "user_repo.py", USER_REPO_BASE)
    _write(repo_path, "auth_service.py", AUTH_SERVICE)
    _write(repo_path, "payments.py", PAYMENTS)
    _write(repo_path, "api.py", API)
    _write(repo_path, "reporting.py", REPORTING_BASE)

    revs = Revisions(remote_root, repo_path)
    revs.base = _commit(repo_path, "base")

    _git(repo_path, "checkout", "--quiet", "-b", "chain")
    _write(repo_path, "user_repo.py", USER_REPO_HEAD)
    revs.chain_head = _commit(repo_path, "touch get_user")

    _git(repo_path, "checkout", "--quiet", "main")
    _git(repo_path, "checkout", "--quiet", "-b", "unrelated")
    _write(repo_path, "reporting.py", REPORTING_HEAD)
    revs.unrelated_head = _commit(repo_path, "extend ReportBuilder docstring")

    _git(repo_path, "checkout", "--quiet", "main")
    return revs


@pytest.fixture
def installation(db_session):
    record = Installation(installation_id=42042, github_user="owner")
    db_session.add(record)
    db_session.commit()
    return record

_PR_NUMBER = 31


def _make_pr_analysis(
    db_session,
    installation,
    head_sha: str,
    base_sha: Optional[str],
    *,
    base_branch: str = "main",
    delivery_id: str = "phase20-delivery",
    github_repo_id: Optional[int] = 606060,
) -> PRAnalysis:
    payload = {"pull_request": {"base": {"ref": base_branch}}}
    if base_sha is not None:
        payload["pull_request"]["base"]["sha"] = base_sha

    webhook = GitHubWebhookEvent(
        delivery_id=delivery_id,
        event_type=WebhookEventType.PULL_REQUEST_OPENED,
        signature_verified=True,
        installation_id=installation.id,
        repository_full_name="owner/repo",
        repository_id=github_repo_id,
        pr_number=_PR_NUMBER,
        pr_head_sha=head_sha,
        pr_base_branch=base_branch,
        pr_head_branch="feature",
        raw_payload=payload,
    )
    db_session.add(webhook)
    db_session.commit()

    analysis = PRAnalysis(
        repository_full_name="owner/repo",
        pr_number=_PR_NUMBER,
        head_sha=head_sha,
        base_branch=base_branch,
        status=PRAnalysisStatus.PENDING,
        webhook_event_id=webhook.id,
    )
    db_session.add(analysis)
    db_session.commit()
    return analysis


def _ledger_run_id(head_sha: str) -> str:
    return f"pr-owner-repo-{_PR_NUMBER}-{head_sha[:7]}"

class _RecordingGitHubService(GitHubService):
    def __init__(self, remote_root: str) -> None:
        super().__init__()
        self.git_remote_base_url = remote_root
        self.token: Optional[str] = "test-token"
        self.comments: List[str] = []
        self.updated_comments: List[dict] = []
        self.checks: List[dict] = []
        self.update_succeeds = True

    def get_installation_token(self, installation_id: int) -> Optional[str]:
        return self.token

    def post_pr_comment(self, **kwargs) -> int:
        self.comments.append(kwargs.get("comment_body", ""))
        return 900 + len(self.comments)

    def update_pr_comment(self, **kwargs) -> bool:
        if not self.update_succeeds:
            return False
        self.updated_comments.append(kwargs)
        return True

    def create_check_run(self, **kwargs) -> int:
        self.checks.append(kwargs)
        return 800 + len(self.checks)


@pytest.fixture
def github_service(revisions) -> _RecordingGitHubService:
    return _RecordingGitHubService(revisions.remote_root)


@pytest.fixture
def ledger_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    return home


@pytest.fixture
def pipeline(db_session, github_service, ledger_home) -> PRAnalysisPipeline:
    return PRAnalysisPipeline(db_session=db_session, github_service=github_service)

def _proposal(
    path: str,
    line_range: str,
    severity: Severity = Severity.HIGH,
    bug_class: BugClass = BugClass.CRASH_RISKS,
    statement: str = "Unguarded dict access can raise",
) -> IntelligenceProposal:
    proposal = IntelligenceProposal()
    proposal.bug_class = bug_class
    proposal.severity = severity
    proposal.problem_statement = statement
    proposal.risk_explanation = "Raises KeyError when the record is missing."
    proposal.root_cause_hypothesis = "No guard was added when the dict was introduced."
    proposal.analyzer_name = "CrashRiskAnalyzer"
    proposal.confidence_level = 80
    proposal.affected_files = [
        AffectedFile(path=path, line_range=line_range, severity=severity)
    ]
    proposal.suggested_strategies = [
        FixStrategy(
            name="Guard the access",
            description="Use .get() with a default.",
            prerequisite_actions=["Confirm callers tolerate None"],
            assumptions=["The key is genuinely optional"],
        ),
        FixStrategy(
            name="Validate upstream",
            description="Reject records without the key before this point.",
            prerequisite_actions=["Locate the write path"],
            assumptions=["Upstream can reject"],
        ),
    ]
    proposal.refresh_derived_proposal_id()
    return proposal


def _run(pipeline: PRAnalysisPipeline, pr_analysis_id: int) -> bool:
    return asyncio.run(
        pipeline.analyze_pr(pr_analysis_id=pr_analysis_id, user_plan="team")
    )


def _results_for_pr(db_session, pr: PRAnalysis) -> List[AnalysisResult]:
    db_session.refresh(pr)
    assert pr.analysis_run_id is not None
    return (
        db_session.query(AnalysisResult)
        .filter_by(run_id=pr.analysis_run_id)
        .order_by(AnalysisResult.id)
        .all()
    )


def _pinned(proposals: List[IntelligenceProposal]):
    return patch.object(
        PRAnalysisPipeline,
        "_run_orchestrator",
        new=AsyncMock(return_value=proposals),
    )

class TestFindingInsideBlastRadius:
    def test_direct_finding_drives_risk_level_and_is_named_as_evidence(
        self, db_session, installation, revisions, pipeline
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.chain_head, revisions.base
        )

        with _pinned([_proposal("user_repo.py", GET_USER_LINES, Severity.CRITICAL)]):
            assert _run(pipeline, pr.id) is True

        db_session.refresh(pr)
        assert pr.status == PRAnalysisStatus.COMPLETED
        assert pr.change_risk_error is None
        assert pr.change_risk_level == "critical"
        assert pr.change_risk_recommendation == "requires_human_review"

        report = pr.change_risk_report
        assert report["findings_evaluated"] == 1
        assert report["findings_in_blast_radius"] == 1
        assert report["findings_outside_blast_radius"] == 0
        assert report["findings_unresolved_location"] == 0

        impacts = report["impact"]["finding_impacts"]
        assert len(impacts) == 1
        assert impacts[0]["relation"] == "direct"
        assert impacts[0]["resolved_node_id"] == "user_repo.py::UserRepository.get_user"

        levels = {f["kind"]: f["level"] for f in report["risk_factors"]}
        assert levels["reliability_finding_in_blast_radius"] == "critical"

        decision = report["decision"]
        assert decision["risk_level"] == "critical"
        assert decision["score"] == 100
        assert decision["human_review_required"] is True
        assert decision["change_relationships"] == ["direct"]
        assert decision["supporting_findings"][0]["symbol_node_id"] == (
            "user_repo.py::UserRepository.get_user"
        )
        verification = report["verification"]
        assert verification["state"] == "blocked"
        assert verification["findings_before"]
        assert verification["findings_after"]
        assert verification["baseline_status"] == "COMPLETED"
        assert verification["comparison_status"] == "COMPLETED"
        assert verification["new_findings"]

    def test_same_critical_finding_outside_the_diff_scores_lower(
        self, db_session, installation, revisions, pipeline
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.chain_head, revisions.base
        )

        with _pinned([_proposal("reporting.py", REPORT_BUILD_LINES, Severity.CRITICAL)]):
            assert _run(pipeline, pr.id) is True

        db_session.refresh(pr)
        report = pr.change_risk_report
        assert report["findings_in_blast_radius"] == 0
        assert report["findings_outside_blast_radius"] == 1
        assert pr.change_risk_level != "critical"
        assert "reliability_finding_in_blast_radius" not in {
            f["kind"] for f in report["risk_factors"]
        }

class TestFindingOutsideBlastRadius:
    def test_outside_finding_is_reported_rather_than_dropped(
        self, db_session, installation, revisions, pipeline
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.chain_head, revisions.base
        )

        with _pinned([_proposal("reporting.py", REPORT_BUILD_LINES, Severity.HIGH)]):
            assert _run(pipeline, pr.id) is True

        db_session.refresh(pr)
        report = pr.change_risk_report
        assert report["findings_evaluated"] == 1
        assert report["findings_outside_blast_radius"] == 1
        assert any("outside the blast radius" in c for c in report["caveats"])

        impacts = report["impact"]["finding_impacts"]
        assert impacts[0]["relation"] == "outside"
        assert impacts[0]["resolved_node_id"] == "reporting.py::ReportBuilder.build"


class TestMultiHopImpact:
    def test_caller_and_downstream_findings_both_land_inside_the_radius(
        self, db_session, installation, revisions, pipeline
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.chain_head, revisions.base
        )
        one_hop = _proposal("auth_service.py", AUTHORIZE_LINES, Severity.MEDIUM)
        two_hop = _proposal(
            "payments.py",
            PROCESS_PAYMENT_LINES,
            Severity.MEDIUM,
            statement="Payment path can raise on an unauthorized user",
        )

        with _pinned([one_hop, two_hop]):
            assert _run(pipeline, pr.id) is True

        db_session.refresh(pr)
        report = pr.change_risk_report
        assert report["findings_in_blast_radius"] == 2

        resolved = {
            i["resolved_node_id"]: i["relation"]
            for i in report["impact"]["finding_impacts"]
        }
        assert resolved["auth_service.py::AuthorizationService.authorize"] in (
            "caller",
            "downstream",
        )
        assert resolved["payments.py::PaymentService.process_payment"] in (
            "caller",
            "downstream",
        )

        impact = report["impact"]
        assert impact["changed_files"] == ["user_repo.py"]
        assert report["blast_radius_size"] > len(impact["changed_symbols"])

    def test_entrypoint_three_hops_from_the_diff_is_reported(
        self, db_session, installation, revisions, pipeline
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.chain_head, revisions.base
        )

        with _pinned([]):
            assert _run(pipeline, pr.id) is True

        db_session.refresh(pr)
        report = pr.change_risk_report
        assert "api.py::create_payment" in report["affected_entrypoints"]
        assert "entrypoint_reachable" in {f["kind"] for f in report["risk_factors"]}
        assert any(
            t["kind"] == "entrypoint" and t["location"] == "api.py::create_payment"
            for t in report["review_targets"]
        )

    def test_unrelated_change_reaches_no_entrypoint(
        self, db_session, installation, revisions, pipeline
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.unrelated_head, revisions.base
        )

        with _pinned([]):
            assert _run(pipeline, pr.id) is True

        db_session.refresh(pr)
        assert pr.change_risk_report["affected_entrypoints"] == []


class TestLowRiskChange:
    def test_unrelated_docstring_edit_needs_no_review(
        self, db_session, installation, revisions, pipeline
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.unrelated_head, revisions.base
        )

        with _pinned([]):
            assert _run(pipeline, pr.id) is True

        db_session.refresh(pr)
        report = pr.change_risk_report
        assert report["impact"]["changed_files"] == ["reporting.py"]
        assert report["findings_in_blast_radius"] == 0
        assert report["affected_entrypoints"] == []
        assert pr.change_risk_level == "low"
        assert pr.change_risk_recommendation == "no_review_required"
        assert {f["kind"] for f in report["risk_factors"]} == {
            "code_changed_no_known_risk"
        }

class TestHighRiskChange:
    def test_high_severity_finding_in_the_radius_requires_human_review(
        self, db_session, installation, revisions, pipeline
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.chain_head, revisions.base
        )

        with _pinned([_proposal("user_repo.py", GET_USER_LINES, Severity.HIGH)]):
            assert _run(pipeline, pr.id) is True

        db_session.refresh(pr)
        assert pr.change_risk_level == "high"
        assert pr.change_risk_recommendation == "requires_human_review"

    def test_medium_finding_escalates_when_an_entrypoint_reaches_it(
        self, db_session, installation, revisions, pipeline
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.chain_head, revisions.base
        )

        with _pinned([_proposal("user_repo.py", GET_USER_LINES, Severity.MEDIUM)]):
            assert _run(pipeline, pr.id) is True

        db_session.refresh(pr)
        report = pr.change_risk_report
        assert pr.change_risk_level == "high"
        levels = {f["kind"]: f["level"] for f in report["risk_factors"]}
        assert levels["reliability_finding_in_blast_radius"] == "medium"
        assert levels["finding_reachable_from_entrypoint"] == "high"


class TestUnresolvedFinding:
    def test_unmappable_location_in_a_changed_file_is_reported_as_unknown(
        self, db_session, installation, revisions, pipeline
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.chain_head, revisions.base
        )

        with _pinned([_proposal("user_repo.py", "900-905", Severity.CRITICAL)]):
            assert _run(pipeline, pr.id) is True

        db_session.refresh(pr)
        report = pr.change_risk_report
        assert report["findings_in_blast_radius"] == 0
        assert report["findings_outside_blast_radius"] == 0
        assert report["findings_unresolved_location"] == 1

        impacts = report["impact"]["finding_impacts"]
        assert impacts[0]["relation"] == "unresolved"
        assert impacts[0]["resolved_node_id"] == ""
        assert impacts[0]["reason"]

        levels = {f["kind"]: f["level"] for f in report["risk_factors"]}
        assert levels["unresolved_finding_location_in_changed_file"] == "medium"
        assert "reliability_finding_in_blast_radius" not in levels
        assert any(t["kind"] == "unresolved_location" for t in report["review_targets"])

    def test_unknown_file_is_unresolved_without_a_changed_file_floor(
        self, db_session, installation, revisions, pipeline
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.chain_head, revisions.base
        )

        with _pinned([_proposal("does/not/exist.py", "1-5", Severity.CRITICAL)]):
            assert _run(pipeline, pr.id) is True

        db_session.refresh(pr)
        report = pr.change_risk_report
        assert report["findings_unresolved_location"] == 1
        assert "unresolved_finding_location_in_changed_file" not in {
            f["kind"] for f in report["risk_factors"]
        }


class TestFindingContextIntegration:
    def test_reuses_one_graph_and_one_impact_calculation_for_context(
        self, db_session, installation, revisions, pipeline
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.chain_head, revisions.base
        )
        seen = {
            "graph_builds": 0,
            "impact_calculations": 0,
            "context_calls": 0,
            "verification_calls": 0,
        }

        real_graph_build = CodeGraphBuilder.build_graph
        real_impact_calculation = ChangeImpactService.compute_change_impact_with_graph

        def counted_graph_build(builder, repo_path):
            seen["graph_builds"] += 1
            return real_graph_build(builder, repo_path)

        def counted_impact_calculation(service, *args, **kwargs):
            seen["impact_calculations"] += 1
            analysis = real_impact_calculation(service, *args, **kwargs)
            seen["analysis"] = analysis
            return analysis

        def captured_context(findings, **kwargs):
            seen["context_calls"] += 1
            seen["context_graph"] = kwargs.get("graph")
            seen["context_impact"] = kwargs.get("impact")
            seen["context_repo_root"] = kwargs.get("repo_root")
            return real_build_finding_contexts(findings, **kwargs)

        real_verification = VerificationEngine.assess

        def captured_verification(engine, impact, contexts, risk, evidence=None):
            seen["verification_calls"] += 1
            seen["verification_impact"] = impact
            seen["verification_contexts"] = contexts
            seen["verification_evidence"] = evidence
            return real_verification(engine, impact, contexts, risk, evidence)

        with _pinned([_proposal("user_repo.py", GET_USER_LINES)]), patch.object(
            CodeGraphBuilder,
            "build_graph",
            new=counted_graph_build,
        ), patch.object(
            ChangeImpactService,
            "compute_change_impact_with_graph",
            new=counted_impact_calculation,
        ), patch(
            "app.services.pr_analysis.build_finding_contexts",
            new=captured_context,
        ), patch.object(
            VerificationEngine,
            "assess",
            new=captured_verification,
        ):
            assert _run(pipeline, pr.id) is True

        analysis = seen["analysis"]
        assert seen["graph_builds"] == 1
        assert seen["impact_calculations"] == 1
        assert seen["context_calls"] == 1
        assert seen["context_graph"] is analysis.graph
        assert seen["context_impact"] is analysis.report
        assert seen["context_repo_root"].endswith("/repo")
        assert seen["verification_calls"] == 1
        assert seen["verification_impact"] is analysis.report
        assert seen["verification_evidence"].findings_after is seen["verification_contexts"]

    def test_changed_symbol_finding_is_persisted_with_direct_evidence(
        self, db_session, installation, revisions, pipeline
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.chain_head, revisions.base
        )

        with _pinned([_proposal("user_repo.py", GET_USER_LINES, Severity.HIGH)]):
            assert _run(pipeline, pr.id) is True

        results = _results_for_pr(db_session, pr)
        assert len(results) == 1
        result = results[0]
        context = result.finding_context
        assert result.file_path == "user_repo.py"
        assert result.line_number == 5
        assert result.severity == "high"
        assert context["symbol"] == "get_user"
        assert context["symbol_node_id"] == "user_repo.py::UserRepository.get_user"
        assert context["caller_count"] == 1
        assert context["downstream_count"] > 0
        assert context["change_relation"] == "direct"
        assert context["production_reachable"] is None
        assert context["file_class"] == "application"
        assert context["relevance"] == "actionable"

    def test_affected_caller_finding_gets_caller_relationship(
        self, db_session, installation, revisions, pipeline
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.chain_head, revisions.base
        )

        with _pinned([_proposal("auth_service.py", AUTHORIZE_LINES, Severity.MEDIUM)]):
            assert _run(pipeline, pr.id) is True

        context = _results_for_pr(db_session, pr)[0].finding_context
        assert context["symbol"] == "authorize"
        assert context["change_relation"] == "caller"
        assert context["caller_count"] == 1

    def test_unrelated_finding_remains_outside_the_change(
        self, db_session, installation, revisions, pipeline
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.chain_head, revisions.base
        )

        with _pinned([_proposal("reporting.py", REPORT_BUILD_LINES, Severity.HIGH)]):
            assert _run(pipeline, pr.id) is True

        context = _results_for_pr(db_session, pr)[0].finding_context
        assert context["symbol"] == "build"
        assert context["change_relation"] == "outside"

    def test_missing_graph_and_impact_leave_evidence_fields_unknown(
        self, db_session, installation, revisions, pipeline
    ):
        pr = _make_pr_analysis(
            db_session,
            installation,
            revisions.chain_head,
            None,
            base_branch="",
        )

        with _pinned([_proposal("user_repo.py", GET_USER_LINES, Severity.HIGH)]):
            assert _run(pipeline, pr.id) is True

        context = _results_for_pr(db_session, pr)[0].finding_context
        assert context["symbol"] is None
        assert context["symbol_node_id"] is None
        assert context["caller_count"] is None
        assert context["downstream_count"] is None
        assert context["change_relation"] is None
        assert context["production_reachable"] is None

    def test_context_adds_no_duplicate_results_and_correlates_existing_findings(
        self, db_session, installation, revisions, pipeline
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.chain_head, revisions.base
        )
        first = _proposal(
            "user_repo.py",
            "5-6",
            Severity.HIGH,
            statement="First unsafe access in the changed lookup",
        )
        second = _proposal(
            "user_repo.py",
            "6-7",
            Severity.HIGH,
            statement="Second unsafe access in the changed lookup",
        )

        with _pinned([first, second]):
            assert _run(pipeline, pr.id) is True

        results = _results_for_pr(db_session, pr)
        assert len(results) == 2
        contexts = [result.finding_context for result in results]
        assert len({context["finding_ref"] for context in contexts}) == 2
        assert {context["correlated_count"] for context in contexts} == {2}
        correlation_ids = {context["correlation_id"] for context in contexts}
        assert len(correlation_ids) == 1
        assert None not in correlation_ids


class TestFailedAnalysisPath:
    def test_clone_failure_fails_the_run_and_stores_no_risk_report(
        self, db_session, installation, revisions, pipeline, github_service
    ):
        github_service.token = None
        pr = _make_pr_analysis(
            db_session, installation, revisions.chain_head, revisions.base
        )

        with _pinned([_proposal("user_repo.py", GET_USER_LINES, Severity.CRITICAL)]):
            assert _run(pipeline, pr.id) is False

        db_session.refresh(pr)
        assert pr.status == PRAnalysisStatus.FAILED
        assert "clone" in (pr.analysis_error or "").lower()
        assert pr.change_risk_level is None
        assert pr.change_risk_report is None
        assert pr.change_risk_hash is None

        events = read_events(_ledger_run_id(revisions.chain_head))
        types = [e["event_type"] for e in events]
        assert "CHANGE_RISK_ASSESSED" not in types

    def test_missing_base_revision_records_why_and_does_not_fail_the_run(
        self, db_session, installation, revisions, pipeline
    ):
        pr = _make_pr_analysis(
            db_session,
            installation,
            revisions.chain_head,
            None,
            base_branch="",
        )

        with _pinned([_proposal("user_repo.py", GET_USER_LINES, Severity.HIGH)]):
            assert _run(pipeline, pr.id) is True

        db_session.refresh(pr)
        assert pr.status == PRAnalysisStatus.COMPLETED
        assert pr.change_risk_report is None
        assert pr.change_risk_level is None
        assert "no base revision" in pr.change_risk_error

        events = read_events(_ledger_run_id(revisions.chain_head))
        assert "CHANGE_RISK_UNAVAILABLE" in [e["event_type"] for e in events]

    def test_assessment_exception_records_why_and_does_not_fail_the_run(
        self, db_session, installation, revisions, pipeline
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.chain_head, revisions.base
        )

        with _pinned([]), patch(
            "app.services.pr_analysis.ChangeRiskService.assess",
            side_effect=RuntimeError("graph build exploded"),
        ):
            assert _run(pipeline, pr.id) is True

        db_session.refresh(pr)
        assert pr.status == PRAnalysisStatus.COMPLETED
        assert pr.change_risk_report is None
        assert "graph build exploded" in pr.change_risk_error

    def test_unresolvable_base_revision_is_recorded_not_raised(
        self, db_session, installation, revisions, pipeline
    ):
        pr = _make_pr_analysis(
            db_session,
            installation,
            revisions.chain_head,
            "0" * 40,
        )

        with _pinned([]):
            assert _run(pipeline, pr.id) is True

        db_session.refresh(pr)
        assert pr.status == PRAnalysisStatus.COMPLETED
        assert pr.change_risk_report is None
        assert pr.change_risk_error

class TestPersistenceAndLedger:
    def test_repaired_boundaries_persist_run_results_and_fixes(
        self, db_session, installation, revisions, pipeline
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.chain_head, revisions.base
        )

        with _pinned([_proposal("user_repo.py", GET_USER_LINES, Severity.HIGH)]):
            assert _run(pipeline, pr.id) is True

        db_session.refresh(pr)
        assert pr.analysis_run_id is not None

        run = db_session.query(AnalysisRun).filter_by(id=pr.analysis_run_id).one()
        assert run.status == RunStatus.COMPLETED
        assert run.github_event == "pull_request"
        assert run.github_commit_sha == revisions.chain_head
        assert run.pull_request_number == _PR_NUMBER

        repository = db_session.query(Repository).filter_by(id=run.repository_id).one()
        assert repository.repo_full_name == "owner/repo"
        assert repository.github_repo_id == 606060

        results = db_session.query(AnalysisResult).filter_by(run_id=run.id).all()
        assert len(results) == 1
        assert results[0].file_path == "user_repo.py"
        assert results[0].line_number == 5
        assert results[0].severity == "high"

        fixes = db_session.query(CodeFix).filter_by(result_id=results[0].id).all()
        assert fixes
        assert all(f.status == FixStatus.PROPOSED for f in fixes)
        assert pr.fix_candidates_count == len(fixes)

    def test_ledger_records_impact_then_risk(
        self, db_session, installation, revisions, pipeline
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.chain_head, revisions.base
        )

        with _pinned([_proposal("user_repo.py", GET_USER_LINES, Severity.HIGH)]):
            assert _run(pipeline, pr.id) is True

        db_session.refresh(pr)
        events = read_events(pr.ledger_run_id)
        types = [e["event_type"] for e in events]
        assert types.index("CHANGE_IMPACT_ANALYZED") < types.index(
            "CHANGE_RISK_ASSESSED"
        )

        risk_event = next(e for e in events if e["event_type"] == "CHANGE_RISK_ASSESSED")
        assert risk_event["payload_ref"] == pr.change_risk_hash
        assert risk_event["phase"] == "PHASE_20"

    def test_reused_repository_row_is_not_duplicated(
        self, db_session, installation, revisions, pipeline
    ):
        first = _make_pr_analysis(
            db_session, installation, revisions.chain_head, revisions.base
        )
        second = _make_pr_analysis(
            db_session,
            installation,
            revisions.unrelated_head,
            revisions.base,
            delivery_id="phase20-delivery-2",
        )

        with _pinned([]):
            assert _run(pipeline, first.id) is True
            assert _run(pipeline, second.id) is True

        assert db_session.query(Repository).count() == 1

class TestDeterminism:
    def test_two_runs_of_the_same_pr_produce_the_same_evidence_hash(
        self, db_session, installation, revisions, pipeline
    ):
        finding = _proposal("user_repo.py", GET_USER_LINES, Severity.HIGH)
        first = _make_pr_analysis(
            db_session, installation, revisions.chain_head, revisions.base
        )
        second = _make_pr_analysis(
            db_session,
            installation,
            revisions.chain_head,
            revisions.base,
            delivery_id="phase20-delivery-repeat",
        )

        with _pinned([finding]):
            assert _run(pipeline, first.id) is True
            assert _run(pipeline, second.id) is True

        db_session.refresh(first)
        db_session.refresh(second)
        assert first.change_risk_hash == second.change_risk_hash
        assert first.change_risk_report == second.change_risk_report

    def test_a_different_finding_location_changes_the_hash(
        self, db_session, installation, revisions, pipeline
    ):
        inside = _make_pr_analysis(
            db_session, installation, revisions.chain_head, revisions.base
        )
        outside = _make_pr_analysis(
            db_session,
            installation,
            revisions.chain_head,
            revisions.base,
            delivery_id="phase20-delivery-outside",
        )

        with _pinned([_proposal("user_repo.py", GET_USER_LINES, Severity.HIGH)]):
            assert _run(pipeline, inside.id) is True
        with _pinned([_proposal("reporting.py", REPORT_BUILD_LINES, Severity.HIGH)]):
            assert _run(pipeline, outside.id) is True

        db_session.refresh(inside)
        db_session.refresh(outside)
        assert inside.change_risk_hash != outside.change_risk_hash

class TestRealOrchestrator:
    def test_unpinned_pipeline_runs_analyzers_and_still_assesses_change_risk(
        self, db_session, installation, revisions, pipeline
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.chain_head, revisions.base
        )

        assert _run(pipeline, pr.id) is True

        db_session.refresh(pr)
        assert pr.status == PRAnalysisStatus.COMPLETED
        assert pr.change_risk_error is None

        report = pr.change_risk_report
        assert report["impact"]["changed_files"] == ["user_repo.py"]
        assert report["confidence"] in ("high", "medium", "low")
        assert report["risk_factors"]
        assert report["deterministic_hash"] == pr.change_risk_hash
        assert report["findings_evaluated"] == (
            report["findings_in_blast_radius"]
            + report["findings_outside_blast_radius"]
            + report["findings_unresolved_location"]
        )


class TestWebhookBackgroundTask:
    def test_run_pr_analysis_background_task_produces_a_risk_report(
        self, db_session, installation, revisions, github_service, ledger_home
    ):
        from app.routers import github_webhooks

        pr = _make_pr_analysis(
            db_session, installation, revisions.chain_head, revisions.base
        )

        real_init = PRAnalysisPipeline.__init__

        def init_with_local_remote(self, db_session, github_service=None):
            real_init(self, db_session=db_session, github_service=github_service)
            self.github_service = _RecordingGitHubService(revisions.remote_root)

        with patch.object(github_webhooks, "SessionLocal", lambda: db_session), patch(
            "app.services.pr_analysis.PRAnalysisPipeline.__init__",
            init_with_local_remote,
        ), patch.object(db_session, "close", lambda: None), _pinned(
            [_proposal("user_repo.py", GET_USER_LINES, Severity.CRITICAL)]
        ):
            asyncio.run(github_webhooks._run_pr_analysis(pr_analysis_id=pr.id))

        db_session.refresh(pr)
        assert pr.status == PRAnalysisStatus.COMPLETED
        assert pr.change_risk_level == "critical"
        assert pr.change_risk_recommendation == "requires_human_review"
        assert pr.change_risk_hash

    def test_get_pr_analysis_endpoint_exposes_the_risk_report(
        self, client, db_session, installation, revisions, pipeline
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.chain_head, revisions.base
        )

        with _pinned([_proposal("user_repo.py", GET_USER_LINES, Severity.HIGH)]):
            assert _run(pipeline, pr.id) is True

        response = client.get(f"/api/github/pr-analyses/{pr.id}")
        assert response.status_code == 200
        body = response.json()
        assert body["change_risk_level"] == "high"
        assert body["change_risk_recommendation"] == "requires_human_review"
        assert body["change_risk_base_revision"] == revisions.base
        assert body["change_risk_hash"] == pr.change_risk_hash
        assert body["change_risk_error"] is None

        risk = body["change_risk"]
        assert risk["available"] is True
        assert risk["unavailable_reason"] is None
        assert risk["risk"]["level"] == "high"
        assert risk["risk"]["recommendation"] == "requires_human_review"
        assert risk["risk"]["recommendation_label"] == "Human review required"
        assert risk["risk"]["confidence"] in ("high", "medium", "low")
        assert risk["risk"]["summary"]

        impact = risk["impact"]
        assert impact["changed_files"] == ["user_repo.py"]
        assert impact["repository"] == "owner/repo"
        assert impact["base_revision"] == revisions.base
        assert impact["target_revision"] == revisions.chain_head
        assert impact["changed_symbols"][0]["node_id"] == (
            "user_repo.py::UserRepository.get_user"
        )
        assert impact["affected_callers"] == [
            "auth_service.py::AuthorizationService.authorize"
        ]
        assert "api.py::create_payment" in impact["affected_entrypoints"]
        assert impact["blast_radius_size"] > 0

        assert risk["findings"] == {
            "evaluated": 1,
            "inside_radius": 1,
            "outside_radius": 0,
            "unresolved": 0,
        }
        assert risk["risk_factors"]
        assert all(
            set(f) == {"kind", "level", "detail", "evidence"}
            for f in risk["risk_factors"]
        )
        assert risk["finding_impacts"][0]["relation"] == "direct"
        assert risk["evidence"]["risk_hash"] == pr.change_risk_hash
        assert risk["evidence"]["impact_hash"]
        assert risk["decision"]["risk_level"] == "high"
        assert isinstance(risk["decision"]["score"], int)
        assert risk["decision"]["human_review_required"] is True
        assert risk["decision"]["reasons"]
        assert risk["verification"]["state"] in {
            "verified", "partially_verified", "unverified", "blocked"
        }
        assert risk["verification"]["required_checks"]
        assert risk["baseline"]["base_revision"] == revisions.base
        assert risk["baseline"]["status"] in {"COMPLETED", "UNAVAILABLE", "FAILED", "TIMEOUT"}
        assert "new_findings" in risk["regression"]
        assert risk["proof"]["verification_hash"]
        assert risk["proof"]["risk_hash"] == pr.change_risk_hash
        assert risk["governance"]["review_requirement"] == "human_review_required"
        assert risk["governance"]["approval_state"] is None
        assert isinstance(risk["impact"]["unresolved_references"], list)
        assert isinstance(risk["verification"]["reasons"], list)
        assert isinstance(risk["verification"]["command_results"], (list, type(None)))

    def test_endpoint_reports_why_the_assessment_is_unavailable(
        self, client, db_session, installation, revisions, pipeline
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.chain_head, "0" * 40
        )

        with _pinned([]):
            assert _run(pipeline, pr.id) is True

        body = client.get(f"/api/github/pr-analyses/{pr.id}").json()
        risk = body["change_risk"]
        assert risk["available"] is False
        assert risk["unavailable_reason"]
        assert risk["risk"] is None
        assert risk["impact"] is None
        assert risk["risk_factors"] == []
        assert risk["decision"] is None
        assert risk["verification"] is None
        assert risk["baseline"] is None
        assert risk["regression"] is None
        assert risk["proof"] is None
        assert risk["governance"] is None

    def test_list_endpoint_returns_change_risk_summaries(
        self, client, db_session, installation, revisions, pipeline
    ):
        low = _make_pr_analysis(
            db_session, installation, revisions.unrelated_head, revisions.base
        )
        high = _make_pr_analysis(
            db_session,
            installation,
            revisions.chain_head,
            revisions.base,
            delivery_id="phase20-delivery-list",
        )

        with _pinned([]):
            assert _run(pipeline, low.id) is True
        with _pinned([_proposal("user_repo.py", GET_USER_LINES, Severity.CRITICAL)]):
            assert _run(pipeline, high.id) is True

        body = client.get("/api/github/pr-analyses").json()
        assert body["count"] == 2
        assert body["repositories"] == ["owner/repo"]

        by_id = {row["id"]: row for row in body["analyses"]}
        assert by_id[low.id]["change_risk_level"] == "low"
        assert by_id[low.id]["change_risk_recommendation"] == "no_review_required"
        assert by_id[high.id]["change_risk_level"] == "critical"
        assert by_id[high.id]["change_risk_recommendation"] == "requires_human_review"
        assert by_id[high.id]["change_risk_available"] is True
        assert by_id[high.id]["change_risk_hash"]
        assert "change_risk_report" not in by_id[high.id]

    def test_list_endpoint_filters_by_repository(
        self, client, db_session, installation, revisions, pipeline
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.chain_head, revisions.base
        )

        with _pinned([]):
            assert _run(pipeline, pr.id) is True

        assert client.get(
            "/api/github/pr-analyses?repository=owner/repo"
        ).json()["count"] == 1
        assert client.get(
            "/api/github/pr-analyses?repository=other/repo"
        ).json()["count"] == 0


class TestClonedRepositorySupportsDiff:
    def test_clone_checks_out_a_sha_and_keeps_history_for_the_diff(
        self, revisions, github_service, tmp_path
    ):
        dest = str(tmp_path / "clone" / "repo")

        assert github_service.clone_repository(
            installation_id=1,
            repo_full_name="owner/repo",
            ref=revisions.chain_head,
            dest_path=dest,
            extra_refs=["main"],
        ) is True

        assert _git(dest, "rev-parse", "HEAD") == revisions.chain_head
        assert _git(dest, "rev-parse", "origin/main") == revisions.base
        assert not os.path.exists(os.path.join(dest, ".git", "shallow"))
        assert _git(
            dest, "diff", "--name-only", f"{revisions.base}..{revisions.chain_head}"
        ) == "user_repo.py"

    def test_shallow_branch_clone_cannot_produce_the_diff(self, revisions, tmp_path):
        dest = str(tmp_path / "shallow" / "repo")

        by_sha = subprocess.run(
            ["git", "clone", "--depth=1", "--branch", revisions.chain_head,
             revisions.repo_path, dest],
            capture_output=True,
            text=True,
        )
        assert by_sha.returncode != 0

        subprocess.run(
            ["git", "clone", "--quiet", "--depth=1", "--branch", "chain",
             f"file://{revisions.repo_path}", dest],
            check=True,
            capture_output=True,
        )
        assert os.path.exists(os.path.join(dest, ".git", "shallow"))
        diff = subprocess.run(
            ["git", "-C", dest, "diff", "--name-only",
             f"{revisions.base}..{revisions.chain_head}"],
            capture_output=True,
            text=True,
        )
        assert diff.returncode != 0

    def test_missing_token_reports_failure(self, github_service, tmp_path):
        github_service.token = None
        assert github_service.clone_repository(
            installation_id=1,
            repo_full_name="owner/repo",
            ref="main",
            dest_path=str(tmp_path / "notoken"),
        ) is False
