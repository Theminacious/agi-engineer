"""
Evidence tests for the intelligence engine.

Each test pins a capability that was previously asserted but never demonstrated,
or a defect found while demonstrating one. The fixtures are minimal but
realistic: the point is that a detector fires on code a reviewer would agree is
a problem, and stays silent on code a reviewer would wave through.

Covered:
- RiskBasedSeverityAdjuster is unwired, and wiring it would be a no-op
  (tripwire: fires if either fact stops holding).
- BrokenInvariantsAnalyzer: all three detectors, positive and negative.
- EnhancedArchitecturalAnalyzer: all four detectors, positive and negative,
  including relative imports and TYPE_CHECKING-only edges.
- proposal_id is content-addressed (different content -> different id).
- Two FixStrategy keyword typos that crashed their analyzers at runtime.
- files_scanned counts distinct files rather than scan passes.
- Serialized payloads do not depend on filesystem walk order or on
  PYTHONHASHSEED.
"""

import ast
import inspect
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import pytest

from agent.intelligence.analyzer import BaseAnalyzer
from agent.intelligence.analyzers.broken_invariants import BrokenInvariantsAnalyzer
from agent.intelligence.analyzers.enhanced_architectural import EnhancedArchitecturalAnalyzer
from agent.intelligence.analyzers.enhanced_performance import EnhancedPerformanceAnalyzer
from agent.intelligence.analyzers.reliability.scalability_risk import ScalabilityRiskAnalyzer
from agent.intelligence.analyzers.test_coverage import TestCoverageAnalyzer as CoverageAnalyzer
from agent.intelligence.proposal import BugClass, IntelligenceProposal, Severity
from agent.intelligence.registry import ANALYZER_REGISTRY

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANALYZER_DIR = os.path.join(REPO_ROOT, "agent", "intelligence", "analyzers")


@pytest.fixture
def repo():
    """An empty temporary repository directory."""
    tmpdir = tempfile.mkdtemp(prefix="evidence-")
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


def write_tree(root: str, files: dict) -> str:
    """Materialise {relative_path: source} under `root`."""
    for relative_path, source in files.items():
        path = os.path.join(root, relative_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as handle:
            handle.write(source)
    return root


def bug_classes(proposals):
    return [p.bug_class for p in proposals]


def python_sources(directory: str):
    """(path, text) for every .py file under `directory`, in a fixed order."""
    for current, dirs, files in os.walk(directory):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for name in sorted(files):
            if name.endswith(".py"):
                path = os.path.join(current, name)
                with open(path, encoding="utf-8") as handle:
                    yield path, handle.read()


# ===========================================================================
# Priority 1: RiskBasedSeverityAdjuster
# ===========================================================================


class TestSeverityAdjusterIsNotWired:
    """
    RiskBasedSeverityAdjuster is deliberately not part of the analysis pipeline.

    Two facts justify leaving it that way, and both are pinned here. If either
    stops holding, the integration decision has to be made rather than
    rediscovered.
    """

    def test_no_production_module_calls_the_adjuster(self):
        """Nothing outside its own module and the tests references it."""
        callers = []
        for directory in ("agent", os.path.join("backend", "app")):
            for path, text in python_sources(os.path.join(REPO_ROOT, directory)):
                if path.endswith(os.path.join("intelligence", "confidence_calibrator.py")):
                    continue
                if "RiskBasedSeverityAdjuster" in text:
                    callers.append(os.path.relpath(path, REPO_ROOT))

        assert callers == [], (
            "RiskBasedSeverityAdjuster is now referenced by production code "
            f"({callers}). Risk-adjusted severity is no longer dead code, so "
            "its behaviour must be covered by pipeline-level tests."
        )

    def test_wiring_the_adjuster_would_change_nothing_today(self):
        """
        Every confidence level assigned by an analyzer is >= 60.

        `adjust_severity` only lowers a severity below confidence 60, so wiring
        it in right now could not change a single proposal. That is what makes
        leaving it unwired a defensible decision rather than an oversight — and
        it stops being true the moment a lower-confidence detector is added.
        """
        levels = []
        for path, text in python_sources(ANALYZER_DIR):
            for match in re.finditer(r"confidence_level\s*=\s*(\d+)", text):
                levels.append((os.path.relpath(path, REPO_ROOT), int(match.group(1))))

        assert levels, "expected analyzers to assign confidence_level literals"
        below = [entry for entry in levels if entry[1] < 60]
        assert below == [], (
            f"analyzers now assign confidence below 60 ({below}). "
            "RiskBasedSeverityAdjuster.adjust_severity would re-grade these "
            "findings, so the decision to leave it unwired must be revisited."
        )


# ===========================================================================
# Priority 2a: BrokenInvariantsAnalyzer
# ===========================================================================


RISKY_INIT = """\
import json


class ConfigLoader:
    def __init__(self, path):
        self.raw = open(path).read()
        self.data = json.load(open(path))
"""

GUARDED_INIT = """\
import json


class ConfigLoader:
    def __init__(self, path):
        self.raw = ""
        self.data = {}
        try:
            self.raw = open(path).read()
            self.data = json.load(open(path))
        except (OSError, ValueError):
            pass
"""

UNGUARDED_RISKY_CALLS = """\
def load(handle):
    return handle.read()


def fetch(session, url):
    return session.parse(url)
"""

GUARDED_RISKY_CALLS = """\
def load(handle):
    try:
        return handle.read()
    except OSError:
        return b""


def fetch(session, url):
    try:
        return session.parse(url)
    except ValueError:
        return None
"""

INCOMPLETE_INIT = """\
class Session:
    def __init__(self):
        self.token = None

    def refresh(self):
        return self.client.post(self.endpoint, self.token, self.retries)
"""

COMPLETE_INIT = """\
class Session:
    def __init__(self, client, endpoint):
        self.token = None
        self.client = client
        self.endpoint = endpoint

    def refresh(self):
        return self.client.post(self.endpoint, self.token)
"""


class TestBrokenInvariantsDetectors:
    """All three BrokenInvariantsAnalyzer detectors, both directions."""

    def test_detects_risky_operations_in_constructor(self, repo):
        write_tree(repo, {"loader.py": RISKY_INIT})
        analyzer = BrokenInvariantsAnalyzer()
        analyzer._reset_metrics()

        issues = analyzer._scan_for_unhandled_exceptions(repo)

        assert issues, "open()/json.load() in __init__ should be reported"
        assert {line for _, line in issues} == {6, 7}

    def test_guarded_constructor_is_not_reported(self, repo):
        """
        Regression: the guard was `'try' not in line`, evaluated per line.

        `self.raw = open(path).read()` nested inside `try:` does not contain the
        word "try", so every correctly handled constructor was reported as
        unhandled.
        """
        write_tree(repo, {"loader.py": GUARDED_INIT})
        analyzer = BrokenInvariantsAnalyzer()
        analyzer._reset_metrics()

        assert analyzer._scan_for_unhandled_exceptions(repo) == []

    def test_detects_unguarded_risky_calls(self, repo):
        write_tree(repo, {"io_paths.py": UNGUARDED_RISKY_CALLS})
        analyzer = BrokenInvariantsAnalyzer()
        analyzer._reset_metrics()

        issues = analyzer._scan_for_missing_error_handling(repo)

        assert {line for _, line in issues} == {2, 6}

    def test_guarded_risky_calls_are_not_reported(self, repo):
        write_tree(repo, {"io_paths.py": GUARDED_RISKY_CALLS})
        analyzer = BrokenInvariantsAnalyzer()
        analyzer._reset_metrics()

        assert analyzer._scan_for_missing_error_handling(repo) == []

    def test_detects_attributes_used_but_never_initialised(self, repo):
        write_tree(repo, {"session.py": INCOMPLETE_INIT})
        analyzer = BrokenInvariantsAnalyzer()
        analyzer._reset_metrics()

        assert analyzer._scan_for_incomplete_init(repo)

    def test_fully_initialised_class_is_not_reported(self, repo):
        """
        Regression: `self\\.\\w+(?!\\s*=)` matched by backtracking.

        With `\\w+` free to shorten ('self.token' -> 'self.toke') the negative
        lookahead passed on assignment lines, so every assignment also counted
        as a use and the effective threshold was `uses > attrs` rather than the
        `uses > attrs * 2` the code states.
        """
        write_tree(repo, {"session.py": COMPLETE_INIT})
        analyzer = BrokenInvariantsAnalyzer()
        analyzer._reset_metrics()

        assert analyzer._scan_for_incomplete_init(repo) == []

    def test_end_to_end_proposal_is_schema_valid(self, repo):
        write_tree(repo, {"loader.py": RISKY_INIT, "session.py": INCOMPLETE_INIT})
        analyzer = BrokenInvariantsAnalyzer()

        proposals = analyzer.analyze(repo, "file://" + repo, "main")

        assert proposals
        assert bug_classes(proposals) == [BugClass.BROKEN_INVARIANTS] * len(proposals)
        for proposal in proposals:
            assert proposal.validate() == []
            assert proposal.analyzer_name == "BrokenInvariantsAnalyzer"

    def test_clean_repository_yields_no_proposals(self, repo):
        write_tree(repo, {"clean.py": COMPLETE_INIT, "guarded.py": GUARDED_INIT})
        analyzer = BrokenInvariantsAnalyzer()

        assert analyzer.analyze(repo, "file://" + repo, "main") == []


# ===========================================================================
# Priority 2b: EnhancedArchitecturalAnalyzer
# ===========================================================================


class TestEnhancedArchitecturalDetectors:
    """All four EnhancedArchitecturalAnalyzer detectors, both directions."""

    def test_detects_cycle_expressed_with_relative_imports(self, repo):
        """
        Regression: relative import specs never resolved to a graph node.

        `from .b import B` was recorded as the literal '.b', which matches no
        key in a graph keyed 'pkg.b'. Relative imports are the dominant
        intra-package idiom, so on flask's source only 2 of 261 edges landed on
        a node and all four detectors were structurally unable to fire.
        """
        write_tree(repo, {
            "pkg/__init__.py": "",
            "pkg/a.py": "from .b import B\n",
            "pkg/b.py": "from .a import A\n",
        })
        analyzer = EnhancedArchitecturalAnalyzer()

        proposals = analyzer.analyze(repo, "file://" + repo, "main")

        cycles = [p for p in proposals if p.bug_class is BugClass.CIRCULAR_DEPENDENCIES]
        assert len(cycles) == 1
        assert "pkg.a" in cycles[0].problem_statement
        assert "pkg.b" in cycles[0].problem_statement
        assert cycles[0].severity is Severity.HIGH

    def test_detects_cycle_expressed_with_absolute_imports(self, repo):
        write_tree(repo, {
            "pkg/__init__.py": "",
            "pkg/a.py": "from pkg.b import B\n",
            "pkg/b.py": "from pkg.a import A\n",
        })
        analyzer = EnhancedArchitecturalAnalyzer()

        proposals = analyzer.analyze(repo, "file://" + repo, "main")

        assert [p for p in proposals if p.bug_class is BugClass.CIRCULAR_DEPENDENCIES]

    def test_type_checking_only_back_edge_is_not_a_cycle(self, repo):
        """
        A TYPE_CHECKING import is erased at runtime, so it cannot form a cycle.

        Counting them reported flask's app/ctx/globals modules as circular when
        the back edges exist only for type checkers. The guard must survive a
        trailing comment: flask writes `if t.TYPE_CHECKING:  # pragma: no cover`.
        """
        write_tree(repo, {
            "pkg/__init__.py": "",
            "pkg/a.py": "from .b import B\n",
            "pkg/b.py": (
                "import typing as t\n"
                "if t.TYPE_CHECKING:  # pragma: no cover\n"
                "    from .a import A\n"
            ),
        })
        analyzer = EnhancedArchitecturalAnalyzer()

        proposals = analyzer.analyze(repo, "file://" + repo, "main")

        assert [p for p in proposals if p.bug_class is BugClass.CIRCULAR_DEPENDENCIES] == []

    def test_detects_lower_layer_importing_higher_layer(self, repo):
        """
        Regression: import-free modules were never registered as graph nodes.

        An edge is only recognised when its target is a node, and the modules
        lower layers hold (models, constants, plain data) frequently import
        nothing, so layer violations could not be detected at all.
        """
        write_tree(repo, {
            "app/__init__.py": "",
            "app/api/__init__.py": "",
            "app/api/handlers.py": "def handle():\n    return None\n",
            "app/models/__init__.py": "",
            "app/models/store.py": "from app.api.handlers import handle\n",
        })
        analyzer = EnhancedArchitecturalAnalyzer()

        proposals = analyzer.analyze(repo, "file://" + repo, "main")

        violations = [
            p for p in proposals
            if p.bug_class is BugClass.ARCHITECTURAL_VIOLATIONS
            and "Layer boundary violation" in p.problem_statement
        ]
        assert len(violations) == 1
        assert "models layer imports from api layer" in violations[0].problem_statement

    def test_higher_layer_importing_lower_layer_is_allowed(self, repo):
        write_tree(repo, {
            "app/__init__.py": "",
            "app/api/__init__.py": "",
            "app/api/handlers.py": "from app.models.store import Store\n",
            "app/models/__init__.py": "",
            "app/models/store.py": "class Store:\n    pass\n",
        })
        analyzer = EnhancedArchitecturalAnalyzer()

        proposals = analyzer.analyze(repo, "file://" + repo, "main")

        assert [p for p in proposals if "Layer boundary violation" in p.problem_statement] == []

    def test_detects_tight_coupling_cluster(self, repo):
        write_tree(repo, {
            "svc/__init__.py": "",
            "svc/one.py": "from svc.two import x\nfrom svc.three import y\nfrom svc.four import z\n",
            "svc/two.py": "from svc.one import a\nfrom svc.three import y\nfrom svc.four import z\n",
            "svc/three.py": "from svc.one import a\nfrom svc.two import x\nfrom svc.four import z\n",
            "svc/four.py": "from svc.one import a\nfrom svc.two import x\nfrom svc.three import y\n",
        })
        analyzer = EnhancedArchitecturalAnalyzer()

        proposals = analyzer.analyze(repo, "file://" + repo, "main")

        clusters = [p for p in proposals if "Tight coupling detected" in p.problem_statement]
        assert len(clusters) == 1
        assert "4 modules" in clusters[0].problem_statement
        # affected_files must be sorted: it feeds proposal_id and the payload.
        paths = [f.path for f in clusters[0].affected_files]
        assert paths == sorted(paths)

    def test_linear_dependency_chain_is_not_a_cluster(self, repo):
        write_tree(repo, {
            "svc/__init__.py": "",
            "svc/one.py": "from svc.two import x\n",
            "svc/two.py": "from svc.three import y\n",
            "svc/three.py": "def y():\n    return None\n",
        })
        analyzer = EnhancedArchitecturalAnalyzer()

        proposals = analyzer.analyze(repo, "file://" + repo, "main")

        assert [p for p in proposals if "Tight coupling detected" in p.problem_statement] == []

    def test_detects_domain_leakage_in_the_stated_direction(self, repo):
        """
        Regression: the domain pair was sorted, so the direction was fabricated.

        Counting under `tuple(sorted(pair))` merged both directions, then the
        proposal named one — "{a} makes N cross-domain imports from {b}" — which
        was backwards whenever the pair sorted the other way. Here billing
        imports auth, never the reverse.
        """
        write_tree(repo, {
            "billing/__init__.py": "",
            "billing/invoice.py": "from auth.hashing import hash_pw\n",
            "billing/refund.py": "from auth.tokens import mint\n",
            "billing/report.py": "from auth.session import load\n",
            "auth/__init__.py": "",
            "auth/hashing.py": "def hash_pw():\n    return None\n",
            "auth/tokens.py": "def mint():\n    return None\n",
            "auth/session.py": "def load():\n    return None\n",
        })
        analyzer = EnhancedArchitecturalAnalyzer()

        proposals = analyzer.analyze(repo, "file://" + repo, "main")

        leakage = [p for p in proposals if p.bug_class is BugClass.ABSTRACTION_LEAKAGE]
        assert len(leakage) == 1
        assert "billing makes 3 cross-domain imports from auth" in leakage[0].problem_statement

    def test_single_domain_is_not_leakage(self, repo):
        write_tree(repo, {
            "billing/__init__.py": "",
            "billing/invoice.py": "from billing.refund import refund\n",
            "billing/refund.py": "def refund():\n    return None\n",
        })
        analyzer = EnhancedArchitecturalAnalyzer()

        proposals = analyzer.analyze(repo, "file://" + repo, "main")

        assert [p for p in proposals if p.bug_class is BugClass.ABSTRACTION_LEAKAGE] == []

    def test_two_cross_domain_imports_stay_below_threshold(self, repo):
        write_tree(repo, {
            "billing/__init__.py": "",
            "billing/invoice.py": "from auth.hashing import hash_pw\n",
            "billing/refund.py": "from auth.tokens import mint\n",
            "auth/__init__.py": "",
            "auth/hashing.py": "def hash_pw():\n    return None\n",
            "auth/tokens.py": "def mint():\n    return None\n",
        })
        analyzer = EnhancedArchitecturalAnalyzer()

        proposals = analyzer.analyze(repo, "file://" + repo, "main")

        assert [p for p in proposals if p.bug_class is BugClass.ABSTRACTION_LEAKAGE] == []


class TestRelativeImportResolution:
    """`_resolve_imports` rebases relative specs onto the importing package."""

    @pytest.mark.parametrize(
        "module_name, spec, expected",
        [
            ("pkg.a", ".b", "pkg.b"),
            ("pkg.sub.a", ".b", "pkg.sub.b"),
            ("pkg.sub.a", "..b", "pkg.b"),
            ("pkg.__init__", ".a", "pkg.a"),
            ("pkg.a", "os.path", "os.path"),
        ],
    )
    def test_resolution(self, module_name, spec, expected):
        analyzer = EnhancedArchitecturalAnalyzer()
        assert analyzer._resolve_imports({spec}, module_name) == {expected}

    def test_bare_dot_resolves_to_the_package(self):
        analyzer = EnhancedArchitecturalAnalyzer()
        assert analyzer._resolve_imports({"."}, "pkg.sub.a") == {"pkg.sub"}


# ===========================================================================
# Priority 3 support: proposal identity
# ===========================================================================


class TestProposalIdentity:
    """proposal_id must be a content address, in both directions."""

    def test_proposals_with_different_content_get_different_ids(self, repo):
        """
        Regression: every proposal in the system shared one proposal_id.

        Analyzers construct `IntelligenceProposal()` and then assign fields, so
        `__post_init__` hashed the dataclass defaults. A full orchestrator run
        produced 9 proposals all carrying
        'd0a0ecd6-28bd-c4d3-d88f-f75e6da3ba12', which breaks CodeFix.finding_id,
        ledger payload_ref and conflicting_analysis_ids alike.
        """
        write_tree(repo, {
            "loader.py": RISKY_INIT,
            "session.py": INCOMPLETE_INIT,
            "io_paths.py": UNGUARDED_RISKY_CALLS,
        })
        analyzer = BrokenInvariantsAnalyzer()

        proposals = analyzer.analyze(repo, "file://" + repo, "main")

        assert len(proposals) > 1, "fixture must produce several proposals"
        ids = [p.proposal_id for p in proposals]
        assert len(set(ids)) == len(ids), f"proposal_id collision: {ids}"

    def test_identical_content_gets_the_same_id(self):
        def make():
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.BROKEN_INVARIANTS
            proposal.problem_statement = "identical statement"
            proposal.severity = Severity.HIGH
            proposal.refresh_derived_proposal_id()
            return proposal

        assert make().proposal_id == make().proposal_id

    def test_explicit_proposal_id_is_preserved(self):
        proposal = IntelligenceProposal(proposal_id="caller-supplied")
        proposal.problem_statement = "changed after construction"

        assert proposal.refresh_derived_proposal_id() == "caller-supplied"

    def test_id_tracks_each_identifying_field(self):
        def make(**overrides):
            proposal = IntelligenceProposal()
            proposal.bug_class = overrides.get("bug_class", BugClass.BROKEN_INVARIANTS)
            proposal.problem_statement = overrides.get("problem_statement", "base")
            proposal.severity = overrides.get("severity", Severity.HIGH)
            proposal.refresh_derived_proposal_id()
            return proposal.proposal_id

        base = make()
        assert make(bug_class=BugClass.GOD_OBJECTS) != base
        assert make(problem_statement="other") != base
        assert make(severity=Severity.LOW) != base


# ===========================================================================
# Crash regressions
# ===========================================================================


COMPLEX_UNTESTED = """\
def very_branchy(a, b, c):
    if a:
        for index in range(10):
            if b:
                while c:
                    if index > 5:
                        return index
            elif index == 2:
                continue
            else:
                pass
    return 0
"""

QUADRATIC_SCAN = """\
def find_duplicates(rows, others):
    hits = []
    for row in rows:
        for other in others:
            if row == other:
                hits.append(row)
    return hits
"""


class TestFixStrategyKeywordRegressions:
    """
    Two FixStrategy calls passed misspelled keywords and raised TypeError.

    Both are reached only when their detector actually finds something, and
    nothing in the suite did, so a full green run coexisted with two analyzers
    that crashed on real input. The orchestrator catches per-analyzer
    exceptions, so in production each looked like "no findings".
    """

    def test_test_coverage_complex_code_path_does_not_crash(self, repo):
        """Regression: `prerequisiate_actions` in _detect_complex_untested_code."""
        write_tree(repo, {"branchy.py": COMPLEX_UNTESTED})
        analyzer = CoverageAnalyzer()

        proposals = analyzer.analyze(repo, "file://" + repo, "main")

        assert any(
            "complex functions" in p.problem_statement for p in proposals
        ), "the complex-untested-code detector should have produced a proposal"

    def test_enhanced_performance_algorithm_path_does_not_crash(self, repo):
        """Regression: `prerequiseffort_actions` in _detect_inefficient_algorithms."""
        write_tree(repo, {"scan.py": QUADRATIC_SCAN})
        analyzer = EnhancedPerformanceAnalyzer()

        proposals = analyzer.analyze(repo, "file://" + repo, "main")

        for proposal in proposals:
            assert proposal.validate() == []

    def test_no_analyzer_passes_an_unknown_fixstrategy_keyword(self):
        """
        Static sweep for the same class of typo anywhere else.

        Both defects were single misspelled keywords that only a matching code
        path would reveal, so this checks every FixStrategy call site directly.
        """
        from agent.intelligence.proposal import FixStrategy

        allowed = set(FixStrategy.__dataclass_fields__)
        offenders = []
        for path, text in python_sources(ANALYZER_DIR):
            tree = ast.parse(text)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
                if name != "FixStrategy":
                    continue
                for keyword in node.keywords:
                    if keyword.arg is not None and keyword.arg not in allowed:
                        offenders.append(
                            f"{os.path.relpath(path, REPO_ROOT)}:{node.lineno} {keyword.arg}"
                        )

        assert offenders == [], f"unknown FixStrategy keyword(s): {offenders}"


# ===========================================================================
# Scan metrics
# ===========================================================================


class TestScanMetrics:
    """files_scanned is evidence on every proposal, so it has to be the truth."""

    def test_files_scanned_counts_distinct_files_not_scan_passes(self, repo):
        """
        Regression: each of the three scan passes incremented the counter, so a
        5-file repository reported files_scanned=15.
        """
        sources = {
            "loader.py": RISKY_INIT,
            "session.py": INCOMPLETE_INIT,
            "io_paths.py": UNGUARDED_RISKY_CALLS,
        }
        write_tree(repo, sources)
        analyzer = BrokenInvariantsAnalyzer()

        analyzer.analyze(repo, "file://" + repo, "main")

        assert analyzer.files_scanned == len(sources)

    def test_metrics_reset_between_runs(self, repo):
        write_tree(repo, {"loader.py": RISKY_INIT})
        analyzer = BrokenInvariantsAnalyzer()

        analyzer.analyze(repo, "file://" + repo, "main")
        first = (analyzer.files_scanned, analyzer.lines_analyzed)
        analyzer.analyze(repo, "file://" + repo, "main")

        assert (analyzer.files_scanned, analyzer.lines_analyzed) == first

    def test_lines_analyzed_matches_the_file(self, repo):
        source = RISKY_INIT
        write_tree(repo, {"loader.py": source})
        analyzer = BrokenInvariantsAnalyzer()

        analyzer.analyze(repo, "file://" + repo, "main")

        # Scanners differ by one on a trailing newline (readlines() vs
        # split('\n')); _record_lines keeps the larger reading.
        assert analyzer.lines_analyzed == len(source.split("\n"))


class TestTryGuardedLines:
    """The block-aware try tracker used by the invariant scanners."""

    def test_marks_try_and_except_suites(self):
        lines = [
            "def f():\n",
            "    try:\n",
            "        risky()\n",
            "    except OSError:\n",
            "        recover()\n",
            "    after()\n",
        ]
        assert BaseAnalyzer._try_guarded_lines(lines) == {3, 5}

    def test_unguarded_file_has_no_guarded_lines(self):
        lines = ["def f():\n", "    risky()\n"]
        assert BaseAnalyzer._try_guarded_lines(lines) == set()

    def test_nested_try_blocks(self):
        lines = [
            "try:\n",
            "    try:\n",
            "        inner()\n",
            "    except ValueError:\n",
            "        pass\n",
            "except OSError:\n",
            "    pass\n",
            "outside()\n",
        ]
        guarded = BaseAnalyzer._try_guarded_lines(lines)
        assert 3 in guarded and 5 in guarded
        assert 8 not in guarded


# ===========================================================================
# Determinism: walk order and process identity
# ===========================================================================


DETERMINISM_FIXTURE = {
    "aaa/alpha.py": RISKY_INIT,
    "zzz/omega.py": INCOMPLETE_INIT,
    "mmm/middle.py": UNGUARDED_RISKY_CALLS,
    "pkg/__init__.py": "",
    "pkg/a.py": "from .b import B\n",
    "pkg/b.py": "from .a import A\n",
    "branchy.py": COMPLEX_UNTESTED,
    "scan.py": QUADRATIC_SCAN,
    # A tight-coupling cluster and a layer violation: the clustering walk and
    # the layer-violation affected_files set were the two nondeterministic
    # paths, so the fixture has to reach both or the test cannot fail.
    "svc/__init__.py": "",
    "svc/one.py": "from svc.two import x\nfrom svc.three import y\nfrom svc.four import z\n",
    "svc/two.py": "from svc.one import a\nfrom svc.three import y\nfrom svc.four import z\n",
    "svc/three.py": "from svc.one import a\nfrom svc.two import x\nfrom svc.four import z\n",
    "svc/four.py": "from svc.one import a\nfrom svc.two import x\nfrom svc.three import y\n",
    "app/__init__.py": "",
    "app/api/__init__.py": "",
    "app/api/handlers.py": "def handle():\n    return None\n",
    "app/models/__init__.py": "",
    "app/models/store.py": (
        "from app.api.handlers import handle\n"
        "from app.api.routing import route\n"
    ),
    "app/api/routing.py": "def route():\n    return None\n",
    #
    # `svc` above is a complete graph, and a complete graph is order-immune:
    # every candidate imports every cluster member, so internal/potential is
    # always 1.0 and BFS reaches the same cluster whatever order it visits in.
    # Removing the sort from _find_tight_coupling_clusters therefore changed
    # nothing and the negative control passed.
    #
    # `mesh` is order-sensitive on purpose. broker imports the other three;
    # queue and worker each import only broker, while router imports broker and
    # queue. A node importing one cluster member passes the 0.5 threshold when
    # the cluster holds two modules (1/2) and fails when it holds three (1/3),
    # so whether worker joins depends on when it is visited:
    #
    #   sorted   (queue, router, worker) -> worker tested at size 3 -> excluded
    #   unsorted (worker, queue, router) -> worker tested at size 1 -> included
    #
    # Measured on this graph with the sort removed: seed 0 gave a 3-module
    # cluster at 83% plus a 4-module cluster at 58%, seed 1 gave 3 modules at
    # 67% plus 3 at 83%, and seed 3 gave a single 4-module cluster at 58% —
    # different cluster counts, sizes, densities and affected_files.
    "mesh/__init__.py": "",
    "mesh/broker.py": (
        "from mesh.queue import enqueue\n"
        "from mesh.router import route\n"
        "from mesh.worker import run\n"
        "\n"
        "\ndef dispatch(message):\n"
        "    return run(route(enqueue(message)))\n"
    ),
    "mesh/queue.py": (
        "from mesh.broker import dispatch\n"
        "\n"
        "\ndef enqueue(message):\n"
        "    return dispatch(message)\n"
    ),
    "mesh/router.py": (
        "from mesh.broker import dispatch\n"
        "from mesh.queue import enqueue\n"
        "\n"
        "\ndef route(message):\n"
        "    return dispatch(enqueue(message))\n"
    ),
    "mesh/worker.py": (
        "from mesh.broker import dispatch\n"
        "\n"
        "\ndef run(message):\n"
        "    return dispatch(message)\n"
    ),
}


class OrderedNeighbours(set):
    """
    A set with a chosen iteration order.

    Lets a test drive the clustering traversal in a specific order without
    depending on PYTHONHASHSEED. Set arithmetic is unaffected: `&` returns a
    plain set, and `sorted()` consumes __iter__ and sorts what it gets.
    """

    def __init__(self, items):
        super().__init__(items)
        self._order = list(items)

    def __iter__(self):
        return iter(self._order)


class TestCouplingClusterOrderInvariance:
    """
    The coupling detector must return the same clusters whatever order it visits
    neighbours in. This is the in-process counterpart of the hash-seed tests: it
    drives the traversal order directly instead of hoping a seed happens to
    produce a hostile one.
    """

    # The `mesh` half of DETERMINISM_FIXTURE, as the import graph the analyzer
    # builds from it: {module: modules it imports}.
    MESH_GRAPH = {
        "mesh.broker": ["mesh.queue", "mesh.router", "mesh.worker"],
        "mesh.queue": ["mesh.broker"],
        "mesh.router": ["mesh.broker", "mesh.queue"],
        "mesh.worker": ["mesh.broker"],
    }

    # Every module imports every other, so every candidate scores 1.0 whenever it
    # is tested.
    SVC_MODULES = ["svc.one", "svc.two", "svc.three", "svc.four"]

    def _clusters(self, graph_spec, order):
        graph = {
            module: OrderedNeighbours(order(list(imports)))
            for module, imports in graph_spec.items()
        }
        found = EnhancedArchitecturalAnalyzer()._find_tight_coupling_clusters(graph)
        return sorted(sorted(cluster) for cluster in found)

    def test_mesh_has_the_marginal_edge_that_makes_order_matter(self):
        """
        mesh.worker imports exactly one of the cluster's modules. Against the
        detector's 0.5 threshold that is a pass at cluster size 2 and a fail at
        size 3, so its membership depends on when it is visited. Without such an
        edge the graph is order-immune and the determinism tests prove nothing.
        """
        assert self.MESH_GRAPH["mesh.worker"] == ["mesh.broker"]
        assert 1 / 2 >= 0.5
        assert 1 / 3 < 0.5

    def test_clusters_do_not_depend_on_neighbour_iteration_order(self):
        forward = self._clusters(self.MESH_GRAPH, lambda items: items)
        backward = self._clusters(self.MESH_GRAPH, lambda items: list(reversed(items)))
        assert forward == backward, f"{forward} != {backward}"

    def test_mesh_clusters_are_the_sorted_traversal_result(self):
        """
        Pins the shape, so a change in cluster membership is visible rather than
        just a change in some hash of it. Under sorted traversal broker's cluster
        excludes worker (tested at size 3), and worker then seeds a second
        cluster that pulls the rest back in.
        """
        assert self._clusters(self.MESH_GRAPH, lambda items: items) == [
            ["mesh.broker", "mesh.queue", "mesh.router"],
            ["mesh.broker", "mesh.queue", "mesh.router", "mesh.worker"],
        ]

    def test_complete_graph_is_order_immune(self):
        """
        Why the `svc` package alone could not catch the bug: in a complete graph
        every candidate imports every cluster member, so internal/potential is
        always 1.0 and the traversal converges on the same cluster from any
        order. Removing the production sort left this graph's output unchanged.
        """
        spec = {
            module: [other for other in self.SVC_MODULES if other != module]
            for module in self.SVC_MODULES
        }
        forward = self._clusters(spec, lambda items: items)
        backward = self._clusters(spec, lambda items: list(reversed(items)))
        assert forward == backward == [sorted(self.SVC_MODULES)]


class TestWalkOrderIndependence:
    """
    Serialized payloads must not depend on the order os.walk yields entries.

    os.walk reports filesystem order, which differs between filesystems and
    between machines. Scan order reaches the payload through affected_files and
    patterns_matched, so a payload that moves with it is not replayable.
    """

    @pytest.mark.parametrize("analyzer_name", sorted(ANALYZER_REGISTRY))
    def test_payload_is_identical_under_reversed_walk(self, repo, analyzer_name, monkeypatch):
        write_tree(repo, DETERMINISM_FIXTURE)
        analyzer_class = ANALYZER_REGISTRY[analyzer_name]["class"]
        real_walk = os.walk

        def ordered_walk(top, *args, **kwargs):
            for root, dirs, files in real_walk(top, *args, **kwargs):
                yield root, sorted(dirs), sorted(files)

        def reversed_walk(top, *args, **kwargs):
            for root, dirs, files in real_walk(top, *args, **kwargs):
                yield root, sorted(dirs, reverse=True), sorted(files, reverse=True)

        monkeypatch.setattr(os, "walk", ordered_walk)
        forward = [p.to_dict() for p in analyzer_class().analyze(repo, "file://" + repo, "main")]

        monkeypatch.setattr(os, "walk", reversed_walk)
        backward = [p.to_dict() for p in analyzer_class().analyze(repo, "file://" + repo, "main")]

        assert forward == backward, f"{analyzer_name} payload depends on walk order"


CROSS_PROCESS_DRIVER = """\
import json, sys
sys.path.insert(0, {root!r})
from agent.intelligence.registry import ANALYZER_REGISTRY

target = sys.argv[1]
payload = {{}}
for name in sorted(ANALYZER_REGISTRY):
    analyzer = ANALYZER_REGISTRY[name]["class"]()
    proposals = analyzer.analyze(
        repository_path=target,
        repository_url="file://" + target,
        branch="main",
    )
    payload[name] = [p.to_dict() for p in proposals]
print(json.dumps(payload))
"""


# The orchestrator is the production entry point, and it gates analyzers by
# plan: IntelligenceOrchestrator() defaults to developer, so enhanced_-
# architectural (min_plan=team) never runs and the clustering path — the one
# that was actually nondeterministic — is not exercised. Enterprise runs all 19.
ORCHESTRATOR_DRIVER = """\
import json, os, sys
sys.path.insert(0, {root!r})
sys.path.append(os.path.join({root!r}, "backend"))
from app.plans import PlanTier, create_plan_context
from agent.intelligence.orchestrator import IntelligenceOrchestrator

target = sys.argv[1]
proposals = IntelligenceOrchestrator().analyze(
    repository_path=target,
    repository_url="file://" + target,
    branch="main",
    plan_context=create_plan_context(PlanTier.ENTERPRISE),
)
print(json.dumps({{"orchestrator": [p.to_dict() for p in proposals]}}))
"""


# Every key of IntelligenceProposal.to_dict(), enumerated rather than derived so
# that adding a serialized field forces a decision about its determinism here
# instead of silently escaping comparison.
SERIALIZED_FIELDS = (
    "affected_files",
    "analyzer_name",
    "branch",
    "bug_class",
    "confidence_explanation",
    "confidence_level",
    "conflicting_analysis_ids",
    "decision_required_for",
    "files_scanned",
    "lines_analyzed",
    "patterns_matched",
    "problem_statement",
    "proposal_id",
    "repository_url",
    "requires_human_decision",
    "risk_explanation",
    "root_cause_hypothesis",
    "severity",
    "suggested_strategies",
)

# Fields whose value is an ordered sequence: a set or dict iteration leaking into
# one of these changes the payload without changing its length, so a count
# comparison cannot see it.
ORDERED_FIELDS = ("affected_files", "patterns_matched", "suggested_strategies")

HASH_SEEDS = ("0", "1", "2", "3")


def payload_divergences(left: dict, right: dict, left_label: str, right_label: str):
    """
    Per-field differences between two {analyzer: [proposal_dict]} maps.

    Compares proposal count, then position by position, then field by field, so a
    failure names the analyzer, the proposal index and the field rather than
    dumping two payloads for the reader to diff.
    """
    report = []
    for name in sorted(set(left) | set(right)):
        first, second = left.get(name, []), right.get(name, [])
        if len(first) != len(second):
            report.append(
                f"{name}: {len(first)} proposals at {left_label} "
                f"vs {len(second)} at {right_label}"
            )
            continue
        for index, (one, other) in enumerate(zip(first, second)):
            for key in sorted(set(one) | set(other)):
                if one.get(key) != other.get(key):
                    report.append(
                        f"{name}[{index}].{key}: {one.get(key)!r} at {left_label} "
                        f"!= {other.get(key)!r} at {right_label}"
                    )
    return report


def all_proposals(payload: dict):
    for name in sorted(payload):
        for proposal in payload[name]:
            yield name, proposal


LONG_CRITICAL_SECTION = "import threading\n\nlock = threading.Lock()\n\n\ndef work():\n    with lock:\n" + "".join(
    f"        step_{index}()\n" for index in range(40)
)

TWO_SECRET_KINDS = """\
password = "hunter2hunter2"
api_key = "sk-live-0123456789abcdef"
token = "ghp_0123456789abcdefghij"
"""

BLOCKING_IO_MANY_PATTERNS = """\
def handle_request(request):
    handle = open("data.txt")
    body = handle.read()
    handle.write(body)
    return body
"""


class TestRealRepositoryRegressions:
    """
    Defects that only appeared when the analyzers were pointed at flask and
    requests. Each is reproduced here with a minimal fixture.
    """

    def test_lock_contention_proposal_sets_root_cause(self, repo):
        """
        Regression: `ValueError: root_cause_hypothesis is required`.

        `_detect_lock_contention_risks` never set the field, so validation raised
        and killed EnhancedConcurrencyAnalyzer entirely — all four of its
        detectors — whenever a lock issue was found. On flask that turned 53
        would-be findings into an exception the orchestrator swallowed as
        "no findings".
        """
        from agent.intelligence.analyzers.enhanced_concurrency import (
            EnhancedConcurrencyAnalyzer,
        )

        write_tree(repo, {"worker.py": LONG_CRITICAL_SECTION})
        analyzer = EnhancedConcurrencyAnalyzer()

        proposals = analyzer.analyze(repo, "file://" + repo, "main")

        lock_findings = [p for p in proposals if "Lock held for too long" in p.problem_statement]
        assert lock_findings, "long critical section should be reported"
        for proposal in lock_findings:
            assert proposal.root_cause_hypothesis
            assert proposal.validate() == []

    def test_secret_types_are_listed_in_a_stable_order(self, repo):
        """
        Regression: the secret-type set was interpolated into problem_statement.

        Set iteration order varies with PYTHONHASHSEED, so on requests the text
        alternated between "private_key, password" and "password, private_key",
        and proposal_id changed with it.
        """
        from agent.intelligence.analyzers.security import SecurityAnalyzer

        write_tree(repo, {"settings.py": TWO_SECRET_KINDS})
        analyzer = SecurityAnalyzer()

        proposals = analyzer.analyze(repo, "file://" + repo, "main")

        secrets = [p for p in proposals if "hardcoded secrets" in p.problem_statement]
        assert secrets
        listed = re.search(r"\(([^)]+)\)", secrets[0].problem_statement)
        assert listed, secrets[0].problem_statement
        kinds = [kind.strip() for kind in listed.group(1).split(",")]
        assert len(kinds) > 1, "fixture must contain more than one kind of secret"
        assert kinds == sorted(kinds)

    def test_blocking_io_reported_once_per_file_and_operation(self, repo):
        """
        Regression: one issue per matching pattern, all indistinguishable.

        `open(`, `read(` and `write(` in one file produced three identical
        'file_io' entries sharing a location and a '0' line range, so the
        analyzer emitted duplicate proposals with a colliding proposal_id.
        """
        write_tree(repo, {"handler.py": BLOCKING_IO_MANY_PATTERNS})
        analyzer = EnhancedPerformanceAnalyzer()

        proposals = analyzer.analyze(repo, "file://" + repo, "main")

        blocking = [p for p in proposals if "Blocking file I/O" in p.problem_statement]
        assert len(blocking) == 1, [p.problem_statement for p in blocking]

        ids = [p.proposal_id for p in proposals]
        assert len(set(ids)) == len(ids)

    def test_blocking_io_line_range_points_at_the_match(self, repo):
        """
        Regression: the line range was the literal '0'.

        Position came from `content.find(pattern)` with `pattern` being the regex
        source ('open\\('), which is never present as a literal, so find()
        returned -1. FixGenerationService interpolates this into a diff hunk
        header.
        """
        write_tree(repo, {"handler.py": BLOCKING_IO_MANY_PATTERNS})
        analyzer = EnhancedPerformanceAnalyzer()

        proposals = analyzer.analyze(repo, "file://" + repo, "main")

        blocking = [p for p in proposals if "Blocking file I/O" in p.problem_statement]
        assert blocking
        line_range = blocking[0].affected_files[0].line_range
        assert line_range == "2", f"open() is on line 2, got {line_range!r}"


N_PLUS_ONE_AND_LOOKALIKES = """\
import os


def real_n_plus_one(user_ids, session):
    results = []
    for user_id in user_ids:
        user = session.query(User).filter_by(id=user_id).first()
        results.append(user)
    return results


def dict_lookup_in_loop(keys, config):
    out = []
    for key in keys:
        out.append(config.get(key, "default"))
    return out


def env_lookup_in_loop(names):
    for name in names:
        yield os.environ.get(name)


def selected_variable_in_loop(rows):
    for row in rows:
        selected = row.strip()
        yield selected


def http_fetch_in_loop(urls, requests):
    for url in urls:
        yield requests.get(url)
"""

RAW_SQL_IN_LOOP = """\
def load_each(ids, cursor):
    for identifier in ids:
        cursor.execute("SELECT name FROM users WHERE id = %s", (identifier,))
        yield cursor.fetchone()
"""


class TestScalabilityRiskNPlusOnePrecision:
    """
    ScalabilityRiskAnalyzer's N+1 scan accepted the bare substrings '.get(' and
    'select' anywhere in the five lines after a loop header, so a dict lookup, an
    environment read, an HTTP call and a variable named `selected` all counted as
    database queries. On the fixture below that was three false positives for
    every true one, while EnhancedPerformanceAnalyzer — which requires an ORM-ish
    receiver — reported only the real N+1.

    The loop-header test was also a substring check ('for ' and ' in ' both
    present), which is not the same thing as a loop.
    """

    def _n_plus_one_lines(self, repo):
        return [line for _, line, _ in ScalabilityRiskAnalyzer()._scan_for_nplus1(repo)]

    def test_real_n_plus_one_is_still_reported(self, repo):
        """Recall is the point of the detector; the precision fix must not cost it."""
        write_tree(repo, {"app.py": N_PLUS_ONE_AND_LOOKALIKES})
        assert 6 in self._n_plus_one_lines(repo), "the session.query loop must be found"

    def test_raw_sql_in_a_loop_is_reported(self, repo):
        write_tree(repo, {"loader.py": RAW_SQL_IN_LOOP})
        assert self._n_plus_one_lines(repo) == [2]

    @pytest.mark.parametrize(
        "line, what",
        [
            (14, "config.get(key) is a dict lookup"),
            (20, "os.environ.get(name) is an environment read"),
            (25, "a variable named `selected` is not SQL"),
            (31, "requests.get(url) is network I/O"),
        ],
    )
    def test_lookalike_is_not_reported(self, repo, line, what):
        write_tree(repo, {"app.py": N_PLUS_ONE_AND_LOOKALIKES})
        assert line not in self._n_plus_one_lines(repo), what

    def test_only_the_real_pattern_is_reported(self, repo):
        write_tree(repo, {"app.py": N_PLUS_ONE_AND_LOOKALIKES})
        assert self._n_plus_one_lines(repo) == [6]

    def test_agrees_with_enhanced_performance(self, repo):
        """
        Two analyzers detecting the same anti-pattern should not disagree about
        whether a given file contains it; the brief flagged the precision gap
        between them, and this pins it closed.
        """
        write_tree(repo, {"app.py": N_PLUS_ONE_AND_LOOKALIKES})

        scalability = {line for _, line, _ in ScalabilityRiskAnalyzer()._scan_for_nplus1(repo)}
        performance = {
            int(issue["line_range"])
            for issue in EnhancedPerformanceAnalyzer()._scan_for_n_plus_one(repo)
        }
        assert scalability == performance == {6}

    def test_a_loop_free_line_does_not_open_a_scan_window(self, repo):
        """
        'for ' and ' in ' can both appear on a line that is not a loop. The
        substring test treated such a line as a loop header and scanned the five
        lines below it.
        """
        source = (
            'MESSAGE = "look for a value in the cache"\n'
            "result = session.query(Thing).all()\n"
        )
        write_tree(repo, {"config.py": source})
        assert self._n_plus_one_lines(repo) == []

    def test_scalability_patterns_constant_is_not_the_detector(self):
        """
        SCALABILITY_PATTERNS is unused: no method reads it. Pinned so nobody
        'fixes' a detector by editing it and concludes the behaviour did not
        change for some other reason.
        """
        source = inspect.getsource(ScalabilityRiskAnalyzer)
        assert source.count("SCALABILITY_PATTERNS") == 1


class TestAffectedFilePaths:
    """
    affected_files must be repository-relative, not absolute host paths.

    Scanners build paths from the analysis root, so they were absolute. That
    reached production three ways: FixGenerationService._generate_patch
    interpolates the path into a `--- a/{path}` diff header (unappliable when
    absolute), proposal_id is derived from these paths so the same commit
    analysed at two checkout locations produced different ids, and the recorded
    payload described the host's directory layout.
    """

    @pytest.mark.parametrize("analyzer_name", sorted(ANALYZER_REGISTRY))
    def test_no_analyzer_emits_absolute_paths(self, repo, analyzer_name):
        write_tree(repo, DETERMINISM_FIXTURE)
        analyzer = ANALYZER_REGISTRY[analyzer_name]["class"]()

        proposals = analyzer.analyze(repo, "file://" + repo, "main")

        absolute = [
            f.path
            for p in proposals
            for f in p.affected_files
            if os.path.isabs(f.path)
        ]
        assert absolute == [], f"{analyzer_name} emitted absolute paths: {absolute}"

    def test_payload_is_identical_from_two_checkout_locations(self, tmp_path):
        """
        The same source analysed under two different directories must produce the
        same payload, proposal_ids included.
        """
        first_root = tmp_path / "checkout-a"
        second_root = tmp_path / "deeply" / "nested" / "checkout-b"
        write_tree(str(first_root), DETERMINISM_FIXTURE)
        write_tree(str(second_root), DETERMINISM_FIXTURE)

        divergent = []
        for name in sorted(ANALYZER_REGISTRY):
            analyzer_class = ANALYZER_REGISTRY[name]["class"]
            first = [
                p.to_dict()
                for p in analyzer_class().analyze(str(first_root), "file://repo", "main")
            ]
            second = [
                p.to_dict()
                for p in analyzer_class().analyze(str(second_root), "file://repo", "main")
            ]
            if first != second:
                divergent.append(name)

        assert divergent == [], f"payload depends on checkout location: {divergent}"


def run_driver(driver_path: str, target: str, seed: str) -> dict:
    env = dict(os.environ, PYTHONHASHSEED=seed)
    result = subprocess.run(
        [sys.executable, driver_path, target],
        capture_output=True, text=True, env=env, cwd=REPO_ROOT,
    )
    assert result.returncode == 0, f"driver failed at PYTHONHASHSEED={seed}:\n{result.stderr}"
    return json.loads(result.stdout)


@pytest.fixture(scope="class")
def seeded_payloads():
    """
    The fixture analysed in a separate process per hash seed, twice over: once
    calling every registered analyzer directly, once through the orchestrator at
    the enterprise plan.

    Class-scoped because eight subprocesses is the expensive part and every test
    in the class reads the same runs.
    """
    root = tempfile.mkdtemp(prefix="evidence-seeds-")
    try:
        target = write_tree(os.path.join(root, "repo"), DETERMINISM_FIXTURE)
        runs = {}
        for label, template in (
            ("registry", CROSS_PROCESS_DRIVER),
            ("orchestrator", ORCHESTRATOR_DRIVER),
        ):
            driver = os.path.join(root, f"{label}_driver.py")
            with open(driver, "w") as handle:
                handle.write(template.format(root=REPO_ROOT))
            runs[label] = {seed: run_driver(driver, target, seed) for seed in HASH_SEEDS}
        yield runs
    finally:
        shutil.rmtree(root, ignore_errors=True)


class TestCrossProcessDeterminism:
    """
    Two processes analysing the same source must agree byte for byte.

    Same-process reruns cannot catch hash-order bugs: string hashing is stable
    within a process and only varies with PYTHONHASHSEED between them. Set
    iteration in the architectural clustering was nondeterministic exactly this
    way, producing a 5-module cluster at 65% coupling in one process and a
    6-module cluster at 53% in the next — a difference in cluster size and
    affected files while proposal_id stayed put, so nothing downstream noticed.

    Both entry points are covered. The direct-registry run reaches all 19
    analyzers; the orchestrator run is the production path, and needs the
    enterprise plan because it defaults to developer and would otherwise skip the
    nine team/enterprise-tier analyzers, enhanced_architectural among them.
    """

    def test_serialized_contract_is_fully_covered(self):
        """
        SERIALIZED_FIELDS must list every key to_dict() emits.

        A field added to the payload but not to this tuple would be compared by
        the dict equality below but not named by the reporting helpers, and a
        field removed here would silently stop being reasoned about.
        """
        assert tuple(sorted(IntelligenceProposal().to_dict())) == SERIALIZED_FIELDS

    @pytest.mark.parametrize("source", ["registry", "orchestrator"])
    def test_fixture_reaches_the_nondeterministic_detectors(self, seeded_payloads, source):
        """
        Guard the guard.

        The clustering, layer-violation and cycle paths were where set iteration
        leaked into the payload. If the fixture stops reaching them, the seed
        comparisons below still pass and prove nothing.
        """
        payload = seeded_payloads[source][HASH_SEEDS[0]]
        statements = " ".join(p["problem_statement"] for _, p in all_proposals(payload))

        for probe in (
            "Tight coupling detected",
            "Layer boundary violation",
            "Circular dependency chain",
        ):
            assert probe in statements, f"{source} payload never reached: {probe}"

        cluster = next(
            p for _, p in all_proposals(payload)
            if "Tight coupling detected" in p["problem_statement"]
        )
        # A one-module "cluster" would not exercise the traversal order.
        assert len(cluster["affected_files"]) >= 3, cluster["problem_statement"]

    def test_ordering_sensitive_fields_are_populated(self, seeded_payloads):
        """
        Comparing payloads only detects order bugs if the ordered fields carry
        more than one element somewhere, and only detects proposal-order bugs if
        some analyzer emits more than one proposal.
        """
        payload = seeded_payloads["registry"][HASH_SEEDS[0]]

        multi_proposal = [name for name in payload if len(payload[name]) > 1]
        assert multi_proposal, "no analyzer emitted 2+ proposals; ordering is untested"

        for field in ORDERED_FIELDS:
            assert any(
                len(p[field]) > 1 for _, p in all_proposals(payload)
            ), f"no proposal has 2+ {field}; its ordering is untested"

        for field in ("proposal_id", "bug_class", "severity", "problem_statement"):
            assert all(p[field] for _, p in all_proposals(payload)), f"{field} is empty"

        # Scan metrics are part of the replay payload, not telemetry, so they
        # have to be real for the comparison to mean anything.
        assert any(p["files_scanned"] for _, p in all_proposals(payload))
        assert any(p["lines_analyzed"] for _, p in all_proposals(payload))

    @pytest.mark.parametrize("source", ["registry", "orchestrator"])
    @pytest.mark.parametrize("seed", HASH_SEEDS[1:])
    def test_full_payload_is_identical_across_hash_seeds(self, seeded_payloads, source, seed):
        reference_seed = HASH_SEEDS[0]
        reference = seeded_payloads[source][reference_seed]
        candidate = seeded_payloads[source][seed]

        divergences = payload_divergences(
            reference, candidate,
            f"PYTHONHASHSEED={reference_seed}", f"PYTHONHASHSEED={seed}",
        )
        assert divergences == [], "\n".join(divergences)

        # Canonical serialization: catches any difference the field walk above
        # could miss, including key ordering inside nested structures.
        assert json.dumps(reference, sort_keys=True) == json.dumps(candidate, sort_keys=True)

    def test_every_analyzer_is_present_in_the_registry_run(self, seeded_payloads):
        assert set(seeded_payloads["registry"][HASH_SEEDS[0]]) == set(ANALYZER_REGISTRY)

    @pytest.mark.parametrize("field", SERIALIZED_FIELDS)
    def test_field_is_stable_across_every_seed(self, seeded_payloads, field):
        """
        One test per serialized field, across all four seeds, so a failure says
        which field moved rather than that "the payload differs".
        """
        for source in ("registry", "orchestrator"):
            runs = seeded_payloads[source]
            reference = [
                (name, index, proposal[field])
                for name in sorted(runs[HASH_SEEDS[0]])
                for index, proposal in enumerate(runs[HASH_SEEDS[0]][name])
            ]
            for seed in HASH_SEEDS[1:]:
                candidate = [
                    (name, index, proposal[field])
                    for name in sorted(runs[seed])
                    for index, proposal in enumerate(runs[seed][name])
                ]
                assert reference == candidate, (
                    f"{source}: {field} differs between PYTHONHASHSEED="
                    f"{HASH_SEEDS[0]} and {seed}"
                )

    def test_proposal_ids_are_unique_and_stable_across_processes(self, seeded_payloads):
        for source in ("registry", "orchestrator"):
            runs = seeded_payloads[source]
            for name in sorted(runs[HASH_SEEDS[0]]):
                ids = [p["proposal_id"] for p in runs[HASH_SEEDS[0]][name]]
                assert len(set(ids)) == len(ids), f"{name} duplicated a proposal_id: {ids}"
                for seed in HASH_SEEDS[1:]:
                    assert ids == [p["proposal_id"] for p in runs[seed][name]], (
                        f"{source}/{name} proposal_ids differ at PYTHONHASHSEED={seed}"
                    )

    def test_proposal_order_is_stable_across_processes(self, seeded_payloads):
        """
        Proposal order is itself payload: the ledger records the list, and a
        reviewer reading position 3 must get the same finding on replay.
        """
        for source in ("registry", "orchestrator"):
            runs = seeded_payloads[source]
            reference = [
                (name, p["bug_class"], p["problem_statement"])
                for name, p in all_proposals(runs[HASH_SEEDS[0]])
            ]
            for seed in HASH_SEEDS[1:]:
                candidate = [
                    (name, p["bug_class"], p["problem_statement"])
                    for name, p in all_proposals(runs[seed])
                ]
                assert reference == candidate, f"{source} proposal order moved at seed {seed}"

    def test_widely_separated_seeds_also_agree(self, repo, tmp_path):
        """
        0-3 are adjacent seeds. Two far-apart values guard against agreement that
        happens to hold only for small integers.
        """
        write_tree(repo, DETERMINISM_FIXTURE)
        driver = tmp_path / "driver.py"
        driver.write_text(CROSS_PROCESS_DRIVER.format(root=REPO_ROOT))

        first = run_driver(str(driver), repo, "12345")
        second = run_driver(str(driver), repo, "999")

        divergences = payload_divergences(first, second, "seed=12345", "seed=999")
        assert divergences == [], "\n".join(divergences)

    def test_every_analyzer_runs_without_raising(self, repo, tmp_path):
        """
        The orchestrator swallows per-analyzer exceptions, so a crashing analyzer
        is indistinguishable from one that found nothing. Calling them directly
        surfaces the difference.
        """
        write_tree(repo, DETERMINISM_FIXTURE)
        failures = {}
        for name in sorted(ANALYZER_REGISTRY):
            analyzer = ANALYZER_REGISTRY[name]["class"]()
            try:
                analyzer.analyze(repo, "file://" + repo, "main")
            except Exception as error:  # noqa: BLE001 - reporting, not handling
                failures[name] = f"{type(error).__name__}: {error}"

        assert failures == {}, f"analyzers raised on a realistic fixture: {failures}"
