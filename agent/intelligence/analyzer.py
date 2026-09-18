"""
Base analyzer class for intelligence modules.

All analyzers are:
- Deterministic: same input → same output
- Stateless: no memory between runs
- Proposal-only: never modify code
- Observable: all decisions are explicit
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import os
import time
from agent.intelligence.proposal import IntelligenceProposal, BugClass


class BaseAnalyzer(ABC):
    """
    Abstract base class for all intelligence analyzers.
    
    Subclasses implement specific bug class detection logic.
    All output is proposal-only and auditable.
    """
    
    def __init__(self):
        self.start_time: Optional[float] = None
        self.files_scanned: int = 0
        self.lines_analyzed: int = 0
        self.patterns_matched: List[str] = []
        self._scan_ledger: Dict[str, int] = {}
    
    @property
    @abstractmethod
    def bug_class(self) -> BugClass:
        """The bug class this analyzer detects."""
        pass
    
    @abstractmethod
    def analyze(
        self,
        repository_path: str,
        repository_url: str,
        branch: str = "main",
    ) -> List[IntelligenceProposal]:
        """
        Analyze a repository and return proposals for detected issues.
        
        This must be DETERMINISTIC: running on same code produces same proposals.
        This must be STATELESS: no memory between invocations.
        This must be PROPOSAL-ONLY: never modify code.
        
        Args:
            repository_path: Local filesystem path to repository
            repository_url: Remote URL (for ledger recording)
            branch: Branch name being analyzed
        
        Returns:
            List of proposals (may be empty if no issues found)
        """
        pass
    
    def start_timing(self) -> None:
        """Start timing the analysis."""
        self.start_time = time.time()
    
    def get_duration_ms(self) -> int:
        """Get elapsed time in milliseconds."""
        if self.start_time is None:
            return 0
        return int((time.time() - self.start_time) * 1000)
    
    def _reset_metrics(self) -> None:
        """Reset analysis metrics for new analysis."""
        self.files_scanned = 0
        self.lines_analyzed = 0
        self.patterns_matched = []
        self._scan_ledger = {}

    def _record_scanned_file(self, file_path: str) -> bool:
        """
        Count `file_path` towards files_scanned once per analysis.

        Analyzers run several scan passes over the same tree, and each pass
        incremented the counter, so files_scanned reported 3x the real number of
        files (15 for a 5-file repository). The count is evidence attached to
        every proposal, so it has to be the number of distinct files read.

        Returns True the first time a path is seen.
        """
        if file_path in self._scan_ledger:
            return False
        self._scan_ledger[file_path] = 0
        self.files_scanned = len(self._scan_ledger)
        return True

    def _record_lines(self, file_path: str, line_count: int) -> None:
        """
        Attribute `line_count` lines to `file_path`, keeping the largest seen.

        Same multi-pass inflation as files_scanned. Per-file attribution makes
        the metric idempotent: re-scanning a file cannot raise the total, and a
        pass that reads further into a file than an earlier one still corrects
        it upwards.
        """
        previous = self._scan_ledger.get(file_path, 0)
        if line_count > previous:
            self._scan_ledger[file_path] = line_count
            self.lines_analyzed += line_count - previous

    @staticmethod
    def _strip_comment(line: str) -> str:
        """
        Return `line` with any trailing `#` comment removed.

        Detection must match against code, never against prose. A line such as

            f = open(path)  # no with statement, no close

        satisfies a negative guard like `'with' not in line` only because the
        explanatory comment mentions "with", so the real finding is silently
        suppressed. The reverse also occurs: a comment naming `requests.` can
        manufacture a finding on a line that calls nothing.

        Quote-aware, so a `#` inside a string literal (URL fragments, regex
        character classes) is preserved. Escapes are honoured. Pure and
        deterministic: same input always yields the same output.

        Line-based, matching the scanners that use it; a `#` inside a
        triple-quoted block spanning several lines is not tracked.
        """
        quote: Optional[str] = None
        i = 0
        while i < len(line):
            ch = line[i]
            if quote is not None:
                if ch == "\\":
                    i += 2
                    continue
                if ch == quote:
                    quote = None
            elif ch in ('"', "'"):
                quote = ch
            elif ch == "#":
                return line[:i]
            i += 1
        return line

    @staticmethod
    def _try_guarded_lines(lines: List[str]) -> set:
        """
        Return the 1-based line numbers that sit inside a `try` statement.

        Detectors that ask "is this risky call handled?" were testing
        `'try' not in line`, which is per-line and so answered no for every
        correctly guarded call: `self.raw = open(path).read()` nested inside
        `try:` does not itself contain the word. Properly handled constructors
        were reported as unhandled.

        Indentation-based, covering the `except`/`else`/`finally` suites as well,
        since code there is also reached only under the statement's error
        handling. Pure and deterministic.
        """
        guarded = set()
        open_try_indents: List[int] = []

        for line_number, raw_line in enumerate(lines, 1):
            stripped = raw_line.strip()
            if not stripped:
                continue
            indent = len(raw_line) - len(raw_line.lstrip())
            is_clause_header = False

            while open_try_indents and indent <= open_try_indents[-1]:
                # A clause of the same statement continues it; anything else at
                # or left of the `try:` column has closed it.
                if indent == open_try_indents[-1] and stripped.startswith(
                    ("except", "finally", "else")
                ):
                    is_clause_header = True
                    break
                open_try_indents.pop()

            if open_try_indents and not is_clause_header:
                guarded.add(line_number)

            if stripped == "try:" or stripped.startswith("try:"):
                open_try_indents.append(indent)

        return guarded

    def _finalize_proposal(
        self,
        proposal: IntelligenceProposal,
        repository_path: Optional[str] = None,
    ) -> IntelligenceProposal:
        """
        Finalize a proposal with timing and metrics.
        Validates that proposal meets Phase 11.1 requirements.

        Phase 11.3: Sets analyzer_name for ledger recording.
        """
        if repository_path:
            self._relativize_affected_files(proposal, repository_path)

        proposal.analysis_duration_ms = self.get_duration_ms()
        proposal.files_scanned = self.files_scanned
        proposal.lines_analyzed = self.lines_analyzed
        proposal.patterns_matched = self.patterns_matched

        # Phase 11.3: Set analyzer name for ledger recording
        proposal.analyzer_name = self.__class__.__name__

        # Content-address the proposal now that its fields are populated.
        proposal.refresh_derived_proposal_id()

        # Validate against Phase 11.1 schema
        errors = proposal.validate()
        if errors:
            raise ValueError(
                f"Proposal validation failed:\n" + "\n".join(errors)
            )

        return proposal

    @staticmethod
    def _relativize_affected_files(proposal, repository_path: str) -> None:
        """
        Rewrite affected_files paths to repository-relative POSIX paths.

        Scanners build paths with `os.path.join(root, file)` off the analysis
        root, so they were absolute. That reaches production three ways:
        `FixGenerationService._generate_patch` interpolates the path into a
        `--- a/{path}` diff header, which is unappliable when the path is
        absolute; `proposal_id` is derived from these paths, so the same commit
        analysed at two checkout locations produced different ids; and the
        payload recorded the host's directory layout.

        Paths outside the repository are left alone rather than turned into a
        chain of '..' segments.
        """
        root = os.path.abspath(repository_path)
        for affected in proposal.affected_files:
            if not affected.path or not os.path.isabs(affected.path):
                continue
            absolute = os.path.abspath(affected.path)
            if absolute == root or absolute.startswith(root + os.sep):
                affected.path = os.path.relpath(absolute, root).replace(os.sep, "/")
