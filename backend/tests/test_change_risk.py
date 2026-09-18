"""Tests for Phase 20 — Change Impact -> Risk Intelligence.

Two layers:

* ``assess_change_risk`` is a pure function of a finalized
  ``ChangeImpactReport``, so most cases are hand-built reports — no git, no
  graph build, and the scoring rule under test is the only variable.
* ``ChangeRiskService`` is exercised end-to-end against real git repos, so
  the diff -> graph -> blast radius -> finding resolution -> risk path is
  proven to work on the finding shape the reliability analyzers emit.

The outside-the-blast-radius cases are written as negative controls: the
same finding is scored twice, once resolving inside the radius and once
outside, and the verdicts must differ. A test that only asserted "outside
finding gives LOW" would still pass if the finding were ignored entirely.
"""

from __future__ import annotations

import os
import subprocess
import textwrap
from pathlib import Path
from typing import Dict, List, Sequence

import pytest

from app.models.change_impact import (
    RISK_LEVEL_RANK,
    ChangedSymbol,
    ChangeImpactReport,
    Confidence,
    FindingImpact,
    ReviewRecommendation,
    RiskLevel,
    UnresolvedReference,
)
from app.services.change_risk_service import (
    WIDE_BLAST_RADIUS_THRESHOLD,
    ChangeRiskService,
    _normalise_findings,
    assess_change_risk,
)

GET_USER = "repository.py::UserRepository.get_user"
AUTHORIZE = "auth_service.py::AuthorizationService.authorize"
PROCESS_PAYMENT = "payment_service.py::PaymentService.process_payment"


# ─── Builders for the pure-scorer layer ─────────────────────────────


def _impact(
    changed_files: Sequence[str] = ("repository.py",),
    changed_symbols: Sequence[str] = (GET_USER,),
    direct: Sequence[str] = (GET_USER,),
    callers: Sequence[str] = (),
    downstream: Sequence[str] = (),
    entrypoints: Sequence[str] = (),
    finding_impacts: Sequence[FindingImpact] = (),
    unresolved_references: Sequence[UnresolvedReference] = (),
    confidence: Confidence = Confidence.HIGH,
) -> ChangeImpactReport:
    report = ChangeImpactReport(
        repository="/repo",
        base_revision="base",
        target_revision="target",
        changed_files=list(changed_files),
        changed_symbols=[
            ChangedSymbol(
                node_id=node_id,
                node_type="method",
                file_path=node_id.split("::")[0],
                name=node_id.split("::")[-1],
                change_kind="modified",
            )
            for node_id in changed_symbols
        ],
        directly_affected_symbols=list(direct),
        callers=list(callers),
        downstream_symbols=list(downstream),
        affected_entrypoints=list(entrypoints),
        finding_impacts=list(finding_impacts),
        unresolved_references=list(unresolved_references),
        confidence=confidence,
    )
    return report.finalize()


def _finding(
    relation: str,
    severity: str = "critical",
    node_id: str = GET_USER,
    file_path: str = "repository.py",
    line_range: str = "2-3",
    overlapping_symbol_count: int = 1,
    reason: str = "",
) -> FindingImpact:
    return FindingImpact(
        finding_ref=f"prop-{relation}-{severity}",
        file_path=file_path,
        line_range=line_range,
        severity=severity,
        relation=relation,
        resolved_node_id="" if relation == "unresolved" else node_id,
        overlapping_symbol_count=overlapping_symbol_count,
        reason=reason,
    )


def _kinds(report) -> List[str]:
    return sorted(f.kind for f in report.risk_factors)


# ─── Empty / no-impact changes ──────────────────────────────────────


def test_no_changes_is_none_risk():
    report = assess_change_risk(_impact(changed_files=(), changed_symbols=(), direct=()))
    assert report.risk_level == RiskLevel.NONE
    assert report.recommendation == ReviewRecommendation.NO_REVIEW_REQUIRED
    assert report.risk_factors == []
    assert "nothing to assess" in report.summary


def test_no_changes_still_reports_finding_counts():
    """A no-op diff must not silently drop findings it was handed."""
    report = assess_change_risk(
        _impact(
            changed_files=(),
            changed_symbols=(),
            direct=(),
            finding_impacts=[_finding("outside")],
        )
    )
    assert report.risk_level == RiskLevel.NONE
    assert report.findings_evaluated == 1
    assert report.findings_outside_blast_radius == 1


def test_change_with_no_known_risk_is_low():
    report = assess_change_risk(_impact())
    assert report.risk_level == RiskLevel.LOW
    assert report.recommendation == ReviewRecommendation.NO_REVIEW_REQUIRED
    assert _kinds(report) == ["code_changed_no_known_risk"]


# ─── Finding inside the blast radius DOES affect the result ─────────


@pytest.mark.parametrize(
    "severity,expected",
    [
        ("critical", RiskLevel.CRITICAL),
        ("high", RiskLevel.HIGH),
        ("low", RiskLevel.LOW),
    ],
)
def test_finding_inside_blast_radius_sets_risk_from_severity(severity, expected):
    report = assess_change_risk(_impact(finding_impacts=[_finding("direct", severity)]))
    assert report.risk_level == expected
    assert report.findings_in_blast_radius == 1
    assert "reliability_finding_in_blast_radius" in _kinds(report)


def test_critical_finding_in_radius_requires_human_review():
    report = assess_change_risk(_impact(finding_impacts=[_finding("direct", "critical")]))
    assert report.recommendation == ReviewRecommendation.REQUIRES_HUMAN_REVIEW


def test_multi_hop_downstream_finding_is_in_radius():
    """A finding two hops from the change still counts against it."""
    report = assess_change_risk(
        _impact(
            callers=(AUTHORIZE,),
            downstream=(PROCESS_PAYMENT,),
            finding_impacts=[
                _finding(
                    "downstream",
                    "critical",
                    node_id=PROCESS_PAYMENT,
                    file_path="payment_service.py",
                    line_range="7-10",
                )
            ],
        )
    )
    assert report.risk_level == RiskLevel.CRITICAL
    assert report.findings_in_blast_radius == 1
    locations = [t.location for t in report.review_targets]
    assert "payment_service.py:7-10" in locations


def test_unknown_severity_in_radius_is_medium_not_ignored():
    report = assess_change_risk(_impact(finding_impacts=[_finding("direct", "not-a-severity")]))
    assert report.risk_level == RiskLevel.MEDIUM


def test_all_in_radius_relations_count():
    for relation in ("direct", "caller", "downstream"):
        report = assess_change_risk(
            _impact(
                callers=(AUTHORIZE,),
                downstream=(PROCESS_PAYMENT,),
                finding_impacts=[_finding(relation, "high")],
            )
        )
        assert report.findings_in_blast_radius == 1, relation
        assert report.risk_level == RiskLevel.HIGH, relation


# ─── Finding OUTSIDE the blast radius must NOT affect the result ────


def test_outside_finding_does_not_change_the_verdict():
    """Negative control: the identical finding inside vs outside the radius.

    Both halves matter. Equality with the no-findings run proves the outside
    finding contributed nothing; inequality with the inside run proves the
    scorer is not simply ignoring every finding.
    """
    outside = assess_change_risk(_impact(finding_impacts=[_finding("outside", "critical")]))
    none = assess_change_risk(_impact())
    inside = assess_change_risk(_impact(finding_impacts=[_finding("direct", "critical")]))

    assert outside.risk_level == none.risk_level == RiskLevel.LOW
    assert _kinds(outside) == _kinds(none) == ["code_changed_no_known_risk"]
    assert outside.recommendation == ReviewRecommendation.NO_REVIEW_REQUIRED
    assert inside.risk_level == RiskLevel.CRITICAL


def test_outside_finding_is_still_counted_and_caveated():
    report = assess_change_risk(_impact(finding_impacts=[_finding("outside", "critical")]))
    assert report.findings_evaluated == 1
    assert report.findings_outside_blast_radius == 1
    assert report.findings_in_blast_radius == 0
    assert any("outside the blast" in c for c in report.caveats)
    assert not any(t.kind == "finding" for t in report.review_targets)


def test_outside_finding_does_not_dilute_an_inside_finding():
    report = assess_change_risk(
        _impact(
            finding_impacts=[
                _finding("outside", "critical", node_id="other.py::helper", file_path="other.py"),
                _finding("direct", "medium"),
            ]
        )
    )
    assert report.risk_level == RiskLevel.MEDIUM
    assert report.findings_in_blast_radius == 1
    assert report.findings_outside_blast_radius == 1


# ─── Unresolved locations: conservative, never certain ──────────────


def test_unresolved_finding_in_changed_file_raises_floor_to_medium():
    report = assess_change_risk(
        _impact(
            finding_impacts=[
                _finding(
                    "unresolved",
                    "critical",
                    line_range="bad",
                    overlapping_symbol_count=0,
                    reason="unparseable line_range 'bad'",
                )
            ]
        )
    )
    assert report.risk_level == RiskLevel.MEDIUM
    assert report.recommendation == ReviewRecommendation.REVIEW_RECOMMENDED
    assert "unresolved_finding_location_in_changed_file" in _kinds(report)
    # Counted as neither inside nor outside — the analysis does not know.
    assert report.findings_unresolved_location == 1
    assert report.findings_in_blast_radius == 0
    assert report.findings_outside_blast_radius == 0


def test_unresolved_finding_is_not_promoted_to_its_severity():
    """A critical finding that could not be located must not score CRITICAL.

    Doing so would claim the finding is in the affected area, which is
    exactly what could not be established.
    """
    report = assess_change_risk(
        _impact(finding_impacts=[_finding("unresolved", "critical", line_range="bad")])
    )
    assert report.risk_level == RiskLevel.MEDIUM


def test_unresolved_finding_outside_changed_files_does_not_escalate():
    report = assess_change_risk(
        _impact(
            finding_impacts=[
                _finding("unresolved", "critical", file_path="untouched.py", line_range="bad")
            ]
        )
    )
    assert report.risk_level == RiskLevel.LOW
    assert report.findings_unresolved_location == 1
    assert "unresolved_finding_location_in_changed_file" not in _kinds(report)


def test_unresolved_location_in_changed_file_is_a_review_target():
    report = assess_change_risk(
        _impact(
            finding_impacts=[
                _finding(
                    "unresolved", "high", line_range="bad", reason="unparseable line_range 'bad'"
                )
            ]
        )
    )
    targets = [t for t in report.review_targets if t.kind == "unresolved_location"]
    assert len(targets) == 1
    assert targets[0].location == "repository.py:bad"
    assert "unparseable" in targets[0].detail


def test_unresolved_changed_lines_are_reported_as_a_gap():
    report = assess_change_risk(
        _impact(
            unresolved_references=[
                UnresolvedReference(
                    file_path="repository.py",
                    detail="lines 1-1",
                    reason="no enclosing symbol",
                )
            ]
        )
    )
    assert "unresolved_changed_lines" in _kinds(report)
    factor = next(f for f in report.risk_factors if f.kind == "unresolved_changed_lines")
    assert factor.level == RiskLevel.LOW
    assert factor.evidence == ["repository.py:lines 1-1 (no enclosing symbol)"]


# ─── Entry points, blast radius width, confidence ───────────────────


def test_entrypoint_reachable_is_medium():
    report = assess_change_risk(_impact(entrypoints=("routes.py::get_user_handler",)))
    assert report.risk_level == RiskLevel.MEDIUM
    assert "entrypoint_reachable" in _kinds(report)
    assert any(t.kind == "entrypoint" for t in report.review_targets)


def test_entrypoint_escalates_medium_finding_to_high():
    with_entry = assess_change_risk(
        _impact(
            entrypoints=("routes.py::get_user_handler",),
            finding_impacts=[_finding("direct", "medium")],
        )
    )
    without_entry = assess_change_risk(_impact(finding_impacts=[_finding("direct", "medium")]))

    assert without_entry.risk_level == RiskLevel.MEDIUM
    assert with_entry.risk_level == RiskLevel.HIGH
    assert "finding_reachable_from_entrypoint" in _kinds(with_entry)
    assert "finding_reachable_from_entrypoint" not in _kinds(without_entry)


def test_entrypoint_does_not_escalate_a_low_finding():
    report = assess_change_risk(
        _impact(
            entrypoints=("routes.py::get_user_handler",),
            finding_impacts=[_finding("direct", "low")],
        )
    )
    assert "finding_reachable_from_entrypoint" not in _kinds(report)
    assert report.risk_level == RiskLevel.MEDIUM  # from entrypoint_reachable alone


def test_wide_blast_radius_is_medium_at_threshold():
    wide = [f"m.py::f{i}" for i in range(WIDE_BLAST_RADIUS_THRESHOLD)]
    report = assess_change_risk(_impact(direct=(GET_USER,), downstream=wide))
    assert report.blast_radius_size == WIDE_BLAST_RADIUS_THRESHOLD + 1
    assert "wide_blast_radius" in _kinds(report)
    assert report.risk_level == RiskLevel.MEDIUM


def test_narrow_blast_radius_has_no_width_factor():
    report = assess_change_risk(_impact(downstream=("m.py::f0",)))
    assert "wide_blast_radius" not in _kinds(report)


def test_low_impact_confidence_is_a_factor():
    report = assess_change_risk(_impact(confidence=Confidence.LOW))
    assert "low_impact_confidence" in _kinds(report)
    assert report.risk_level == RiskLevel.MEDIUM
    assert report.confidence == Confidence.LOW
    assert any("confidence is low" in c for c in report.caveats)


def test_high_confidence_has_no_confidence_factor_or_caveat():
    report = assess_change_risk(_impact(confidence=Confidence.HIGH))
    assert "low_impact_confidence" not in _kinds(report)
    assert not any("confidence" in c for c in report.caveats)


# ─── Determinism, ordering, traceability ────────────────────────────


def _mixed_findings() -> List[FindingImpact]:
    return [
        _finding("outside", "critical", node_id="z.py::z", file_path="z.py"),
        _finding("direct", "medium"),
        _finding("caller", "high", node_id=AUTHORIZE, file_path="auth_service.py", line_range="7-9"),
        _finding("unresolved", "low", line_range="bad"),
    ]


def test_identical_input_gives_identical_hash_and_dict():
    findings = _mixed_findings()
    r1 = assess_change_risk(_impact(callers=(AUTHORIZE,), finding_impacts=findings))
    r2 = assess_change_risk(_impact(callers=(AUTHORIZE,), finding_impacts=list(findings)))
    assert r1.deterministic_hash == r2.deterministic_hash
    assert r1.to_dict() == r2.to_dict()


def test_input_order_does_not_change_the_output():
    """Finding order is an artifact of analyzer scheduling, not of the code."""
    findings = _mixed_findings()
    forward = assess_change_risk(_impact(callers=(AUTHORIZE,), finding_impacts=findings))
    reverse = assess_change_risk(
        _impact(callers=(AUTHORIZE,), finding_impacts=list(reversed(findings)))
    )
    assert forward.deterministic_hash == reverse.deterministic_hash
    assert [f.kind for f in forward.risk_factors] == [f.kind for f in reverse.risk_factors]
    assert forward.review_targets == reverse.review_targets
    assert forward.caveats == reverse.caveats


def test_hash_changes_when_the_verdict_changes():
    """Negative control on the hash: it must actually cover the content."""
    low = assess_change_risk(_impact())
    high = assess_change_risk(_impact(finding_impacts=[_finding("direct", "critical")]))
    assert low.deterministic_hash != high.deterministic_hash


def test_factors_sorted_by_rank_then_kind():
    report = assess_change_risk(
        _impact(
            entrypoints=("routes.py::h",),
            confidence=Confidence.LOW,
            finding_impacts=[_finding("direct", "critical")],
        )
    )
    ranks = [RISK_LEVEL_RANK[f.level] for f in report.risk_factors]
    assert ranks == sorted(ranks)
    keys = [(RISK_LEVEL_RANK[f.level], f.kind, f.detail) for f in report.risk_factors]
    assert keys == sorted(keys)


def test_evidence_is_deduped_and_sorted():
    report = assess_change_risk(
        _impact(
            entrypoints=("routes.py::b", "routes.py::a", "routes.py::a"),
        )
    )
    factor = next(f for f in report.risk_factors if f.kind == "entrypoint_reachable")
    assert factor.evidence == sorted(set(factor.evidence))


def test_risk_level_equals_max_factor_level():
    report = assess_change_risk(
        _impact(
            entrypoints=("routes.py::h",),
            confidence=Confidence.LOW,
            finding_impacts=[_finding("direct", "high"), _finding("outside", "critical")],
        )
    )
    assert report.risk_level == max(
        (f.level for f in report.risk_factors), key=lambda lvl: RISK_LEVEL_RANK[lvl]
    )
    assert report.risk_level == RiskLevel.HIGH


def test_impact_hash_is_carried_and_impact_is_serialised():
    impact = _impact()
    report = assess_change_risk(impact)
    assert report.impact_hash == impact.deterministic_hash
    assert report.to_dict()["impact"]["deterministic_hash"] == impact.deterministic_hash


def test_overlapping_symbol_caveat_is_stated():
    report = assess_change_risk(
        _impact(finding_impacts=[_finding("direct", "high", overlapping_symbol_count=3)])
    )
    assert any("spanning several symbols" in c for c in report.caveats)


def test_non_python_changed_file_caveat():
    report = assess_change_risk(_impact(changed_files=("repository.py", "notes.txt")))
    assert any("Non-Python" in c for c in report.caveats)


def test_summary_reports_the_counts_it_scored():
    report = assess_change_risk(
        _impact(
            downstream=(PROCESS_PAYMENT,),
            entrypoints=("routes.py::h",),
            finding_impacts=[_finding("direct", "critical"), _finding("outside", "low")],
        )
    )
    assert "CRITICAL risk" in report.summary
    assert "1 of 2 finding location(s) inside it" in report.summary
    assert "requires_human_review" in report.summary


# ─── Finding normalisation ──────────────────────────────────────────


def test_normalise_findings_accepts_dicts_objects_and_skips_junk():
    class Proposal:
        def to_dict(self):
            return {"proposal_id": "p1"}

    assert _normalise_findings(None) == []
    assert _normalise_findings([]) == []
    out = _normalise_findings([{"proposal_id": "p0"}, Proposal(), object()])
    assert out == [{"proposal_id": "p0"}, {"proposal_id": "p1"}]


# ─── End-to-end over real git ───────────────────────────────────────


def _git_env(repo: Path) -> Dict[str, str]:
    home = repo / ".git-home"
    home.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(
        HOME=str(home),
        XDG_CONFIG_HOME=str(home / ".config"),
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_CONFIG_SYSTEM=os.devnull,
    )
    return env


def _git(*args: str, cwd: Path) -> str:
    out = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
        env=_git_env(cwd),
    )
    return out.stdout.strip()


def _write(repo: Path, rel_path: str, content: str) -> None:
    p = repo / rel_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(content))


def _commit(repo: Path, message: str) -> str:
    _git("add", "-A", cwd=repo)
    _git("commit", "-q", "-m", message, cwd=repo)
    return _git("rev-parse", "HEAD", cwd=repo)


@pytest.fixture
def chain_repo(tmp_path: Path) -> Path:
    """UserRepository.get_user <- AuthorizationService.authorize <- PaymentService.process_payment.

    Same shape as the ChangeImpact suite's fixture, plus an unrelated module
    so a finding can be placed outside the blast radius.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _git("init", "-q", cwd=repo)
    _git("config", "user.email", "test@example.com", cwd=repo)
    _git("config", "user.name", "Test", cwd=repo)
    _write(repo, "repository.py", """\
        class UserRepository:
            def get_user(self, user_id):
                return {"id": user_id, "name": "placeholder"}
    """)
    _write(repo, "auth_service.py", """\
        from repository import UserRepository

        class AuthorizationService:
            def __init__(self):
                self.repo = UserRepository()

            def authorize(self, user_id):
                user = self.repo.get_user(user_id)
                return user is not None
    """)
    _write(repo, "payment_service.py", """\
        from auth_service import AuthorizationService

        class PaymentService:
            def __init__(self):
                self.auth = AuthorizationService()

            def process_payment(self, user_id, amount):
                if not self.auth.authorize(user_id):
                    raise PermissionError("not authorized")
                return {"charged": amount}
    """)
    _write(repo, "reporting.py", """\
        def build_monthly_report(rows):
            total = 0
            for row in rows:
                total += row["amount"]
            return {"total": total}
    """)
    return repo


def _modify_get_user(repo: Path) -> str:
    _write(repo, "repository.py", """\
        class UserRepository:
            def get_user(self, user_id):
                if user_id is None:
                    raise ValueError("user_id required")
                return {"id": user_id, "name": "placeholder"}
    """)
    return _commit(repo, "modify get_user")


# A reliability finding in the shape IntelligenceProposal.to_dict() emits:
# a repo-relative path and a "start-end" line range, with no graph node id.
def _proposal_dict(path: str, line_range: str, severity: str, proposal_id: str) -> dict:
    return {
        "proposal_id": proposal_id,
        "bug_class": "crash_risks",
        "severity": severity,
        "problem_statement": "unchecked dict access",
        "affected_files": [{"path": path, "line_range": line_range, "severity": severity}],
    }


def test_e2e_multi_hop_finding_in_blast_radius_drives_the_verdict(chain_repo: Path):
    """The full path: diff -> graph -> 2-hop radius -> finding -> risk.

    The change is in repository.py; the finding is in payment_service.py,
    two call hops away. Nothing in the diff mentions payment_service.py, so
    the only way this finding can be reached is through the graph.
    """
    base = _commit(chain_repo, "base")
    target = _modify_get_user(chain_repo)

    finding = _proposal_dict("payment_service.py", "7-10", "critical", "prop-payment")
    report = ChangeRiskService().assess(str(chain_repo), base, target, findings=[finding])

    assert report.changed_file_count == 1
    resolved = [f for f in report.impact.finding_impacts if f.finding_ref == "prop-payment"]
    assert len(resolved) == 1
    assert resolved[0].relation in ("caller", "downstream")
    assert "PaymentService.process_payment" in resolved[0].resolved_node_id

    assert report.findings_in_blast_radius == 1
    assert report.risk_level == RiskLevel.CRITICAL
    assert report.recommendation == ReviewRecommendation.REQUIRES_HUMAN_REVIEW
    assert "payment_service.py:7-10" in [t.location for t in report.review_targets]


def test_e2e_finding_outside_blast_radius_does_not_affect_the_verdict(chain_repo: Path):
    """Negative control against a real graph, not a hand-built report.

    reporting.py is in the repo but nothing in the changed call chain reaches
    it, so a critical finding there must leave the verdict where a run with
    no findings at all leaves it.
    """
    base = _commit(chain_repo, "base")
    target = _modify_get_user(chain_repo)

    svc = ChangeRiskService()
    outside_finding = _proposal_dict("reporting.py", "1-5", "critical", "prop-reporting")
    outside = svc.assess(str(chain_repo), base, target, findings=[outside_finding])
    baseline = svc.assess(str(chain_repo), base, target)

    resolved = [f for f in outside.impact.finding_impacts if f.finding_ref == "prop-reporting"]
    assert len(resolved) == 1
    assert resolved[0].relation == "outside"
    assert "build_monthly_report" in resolved[0].resolved_node_id

    assert outside.findings_outside_blast_radius == 1
    assert outside.findings_in_blast_radius == 0
    assert outside.risk_level == baseline.risk_level
    assert _kinds(outside) == _kinds(baseline)
    assert outside.recommendation == baseline.recommendation

    # And the same finding moved into the affected area does change it —
    # otherwise the assertion above would pass on a scorer that reads no
    # findings at all.
    inside_finding = _proposal_dict("payment_service.py", "7-10", "critical", "prop-payment")
    inside = svc.assess(str(chain_repo), base, target, findings=[inside_finding])
    assert inside.risk_level == RiskLevel.CRITICAL
    assert RISK_LEVEL_RANK[inside.risk_level] > RISK_LEVEL_RANK[outside.risk_level]


def test_e2e_unresolvable_finding_location_is_conservative(chain_repo: Path):
    """An unparseable range in a changed file is reported, not guessed at."""
    base = _commit(chain_repo, "base")
    target = _modify_get_user(chain_repo)

    finding = _proposal_dict("repository.py", "not-a-range", "critical", "prop-broken")
    report = ChangeRiskService().assess(str(chain_repo), base, target, findings=[finding])

    resolved = [f for f in report.impact.finding_impacts if f.finding_ref == "prop-broken"]
    assert len(resolved) == 1
    assert resolved[0].relation == "unresolved"
    assert resolved[0].resolved_node_id == ""
    assert "unparseable" in resolved[0].reason

    assert report.findings_unresolved_location == 1
    assert report.risk_level == RiskLevel.MEDIUM
    assert report.recommendation == ReviewRecommendation.REVIEW_RECOMMENDED
    assert any(t.kind == "unresolved_location" for t in report.review_targets)


def test_e2e_finding_in_an_unknown_file_is_unresolved_not_outside(chain_repo: Path):
    base = _commit(chain_repo, "base")
    target = _modify_get_user(chain_repo)

    finding = _proposal_dict("does_not_exist.py", "1-5", "high", "prop-ghost")
    report = ChangeRiskService().assess(str(chain_repo), base, target, findings=[finding])

    resolved = [f for f in report.impact.finding_impacts if f.finding_ref == "prop-ghost"]
    assert resolved[0].relation == "unresolved"
    assert report.findings_outside_blast_radius == 0
    assert report.findings_unresolved_location == 1


def test_e2e_wide_line_range_resolves_to_the_narrowest_in_radius_symbol(chain_repo: Path):
    """A range covering a class and its method must resolve to the method.

    Reliability analyzers build line_range as min..max of every location
    matched in the file, so ranges routinely span a class and its methods.
    Both are graph nodes and both can be in the radius; the narrower one is
    the more useful answer, and the choice must not depend on id ordering.
    """
    base = _commit(chain_repo, "base")
    target = _modify_get_user(chain_repo)

    # auth_service.py lines 3-9 cover class AuthorizationService, __init__
    # and authorize.
    finding = _proposal_dict("auth_service.py", "3-9", "high", "prop-wide")
    report = ChangeRiskService().assess(str(chain_repo), base, target, findings=[finding])

    resolved = next(f for f in report.impact.finding_impacts if f.finding_ref == "prop-wide")
    assert resolved.relation in ("caller", "downstream")
    assert resolved.resolved_node_id.endswith("AuthorizationService.authorize")
    assert resolved.overlapping_symbol_count > 1
    assert any("spanning several symbols" in c for c in report.caveats)


def test_e2e_deterministic_across_two_runs(chain_repo: Path):
    base = _commit(chain_repo, "base")
    target = _modify_get_user(chain_repo)

    findings = [
        _proposal_dict("payment_service.py", "7-10", "critical", "prop-payment"),
        _proposal_dict("reporting.py", "1-5", "high", "prop-reporting"),
        _proposal_dict("repository.py", "not-a-range", "low", "prop-broken"),
    ]
    svc = ChangeRiskService()
    r1 = svc.assess(str(chain_repo), base, target, findings=findings)
    r2 = svc.assess(str(chain_repo), base, target, findings=list(reversed(findings)))

    assert r1.deterministic_hash == r2.deterministic_hash
    assert r1.to_dict() == r2.to_dict()


def test_e2e_no_changes_is_none_risk(chain_repo: Path):
    base = _commit(chain_repo, "base")
    report = ChangeRiskService().assess(str(chain_repo), base, base)
    assert report.changed_file_count == 0
    assert report.risk_level == RiskLevel.NONE
    assert report.recommendation == ReviewRecommendation.NO_REVIEW_REQUIRED


def test_e2e_ledger_records_impact_then_risk(chain_repo: Path):
    base = _commit(chain_repo, "base")
    target = _modify_get_user(chain_repo)

    events: List[dict] = []

    class FakeLedger:
        def append_event(self, event_type, summary, **kwargs):
            events.append({"event_type": event_type, "summary": summary, **kwargs})
            return True

    report = ChangeRiskService().assess(str(chain_repo), base, target, ledger=FakeLedger())

    assert [e["event_type"] for e in events] == [
        "CHANGE_IMPACT_ANALYZED",
        "CHANGE_RISK_ASSESSED",
    ]
    risk_event = events[1]
    assert risk_event["phase"] == "PHASE_20"
    assert risk_event["payload_ref"] == report.deterministic_hash
    assert risk_event["summary"] == report.summary


def test_e2e_ledger_failure_does_not_fail_the_assessment(chain_repo: Path):
    base = _commit(chain_repo, "base")
    target = _modify_get_user(chain_repo)

    class BrokenLedger:
        def append_event(self, *args, **kwargs):
            raise RuntimeError("ledger unavailable")

    report = ChangeRiskService().assess(str(chain_repo), base, target, ledger=BrokenLedger())
    assert report.deterministic_hash


def test_e2e_accepts_intelligence_proposal_objects(chain_repo: Path):
    """The analyzers hand out IntelligenceProposal objects, not dicts."""
    from agent.intelligence.proposal import (
        AffectedFile,
        BugClass,
        IntelligenceProposal,
        Severity,
    )

    base = _commit(chain_repo, "base")
    target = _modify_get_user(chain_repo)

    proposal = IntelligenceProposal(
        bug_class=BugClass.CRASH_RISKS,
        problem_statement="unchecked dict access in process_payment",
        severity=Severity.CRITICAL,
        affected_files=[
            AffectedFile(path="payment_service.py", line_range="7-10", severity=Severity.CRITICAL)
        ],
    )
    proposal.refresh_derived_proposal_id()

    report = ChangeRiskService().assess(str(chain_repo), base, target, findings=[proposal])

    refs = {f.finding_ref for f in report.impact.finding_impacts}
    assert proposal.proposal_id in refs
    assert report.findings_in_blast_radius == 1
    assert report.risk_level == RiskLevel.CRITICAL
