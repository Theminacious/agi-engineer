"""
Regression tests for defects found during the failure-triage hardening pass.

Every test here corresponds to a bug that reached the working tree because
nothing exercised the code path. They are deliberately narrow: each one fails
if its specific defect returns, and says which one in its own docstring.

Covered:
- EnhancedPerformanceAnalyzer N+1 proposal formatting crashed with
  `TypeError: can only concatenate str (not "int") to str`.
- EnhancedPerformanceAnalyzer N+1 detection matched a bare `.get(` / `.filter(`
  anywhere in a file, with no loop, because of regex alternation precedence.
- ResourceLeakAnalyzer grouping crashed with
  `ValueError: too many values to unpack (expected 2)`.
- `IntelligenceProposal.to_dict()` embedded wall-clock readings, so two runs of
  the same analysis shared a proposal_id while disagreeing on their payload.
- Reliability scanners walked files in filesystem order, so scan order (and the
  payload derived from it) depended on the host filesystem.
"""

import os
import shutil
import tempfile

import pytest

from agent.intelligence.analyzers.enhanced_performance import EnhancedPerformanceAnalyzer
from agent.intelligence.analyzers.reliability.resource_leak import ResourceLeakAnalyzer

# A genuine N+1: a loop whose body issues one database query per iteration.
REAL_N_PLUS_ONE = """\
def get_users_with_posts():
    users = User.query.all()
    for user in users:
        posts = Post.query.filter_by(user_id=user.id).all()
        user.posts = posts
    return users
"""

# No loop and no database access. Every call here is a plain mapping lookup.
NO_QUERY_AT_ALL = """\
import os

def totally_innocent(config: dict):
    host = config.get("host")
    port = os.environ.get("PORT")
    return host, port
"""


@pytest.fixture
def repo():
    """An empty temporary repository directory."""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


def write(repo_path: str, name: str, source: str) -> str:
    path = os.path.join(repo_path, name)
    with open(path, "w") as handle:
        handle.write(source)
    return path


class TestEnhancedPerformanceNPlusOne:
    """EnhancedPerformanceAnalyzer N+1 detection and reporting."""

    def test_n_plus_one_proposal_formats_without_typeerror(self, repo):
        """Regression: `TypeError: can only concatenate str (not "int") to str`.

        `_scan_for_n_plus_one` reports `item_count='many'` because a loop bound
        is not statically knowable. The problem statement did
        `issue['item_count'] + 1`, which raises on a str. Building the proposal
        must succeed, and must not invent a numeric count it cannot know.
        """
        write(repo, "n1.py", REAL_N_PLUS_ONE)

        proposals = EnhancedPerformanceAnalyzer().analyze(
            repository_path=repo,
            repository_url="test://repo",
            branch="main",
        )

        n1 = [p for p in proposals if "N+1" in p.problem_statement]
        assert len(n1) == 1, "the seeded N+1 should produce exactly one proposal"
        assert "many" in n1[0].problem_statement
        # No fabricated arithmetic result leaked into the prose.
        assert "many1" not in n1[0].problem_statement

    def test_no_n_plus_one_finding_without_a_loop(self, repo):
        """Regression: regex alternation precedence produced false positives.

        The pattern was::

            r'for\\s+\\w+\\s+in\\s+.*?:.*?\\.query\\(|\\.get\\(|\\.filter\\('

        `|` binds looser than the surrounding sequence, so this is three
        independent branches and the last two match a bare `.get(` or
        `.filter(` with no loop present. `config.get("host")` and
        `os.environ.get("PORT")` were each reported as an N+1 query.
        """
        write(repo, "innocent.py", NO_QUERY_AT_ALL)

        issues = EnhancedPerformanceAnalyzer()._scan_for_n_plus_one(repo)

        assert issues == [], (
            "dict/env lookups outside any loop are not N+1 queries; "
            f"got {issues}"
        )

    def test_real_n_plus_one_is_still_detected(self, repo):
        """The precision fix must not have been a suppression.

        Tightening the pattern is only correct if genuine N+1 patterns still
        report, at a 1-based line number.
        """
        write(repo, "n1.py", REAL_N_PLUS_ONE)
        write(repo, "innocent.py", NO_QUERY_AT_ALL)

        issues = EnhancedPerformanceAnalyzer()._scan_for_n_plus_one(repo)

        assert len(issues) == 1
        assert issues[0]["location"] == "n1.py"
        # `for user in users:` is line 3 of REAL_N_PLUS_ONE, counting from 1.
        assert issues[0]["line_range"] == "3"

    def test_dict_get_inside_a_loop_is_not_a_query(self, repo):
        """A mapping lookup in a loop is not a database hit.

        Requiring a loop is necessary but not sufficient: `d.get(k)` and
        `requests.get(url)` inside a loop are a dict lookup and network I/O
        respectively, neither of which is an N+1 *query*.
        """
        write(
            repo,
            "loopy.py",
            "def f(keys, d, urls):\n"
            "    for k in keys:\n"
            "        v = d.get(k)\n"
            "    for u in urls:\n"
            "        r = requests.get(u)\n",
        )

        assert EnhancedPerformanceAnalyzer()._scan_for_n_plus_one(repo) == []


class TestResourceLeakGrouping:
    """ResourceLeakAnalyzer per-file grouping."""

    def test_affected_file_line_range_unpacks_three_tuples(self, repo):
        """Regression: `ValueError: too many values to unpack (expected 2)`.

        Leaks are grouped as `(line_num, leak_type, code_snippet)` 3-tuples,
        but the line_range comprehension destructured them as `for l, _ in
        locations`. Two leaks of the same kind in one file are needed to reach
        the grouping code.
        """
        write(
            repo,
            "leaky.py",
            'import sqlite3\n'
            'f = open("a.txt")\n'
            'g = open("b.txt")\n'
            'conn = sqlite3.connect("db.sqlite")\n'
            'cur = conn.cursor()\n',
        )

        proposals = ResourceLeakAnalyzer().analyze(
            repository_path=repo,
            repository_url="test://repo",
            branch="main",
        )

        assert proposals, "seeded leaks should produce proposals"
        ranges = [
            af.line_range
            for p in proposals
            for af in p.affected_files
        ]
        assert ranges, "proposals should attribute affected files"
        for line_range in ranges:
            low, _, high = line_range.partition("-")
            assert low.isdigit() and high.isdigit(), (
                f"expected a 'low-high' 1-based range, got {line_range!r}"
            )
            assert int(low) >= 1, "line numbers are 1-based"
            assert int(low) <= int(high)


class TestProposalPayloadDeterminism:
    """`to_dict()` is the replay payload and must not carry clock readings."""

    def test_to_dict_identical_across_runs(self, repo):
        """Regression: identical proposal_id, divergent payload.

        `to_dict()` included `analysis_duration_ms`, a wall-clock measurement
        in milliseconds, so re-analysing the same code produced a different
        payload under the same content-derived proposal_id (observed 14 vs 0).
        """
        write(
            repo,
            "leaky.py",
            'f = open("a.txt")\ng = open("b.txt")\n',
        )

        def run():
            return [
                p.to_dict()
                for p in ResourceLeakAnalyzer().analyze(
                    repository_path=repo,
                    repository_url="test://repo",
                    branch="main",
                )
            ]

        first, second = run(), run()

        assert first, "expected at least one proposal to compare"
        assert first == second, "same code must serialise to the same payload"

        for payload in first:
            assert "analysis_duration_ms" not in payload
            assert "timestamp" not in payload

    def test_duration_still_available_for_telemetry(self, repo):
        """Excluding duration from the payload must not discard it.

        `ledger_adapter.proposal_to_ledger_event` reads timing off the object
        into its `metadata` block, so the attribute has to survive.
        """
        write(repo, "leaky.py", 'f = open("a.txt")\ng = open("b.txt")\n')

        proposals = ResourceLeakAnalyzer().analyze(
            repository_path=repo,
            repository_url="test://repo",
            branch="main",
        )

        assert proposals
        for proposal in proposals:
            assert isinstance(proposal.analysis_duration_ms, int)
            assert proposal.timestamp is not None


class TestScanOrderDeterminism:
    """Scanners must not inherit the host filesystem's directory order."""

    def test_reliability_scanners_sort_file_entries(self):
        """Regression: `for file in files` left scan order OS-dependent.

        `os.walk` yields entries in filesystem order, which differs across
        filesystems. Order reaches the payload through `affected_files` and
        `patterns_matched`, so every scanner iterates `sorted(files)`.
        `enhanced_performance.py` already did; the Phase 16 reliability
        analyzers did not.
        """
        import pathlib

        reliability = pathlib.Path("agent/intelligence/analyzers/reliability")
        offenders = {
            path.name: path.read_text().count("for file in files:")
            for path in sorted(reliability.glob("*.py"))
            if "for file in files:" in path.read_text()
        }

        assert offenders == {}, (
            "unsorted os.walk iteration reintroduces nondeterministic scan "
            f"order in: {offenders}"
        )
