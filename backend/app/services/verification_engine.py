"""Deterministic verification and proof over explicit execution evidence."""

from __future__ import annotations

import hashlib
import json
import os
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
    test_execution_result: Optional[str] = None  # passed | failed | blocked | unavailable
    relevant_tests: Optional[Sequence[str]] = None
    static_analysis_executed: Optional[bool] = None
    static_analysis_result: Optional[str] = None  # passed | failed | completed | unavailable
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
    test_selection_provenance: Optional[str] = None
    target_identity: Optional[str] = None  # verified|mismatch|unverifiable|dirty
    target_identity_reason: Optional[str] = None


@dataclass(frozen=True)
class BehavioralTestComparison:
    """Deterministic base-vs-target comparison for one selected test.

    Node statuses are ``passed | failed | skipped | unavailable |
    execution_timeout``. A side that could not be executed (infrastructure
    failure, timeout, missing file, unparsable results) is ``unavailable`` —
    never coerced to passed or failed. ``execution_timeout`` marks a node that
    passed on the base revision but did not produce a terminal pytest result on
    the target revision because execution exceeded AGI Engineer's bounded
    execution boundary; it is an execution outcome, never a fabricated pytest
    node failure. ``baseline_outcome`` / ``target_outcome`` record where each
    disposition came from (see ``classify_execution_outcome``). ``regression``
    is True only when the same test node passed on the base revision and either
    failed or timed out under the execution boundary on the target revision;
    any unavailable element yields ``None`` (unknown), never a guessed verdict.
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
    baseline_outcome: Optional[Dict[str, Any]] = None
    target_outcome: Optional[Dict[str, Any]] = None
    timeout_attribution: Optional[str] = None
    timeout_attribution_source: Optional[str] = None

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
            "baseline_outcome": self.baseline_outcome,
            "target_outcome": self.target_outcome,
            "timeout_attribution": self.timeout_attribution,
            "timeout_attribution_source": self.timeout_attribution_source,
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


PROOF_HASH_SCHEMA = "agi-verification-proof-hash"
# v2: canonical payload gained target_identity (target-tree execution-boundary
#     provenance).
# v3: canonical payload gained test_selection_provenance (which tests, why) and
#     node_results_source (how node outcomes were obtained). Bumped so historical
#     v1/v2 hashes are not silently reinterpreted.
PROOF_HASH_VERSION = 3

# Target-tree identity at the verification execution boundary. Only VERIFIED
# permits trustworthy verification; every other value blocks it. See
# VerificationExecutor.execute.
TARGET_IDENTITY_VERIFIED = "verified"
TARGET_IDENTITY_MISMATCH = "mismatch"
TARGET_IDENTITY_UNVERIFIABLE = "unverifiable"
TARGET_IDENTITY_DIRTY = "dirty"

# Keys whose values are runtime/environment-specific (durations, raw captured
# output, absolute temp/worktree paths). They stay in the display/audit
# ``to_dict`` payload but are removed from the canonical hash payload so two
# semantically identical runs hash identically.
_VOLATILE_HASH_KEYS = frozenset(
    {
        "duration_ms",
        "stdout",
        "stderr",
        "working_directory",
        "discovered_test_count",
        "executed_test_count",
    }
)

_INTERPRETER_PLACEHOLDER = "<python>"


def _canonicalize_command(command: List[Any]) -> List[Any]:
    """Strip machine-specific paths from a captured command vector.

    The leading interpreter (an absolute path such as a venv's ``python``)
    collapses to a stable placeholder so any interpreter location hashes the
    same; any other absolute-path token is reduced to its basename. Relative
    arguments (module flags, test targets) are preserved verbatim.
    """
    normalized: List[Any] = []
    for index, token in enumerate(command):
        if isinstance(token, str) and os.path.isabs(token):
            normalized.append(
                _INTERPRETER_PLACEHOLDER if index == 0 else os.path.basename(token)
            )
        else:
            normalized.append(token)
    return normalized


def _normalize_selection_provenance(raw: Optional[str]) -> Optional[Any]:
    """Deterministic, first-class form of the test-selection provenance.

    Reuses the evidence's existing ``test_selection_provenance`` (a canonical
    JSON string of per-test selection records: test file identity, evidence
    tier, changed-symbol relation, deterministic reason). It is parsed and the
    record list re-sorted by stable identity so equivalent selections hash
    identically regardless of input ordering. Unparseable or ``unavailable``
    provenance is preserved verbatim (still deterministic) or dropped.
    """
    if not raw or raw == "unavailable":
        return None
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return raw
    if isinstance(data, list):
        return sorted(
            data,
            key=lambda record: (
                str(record.get("test_file", "")),
                str(record.get("changed_file", "")),
                str(record.get("changed_module", "")),
                str(record.get("evidence", "")),
            ),
        )
    return data


def _node_results_source(
    behavioral: Optional[Sequence["BehavioralTestComparison"]],
) -> Optional[Dict[str, List[str]]]:
    """How per-node outcomes were obtained, per behavioral side.

    Surfaces the existing ``node_results_source`` recorded on each behavioral
    bundle (lifecycle events vs -rA text summary vs none) as sorted, de-duped
    lists so ordering never affects the hash. ``None`` when no behavioral
    evidence is present.
    """
    if not behavioral:
        return None

    def _sources(attr: str) -> List[str]:
        found = set()
        for comparison in behavioral:
            bundle = getattr(comparison, attr, None)
            if isinstance(bundle, dict):
                source = bundle.get("node_results_source")
                if source:
                    found.add(str(source))
        return sorted(found)

    baseline = _sources("baseline_execution")
    target = _sources("target_execution")
    if not baseline and not target:
        return None
    return {"baseline": baseline, "target": target}


def _canonicalize_for_hash(value: Any) -> Any:
    """Recursively drop volatile evidence and normalize command vectors.

    Deterministic evidence (revisions, states, node outcomes, findings,
    checks, stable provenance) is preserved unchanged; only the enumerated
    volatile keys are removed and ``command`` vectors are path-normalized.
    """
    if isinstance(value, dict):
        canonical: Dict[str, Any] = {}
        for key, sub in value.items():
            if key in _VOLATILE_HASH_KEYS:
                continue
            if key == "command" and isinstance(sub, list):
                canonical[key] = _canonicalize_command(sub)
            else:
                canonical[key] = _canonicalize_for_hash(sub)
        return canonical
    if isinstance(value, list):
        return [_canonicalize_for_hash(item) for item in value]
    return value


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
    target_identity: Optional[str] = None
    target_identity_reason: Optional[str] = None
    test_selection_provenance: Optional[Any] = None
    node_results_source: Optional[Dict[str, List[str]]] = None
    reasons: List[str] = field(default_factory=list)
    hash_schema_version: int = PROOF_HASH_VERSION
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
            "target_identity": self.target_identity,
            "target_identity_reason": self.target_identity_reason,
            "test_selection_provenance": self.test_selection_provenance,
            "node_results_source": self.node_results_source,
            "reasons": self.reasons,
            "hash_schema_version": self.hash_schema_version,
            "deterministic_hash": self.deterministic_hash,
        }

    def canonical_hash_payload(self) -> Dict[str, Any]:
        """The semantically deterministic evidence the proof hash covers.

        Derived from ``to_dict`` with the mutable ``deterministic_hash``
        removed and all runtime/environment-specific values normalized away
        (see ``_canonicalize_for_hash``). The result is wrapped with an
        explicit schema identifier and version so historical proof-hash
        meaning stays stable and future schema evolution is an intentional,
        visible change rather than a silent one.
        """
        return _canonical_hash_payload_from_dict(self.to_dict())

    def finalize(self) -> "VerificationProof":
        self.deterministic_hash = _hash_canonical_payload(self.canonical_hash_payload())
        return self


def _canonical_hash_payload_from_dict(proof_payload: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(proof_payload)
    payload.pop("deterministic_hash", None)
    version = payload.get("hash_schema_version", PROOF_HASH_VERSION)
    return {
        "schema": PROOF_HASH_SCHEMA,
        "version": version,
        "proof": _canonicalize_for_hash(payload),
    }


def _hash_canonical_payload(canonical: Dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def recompute_proof_hash(proof_payload: Any) -> Optional[str]:
    """Recompute a persisted proof body's deterministic hash, or ``None``.

    Applies the identical canonicalization and SHA-256 the proof used at write
    time (``_canonical_hash_payload_from_dict`` + ``_hash_canonical_payload``),
    so a body that is byte-for-byte the finalized ``to_dict`` reproduces its own
    ``deterministic_hash``. Returns ``None`` for a missing or unhashable body;
    the proof is never mutated or repaired.
    """
    if not isinstance(proof_payload, dict) or not proof_payload:
        return None
    try:
        return _hash_canonical_payload(_canonical_hash_payload_from_dict(proof_payload))
    except (TypeError, ValueError):
        return None


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

        target_identity_failed = (
            evidence.target_identity is not None
            and evidence.target_identity != TARGET_IDENTITY_VERIFIED
        )
        blocked = evidence.blocked_reason is not None
        blocked = blocked or evidence.test_execution_result in {"failed", "blocked"}
        blocked = blocked or evidence.static_analysis_result == "failed"
        blocked = blocked or bool(new_findings)
        blocked = blocked or target_identity_failed

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
        if evidence.test_execution_result == "unavailable":
            reasons.append(
                "test execution evidence is unavailable: pytest did not produce a "
                "genuine per-node result (collection failure, timeout, or execution error)"
            )
        if evidence.static_analysis_executed is True:
            reasons.append(
                f"static analysis execution result is {evidence.static_analysis_result or 'unknown'}"
            )
        elif evidence.static_analysis_result == "unavailable":
            reasons.append(
                "static analysis evidence is unavailable: analyzer did not execute or "
                "terminated without producing findings evidence"
            )
        if new_findings:
            reasons.append(f"{len(new_findings)} new finding(s) were introduced")
        elif findings_before is None or findings_after is None:
            reasons.append("finding comparison evidence is unavailable")
        else:
            reasons.append("finding comparison found no newly introduced findings")
        if impact.confidence == Confidence.LOW:
            reasons.append("impact confidence is low; verification coverage may be incomplete")
        if target_identity_failed:
            reasons.append(
                "target-tree identity was not established; verification cannot be trusted"
                + (f": {evidence.target_identity_reason}" if evidence.target_identity_reason else "")
            )
        elif evidence.target_identity == TARGET_IDENTITY_VERIFIED:
            reasons.append("target-tree identity verified against the expected revision")
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
            target_identity=evidence.target_identity,
            target_identity_reason=evidence.target_identity_reason,
            test_selection_provenance=_normalize_selection_provenance(
                evidence.test_selection_provenance
            ),
            node_results_source=_node_results_source(evidence.behavioral),
            reasons=sorted(set(reasons)),
        )
        return proof.finalize()