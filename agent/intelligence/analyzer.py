"""
Base analyzer class for intelligence modules.

All analyzers are:
- Deterministic: same input → same output
- Stateless: no memory between runs
- Proposal-only: never modify code
- Observable: all decisions are explicit
"""

from abc import ABC, abstractmethod
from typing import List, Optional
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
    
    def _finalize_proposal(
        self,
        proposal: IntelligenceProposal,
    ) -> IntelligenceProposal:
        """
        Finalize a proposal with timing and metrics.
        Validates that proposal meets Phase 11.1 requirements.
        
        Phase 11.3: Sets analyzer_name for ledger recording.
        """
        proposal.analysis_duration_ms = self.get_duration_ms()
        proposal.files_scanned = self.files_scanned
        proposal.lines_analyzed = self.lines_analyzed
        proposal.patterns_matched = self.patterns_matched
        
        # Phase 11.3: Set analyzer name for ledger recording
        proposal.analyzer_name = self.__class__.__name__
        
        # Validate against Phase 11.1 schema
        errors = proposal.validate()
        if errors:
            raise ValueError(
                f"Proposal validation failed:\n" + "\n".join(errors)
            )
        
        return proposal
