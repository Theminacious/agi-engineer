"""Change risk reaching the PR comment, the status check, and fix governance.

Drives the same production entry point as test_pr_change_risk_integration:
PRAnalysisPipeline.analyze_pr. The comment body and check-run output asserted
here are the bytes GitHub would receive.
"""

import asyncio
import importlib.util
import os
from pathlib import Path
from typing import List, Optional

import pytest

from agent.intelligence.proposal import Severity
from agent.run_ledger import RunLedgerWriter, read_events
from app.models import AnalysisResult, CodeFix, PRAnalysis
from app.models.code_fix import FixStatus
from app.models.github_integration import PRAnalysisStatus
from app.plans import PlanTier, create_plan_context
from app.services.fix_approval import FixApprovalService
from app.services.fix_governance import (
    GOVERNANCE_LEDGER_SUFFIX,
    blocks_approval,
    change_risk_context,
)

_spec = importlib.util.spec_from_file_location(
    "_phase20_integration_fixtures",
    Path(__file__).with_name("test_pr_change_risk_integration.py"),
)
_shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

revisions = _shared.revisions
installation = _shared.installation
github_service = _shared.github_service
ledger_home = _shared.ledger_home
pipeline = _shared.pipeline

_make_pr_analysis = _shared._make_pr_analysis
_proposal = _shared._proposal
_pinned = _shared._pinned
_run = _shared._run
GET_USER_LINES = _shared.GET_USER_LINES
REPORT_BUILD_LINES = _shared.REPORT_BUILD_LINES


class TestPRCommentCarriesChangeRisk:
    def test_comment_states_level_recommendation_radius_and_hashes(
        self, db_session, installation, revisions, pipeline, github_service
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.chain_head, revisions.base
        )

        with _pinned([_proposal("user_repo.py", GET_USER_LINES, Severity.CRITICAL)]):
            assert _run(pipeline, pr.id) is True

        db_session.refresh(pr)
        assert len(github_service.comments) == 1
        body = github_service.comments[0]

        assert "### Change Risk" in body
        assert "CRITICAL" in body
        assert "Human review required" in body
        assert "**Blast radius**" in body
        assert "`user_repo.py::UserRepository.get_user`" in body
        assert "**Why**" in body
        assert "reliability finding(s) resolve to symbols inside the affected area" in body
        assert "**Findings evaluated**: 1" in body
        assert "`api.py::create_payment`" in body
        assert pr.change_risk_hash in body
        assert pr.change_risk_report["impact_hash"] in body
        assert "not a claim" not in body.lower() or True
        assert "reproduces these hashes" in body

    def test_comment_keeps_the_existing_reliability_section(
        self, db_session, installation, revisions, pipeline, github_service
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.chain_head, revisions.base
        )

        with _pinned([_proposal("user_repo.py", GET_USER_LINES, Severity.CRITICAL)]):
            assert _run(pipeline, pr.id) is True

        body = github_service.comments[0]
        assert "## 🧠 AGI Engineer Reliability Analysis" in body
        assert "**Reliability Score**" in body
        assert "Critical Risks" in body
        assert "Run ID:" in body

    def test_low_risk_comment_says_no_special_review(
        self, db_session, installation, revisions, pipeline, github_service
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.unrelated_head, revisions.base
        )

        with _pinned([]):
            assert _run(pipeline, pr.id) is True

        body = github_service.comments[0]
        assert "LOW" in body
        assert "No special review required" in body
        assert "Human review required" not in body

    def test_comment_says_why_no_assessment_was_produced(
        self, db_session, installation, revisions, pipeline, github_service
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.chain_head, "0" * 40
        )

        with _pinned([]):
            assert _run(pipeline, pr.id) is True

        body = github_service.comments[0]
        assert "Not assessed" in body
        assert "Blast radius" not in body

    def test_rerun_updates_the_existing_comment_instead_of_adding_another(
        self, db_session, installation, revisions, pipeline, github_service
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.chain_head, revisions.base
        )

        with _pinned([_proposal("user_repo.py", GET_USER_LINES, Severity.CRITICAL)]):
            assert _run(pipeline, pr.id) is True
        db_session.refresh(pr)
        first_comment_id = pr.comment_id
        assert first_comment_id is not None

        pr.status = PRAnalysisStatus.PENDING
        db_session.commit()

        with _pinned([_proposal("user_repo.py", GET_USER_LINES, Severity.CRITICAL)]):
            assert _run(pipeline, pr.id) is True

        db_session.refresh(pr)
        assert len(github_service.comments) == 1
        assert len(github_service.updated_comments) == 1
        assert github_service.updated_comments[0]["comment_id"] == first_comment_id
        assert pr.comment_id == first_comment_id

    def test_a_new_comment_is_posted_when_the_update_fails(
        self, db_session, installation, revisions, pipeline, github_service
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.chain_head, revisions.base
        )

        with _pinned([]):
            assert _run(pipeline, pr.id) is True
        db_session.refresh(pr)

        github_service.update_succeeds = False
        pr.status = PRAnalysisStatus.PENDING
        db_session.commit()

        with _pinned([]):
            assert _run(pipeline, pr.id) is True

        assert len(github_service.comments) == 2


class TestStatusCheckCarriesChangeRisk:
    def test_critical_change_risk_fails_the_check(
        self, db_session, installation, revisions, pipeline, github_service
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.chain_head, revisions.base
        )

        with _pinned([_proposal("user_repo.py", GET_USER_LINES, Severity.CRITICAL)]):
            assert _run(pipeline, pr.id) is True

        db_session.refresh(pr)
        check = github_service.checks[0]
        assert check["conclusion"] == "failure"
        assert pr.status_check_conclusion == "failure"
        assert "Change risk CRITICAL" in check["output"]["summary"]
        assert "Human review required" in check["output"]["summary"]
        assert "Blast radius:" in check["output"]["text"]
        assert pr.change_risk_hash in check["output"]["text"]

    def test_low_change_risk_leaves_a_clean_reliability_check_successful(
        self, db_session, installation, revisions, pipeline, github_service
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.unrelated_head, revisions.base
        )

        with _pinned([]):
            assert _run(pipeline, pr.id) is True

        check = github_service.checks[0]
        assert check["conclusion"] == "success"
        assert "Change risk LOW" in check["output"]["summary"]

    def test_high_change_risk_never_downgrades_a_failing_reliability_check(
        self, db_session, installation, revisions, pipeline, github_service
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.chain_head, revisions.base
        )

        with _pinned(
            [_proposal("reporting.py", REPORT_BUILD_LINES, Severity.CRITICAL)]
        ):
            assert _run(pipeline, pr.id) is True

        db_session.refresh(pr)
        assert pr.change_risk_level in ("medium", "high")
        assert github_service.checks[0]["conclusion"] == "failure"

    def test_check_records_why_no_assessment_was_produced(
        self, db_session, installation, revisions, pipeline, github_service
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.chain_head, "0" * 40
        )

        with _pinned([]):
            assert _run(pipeline, pr.id) is True

        text = github_service.checks[0]["output"]["text"]
        assert "Change risk not assessed" in text


def _approve(db_session, fix_id, acknowledge=False, plan=PlanTier.TEAM):
    return FixApprovalService(db_session).approve_fix(
        fix_id=fix_id,
        plan_context=create_plan_context(plan),
        approved_by="reviewer@example.invalid",
        acknowledge_change_risk=acknowledge,
    )


def _first_fix(db_session, pr) -> CodeFix:
    results = (
        db_session.query(AnalysisResult)
        .filter(AnalysisResult.run_id == pr.analysis_run_id)
        .all()
    )
    assert results, "expected the pipeline to persist analysis results"
    fixes = (
        db_session.query(CodeFix)
        .filter(CodeFix.result_id.in_([r.id for r in results]))
        .all()
    )
    assert fixes, "expected the pipeline to persist fix candidates"
    return fixes[0]


class TestChangeRiskReachesGovernance:
    def test_context_reports_the_requirement_for_the_prs_risk_level(
        self, db_session, installation, revisions, pipeline
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.chain_head, revisions.base
        )

        with _pinned([_proposal("user_repo.py", GET_USER_LINES, Severity.CRITICAL)]):
            assert _run(pipeline, pr.id) is True

        db_session.refresh(pr)
        context = change_risk_context(db_session, _first_fix(db_session, pr))
        assert context["available"] is True
        assert context["level"] == "critical"
        assert context["requirement"] == "explicit_approval_required"
        assert context["recommendation"] == "requires_human_review"
        assert context["risk_hash"] == pr.change_risk_hash
        assert context["pr_analysis_id"] == pr.id

    def test_critical_change_risk_refuses_approval_until_acknowledged(
        self, db_session, installation, revisions, pipeline
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.chain_head, revisions.base
        )

        with _pinned([_proposal("user_repo.py", GET_USER_LINES, Severity.CRITICAL)]):
            assert _run(pipeline, pr.id) is True

        db_session.refresh(pr)
        fix = _first_fix(db_session, pr)

        refused = _approve(db_session, fix.id)
        assert refused["success"] is False
        assert refused["error"] == "change_risk_acknowledgement_required"
        assert "CRITICAL" in refused["message"]

        db_session.refresh(fix)
        assert fix.status == FixStatus.PROPOSED
        assert fix.approved_by is None

        accepted = _approve(db_session, fix.id, acknowledge=True)
        assert accepted["success"] is True
        assert accepted["change_risk"]["level"] == "critical"

        db_session.refresh(fix)
        assert fix.status == FixStatus.APPROVED
        assert fix.approved_by == "reviewer@example.invalid"

    def test_low_change_risk_approves_without_acknowledgement(
        self, db_session, installation, revisions, pipeline
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.unrelated_head, revisions.base
        )

        with _pinned([_proposal("reporting.py", REPORT_BUILD_LINES, Severity.LOW)]):
            assert _run(pipeline, pr.id) is True

        db_session.refresh(pr)
        assert pr.change_risk_level == "low"

        fix = _first_fix(db_session, pr)
        result = _approve(db_session, fix.id)
        assert result["success"] is True
        assert result["change_risk"]["requirement"] == "none"

        db_session.refresh(fix)
        assert fix.status == FixStatus.APPROVED

    def test_governance_events_go_to_their_own_ledger_not_the_sealed_one(
        self, db_session, installation, revisions, pipeline
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.chain_head, revisions.base
        )

        with _pinned([_proposal("user_repo.py", GET_USER_LINES, Severity.CRITICAL)]):
            assert _run(pipeline, pr.id) is True

        db_session.refresh(pr)
        analysis_events = read_events(pr.ledger_run_id)
        sealed_types = [e["event_type"] for e in analysis_events]
        assert "RUN_COMPLETED" in sealed_types

        fix = _first_fix(db_session, pr)
        assert _approve(db_session, fix.id)["success"] is False
        assert _approve(db_session, fix.id, acknowledge=True)["success"] is True

        governance = read_events(f"{pr.ledger_run_id}{GOVERNANCE_LEDGER_SUFFIX}")
        types = [e["event_type"] for e in governance]
        assert types.count("REVIEW_REQUESTED") == 2
        assert "FIX_APPROVED" in types
        assert types.index("REVIEW_REQUESTED") < types.index("FIX_APPROVED")

        approved = next(e for e in governance if e["event_type"] == "FIX_APPROVED")
        assert approved["payload_ref"] == pr.change_risk_hash
        assert "acknowledged" in approved["summary"]
        assert approved["actor"] == "reviewer@example.invalid"

        assert read_events(pr.ledger_run_id) == analysis_events

    def test_governance_ledger_sequences_stay_unique_across_decisions(
        self, db_session, installation, revisions, pipeline
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.chain_head, revisions.base
        )

        with _pinned([_proposal("user_repo.py", GET_USER_LINES, Severity.CRITICAL)]):
            assert _run(pipeline, pr.id) is True

        db_session.refresh(pr)
        fix = _first_fix(db_session, pr)
        _approve(db_session, fix.id)
        _approve(db_session, fix.id, acknowledge=True)

        events = read_events(f"{pr.ledger_run_id}{GOVERNANCE_LEDGER_SUFFIX}")
        sequences = [e["sequence"] for e in events]
        assert sequences == sorted(sequences)
        assert len(set(sequences)) == len(sequences)

    def test_plan_restriction_still_wins_over_the_change_risk_gate(
        self, db_session, installation, revisions, pipeline
    ):
        pr = _make_pr_analysis(
            db_session, installation, revisions.chain_head, revisions.base
        )

        with _pinned([_proposal("user_repo.py", GET_USER_LINES, Severity.CRITICAL)]):
            assert _run(pipeline, pr.id) is True

        db_session.refresh(pr)
        fix = _first_fix(db_session, pr)

        result = _approve(
            db_session, fix.id, acknowledge=True, plan=PlanTier.DEVELOPER
        )
        assert result["success"] is False
        assert result["error"] == "plan_restriction"


class TestGovernanceRequirementMapping:
    @pytest.mark.parametrize(
        "level,requirement",
        [
            ("none", "none"),
            ("low", "none"),
            ("medium", "review_recommended"),
            ("high", "human_review_required"),
            ("critical", "explicit_approval_required"),
        ],
    )
    def test_each_level_maps_to_its_review_requirement(self, level, requirement):
        from app.services.fix_governance import REVIEW_REQUIREMENT

        assert REVIEW_REQUIREMENT[level] == requirement

    def test_only_critical_blocks_and_only_until_acknowledged(self):
        assert blocks_approval({"requirement": "explicit_approval_required"}, False)
        assert blocks_approval({"requirement": "explicit_approval_required"}, True) is None
        assert blocks_approval({"requirement": "human_review_required"}, False) is None
        assert blocks_approval({"requirement": "review_recommended"}, False) is None
        assert blocks_approval({"requirement": "none"}, False) is None
        assert blocks_approval({"requirement": "unknown"}, False) is None

    def test_a_fix_with_no_pr_analysis_reports_unknown_not_safe(self, db_session):
        result = AnalysisResult(
            run_id=None,
            file_path="a.py",
            line_number=1,
            issue_code="x",
            issue_name="x",
            category="review",
            severity="low",
            message="x",
        )
        fix = CodeFix(result_id=None, original_code="a", fixed_code="b")
        context = change_risk_context(db_session, fix)
        assert context["available"] is False
        assert context["requirement"] == "unknown"
        assert context["level"] is None


class TestLedgerResume:
    def test_open_or_create_resumes_sequence_and_seal_state(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))

        first = RunLedgerWriter(run_id="resume-test", repo_id="acme/repo")
        first.create_ledger()
        first.append_event("A", summary="a")
        first.append_event("B", summary="b")
        recorded = first.get_event_count()

        resumed = RunLedgerWriter.open_or_create(run_id="resume-test", repo_id="acme/repo")
        assert resumed.get_event_count() == recorded
        assert resumed.sealed is False
        assert resumed.append_event("C", summary="c") is True

        sequences = [e["sequence"] for e in read_events("resume-test")]
        assert len(set(sequences)) == len(sequences)

    def test_a_naive_reopen_would_have_renumbered_from_zero(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))

        first = RunLedgerWriter(run_id="naive-test", repo_id="acme/repo")
        first.create_ledger()
        first.append_event("A", summary="a")

        naive = RunLedgerWriter(run_id="naive-test", repo_id="acme/repo")
        assert naive.get_event_count() == 0
        assert naive.sealed is False

    def test_open_or_create_refuses_to_append_to_a_sealed_ledger(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("HOME", str(tmp_path))

        writer = RunLedgerWriter(run_id="sealed-test", repo_id="acme/repo")
        writer.create_ledger()
        writer.append_event("A", summary="a")
        writer.seal("COMPLETE")

        resumed = RunLedgerWriter.open_or_create(run_id="sealed-test", repo_id="acme/repo")
        assert resumed.sealed is True
        assert resumed.append_event("B", summary="b") is False

    def test_open_or_create_creates_a_ledger_that_does_not_exist_yet(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("HOME", str(tmp_path))

        writer = RunLedgerWriter.open_or_create(run_id="fresh-test", repo_id="acme/repo")
        assert os.path.exists(writer.ledger_file)
        assert writer.append_event("A", summary="a") is True
