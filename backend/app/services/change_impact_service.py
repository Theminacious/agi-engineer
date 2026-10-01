"""Phase 20 — Change Impact Intelligence (Week 1).

Composes existing systems only:

    git diff
       -> ChangeImpactService (this file)
       -> existing CodeGraphService / CodeGraphBuilder / GraphStore
       -> existing reliability findings (optional intersection)
       -> existing ledger (optional event)

No new graph, no new analyzers, no LLM calls. Everything here either
reads git via subprocess or reads the already-built CodeGraph.
"""

from __future__ import annotations

import hashlib
import json
import os
import logging
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from app.intelligence.code_graph.code_graph_builder import CodeGraphBuilder
from app.intelligence.code_graph.graph_store import CodeGraph, EdgeType, Node, NodeType
from app.models.change_impact import (
    ChangedSymbol,
    ChangeImpactReport,
    Confidence,
    FindingImpact,
    ImpactPathStep,
    UnresolvedReference,
)

logger = logging.getLogger(__name__)

# Best-effort, explicitly-scoped entry-point heuristics. If a decorator
# doesn't match one of these, we do NOT claim it's an entry point — it
# just isn't counted, which is safer than a false claim.
_ENTRYPOINT_DECORATOR_PATTERNS = [
    re.compile(r"@?(app|router)\.(get|post|put|delete|patch|websocket)"),  # FastAPI
    re.compile(r"@?(app)\.route"),                                        # Flask
    re.compile(r"@?(api_view|action)"),                                   # DRF
]


class ChangeImpactError(Exception):
    """Raised only for unrecoverable errors (e.g. not a git repo)."""


@dataclass(frozen=True)
class ChangeImpactAnalysis:
    """One change-impact calculation and the exact graph that produced it.

    ``graph`` is runtime evidence only. It is deliberately kept outside the
    serialised ``ChangeImpactReport`` so report hashes and API payloads remain
    unchanged while downstream deterministic consumers can reuse the graph
    without rebuilding it.
    """

    report: ChangeImpactReport
    graph: Optional[CodeGraph]


class ChangeImpactService:
    """Given a repo + two revisions, compute a deterministic ChangeImpactReport."""

    def __init__(self, graph_builder: Optional[CodeGraphBuilder] = None) -> None:
        self._graph_builder = graph_builder or CodeGraphBuilder()

    # ── Public API ───────────────────────────────────────────────

    def compute_change_impact(
        self,
        repo_path: str,
        base_revision: str,
        target_revision: str,
        findings: Optional[List[Dict[str, Any]]] = None,
        ledger: Optional[Any] = None,
        max_impact_depth: int = 3,
        repository_label: Optional[str] = None,
    ) -> ChangeImpactReport:
        """Compute change impact while preserving the historical report API."""

        return self.compute_change_impact_with_graph(
            repo_path=repo_path,
            base_revision=base_revision,
            target_revision=target_revision,
            findings=findings,
            ledger=ledger,
            max_impact_depth=max_impact_depth,
            repository_label=repository_label,
        ).report

    def compute_change_impact_with_graph(
        self,
        repo_path: str,
        base_revision: str,
        target_revision: str,
        findings: Optional[List[Dict[str, Any]]] = None,
        ledger: Optional[Any] = None,
        max_impact_depth: int = 3,
        repository_label: Optional[str] = None,
    ) -> ChangeImpactAnalysis:
        """Compute the semantic blast radius of the diff base..target.

        Parameters
        ----------
        repo_path:
            Path to a local git repository (must contain both revisions).
        base_revision / target_revision:
            Any git-resolvable refs (SHAs, branch names, tags).
        findings:
            Optional list of existing reliability findings. Either shape is
            accepted: an explicit ``symbol_id``/``node_id`` naming a graph
            node, or the shape the analyzers already emit
            (``affected_files: [{path, line_range, severity}]``), whose
            locations are resolved through the graph. Each location is
            classified into ``report.finding_impacts``; no analyzers are
            re-run here.
        ledger:
            Optional object exposing ``append_event(event_type, summary,
            **kwargs)`` (matches ``RunLedgerWriter``). If provided, a
            single ``CHANGE_IMPACT_ANALYZED`` event is recorded.
        max_impact_depth:
            BFS depth for downstream/upstream traversal.
        repository_label:
            Stable identity to record as ``report.repository`` instead of the
            local path. A throwaway clone path would otherwise enter the
            deterministic hash and change on every run.
        """
        repo = Path(repo_path).resolve()
        if not (repo / ".git").exists():
            raise ChangeImpactError(f"Not a git repository: {repo}")

        resolved_base = self._resolve_commit(repo, base_revision)
        resolved_target = self._resolve_commit(repo, target_revision)
        if resolved_base is None or resolved_target is None:
            unresolved = base_revision if resolved_base is None else target_revision
            raise ChangeImpactError(
                f"revision does not resolve to a commit: {unresolved}"
            )
        base_revision, target_revision = resolved_base, resolved_target

        report = ChangeImpactReport(
            repository=repository_label or str(repo),
            base_revision=base_revision,
            target_revision=target_revision,
        )

        # 1. Resolve the diff between the two revisions (no checkout needed).
        try:
            changed_ranges = self._diff_changed_ranges(repo, base_revision, target_revision)
        except subprocess.CalledProcessError as e:
            raise ChangeImpactError(f"git diff failed: {e}") from e

        report.changed_files = sorted(changed_ranges.keys())

        if not changed_ranges:
            report.impact_summary = "No changes detected between revisions."
            report.confidence = Confidence.HIGH
            return ChangeImpactAnalysis(
                report=self._finalize(report, ledger),
                graph=None,
            )

        # 2. Build the graph for the TARGET revision only (deterministic —
        #    checked out into an isolated worktree so we never touch the
        #    caller's working tree).
        graph, resolvable = self._build_graph_for_revision(repo, target_revision)
        if not resolvable:
            report.impact_summary = (
                "Target revision could not be checked out; impact analysis skipped."
            )
            report.confidence = Confidence.LOW
            for f in report.changed_files:
                report.unresolved_references.append(
                    UnresolvedReference(
                        file_path=f,
                        detail="entire file",
                        reason="target revision unavailable for graph build",
                    )
                )
            return ChangeImpactAnalysis(
                report=self._finalize(report, ledger),
                graph=None,
            )

        # 3. Map changed line ranges -> graph symbols.
        matched_any = False
        total_hunk_files = 0
        for file_path, ranges in changed_ranges.items():
            if not file_path.endswith(".py"):
                report.unresolved_references.append(
                    UnresolvedReference(
                        file_path=file_path,
                        detail="non-Python file",
                        reason="symbol extraction currently supports Python only",
                    )
                )
                continue

            total_hunk_files += 1
            symbols_in_file = self._symbols_in_file(graph, file_path)
            if not symbols_in_file:
                report.unresolved_references.append(
                    UnresolvedReference(
                        file_path=file_path,
                        detail="whole file",
                        reason="file not present in code graph (not resolvable)",
                    )
                )
                continue

            file_matched = False
            for (start, end) in ranges:
                hit = self._match_range_to_symbol(symbols_in_file, start, end)
                if hit is None:
                    report.unresolved_references.append(
                        UnresolvedReference(
                            file_path=file_path,
                            detail=f"lines {start}-{end}",
                            reason=(
                                "changed range does not fall inside any known "
                                "symbol (likely module-level code, imports, or "
                                "whitespace)"
                            ),
                        )
                    )
                    continue
                node, kind = hit
                report.changed_symbols.append(
                    ChangedSymbol(
                        node_id=node.id,
                        node_type=node.node_type.value,
                        file_path=file_path,
                        name=node.name,
                        change_kind=kind,
                    )
                )
                report.directly_affected_symbols.append(node.id)
                file_matched = True
                matched_any = True

            if file_matched:
                pass
            else:
                # nothing in this file's changed ranges hit a symbol
                pass

        # 4. Traverse the graph from every directly-affected symbol.
        for node_id in list(report.directly_affected_symbols):
            self._collect_downstream(graph, node_id, max_impact_depth, report)

        # 5. Entry-point / API-surface detection (best-effort, explicit).
        self._detect_entrypoints(graph, report)

        # 6. Finding intersection (optional, minimal — no re-run of analyzers).
        if findings:
            self._intersect_findings(report, findings, graph)

        # 7. Confidence + summary.
        report.confidence = self._assess_confidence(report, total_hunk_files)
        report.impact_summary = self._build_summary(report)

        return ChangeImpactAnalysis(
            report=self._finalize(report, ledger),
            graph=graph,
        )

    def intersect_findings(
        self,
        analysis: ChangeImpactAnalysis,
        findings: Optional[List[Dict[str, Any]]],
    ) -> ChangeImpactReport:
        """Attach findings to an existing impact calculation without rebuilding it.

        Replacement semantics make retries idempotent and prevent duplicate
        finding-impact rows. When no graph was available during the original
        calculation, no relationship is invented.
        """

        report = analysis.report
        report.intersecting_findings = []
        report.finding_impacts = []
        if findings and analysis.graph is not None:
            self._intersect_findings(report, findings, analysis.graph)
        return report.finalize()

    def record(self, report: ChangeImpactReport, ledger: Optional[Any]) -> None:
        """Record one finalized impact report in the optional run ledger."""

        self._record(report, ledger)

    def _resolve_commit(self, repo: Path, revision: str) -> Optional[str]:
        """Pin any resolvable ref/SHA to a full commit SHA, or None.

        Resolving to an immutable commit SHA up front means every downstream
        conclusion (diff, graph, proof hash, worktree checkout) is anchored to
        the exact commit, not a mutable ref that could move between steps.
        """
        if not revision:
            return None
        try:
            out = subprocess.run(
                ["git", "rev-parse", "--verify", "--quiet", f"{revision}^{{commit}}"],
                cwd=str(repo),
                check=True,
                capture_output=True,
                text=True,
                env=self._git_env(repo),
            )
        except subprocess.CalledProcessError:
            return None
        sha = out.stdout.strip()
        return sha or None

    def _git_env(self, repo: Path) -> Dict[str, str]:
        """Run git without reading the user's global config or home directory."""

        safe_home = Path(tempfile.gettempdir()) / "agi-impact-git-home"
        safe_home.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["HOME"] = str(safe_home)
        env["XDG_CONFIG_HOME"] = str(safe_home / ".config")
        env["GIT_CONFIG_NOSYSTEM"] = "1"
        env["GIT_CONFIG_GLOBAL"] = os.devnull
        env["GIT_CONFIG_SYSTEM"] = os.devnull
        return env

    # ── Diff parsing ─────────────────────────────────────────────

    def _diff_changed_ranges(
        self, repo: Path, base: str, target: str
    ) -> Dict[str, List[Tuple[int, int]]]:
        """Return {file_path: [(start_line, end_line), ...]} for TARGET-side
        (added/modified) line ranges only. Uses --unified=0 so hunk headers
        give exact changed ranges with no surrounding context noise.
        """
        cmd = ["git", "diff", "--unified=0", "--no-color", f"{base}..{target}"]
        out = subprocess.run(
            cmd,
            cwd=str(repo),
            check=True,
            capture_output=True,
            text=True,
            env=self._git_env(repo),
        ).stdout

        changes: Dict[str, List[Tuple[int, int]]] = {}
        current_file: Optional[str] = None

        # unified diff hunk header: @@ -a,b +c,d @@
        hunk_re = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
        file_re = re.compile(r"^\+\+\+ b/(.+)$")

        for line in out.splitlines():
            if line.startswith("+++ "):
                m = file_re.match(line)
                current_file = m.group(1) if m else None
                if current_file == "dev/null":
                    current_file = None
                continue
            if line.startswith("@@") and current_file:
                m = hunk_re.match(line)
                if not m:
                    continue
                start = int(m.group(1))
                count = int(m.group(2)) if m.group(2) is not None else 1
                if count == 0:
                    # pure deletion at this point in target — no target lines
                    # to map; record as a 1-line marker at the insertion point
                    # so it still surfaces as "near this location" rather than
                    # silently vanishing.
                    end = start
                else:
                    end = start + count - 1
                changes.setdefault(current_file, []).append((start, end))

        return changes

    # ── Graph construction for a specific revision ──────────────

    def _build_graph_for_revision(
        self, repo: Path, revision: str
    ) -> Tuple[Optional[CodeGraph], bool]:
        """Build the code graph for `revision` via an isolated worktree so the
        caller's working tree/branch is never touched or checked out.
        """
        with tempfile.TemporaryDirectory(prefix="agi-impact-") as tmp:
            worktree_path = str(Path(tmp) / "wt")
            try:
                subprocess.run(
                    ["git", "worktree", "add", "--detach", worktree_path, revision],
                    cwd=str(repo),
                    check=True,
                    capture_output=True,
                    text=True,
                    env=self._git_env(repo),
                )
            except subprocess.CalledProcessError as e:
                logger.warning("Could not create worktree for %s: %s", revision, e.stderr)
                return None, False

            head = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=worktree_path,
                check=False,
                capture_output=True,
                text=True,
                env=self._git_env(repo),
            ).stdout.strip()
            if head != revision:
                logger.warning(
                    "Worktree HEAD %s does not match requested revision %s; refusing to build graph",
                    head, revision,
                )
                subprocess.run(
                    ["git", "worktree", "remove", "--force", worktree_path],
                    cwd=str(repo), check=False, capture_output=True, text=True,
                    env=self._git_env(repo),
                )
                return None, False

            try:
                graph = self._graph_builder.build_graph(worktree_path)
                return graph, True
            finally:
                subprocess.run(
                    ["git", "worktree", "remove", "--force", worktree_path],
                    cwd=str(repo),
                    check=False,
                    capture_output=True,
                    text=True,
                    env=self._git_env(repo),
                )

    # ── Line-range -> symbol matching ───────────────────────────

    def _symbols_in_file(self, graph: CodeGraph, file_path: str) -> List[Node]:
        return sorted(
            (
                n for n in graph.nodes.values()
                if n.file_path == file_path
                and n.node_type in (NodeType.FUNCTION, NodeType.METHOD, NodeType.CLASS)
            ),
            key=lambda n: (n.line_number or 0),
        )

    def _match_range_to_symbol(
        self, symbols: List[Node], start: int, end: int
    ) -> Optional[Tuple[Node, str]]:
        """Find the smallest symbol whose [line_number, end_line] contains the
        changed range. Prefers METHOD/FUNCTION over CLASS when both contain
        the range (more specific = more useful).
        """
        candidates: List[Node] = []
        for n in symbols:
            n_start = n.line_number or 0
            n_end = n.metadata.get("end_line") or n_start
            if n_start <= start and end <= n_end:
                candidates.append(n)
            elif n_start <= end and start <= n_end:
                # partial overlap (e.g. change spans a symbol boundary)
                candidates.append(n)

        if not candidates:
            return None

        # smallest span = most specific match
        def span(n: Node) -> int:
            n_start = n.line_number or 0
            n_end = n.metadata.get("end_line") or n_start
            return max(n_end - n_start, 0)

        best = min(candidates, key=span)
        # kind is "modified" for week-1 scope; added/deleted detection
        # requires base-revision symbol diffing, left for a follow-up pass
        # rather than guessed here.
        return best, "modified"

    # ── Traversal ────────────────────────────────────────────────

    def _collect_downstream(
        self, graph: CodeGraph, node_id: str, max_depth: int, report: ChangeImpactReport
    ) -> None:
        node = graph.get_node(node_id)
        if node is None:
            return

        impacted = graph.get_impact_set(node_id, max_depth=max_depth)
        report.downstream_symbols.extend(impacted)

        callers = graph.get_callers(node_id)
        callees = graph.get_callees(node_id)
        report.callers.extend(c.id for c in callers)
        report.callees.extend(c.id for c in callees)

        # Build one explainable path: changed symbol -> caller -> caller ...
        path: List[ImpactPathStep] = [
            ImpactPathStep(node_id=node.id, node_type=node.node_type.value, name=node.name)
        ]
        current = node
        visited = {current.id}
        for _ in range(max_depth):
            callers_of_current = graph.get_callers(current.id)
            next_hop = next((c for c in callers_of_current if c.id not in visited), None)
            if next_hop is None:
                break
            path.append(
                ImpactPathStep(
                    node_id=next_hop.id, node_type=next_hop.node_type.value, name=next_hop.name
                )
            )
            visited.add(next_hop.id)
            current = next_hop

        if len(path) > 1:
            report.impact_paths.setdefault(node_id, []).append(path)

    # ── Entry points ─────────────────────────────────────────────

    def _detect_entrypoints(self, graph: CodeGraph, report: ChangeImpactReport) -> None:
        reachable = set(report.directly_affected_symbols) | set(report.downstream_symbols) | set(
            report.callers
        )
        for node_id in reachable:
            node = graph.get_node(node_id)
            if node is None or node.node_type not in (NodeType.FUNCTION, NodeType.METHOD):
                continue
            decorators = node.metadata.get("decorators") or []
            for dec in decorators:
                if any(p.search(dec) for p in _ENTRYPOINT_DECORATOR_PATTERNS):
                    report.affected_entrypoints.append(node_id)
                    report.affected_api_surfaces.append(f"{node.name} ({dec})")
                    break

    # ── Finding intersection ────────────────────────────────────

    def _intersect_findings(
        self,
        report: ChangeImpactReport,
        findings: List[Dict[str, Any]],
        graph: CodeGraph,
    ) -> None:
        """Classify every finding location against the blast radius.

        Two finding shapes are accepted:

        * an explicit ``symbol_id``/``node_id`` naming a graph node;
        * the shape reliability analyzers actually emit —
          ``affected_files: [{path, line_range, severity}]`` (see
          ``IntelligenceProposal.to_dict``), which carries no node id, so
          the location is resolved through the graph built above.

        Findings whose location cannot be resolved are recorded as
        ``relation="unresolved"``, never as "outside".
        """
        direct = set(report.directly_affected_symbols)
        callers = set(report.callers)
        downstream = set(report.downstream_symbols)
        affected = direct | callers | downstream

        for finding in findings:
            ref = self._finding_ref(finding)
            finding_severity = str(finding.get("severity") or "unknown")

            symbol_ref = finding.get("symbol_id") or finding.get("node_id")
            if symbol_ref:
                node = graph.get_node(symbol_ref)
                report.finding_impacts.append(
                    FindingImpact(
                        finding_ref=ref,
                        file_path=(node.file_path if node else "") or "",
                        line_range=str(node.line_number) if node and node.line_number else "",
                        severity=finding_severity,
                        relation=self._relation_for(
                            symbol_ref, direct, callers, downstream, known=node is not None
                        ),
                        resolved_node_id=symbol_ref,
                        overlapping_symbol_count=1 if node else 0,
                        reason="" if node else "symbol_id not present in code graph",
                    )
                )
                if symbol_ref in affected:
                    report.intersecting_findings.append(finding)
                continue

            locations = finding.get("affected_files") or []
            if not locations:
                report.finding_impacts.append(
                    FindingImpact(
                        finding_ref=ref,
                        file_path="",
                        line_range="",
                        severity=finding_severity,
                        relation="unresolved",
                        reason="finding carries no symbol id and no affected_files",
                    )
                )
                continue

            in_radius = False
            for location in locations:
                impact = self._classify_location(
                    graph, report, location, ref, finding_severity, direct, callers, downstream
                )
                report.finding_impacts.append(impact)
                in_radius = in_radius or impact.is_in_blast_radius()

            if in_radius:
                report.intersecting_findings.append(finding)

    def _classify_location(
        self,
        graph: CodeGraph,
        report: ChangeImpactReport,
        location: Dict[str, Any],
        finding_ref: str,
        finding_severity: str,
        direct: Set[str],
        callers: Set[str],
        downstream: Set[str],
    ) -> FindingImpact:
        file_path = str(location.get("path") or "")
        line_range = str(location.get("line_range") or "")
        # The per-file severity an analyzer attached to this location is more
        # specific than the proposal-level one; fall back to the latter.
        severity = str(location.get("severity") or finding_severity)

        def unresolved(reason: str) -> FindingImpact:
            return FindingImpact(
                finding_ref=finding_ref,
                file_path=file_path,
                line_range=line_range,
                severity=severity,
                relation="unresolved",
                reason=reason,
            )

        if not file_path:
            return unresolved("finding location has no file path")

        bounds = self._parse_line_range(line_range)
        if bounds is None:
            return unresolved(f"unparseable line_range {line_range!r}")

        symbols = self._symbols_in_file(graph, file_path)
        if not symbols:
            return unresolved("file has no symbols in the code graph")

        start, end = bounds
        overlapping = self._symbols_overlapping_range(symbols, start, end)
        if not overlapping:
            return unresolved("line range does not overlap any known symbol")

        # Prefer an overlapping symbol that is inside the radius: the question
        # being answered is "does this finding touch the affected area?", and a
        # wide line_range can overlap both affected and unaffected symbols.
        # Within that preference take the narrowest span, so a range covering
        # both a class and one of its methods resolves to the method rather
        # than to whichever id sorts first.
        in_radius = [n for n in overlapping if n.id in (direct | callers | downstream)]
        chosen = min(in_radius or overlapping, key=lambda n: (self._symbol_span(n), n.id))

        return FindingImpact(
            finding_ref=finding_ref,
            file_path=file_path,
            line_range=line_range,
            severity=severity,
            relation=self._relation_for(chosen.id, direct, callers, downstream, known=True),
            resolved_node_id=chosen.id,
            overlapping_symbol_count=len(overlapping),
        )

    @staticmethod
    def _relation_for(
        node_id: str,
        direct: Set[str],
        callers: Set[str],
        downstream: Set[str],
        known: bool,
    ) -> str:
        if not known:
            return "unresolved"
        if node_id in direct:
            return "direct"
        if node_id in callers:
            return "caller"
        if node_id in downstream:
            return "downstream"
        return "outside"

    @staticmethod
    def _finding_ref(finding: Dict[str, Any]) -> str:
        """Stable identifier for a finding, for ordering and audit.

        Uses the analyzer's own ``proposal_id`` when present; otherwise a
        digest of the finding's content, so the reference is reproducible
        across runs rather than positional.
        """
        explicit = finding.get("proposal_id") or finding.get("finding_id") or finding.get("id")
        if explicit:
            return str(explicit)
        blob = json.dumps(finding, sort_keys=True, default=str)
        return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _parse_line_range(line_range: str) -> Optional[Tuple[int, int]]:
        """Parse ``"12-40"`` or ``"12"`` into inclusive bounds.

        Returns None rather than a guess for anything else — an unparseable
        range must surface as unresolved.
        """
        text = line_range.strip()
        if not text:
            return None
        parts = text.split("-", 1)
        try:
            start = int(parts[0])
            end = int(parts[1]) if len(parts) == 2 else start
        except ValueError:
            return None
        if start <= 0 or end < start:
            return None
        return start, end

    @staticmethod
    def _symbol_span(node: Node) -> int:
        start = node.line_number or 0
        end = node.metadata.get("end_line") or start
        return max(end - start, 0)

    def _symbols_overlapping_range(
        self, symbols: List[Node], start: int, end: int
    ) -> List[Node]:
        """Every symbol whose line span overlaps [start, end], id-ordered.

        All of them, not just the innermost: a reliability finding's
        line_range spans min..max of the locations matched in the file, so it
        can cover several symbols and the blast radius may intersect any one
        of them.
        """
        hits = [
            n
            for n in symbols
            if (n.line_number or 0) <= end
            and start <= (n.metadata.get("end_line") or n.line_number or 0)
        ]
        return sorted(hits, key=lambda n: n.id)

    # ── Confidence & summary ────────────────────────────────────

    def _assess_confidence(self, report: ChangeImpactReport, total_hunk_files: int) -> Confidence:
        if total_hunk_files == 0:
            return Confidence.LOW
        unresolved_count = len(report.unresolved_references)
        matched_count = len(report.changed_symbols)
        if unresolved_count == 0 and matched_count > 0:
            return Confidence.HIGH
        if matched_count == 0:
            return Confidence.LOW
        ratio = unresolved_count / max(matched_count + unresolved_count, 1)
        return Confidence.MEDIUM if ratio < 0.5 else Confidence.LOW

    def _build_summary(self, report: ChangeImpactReport) -> str:
        return (
            f"{len(report.changed_files)} file(s) changed, "
            f"{len(report.changed_symbols)} symbol(s) directly affected, "
            f"{len(set(report.downstream_symbols))} symbol(s) downstream, "
            f"{len(set(report.affected_entrypoints))} entrypoint(s) reachable, "
            f"{len(report.unresolved_references)} unresolved reference(s)."
        )

    # ── Finalization / ledger ───────────────────────────────────

    def _finalize(
        self, report: ChangeImpactReport, ledger: Optional[Any]
    ) -> ChangeImpactReport:
        report.finalize()
        self._record(report, ledger)
        return report

    @staticmethod
    def _record(report: ChangeImpactReport, ledger: Optional[Any]) -> None:
        if ledger is not None and hasattr(ledger, "append_event"):
            try:
                ledger.append_event(
                    "CHANGE_IMPACT_ANALYZED",
                    summary=report.impact_summary or "Change impact analysis completed",
                    actor="system",
                    actor_role="System",
                    phase="PHASE_20",
                    payload_ref=report.deterministic_hash,
                )
            except Exception as e:  # non-fatal, matches ledger's own failure policy
                logger.warning("Failed to record CHANGE_IMPACT_ANALYZED event: %s", e)
