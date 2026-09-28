"""Deterministic verification and proof over explicit execution evidence."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from app.models.change_impact import ChangeImpactReport, Confidence, RiskLevel
from app.services.change_risk_engine import ChangeRiskAssessment
from app.services.finding_context import FindingContext


class VerificationState(str, Enum):
    VERIFIED = "verified"
    PARTIALLY_VERIFIED = "partially_verified"
    UNVERIFIED = "unverified"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class VerificationEvidence:
    """Facts supplied by an actual test/static-analysis execution boundary.

    ``None`` means unavailable. An empty collection means the boundary ran and
    found nothing, which is deliberately different from unavailable evidence.
    """

    tests_discovered: Optional[Sequence[str]] = None
    tests_executed: Optional[Sequence[str]] = None
    test_execution_result: Optional[str] = None  # passed | failed | blocked
    relevant_tests: Optional[Sequence[str]] = None
    static_analysis_executed: Optional[bool] = None
    static_analysis_result: Optional[str] = None  # passed | failed | completed
    findings_before: Optional[Sequence[Any]] = None
    findings_after: Optional[Sequence[Any]] = None
    blocked_reason: Optional[str] = None
    command_results: Optional[Sequence[Dict[str, Any]]] = None
    relevant_test_selection: Optional[str] = None
    baseline_status: Optional[str] = None
    comparison_status: Optional[str] = None
    baseline_error: Optional[str] = None
    comparison_findings_before: Optional[Sequence[Any]] = None
    comparison_findings_after: Optional[Sequence[Any]] = None
    behavioral: Optional[Sequence["BehavioralTestComparison"]] = None


@dataclass(frozen=True)
class BehavioralTestComparison:
    """Deterministic base-vs-target comparison for one selected test.

    Node statuses are ``passed | failed | skipped | unavailable``. A side that
    could not be executed (infrastructure failure, timeout, missing file,
    unparsable results) is ``unavailable`` — never coerced to passed or
    failed. ``regression`` is True only when the same test node passed on the
    base revision and failed on the target revision; any unavailable element
    yields ``None`` (unknown), never a guessed verdict.
    """

    test_file: Optional[str]
    test_node_id: Optional[str]
    baseline_status: str
    target_status: str
    regression: Optional[bool]
    comparison_status: str  # REGRESSION | PRE_EXISTING | CONSISTENT | IMPROVED | UNKNOWN
    changed_files: List[str] = field(default_factory=list)
    changed_symbols: List[str] = field(default_factory=list)
    selection_provenance: str = ""
    baseline_execution: Dict[str, Any] = field(default_factory=dict)
    target_execution: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_file": self.test_file,
            "test_node_id": self.test_node_id,
            "baseline_status": self.baseline_status,
            "target_status": self.target_status,
            "regression": self.regression,
            "comparison_status": self.comparison_status,
            "changed_files": list(self.changed_files),
            "changed_symbols": list(self.changed_symbols),
            "selection_provenance": self.selection_provenance,
            "baseline_execution": self.baseline_execution,
            "target_execution": self.target_execution,
        }


def _sorted_strings(values: Optional[Iterable[str]]) -> Optional[List[str]]:
    if values is None:
        return None
    return sorted({str(value) for value in values})


def _finding_key(finding: Any) -> str:
    if isinstance(finding, FindingContext):
        if finding.symbol_node_id:
            return "|".join(
                (finding.file_path, finding.rule_code, finding.symbol_node_id)
            )
        return finding.finding_ref
    if isinstance(finding, dict):
        path = str(finding.get("file_path", "")).replace("\\", "/").lstrip("./")
        code = str(finding.get("issue_code") or finding.get("rule_code") or "")
        symbol = finding.get("symbol") or finding.get("symbol_node_id")
        if symbol:
            return "|".join((path, code, str(symbol)))
        message = str(finding.get("message") or finding.get("issue_name") or "")
        message = re.sub(r"\bline\s+\d+\b", "line", message, flags=re.IGNORECASE)
        message = re.sub(r"\s+", " ", message).strip()
        return json.dumps(
            {
                "file_path": path,
                "issue_code": code,
                "message": message,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    return str(finding)


def _finding_keys(findings: Optional[Sequence[Any]]) -> Optional[List[str]]:
    if findings is None:
        return None
    return sorted({_finding_key(finding) for finding in findings})


def _finding_location(finding: Any) -> Tuple[Optional[str], Optional[str]]:
    if isinstance(finding, FindingContext):
        return finding.file_path or None, finding.symbol_node_id
    if isinstance(finding, dict):
        path = str(finding.get("file_path") or "").replace("\\", "/").lstrip("./")
        symbol = finding.get("symbol_id") or finding.get("node_id")
        symbol = symbol or finding.get("symbol_node_id") or finding.get("symbol")
        return path or None, str(symbol) if symbol else None
    return None, None


def _attribute_finding(
    finding: Any,
    impact: ChangeImpactReport,
) -> Dict[str, Any]:
    path, symbol = _finding_location(finding)
    direct = set(impact.directly_affected_symbols)
    callers = set(impact.callers)
    downstream = set(impact.downstream_symbols)
    changed_files = set(impact.changed_files)

    if symbol in direct:
        attribution = "DIRECT_CHANGE"
        relationship = "changed symbol"
    elif symbol in callers:
        attribution = "CALLER_IMPACT"
        relationship = "caller of changed symbol"
    elif symbol in downstream:
        attribution = "DOWNSTREAM_IMPACT"
        relationship = "downstream of changed symbol"
    elif path and path in changed_files:
        attribution = "CHANGED_FILE"
        relationship = "changed file without resolved symbol"
    elif path:
        attribution = "OUTSIDE_IMPACT"
        relationship = "outside changed files and known impact relationships"
    elif symbol or path is None:
        attribution = "UNRESOLVED"
        relationship = "finding has insufficient file or symbol location evidence"
    else:
        attribution = "UNKNOWN"
        relationship = "relationship could not be classified deterministically"

    return {
        "finding": _finding_key(finding),
        "attribution": attribution,
        "file_path": path,
        "symbol": symbol,
        "relationship": relationship,
    }


def _context_key(context: FindingContext) -> Tuple[str, str, int]:
    return (context.finding_ref, context.file_path, context.line_number)


@dataclass
class VerificationProof:
    """A bounded, explainable proof state derived from supplied evidence."""

    state: VerificationState
    tests_discovered: Optional[List[str]]
    tests_executed: Optional[List[str]]
    test_execution_result: Optional[str]
    static_analysis_executed: Optional[bool]
    static_analysis_result: Optional[str]
    findings_before: Optional[List[str]]
    findings_after: Optional[List[str]]
    new_findings: Optional[List[str]]
    unchanged_findings: Optional[List[str]]
    resolved_findings: Optional[List[str]]
    new_findings_attribution: Optional[List[Dict[str, Any]]]
    command_results: Optional[List[Dict[str, Any]]]
    relevant_test_selection: Optional[str]
    baseline_status: Optional[str]
    comparison_status: Optional[str]
    baseline_error: Optional[str]
    affected_symbols: List[str]
    affected_files: List[str]
    change_risk: str
    required_checks: List[str] = field(default_factory=list)
    completed_checks: List[str] = field(default_factory=list)
    missing_checks: List[str] = field(default_factory=list)
    verification_confidence: str = "unknown"
    behavioral_regressions: Optional[List[Dict[str, Any]]] = None
    behavioral_comparison_status: Optional[str] = None
    reasons: List[str] = field(default_factory=list)
    deterministic_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "tests_discovered": self.tests_discovered,
            "tests_executed": self.tests_executed,
            "test_execution_result": self.test_execution_result,
            "static_analysis_executed": self.static_analysis_executed,
            "static_analysis_result": self.static_analysis_result,
            "findings_before": self.findings_before,
            "findings_after": self.findings_after,
            "new_findings": self.new_findings,
            "unchanged_findings": self.unchanged_findings,
            "resolved_findings": self.resolved_findings,
            "new_findings_attribution": self.new_findings_attribution,
            "command_results": self.command_results,
            "relevant_test_selection": self.relevant_test_selection,
            "baseline_status": self.baseline_status,
            "comparison_status": self.comparison_status,
            "baseline_error": self.baseline_error,
            "affected_symbols": self.affected_symbols,
            "affected_files": self.affected_files,
            "change_risk": self.change_risk,
            "required_checks": self.required_checks,
            "completed_checks": self.completed_checks,
            "missing_checks": self.missing_checks,
            "verification_confidence": self.verification_confidence,
            "behavioral_regressions": self.behavioral_regressions,
            "behavioral_comparison_status": self.behavioral_comparison_status,
            "reasons": self.reasons,
            "deterministic_hash": self.deterministic_hash,
        }

    def finalize(self) -> "VerificationProof":
        payload = self.to_dict()
        payload.pop("deterministic_hash")
        self.deterministic_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return self


class VerificationEngine:
    """Evaluate verification state without inferring execution success."""

    def assess(
        self,
        impact: ChangeImpactReport,
        contexts: Sequence[FindingContext],
        risk: ChangeRiskAssessment,
        evidence: Optional[VerificationEvidence] = None,
    ) -> VerificationProof:
        evidence = evidence or VerificationEvidence()
        tests_discovered = _sorted_strings(evidence.tests_discovered)
        tests_executed = _sorted_strings(evidence.tests_executed)
        comparison_before = (
            evidence.comparison_findings_before
            if evidence.comparison_findings_before is not None
            else evidence.findings_before
        )
        comparison_after = (
            evidence.comparison_findings_after
            if evidence.comparison_findings_after is not None
            else evidence.findings_after
        )
        findings_before = _finding_keys(comparison_before)
        findings_after = _finding_keys(comparison_after)

        if findings_before is not None and findings_after is not None:
            before = set(findings_before)
            after = set(findings_after)
            new_findings = sorted(after - before)
            unchanged_findings = sorted(before & after)
            resolved_findings = sorted(before - after)
            after_by_key = {_finding_key(finding): finding for finding in comparison_after or []}
            new_findings_attribution = [
                _attribute_finding(after_by_key[key], impact)
                for key in sorted(after - before)
            ]
        else:
            new_findings = None
            unchanged_findings = None
            resolved_findings = None
            new_findings_attribution = None

        high_risk = risk.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}
        required_checks = ["static_analysis_execution", "test_execution"]
        if findings_before is None or findings_after is None:
            required_checks.append("finding_comparison")
        if impact.confidence == Confidence.LOW:
            required_checks.append("impact_confidence")
        if high_risk:
            required_checks.extend(["relevant_test_evidence", "impact_confidence"])
        required_checks = sorted(set(required_checks))

        completed_checks: List[str] = []
        if evidence.static_analysis_executed is True and evidence.static_analysis_result in {
            "passed",
            "completed",
        }:
            completed_checks.append("static_analysis_execution")
        if (
            tests_executed
            and evidence.test_execution_result == "passed"
        ):
            completed_checks.append("test_execution")
        if tests_executed and evidence.relevant_tests:
            completed_checks.append("relevant_test_evidence")
        if findings_before is not None and findings_after is not None:
            completed_checks.append("finding_comparison")
        if impact.confidence != Confidence.LOW:
            completed_checks.append("impact_confidence")
        completed_checks = sorted(set(completed_checks))
        missing_checks = sorted(set(required_checks) - set(completed_checks))

        blocked = evidence.blocked_reason is not None
        blocked = blocked or evidence.test_execution_result in {"failed", "blocked"}
        blocked = blocked or evidence.static_analysis_result == "failed"
        blocked = blocked or bool(new_findings)

        if blocked:
            state = VerificationState.BLOCKED
        elif not (set(completed_checks) - {"impact_confidence"}):
            state = VerificationState.UNVERIFIED
        elif missing_checks:
            state = VerificationState.PARTIALLY_VERIFIED
        else:
            state = VerificationState.VERIFIED

        if state is VerificationState.VERIFIED:
            confidence = "high"
        elif impact.confidence == Confidence.LOW:
            confidence = "low"
        elif set(completed_checks) - {"impact_confidence"}:
            confidence = "medium"
        else:
            confidence = "unknown"

        ordered_contexts = sorted(contexts, key=_context_key)
        affected_symbols = sorted(
            {
                context.symbol_node_id
                for context in ordered_contexts
                if context.symbol_node_id
            }
            | set(impact.directly_affected_symbols)
            | set(impact.callers)
            | set(impact.downstream_symbols)
        )
        affected_files = sorted(
            set(impact.changed_files)
            | {
                context.file_path
                for context in ordered_contexts
                if context.change_relation in {"direct", "caller", "downstream"}
            }
        )

        reasons = []
        if not tests_discovered:
            reasons.append("test discovery evidence is unavailable or found no tests")
        elif not tests_executed:
            reasons.append("tests were discovered but no test execution evidence exists")
        if tests_executed and evidence.test_execution_result == "passed":
            reasons.append("executed tests reported a pass")
        if evidence.static_analysis_executed is True:
            reasons.append(
                f"static analysis execution result is {evidence.static_analysis_result or 'unknown'}"
            )
        if new_findings:
            reasons.append(f"{len(new_findings)} new finding(s) were introduced")
        elif findings_before is None or findings_after is None:
            reasons.append("finding comparison evidence is unavailable")
        else:
            reasons.append("finding comparison found no newly introduced findings")
        if impact.confidence == Confidence.LOW:
            reasons.append("impact confidence is low; verification coverage may be incomplete")
        if evidence.blocked_reason:
            reasons.append(f"verification is blocked: {evidence.blocked_reason}")
        if missing_checks:
            reasons.append("missing checks: " + ", ".join(missing_checks))

        # Behavioral regression evidence: pass-through only. It never changes
        # the state machine, required checks, or risk scoring; it explains
        # WHICH target-side failures are mutation-attributable.
        behavioral_regressions: Optional[List[Dict[str, Any]]] = None
        behavioral_comparison_status: Optional[str] = None
        if evidence.behavioral is not None:
            behavioral_regressions = [
                comparison.to_dict()
                for comparison in evidence.behavioral
                if comparison.regression is True
            ]
            if any(c.comparison_status == "REGRESSION" for c in evidence.behavioral):
                behavioral_comparison_status = "REGRESSIONS_FOUND"
            elif all(
                c.comparison_status in ("CONSISTENT", "PRE_EXISTING", "IMPROVED")
                for c in evidence.behavioral
            ):
                behavioral_comparison_status = "NO_REGRESSIONS"
            else:
                behavioral_comparison_status = "UNKNOWN"
            if behavioral_regressions:
                reasons.append(
                    f"behavioral regression evidence: {len(behavioral_regressions)} "
                    f"test(s) passed on the base revision and failed on the target revision"
                )

        proof = VerificationProof(
            state=state,
            tests_discovered=tests_discovered,
            tests_executed=tests_executed,
            test_execution_result=evidence.test_execution_result,
            static_analysis_executed=evidence.static_analysis_executed,
            static_analysis_result=evidence.static_analysis_result,
            findings_before=findings_before,
            findings_after=findings_after,
            new_findings=new_findings,
            unchanged_findings=unchanged_findings,
            resolved_findings=resolved_findings,
            new_findings_attribution=new_findings_attribution,
            command_results=(
                sorted(
                    [dict(result) for result in evidence.command_results],
                    key=lambda result: (
                        str(result.get("check", "")),
                        json.dumps(result, sort_keys=True, default=str),
                    ),
                )
                if evidence.command_results is not None
                else None
            ),
            relevant_test_selection=evidence.relevant_test_selection,
            baseline_status=evidence.baseline_status,
            comparison_status=evidence.comparison_status,
            baseline_error=evidence.baseline_error,
            affected_symbols=affected_symbols,
            affected_files=affected_files,
            change_risk=risk.risk_level.value,
            required_checks=required_checks,
            completed_checks=completed_checks,
            missing_checks=missing_checks,
            verification_confidence=confidence,
            behavioral_regressions=behavioral_regressions,
            behavioral_comparison_status=behavioral_comparison_status,
            reasons=sorted(set(reasons)),
        )
        return proof.finalize()