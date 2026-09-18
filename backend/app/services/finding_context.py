"""Deterministic Finding Context / Relevance layer, after analyzers, before the report."""

from __future__ import annotations

import hashlib
import json
import posixpath
import re
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple


class FileClass(str, Enum):
    APPLICATION = "application"
    TYPE_STUB = "type_stub"
    GENERATED = "generated"
    VENDORED = "vendored"
    TEST = "test"
    TEST_FIXTURE = "test_fixture"
    DOCUMENTATION = "documentation"
    BUILD_CONFIG = "build_config"


class Relevance(str, Enum):
    ACTIONABLE = "actionable"
    REVIEW = "review"
    INFORMATIONAL = "informational"
    UNKNOWN = "unknown"


class Recommendation(str, Enum):
    FIX = "fix"
    REVIEW = "review"
    ACKNOWLEDGE = "acknowledge"
    SUPPRESS_CANDIDATE = "suppress_candidate"


_VENDOR_SEGMENTS = frozenset({
    "vendor", "vendored", "third_party", "thirdparty", "3rdparty",
    "node_modules", "site-packages", "dist-packages", "bundled",
    "external", "externals", "_vendor",
})

_TEST_SEGMENTS = frozenset({
    "test", "tests", "testing", "spec", "specs", "__tests__",
})

_FIXTURE_SEGMENTS = frozenset({
    "fixtures", "fixture", "testdata", "test_data", "snapshots",
    "__snapshots__", "golden", "cassettes",
})

_DOC_SEGMENTS = frozenset({
    "docs", "doc", "documentation", "examples", "example", "samples",
    "sample", "demo", "demos", "tutorial", "tutorials",
})

_GENERATED_SEGMENTS = frozenset({
    "generated", "_generated", "autogen", "build", "dist",
    "migrations", "__pycache__", ".next", "out", "target",
    "protos", "swagger", "openapi",
})

_BUILD_CONFIG_NAMES = frozenset({
    "setup.py", "conftest.py", "manage.py", "noxfile.py", "tasks.py",
    "setup.cfg", "pyproject.toml", "tox.ini", ".eslintrc.json",
    "webpack.config.js", "rollup.config.js", "vite.config.js",
    "jest.config.js", "babel.config.js", "next.config.js",
})

_DOC_SUFFIXES = (".md", ".rst", ".txt", ".adoc", ".ipynb")
_BUILD_CONFIG_SUFFIXES = (".toml", ".ini", ".cfg", ".lock")

_GENERATED_STEM_PATTERNS = (
    re.compile(r"_pb2(_grpc)?$"),
    re.compile(r"\.generated$"),
    re.compile(r"_generated$"),
    re.compile(r"^generated_"),
)

_GENERATED_NAME_SUFFIXES = (".min.js", ".min.css", ".bundle.js", ".map")

_TEST_NAME_PATTERNS = (
    re.compile(r"^test_"),
    re.compile(r"_test$"),
    re.compile(r"\.test$"),
    re.compile(r"\.spec$"),
)

_STUB_TREE_ROOTS = ("stubs", "stdlib")


def _normalize_path(path: str) -> str:
    return path.replace("\\", "/").strip()


def _segments(normalized: str) -> Tuple[str, ...]:
    return tuple(part for part in normalized.split("/") if part and part != ".")


@dataclass(frozen=True)
class FileClassification:
    file_class: FileClass
    reasons: Tuple[str, ...] = ()
    also: Tuple[FileClass, ...] = ()


_CLASS_PRECEDENCE = (
    FileClass.VENDORED,
    FileClass.GENERATED,
    FileClass.TYPE_STUB,
    FileClass.TEST_FIXTURE,
    FileClass.TEST,
    FileClass.DOCUMENTATION,
    FileClass.BUILD_CONFIG,
)


def classify_file(path: str) -> FileClassification:
    normalized = _normalize_path(path)
    if not normalized:
        return FileClassification(FileClass.APPLICATION, ("empty path",))

    segs = _segments(normalized)
    lower_segs = tuple(s.lower() for s in segs)
    name = segs[-1] if segs else ""
    lower_name = name.lower()
    stem, _, suffix = lower_name.rpartition(".")
    if not stem:
        stem, suffix = lower_name, ""
    dot_suffix = f".{suffix}" if suffix else ""

    matched: List[Tuple[FileClass, str]] = []

    for seg in lower_segs[:-1]:
        if seg in _VENDOR_SEGMENTS:
            matched.append((FileClass.VENDORED, f"path segment '{seg}'"))
        if seg in _GENERATED_SEGMENTS:
            matched.append((FileClass.GENERATED, f"path segment '{seg}'"))
        if seg in _FIXTURE_SEGMENTS:
            matched.append((FileClass.TEST_FIXTURE, f"path segment '{seg}'"))
        if seg in _TEST_SEGMENTS:
            matched.append((FileClass.TEST, f"path segment '{seg}'"))
        if seg in _DOC_SEGMENTS:
            matched.append((FileClass.DOCUMENTATION, f"path segment '{seg}'"))

    if dot_suffix == ".pyi":
        matched.append((FileClass.TYPE_STUB, "'.pyi' type-stub extension"))
    if lower_name.endswith(".d.ts"):
        matched.append((FileClass.TYPE_STUB, "'.d.ts' declaration file"))
    if lower_segs and lower_segs[0] in _STUB_TREE_ROOTS:
        matched.append((FileClass.TYPE_STUB, f"top-level '{lower_segs[0]}/' stub tree"))

    for pattern in _GENERATED_STEM_PATTERNS:
        if pattern.search(stem):
            matched.append((FileClass.GENERATED, f"filename stem matches /{pattern.pattern}/"))
            break
    for gen_suffix in _GENERATED_NAME_SUFFIXES:
        if lower_name.endswith(gen_suffix):
            matched.append((FileClass.GENERATED, f"'{gen_suffix}' build artifact"))
            break

    for pattern in _TEST_NAME_PATTERNS:
        if pattern.search(stem):
            matched.append((FileClass.TEST, f"filename matches /{pattern.pattern}/"))
            break

    if dot_suffix in _DOC_SUFFIXES:
        matched.append((FileClass.DOCUMENTATION, f"'{dot_suffix}' document"))
    if lower_name in _BUILD_CONFIG_NAMES or dot_suffix in _BUILD_CONFIG_SUFFIXES:
        matched.append((FileClass.BUILD_CONFIG, f"'{lower_name}' build/config file"))

    if not matched:
        return FileClassification(
            FileClass.APPLICATION,
            ("no stub/vendor/generated/test marker in path",),
        )

    by_class: Dict[FileClass, List[str]] = {}
    for file_class, reason in matched:
        by_class.setdefault(file_class, []).append(reason)

    primary = next(fc for fc in _CLASS_PRECEDENCE if fc in by_class)
    reasons = tuple(sorted(set(by_class[primary])))
    also = tuple(fc for fc in _CLASS_PRECEDENCE if fc in by_class and fc is not primary)
    return FileClassification(primary, reasons, also)


@dataclass(frozen=True)
class RuleSemantics:
    code: str
    description: str
    premise_broken_in: Tuple[FileClass, ...] = ()
    premise_weakened_in: Tuple[FileClass, ...] = ()


_RULE_SEMANTICS: Dict[str, RuleSemantics] = {
    "F811": RuleSemantics(
        "F811", "Redefinition of unused name",
        premise_broken_in=(FileClass.TYPE_STUB,),
        premise_weakened_in=(FileClass.GENERATED, FileClass.VENDORED, FileClass.TEST_FIXTURE),
    ),
    "F401": RuleSemantics(
        "F401", "Unused import",
        premise_broken_in=(FileClass.TYPE_STUB,),
        premise_weakened_in=(FileClass.GENERATED, FileClass.VENDORED, FileClass.DOCUMENTATION),
    ),
    "F403": RuleSemantics(
        "F403", "Star import",
        premise_broken_in=(FileClass.TYPE_STUB,),
        premise_weakened_in=(FileClass.GENERATED, FileClass.VENDORED),
    ),
    "F405": RuleSemantics(
        "F405", "Name may be undefined from star import",
        premise_broken_in=(FileClass.TYPE_STUB,),
        premise_weakened_in=(FileClass.GENERATED, FileClass.VENDORED),
    ),
    "F841": RuleSemantics(
        "F841", "Unused local variable",
        premise_weakened_in=(
            FileClass.TEST, FileClass.TEST_FIXTURE, FileClass.GENERATED, FileClass.VENDORED,
        ),
    ),
    "E501": RuleSemantics(
        "E501", "Line too long",
        premise_weakened_in=(
            FileClass.GENERATED, FileClass.VENDORED, FileClass.TYPE_STUB,
            FileClass.DOCUMENTATION, FileClass.TEST_FIXTURE,
        ),
    ),
    "E701": RuleSemantics(
        "E701", "Multiple statements on one line",
        premise_broken_in=(FileClass.TYPE_STUB,),
        premise_weakened_in=(FileClass.GENERATED,),
    ),
    "E702": RuleSemantics(
        "E702", "Unnecessary semicolon",
        premise_weakened_in=(FileClass.GENERATED, FileClass.VENDORED),
    ),
    "no-unused-vars": RuleSemantics(
        "no-unused-vars", "Unused variable",
        premise_broken_in=(FileClass.TYPE_STUB,),
        premise_weakened_in=(FileClass.TEST, FileClass.GENERATED, FileClass.VENDORED),
    ),
    "no-undef": RuleSemantics(
        "no-undef", "Undefined name",
        premise_broken_in=(FileClass.TYPE_STUB,),
        premise_weakened_in=(FileClass.GENERATED, FileClass.VENDORED),
    ),
    "no-console": RuleSemantics(
        "no-console", "Console statement",
        premise_weakened_in=(
            FileClass.TEST, FileClass.DOCUMENTATION, FileClass.BUILD_CONFIG,
            FileClass.GENERATED, FileClass.VENDORED,
        ),
    ),
}

_GENERIC_WEAKENED_IN = (
    FileClass.GENERATED, FileClass.VENDORED, FileClass.TEST_FIXTURE,
    FileClass.DOCUMENTATION,
)


def rule_semantics(code: str) -> RuleSemantics:
    known = _RULE_SEMANTICS.get(code)
    if known:
        return known
    return RuleSemantics(code, f"Rule {code}", premise_weakened_in=_GENERIC_WEAKENED_IN)


_BASE_CONFIDENCE = 75

_CONFIDENCE_ADJUSTMENTS: Dict[FileClass, int] = {
    FileClass.APPLICATION: 0,
    FileClass.BUILD_CONFIG: -10,
    FileClass.TEST: -15,
    FileClass.DOCUMENTATION: -25,
    FileClass.TEST_FIXTURE: -30,
    FileClass.GENERATED: -40,
    FileClass.VENDORED: -45,
    FileClass.TYPE_STUB: -50,
}

_PREMISE_BROKEN_CEILING = 20
_UNREACHABLE_PENALTY = -15
_REACHABLE_BONUS = 10
_CORRELATED_PENALTY = -5


def _clamp(value: int, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, value))


@dataclass
class FindingContext:
    finding_ref: str
    file_path: str
    line_number: int
    rule_code: str

    file_class: FileClass = FileClass.APPLICATION
    classification_reasons: List[str] = field(default_factory=list)
    secondary_file_classes: List[FileClass] = field(default_factory=list)

    symbol: Optional[str] = None
    symbol_node_id: Optional[str] = None
    caller_count: Optional[int] = None
    downstream_count: Optional[int] = None
    production_reachable: Optional[bool] = None
    reachability_reason: str = ""

    change_relation: Optional[str] = None

    relevance: Relevance = Relevance.UNKNOWN
    relevance_reasons: List[str] = field(default_factory=list)
    confidence: int = _BASE_CONFIDENCE
    confidence_reasons: List[str] = field(default_factory=list)
    severity: str = "warning"
    recommendation: Recommendation = Recommendation.REVIEW

    correlation_id: Optional[str] = None
    correlated_count: int = 1

    context_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["file_class"] = self.file_class.value
        payload["relevance"] = self.relevance.value
        payload["recommendation"] = self.recommendation.value
        payload["secondary_file_classes"] = [c.value for c in self.secondary_file_classes]
        return payload

    def context_hash(self) -> str:
        return hashlib.sha256(
            json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


def _finding_ref(finding: Dict[str, Any]) -> str:
    existing = finding.get("finding_ref") or finding.get("proposal_id")
    if existing:
        return str(existing)
    basis = "|".join([
        str(finding.get("file_path", "")),
        str(finding.get("line_number", 0)),
        str(finding.get("issue_code", "")),
        str(finding.get("message", "")),
    ])
    return hashlib.sha256(basis.encode()).hexdigest()[:16]


_SYMBOL_IN_MESSAGE = re.compile(r"`([A-Za-z_][A-Za-z0-9_.]*)`")


def _symbol_from_message(message: str) -> Optional[str]:
    match = _SYMBOL_IN_MESSAGE.search(message or "")
    return match.group(1) if match else None


def _enrich_from_graph(context: FindingContext, graph: Any) -> None:
    if graph is None:
        return
    try:
        nodes = graph.nodes
    except Exception:
        context.reachability_reason = "graph unavailable"
        return

    candidates = [
        node for node in nodes.values()
        if getattr(node, "file_path", None) == context.file_path
    ]
    if not candidates:
        context.reachability_reason = f"file not present in code graph ({context.file_path})"
        return

    line = context.line_number
    enclosing = None
    for node in candidates:
        start = getattr(node, "line_number", None)
        if start is None:
            continue
        end = (getattr(node, "metadata", {}) or {}).get("end_line")
        if start <= line and (end is None or line <= end):
            if enclosing is None or start > getattr(enclosing, "line_number", -1):
                enclosing = node

    if enclosing is None:
        context.reachability_reason = "no symbol in graph encloses this line"
        return

    context.symbol = getattr(enclosing, "name", None) or context.symbol
    context.symbol_node_id = getattr(enclosing, "id", None)

    try:
        context.caller_count = len(graph.get_callers(context.symbol_node_id))
    except Exception:
        context.caller_count = None
    try:
        context.downstream_count = max(
            0, len(graph.get_impact_set(context.symbol_node_id, max_depth=3))
        )
    except Exception:
        context.downstream_count = None

    if context.caller_count is not None or context.downstream_count is not None:
        caller_text = (
            f"{context.caller_count} caller(s)"
            if context.caller_count is not None
            else "caller count unavailable"
        )
        downstream_text = (
            f"{context.downstream_count} transitively affected symbol(s)"
            if context.downstream_count is not None
            else "downstream count unavailable"
        )
        context.reachability_reason = (
            f"call-graph evidence: {caller_text}, {downstream_text}; "
            "runtime/production reachability is not established"
        )


def _enrich_from_impact(context: FindingContext, impact: Any) -> None:
    if impact is None:
        return
    try:
        rows = impact.finding_impacts
    except Exception:
        return
    matches = [
        row for row in rows
        if getattr(row, "finding_ref", None) == context.finding_ref
    ]
    if not matches:
        return

    path_matches = [
        row for row in matches
        if getattr(row, "file_path", None) == context.file_path
    ]
    if path_matches:
        matches = path_matches
    elif len(matches) != 1:
        # A multi-location finding must not borrow evidence from a different
        # file merely because it shares the proposal id.
        return

    row = matches[0]
    context.change_relation = getattr(row, "relation", None)
    resolved = getattr(row, "resolved_node_id", "")
    if resolved and not context.symbol_node_id:
        context.symbol_node_id = resolved
    severity = getattr(row, "severity", None)
    if severity and severity != "unknown":
        context.severity = severity


def _score(context: FindingContext, semantics: RuleSemantics) -> None:
    file_class = context.file_class
    confidence = _BASE_CONFIDENCE
    confidence_reasons = [f"base confidence {_BASE_CONFIDENCE} for a static-pattern match"]
    relevance_reasons: List[str] = []

    adjustment = _CONFIDENCE_ADJUSTMENTS.get(file_class, 0)
    if adjustment:
        confidence += adjustment
        confidence_reasons.append(
            f"{adjustment:+d} because the file is classified {file_class.value}"
        )

    premise_broken = file_class in semantics.premise_broken_in
    if premise_broken:
        confidence_reasons.append(
            f"capped at {_PREMISE_BROKEN_CEILING} because {semantics.code} assumes a context "
            f"that does not hold in {file_class.value} files"
        )
        relevance_reasons.append(
            f"{semantics.code} ({semantics.description}) describes the normal shape of "
            f"{file_class.value} files rather than a defect"
        )
        context.relevance = Relevance.INFORMATIONAL
    elif file_class in semantics.premise_weakened_in:
        relevance_reasons.append(
            f"{semantics.code} applies, but {file_class.value} code is not authored "
            f"application code"
        )
        context.relevance = Relevance.REVIEW
    elif file_class is FileClass.APPLICATION:
        relevance_reasons.append("authored application code; rule premise holds")
        context.relevance = Relevance.ACTIONABLE
    else:
        relevance_reasons.append(
            f"file is {file_class.value}; no rule-specific exemption for {semantics.code}"
        )
        context.relevance = Relevance.REVIEW

    if context.production_reachable is True:
        confidence += _REACHABLE_BONUS
        confidence_reasons.append(
            f"{_REACHABLE_BONUS:+d} because the enclosing symbol has callers in the code graph"
        )
        if context.relevance is Relevance.REVIEW:
            context.relevance = Relevance.ACTIONABLE
            relevance_reasons.append("promoted: reachable from other code")
    elif context.production_reachable is False:
        confidence += _UNREACHABLE_PENALTY
        confidence_reasons.append(
            f"{_UNREACHABLE_PENALTY:+d} because no caller was found in the code graph"
        )
        relevance_reasons.append("no caller found; may be dead or externally-invoked code")
    else:
        detail = f" ({context.reachability_reason})" if context.reachability_reason else ""
        confidence_reasons.append(f"reachability not established{detail}")

    if context.change_relation == "direct":
        relevance_reasons.append("inside the change's blast radius (directly modified symbol)")
        if context.relevance is Relevance.REVIEW:
            context.relevance = Relevance.ACTIONABLE
    elif context.change_relation in ("caller", "downstream"):
        relevance_reasons.append(f"inside the change's blast radius ({context.change_relation})")
    elif context.change_relation == "outside":
        relevance_reasons.append("outside the change's blast radius (pre-existing)")

    if context.correlated_count > 1:
        confidence += _CORRELATED_PENALTY
        confidence_reasons.append(
            f"{_CORRELATED_PENALTY:+d} because {context.correlated_count} findings in this file "
            f"report {semantics.code}, suggesting one systemic cause rather than "
            f"{context.correlated_count} defects"
        )

    if premise_broken:
        confidence = min(confidence, _PREMISE_BROKEN_CEILING)

    context.confidence = _clamp(confidence, low=1)
    context.confidence_reasons = confidence_reasons
    context.relevance_reasons = relevance_reasons
    context.recommendation = _recommend(context)


def _recommend(context: FindingContext) -> Recommendation:
    if context.relevance is Relevance.INFORMATIONAL:
        return Recommendation.SUPPRESS_CANDIDATE
    if context.relevance is Relevance.UNKNOWN:
        return Recommendation.REVIEW
    if context.relevance is Relevance.ACTIONABLE and context.confidence >= 70:
        return Recommendation.FIX
    if context.confidence < 40:
        return Recommendation.ACKNOWLEDGE
    return Recommendation.REVIEW


def relative_path(path: str, repo_root: str) -> str:
    normalized = _normalize_path(path)
    if not repo_root:
        return normalized
    root = _normalize_path(repo_root).rstrip("/")
    if root and normalized.startswith(root + "/"):
        return normalized[len(root) + 1:]
    if normalized == root:
        return posixpath.basename(root)
    return normalized


def _correlation_key(finding: Dict[str, Any]) -> Tuple[str, str]:
    return (str(finding.get("file_path", "")), str(finding.get("issue_code", "")))


def build_finding_contexts(
    findings: Sequence[Dict[str, Any]],
    *,
    graph: Any = None,
    impact: Any = None,
    repo_root: str = "",
) -> List[FindingContext]:
    prepared: List[Dict[str, Any]] = []
    for finding in findings:
        row = dict(finding)
        row["file_path"] = relative_path(str(row.get("file_path", "")), repo_root)
        prepared.append(row)

    group_counts: Dict[Tuple[str, str], int] = {}
    for row in prepared:
        key = _correlation_key(row)
        group_counts[key] = group_counts.get(key, 0) + 1

    contexts: List[FindingContext] = []
    for row in prepared:
        path = str(row.get("file_path", ""))
        code = str(row.get("issue_code", ""))
        classification = classify_file(path)
        key = _correlation_key(row)
        count = group_counts[key]

        context = FindingContext(
            finding_ref=_finding_ref(row),
            file_path=path,
            line_number=int(row.get("line_number", 0) or 0),
            rule_code=code,
            file_class=classification.file_class,
            classification_reasons=list(classification.reasons),
            secondary_file_classes=list(classification.also),
            severity=str(row.get("severity", "warning")),
            correlated_count=count,
        )
        context.symbol = _symbol_from_message(str(row.get("message", "")))
        if count > 1:
            context.correlation_id = hashlib.sha256("|".join(key).encode()).hexdigest()[:16]

        _enrich_from_graph(context, graph)
        _enrich_from_impact(context, impact)
        _score(context, rule_semantics(code))
        contexts.append(context)

    return contexts


def summarize_contexts(contexts: Sequence[FindingContext]) -> Dict[str, Any]:
    by_relevance = {r.value: 0 for r in Relevance}
    by_recommendation = {r.value: 0 for r in Recommendation}
    by_file_class: Dict[str, int] = {}
    correlation_groups = set()

    for context in contexts:
        by_relevance[context.relevance.value] += 1
        by_recommendation[context.recommendation.value] += 1
        by_file_class[context.file_class.value] = by_file_class.get(context.file_class.value, 0) + 1
        if context.correlation_id:
            correlation_groups.add(context.correlation_id)

    ungrouped = sum(1 for c in contexts if not c.correlation_id)
    return {
        "total_findings": len(contexts),
        "by_relevance": by_relevance,
        "by_file_class": dict(sorted(by_file_class.items())),
        "by_recommendation": by_recommendation,
        "actionable_count": by_relevance[Relevance.ACTIONABLE.value],
        "informational_count": by_relevance[Relevance.INFORMATIONAL.value],
        "correlation_group_count": len(correlation_groups),
        "distinct_issues": ungrouped + len(correlation_groups),
    }
