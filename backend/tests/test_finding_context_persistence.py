"""Phase 21 — finding context survives persistence and reaches the API."""

import pytest

from app.models.analysis_result import AnalysisResult, IssueCategory
from app.models.analysis_run import AnalysisRun, RunStatus
from app.models.installation import Installation
from app.models.repository import Repository
from app.routers.analysis import summarize_persisted_results
from app.services.finding_context import (
    FileClass,
    Recommendation,
    Relevance,
    build_finding_contexts,
)


@pytest.fixture
def repo(db_session):
    installation = Installation(installation_id=987654, github_user="tester")
    db_session.add(installation)
    db_session.flush()

    repository = Repository(
        installation_id=installation.id,
        repo_name="typeshed",
        repo_full_name="python/typeshed",
        github_repo_id=31696383,
        is_enabled=True,
    )
    db_session.add(repository)
    db_session.commit()
    return repository


@pytest.fixture
def run(db_session, repo):
    analysis_run = AnalysisRun(
        repository_id=repo.id,
        github_event="push",
        github_branch="main",
        github_commit_sha="HEAD",
        status=RunStatus.COMPLETED,
    )
    db_session.add(analysis_run)
    db_session.commit()
    return analysis_run


TYPESHED_FINDINGS = [
    {
        "file_path": "/tmp/agi-analysis-xyz/stdlib/_socket.pyi",
        "line_number": 846,
        "issue_code": "F811",
        "issue_name": "Redefinition of unused `timeout` from line 4",
        "message": "Redefinition of unused `timeout` from line 4",
        "severity": "warning",
    },
    {
        "file_path": "/tmp/agi-analysis-xyz/stdlib/_socket.pyi",
        "line_number": 949,
        "issue_code": "F811",
        "issue_name": "Redefinition of unused `timeout` from line 4",
        "message": "Redefinition of unused `timeout` from line 4",
        "severity": "warning",
    },
    {
        "file_path": "/tmp/agi-analysis-xyz/app/billing.py",
        "line_number": 12,
        "issue_code": "F811",
        "issue_name": "Redefinition of unused `charge` from line 3",
        "message": "Redefinition of unused `charge` from line 3",
        "severity": "warning",
    },
]


def persist(db_session, run, findings):
    contexts = build_finding_contexts(findings, repo_root="/tmp/agi-analysis-xyz")
    rows = []
    for finding, context in zip(findings, contexts):
        payload = context.to_dict()
        rows.append(
            AnalysisResult(
                run_id=run.id,
                file_path=context.file_path,
                line_number=finding["line_number"],
                issue_code=finding["issue_code"],
                issue_name=finding["issue_name"],
                category=IssueCategory.SUGGESTION,
                severity=finding["severity"],
                message=finding["message"],
                is_fixed=0,
                file_class=payload["file_class"],
                relevance=payload["relevance"],
                confidence=payload["confidence"],
                recommendation=payload["recommendation"],
                finding_context=payload,
            )
        )
    db_session.add_all(rows)
    db_session.commit()
    return rows


class TestPersistence:
    def test_context_columns_round_trip(self, db_session, run):
        persist(db_session, run, TYPESHED_FINDINGS)
        stored = (
            db_session.query(AnalysisResult)
            .filter(AnalysisResult.run_id == run.id)
            .order_by(AnalysisResult.id)
            .all()
        )
        assert [r.file_class for r in stored] == ["type_stub", "type_stub", "application"]
        assert [r.relevance for r in stored] == ["informational", "informational", "actionable"]
        assert stored[0].recommendation == Recommendation.SUPPRESS_CANDIDATE.value
        assert stored[2].recommendation == Recommendation.FIX.value

    def test_repo_relative_paths_are_persisted(self, db_session, run):
        persist(db_session, run, TYPESHED_FINDINGS)
        stored = db_session.query(AnalysisResult).order_by(AnalysisResult.id).all()
        assert stored[0].file_path == "stdlib/_socket.pyi"
        assert not any("/tmp/" in r.file_path for r in stored)

    def test_evidence_blob_keeps_reasons(self, db_session, run):
        persist(db_session, run, TYPESHED_FINDINGS)
        stored = db_session.query(AnalysisResult).order_by(AnalysisResult.id).first()
        blob = stored.finding_context
        assert blob["classification_reasons"]
        assert blob["relevance_reasons"]
        assert blob["confidence_reasons"]
        assert blob["production_reachable"] is None

    def test_no_finding_is_dropped_on_persist(self, db_session, run):
        persist(db_session, run, TYPESHED_FINDINGS)
        assert db_session.query(AnalysisResult).filter(
            AnalysisResult.run_id == run.id
        ).count() == len(TYPESHED_FINDINGS)


class TestSummarizePersistedResults:
    def test_counts_split_by_relevance(self, db_session, run):
        rows = persist(db_session, run, TYPESHED_FINDINGS)
        summary = summarize_persisted_results(rows)
        assert summary["actionable_count"] == 1
        assert summary["informational_count"] == 2
        assert summary["by_file_class"] == {"application": 1, "type_stub": 2}
        assert summary["unclassified_count"] == 0

    def test_legacy_rows_without_context_are_counted_unclassified(self, db_session, run):
        legacy = AnalysisResult(
            run_id=run.id,
            file_path="stdlib/old.pyi",
            line_number=1,
            issue_code="F811",
            issue_name="Redefinition",
            category=IssueCategory.SUGGESTION,
            severity="warning",
            message="Redefinition",
            is_fixed=0,
        )
        db_session.add(legacy)
        db_session.commit()
        summary = summarize_persisted_results([legacy])
        assert summary["unclassified_count"] == 1
        assert summary["actionable_count"] == 0
        assert summary["by_file_class"] == {"unclassified": 1}

    def test_empty_result_set(self):
        summary = summarize_persisted_results([])
        assert summary["actionable_count"] == 0
        assert summary["by_relevance"][Relevance.ACTIONABLE.value] == 0


class TestRunDetailEndpoint:
    def test_endpoint_exposes_context_fields(self, client, db_session, run):
        persist(db_session, run, TYPESHED_FINDINGS)
        response = client.get(f"/api/runs/{run.id}")
        assert response.status_code == 200
        body = response.json()

        assert body["total_results"] == 3
        assert body["relevance_summary"]["actionable_count"] == 1
        assert body["relevance_summary"]["informational_count"] == 2
        assert body["executed_analyzers"]

        first = body["results"][0]
        for key in (
            "file_class", "relevance", "confidence", "recommendation",
            "severity", "context",
        ):
            assert key in first
        assert first["file_class"] == "type_stub"
        assert first["relevance"] == "informational"
        assert first["context"]["rule_code"] == "F811"

    def test_stub_findings_are_still_returned_not_filtered(self, client, db_session, run):
        persist(db_session, run, TYPESHED_FINDINGS)
        body = client.get(f"/api/runs/{run.id}").json()
        stub_rows = [r for r in body["results"] if r["file_class"] == "type_stub"]
        assert len(stub_rows) == 2

    def test_severity_is_no_longer_dropped(self, client, db_session, run):
        persist(db_session, run, TYPESHED_FINDINGS)
        body = client.get(f"/api/runs/{run.id}").json()
        assert all(r["severity"] == "warning" for r in body["results"])
