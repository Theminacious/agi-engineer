"""Phase 20 — Change Impact domain model.

``ChangeImpactReport`` is the deterministic output of mapping a git diff
onto the existing Code Graph (Phase 19) and traversing it to find the
semantic blast radius of a change.

``ChangeRiskReport`` is the decision derived from it: the blast radius
intersected with existing reliability findings, scored into a risk level
and a review recommendation. Both are pure data — the scoring lives in
``app.services.change_risk_service``.

Design notes
------------
* Every collection is sorted before being stored/serialised so that two
  runs against the same repository state produce byte-identical output.
* Nothing here re-implements graph traversal or symbol extraction —
  this module is a pure data carrier consumed/produced by
  ``ChangeImpactService``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List


class Confidence(str, Enum):
    """How much of the impact analysis is grounded in explicit graph data."""

    HIGH = "high"      # every changed line mapped to exactly one known symbol
    MEDIUM = "medium"   # some relationships required inference
    LOW = "low"         # significant portions could not be resolved


@dataclass
class ChangedSymbol:
    """A symbol whose source lines were directly touched by the diff."""

    node_id: str
    node_type: str
    file_path: str
    name: str
    change_kind: str  # "modified" | "added" | "deleted" | "unresolved"


@dataclass
class ImpactPathStep:
    """One hop in an explainable caller chain from a changed symbol."""

    node_id: str
    node_type: str
    name: str


@dataclass
class UnresolvedReference:
    """Something the analysis could not confidently map, with a reason."""

    file_path: str
    detail: str
    reason: str


@dataclass
class FindingImpact:
    """Where one reliability finding sits relative to the blast radius.

    One row per (finding, affected file) pair — a finding reporting three
    files produces three rows, because each location resolves separately.

    ``relation`` is the only thing the risk layer reads:

    * ``direct``      — resolved to a symbol the diff itself touched
    * ``caller``      — resolved to a direct caller of a changed symbol
    * ``downstream``  — resolved to a symbol reachable from a changed symbol
    * ``outside``     — resolved to a known symbol that is not in the radius
    * ``unresolved``  — could not be resolved to a symbol at all

    ``unresolved`` is never treated as ``outside``: the analysis does not
    know, and says so.
    """

    finding_ref: str            # proposal_id when present, else a content digest
    file_path: str
    line_range: str
    severity: str               # "critical" | "high" | "medium" | "low" | "unknown"
    relation: str
    resolved_node_id: str = ""  # "" when relation == "unresolved"
    # Reliability findings report line_range as min..max of every location
    # matched in the file, so a range can span several symbols. >1 means the
    # resolution had to pick one, and the risk layer records that caveat.
    overlapping_symbol_count: int = 0
    reason: str = ""            # why it could not be resolved, when unresolved

    IN_RADIUS_RELATIONS = ("direct", "caller", "downstream")

    def is_in_blast_radius(self) -> bool:
        return self.relation in self.IN_RADIUS_RELATIONS


@dataclass
class ChangeImpactReport:
    repository: str
    base_revision: str
    target_revision: str

    changed_files: List[str] = field(default_factory=list)
    changed_symbols: List[ChangedSymbol] = field(default_factory=list)

    directly_affected_symbols: List[str] = field(default_factory=list)
    downstream_symbols: List[str] = field(default_factory=list)

    callers: List[str] = field(default_factory=list)
    callees: List[str] = field(default_factory=list)

    affected_entrypoints: List[str] = field(default_factory=list)
    affected_api_surfaces: List[str] = field(default_factory=list)

    impact_paths: Dict[str, List[List[ImpactPathStep]]] = field(default_factory=dict)

    unresolved_references: List[UnresolvedReference] = field(default_factory=list)

    intersecting_findings: List[Dict[str, Any]] = field(default_factory=list)

    # Every finding location the analysis was given, classified against the
    # blast radius — including the ones that fell outside it, which is what
    # makes "this risk is not in the affected area" an auditable statement
    # rather than an absence.
    finding_impacts: List[FindingImpact] = field(default_factory=list)

    impact_summary: str = ""
    confidence: Confidence = Confidence.LOW

    # populated by finalize()
    deterministic_hash: str = ""

    # ── Determinism helpers ─────────────────────────────────────

    def _sort_all(self) -> None:
        self.changed_files = sorted(set(self.changed_files))
        # Dedupe by node_id: a symbol touched by multiple diff hunks (e.g.
        # a large docstring rewrite split into several hunks by git) must
        # appear once, not once per hunk.
        by_id: Dict[str, ChangedSymbol] = {}
        for s in self.changed_symbols:
            by_id[s.node_id] = s
        self.changed_symbols = sorted(by_id.values(), key=lambda s: s.node_id)
        self.directly_affected_symbols = sorted(set(self.directly_affected_symbols))
        self.downstream_symbols = sorted(set(self.downstream_symbols))
        self.callers = sorted(set(self.callers))
        self.callees = sorted(set(self.callees))
        self.affected_entrypoints = sorted(set(self.affected_entrypoints))
        self.affected_api_surfaces = sorted(set(self.affected_api_surfaces))
        self.unresolved_references = sorted(
            self.unresolved_references, key=lambda u: (u.file_path, u.detail)
        )
        self.intersecting_findings = sorted(
            self.intersecting_findings, key=lambda f: json.dumps(f, sort_keys=True)
        )
        self.finding_impacts = sorted(
            self.finding_impacts,
            key=lambda f: (f.file_path, f.line_range, f.finding_ref, f.relation),
        )

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["confidence"] = self.confidence.value
        return d

    def compute_hash(self) -> str:
        """Deterministic hash over the report contents (excludes the hash field itself)."""

        payload = self.to_dict()
        payload.pop("deterministic_hash", None)
        blob = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def finalize(self) -> "ChangeImpactReport":
        """Sort everything and stamp the deterministic hash. Call once, last."""

        self._sort_all()
        self.deterministic_hash = self.compute_hash()
        return self

    # ── Summary ──────────────────────────────────────────────────

    def blast_radius_size(self) -> int:
        return len(
            set(self.directly_affected_symbols)
            | set(self.downstream_symbols)
            | set(self.callers)
        )


# ── Risk assessment over an impact report ───────────────────────────


class RiskLevel(str, Enum):
    """Aggregate risk of a change. Ranked by ``RISK_LEVEL_RANK``."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


RISK_LEVEL_RANK: Dict[RiskLevel, int] = {
    RiskLevel.NONE: 0,
    RiskLevel.LOW: 1,
    RiskLevel.MEDIUM: 2,
    RiskLevel.HIGH: 3,
    RiskLevel.CRITICAL: 4,
}


class ReviewRecommendation(str, Enum):
    """What the system recommends a human do.

    A recommendation, not an enforcement action: nothing here blocks a
    merge or approves a fix. The existing approval pipeline still owns
    those decisions.
    """

    NO_REVIEW_REQUIRED = "no_review_required"
    REVIEW_RECOMMENDED = "review_recommended"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"


@dataclass
class RiskFactor:
    """One named, individually-explainable reason the risk level is what it is.

    The report's ``risk_level`` is the maximum ``level`` across its factors,
    so every point of the score can be traced back to a factor.
    """

    kind: str
    level: RiskLevel
    detail: str
    evidence: List[str] = field(default_factory=list)


@dataclass
class ReviewTarget:
    """A concrete thing a human should look at."""

    kind: str          # "finding" | "entrypoint" | "unresolved_location"
    location: str      # file path, node id, or "file:line_range"
    detail: str


@dataclass
class ChangeRiskReport:
    """Structured change decision derived from a ``ChangeImpactReport``.

    Deterministic and LLM-free: every field is a pure function of the
    impact report and the findings it was given.
    """

    repository: str
    base_revision: str
    target_revision: str

    risk_level: RiskLevel = RiskLevel.NONE
    recommendation: ReviewRecommendation = ReviewRecommendation.NO_REVIEW_REQUIRED

    # Reused from the impact analysis rather than recomputed — there is one
    # confidence in this system and it belongs to the impact resolution.
    confidence: Confidence = Confidence.LOW

    risk_factors: List[RiskFactor] = field(default_factory=list)
    review_targets: List[ReviewTarget] = field(default_factory=list)

    findings_evaluated: int = 0
    findings_in_blast_radius: int = 0
    findings_outside_blast_radius: int = 0
    findings_unresolved_location: int = 0

    changed_file_count: int = 0
    changed_symbol_count: int = 0
    blast_radius_size: int = 0
    affected_entrypoints: List[str] = field(default_factory=list)

    # Caveats that qualify the verdict, stated rather than implied.
    caveats: List[str] = field(default_factory=list)

    summary: str = ""

    # The evidence this decision was computed from. Carried so the decision
    # is auditable on its own, and so its hash covers what produced it.
    impact: Any = None  # ChangeImpactReport | None
    impact_hash: str = ""

    deterministic_hash: str = ""

    def _sort_all(self) -> None:
        self.risk_factors = sorted(
            self.risk_factors, key=lambda f: (RISK_LEVEL_RANK[f.level], f.kind, f.detail)
        )
        for factor in self.risk_factors:
            factor.evidence = sorted(set(factor.evidence))
        self.review_targets = sorted(
            self.review_targets, key=lambda t: (t.kind, t.location, t.detail)
        )
        self.affected_entrypoints = sorted(set(self.affected_entrypoints))
        self.caveats = sorted(set(self.caveats))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repository": self.repository,
            "base_revision": self.base_revision,
            "target_revision": self.target_revision,
            "risk_level": self.risk_level.value,
            "recommendation": self.recommendation.value,
            "confidence": self.confidence.value,
            "risk_factors": [
                {
                    "kind": f.kind,
                    "level": f.level.value,
                    "detail": f.detail,
                    "evidence": f.evidence,
                }
                for f in self.risk_factors
            ],
            "review_targets": [asdict(t) for t in self.review_targets],
            "findings_evaluated": self.findings_evaluated,
            "findings_in_blast_radius": self.findings_in_blast_radius,
            "findings_outside_blast_radius": self.findings_outside_blast_radius,
            "findings_unresolved_location": self.findings_unresolved_location,
            "changed_file_count": self.changed_file_count,
            "changed_symbol_count": self.changed_symbol_count,
            "blast_radius_size": self.blast_radius_size,
            "affected_entrypoints": self.affected_entrypoints,
            "caveats": self.caveats,
            "summary": self.summary,
            "impact_hash": self.impact_hash,
            "impact": self.impact.to_dict() if self.impact is not None else None,
            "deterministic_hash": self.deterministic_hash,
        }

    def compute_hash(self) -> str:
        payload = self.to_dict()
        payload.pop("deterministic_hash", None)
        blob = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def finalize(self) -> "ChangeRiskReport":
        """Sort everything and stamp the deterministic hash. Call once, last."""

        self._sort_all()
        self.deterministic_hash = self.compute_hash()
        return self