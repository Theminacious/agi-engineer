"""
Proposal data models for intelligence analysis.

All proposals conform to Phase 11.1 Intelligence Scope contract.
Proposals are immutable once created and recorded in ledger.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime

# Use deterministic ID generation for reproducibility and ledger compliance
# UUIDs are non-deterministic; we use content-based hashing instead
_deterministic_ids_initialized = False


class BugClass(Enum):
    """Allowed bug classes from Phase 11.1 Section 3."""
    ARCHITECTURAL_VIOLATIONS = "architectural_violations"
    GOD_OBJECTS = "god_objects"
    BROKEN_INVARIANTS = "broken_invariants"
    CIRCULAR_DEPENDENCIES = "circular_dependencies"
    SECURITY_MISCONFIGURATIONS = "security_misconfigurations"
    PERFORMANCE_ANTI_PATTERNS = "performance_anti_patterns"
    CONCURRENCY_HAZARDS = "concurrency_hazards"
    TEST_COVERAGE_BLIND_SPOTS = "test_coverage_blind_spots"
    CONFIGURATION_DRIFT = "configuration_drift"
    DEPENDENCY_MISUSE = "dependency_misuse"
    API_CONTRACT_VIOLATIONS = "api_contract_violations"
    ABSTRACTION_LEAKAGE = "abstraction_leakage"
    # Phase 16: Reliability Intelligence Engine
    CRASH_RISKS = "crash_risks"
    RESOURCE_LEAKS = "resource_leaks"
    RELIABILITY_ANTI_PATTERNS = "reliability_anti_patterns"
    SCALABILITY_RISKS = "scalability_risks"
    EDGE_CASE_VULNERABILITIES = "edge_case_vulnerabilities"


class Severity(Enum):
    """Severity levels from Phase 11.1."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EffortEstimate(Enum):
    """Effort estimates for strategies."""
    TRIVIAL = "trivial"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    VERY_LARGE = "very_large"


@dataclass
class AffectedFile:
    """Metadata about a file affected by a problem."""
    path: str
    line_range: Optional[str] = None  # Format: "start-end" or "start"
    severity: Severity = Severity.MEDIUM


@dataclass
class FixStrategy:
    """A proposed strategy to address a problem.
    
    Per Phase 11.1, each problem must have >= 2 strategies.
    Strategies are proposals, not executable instructions.
    """
    strategy_id: str = ""  # Will be set deterministically based on content
    name: str = ""  # Short name (<100 chars)
    description: str = ""  # Plain English (<500 chars)
    effort_estimate: EffortEstimate = EffortEstimate.MEDIUM
    prerequisite_actions: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Generate deterministic strategy_id if not set."""
        if not self.strategy_id:
            from agent.intelligence.deterministic_ids import generate_strategy_id
            self.strategy_id = generate_strategy_id(
                self.name,
                self.description,
                self.effort_estimate.value,
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "description": self.description,
            "effort_estimate": self.effort_estimate.value,
            "prerequisite_actions": self.prerequisite_actions,
            "assumptions": self.assumptions,
            "risks": self.risks,
        }


@dataclass
class IntelligenceProposal:
    """
    An intelligence proposal for a detected problem.
    
    Conforms to Phase 11.1 Intelligence Output Contract (Section 4).
    All proposals are:
    - Deterministic (same code → same proposal ID)
    - Immutable (recorded in ledger, never modified)
    - Non-executable (proposal only, no code generation)
    - Human-reviewable (structured, clear, auditable)
    """
    
    # Core identification
    proposal_id: str = ""  # Will be set deterministically based on content
    timestamp: datetime = field(default_factory=datetime.utcnow)
    repository_url: str = ""
    branch: str = "main"
    
    # Phase 11.3: Analyzer identification for ledger recording
    analyzer_name: str = ""  # Set by BaseAnalyzer._finalize_proposal()
    
    # Problem characterization
    bug_class: BugClass = BugClass.ARCHITECTURAL_VIOLATIONS
    problem_statement: str = ""  # <500 chars, plain English
    
    # Impact assessment
    affected_files: List[AffectedFile] = field(default_factory=list)
    severity: Severity = Severity.MEDIUM
    risk_explanation: str = ""  # <1000 chars, why this is a risk
    root_cause_hypothesis: str = ""  # <500 chars, why it exists
    
    # Strategies
    suggested_strategies: List[FixStrategy] = field(default_factory=list)
    
    # Confidence and uncertainty
    confidence_level: int = 50  # 0-100
    confidence_explanation: str = ""  # <300 chars, why confident or not
    
    # Conflict tracking
    conflicting_analysis_ids: List[str] = field(default_factory=list)
    
    # Ledger integration
    requires_human_decision: bool = False
    decision_required_for: str = ""  # If true, explain what decision
    
    # Metadata
    analysis_duration_ms: int = 0
    files_scanned: int = 0
    lines_analyzed: int = 0
    patterns_matched: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Generate deterministic proposal_id if not set."""
        if not self.proposal_id:
            from agent.intelligence.deterministic_ids import generate_proposal_id
            self.proposal_id = generate_proposal_id(
                self.bug_class.value,
                self.problem_statement,
                [f.path for f in self.affected_files],
                self.severity.value,
            )

    def validate(self) -> List[str]:
        """
        Validate proposal against Phase 11.1 constraints.
        Returns list of errors (empty if valid).
        """
        errors = []
        
        # Required fields
        if not self.problem_statement:
            errors.append("problem_statement is required")
        if not self.root_cause_hypothesis:
            errors.append("root_cause_hypothesis is required")
        if not self.risk_explanation:
            errors.append("risk_explanation is required")
        
        # Strategy constraints (Phase 11.1 Section 4)
        if len(self.suggested_strategies) < 2:
            errors.append("Must have >= 2 suggested strategies")
        
        for idx, strategy in enumerate(self.suggested_strategies):
            if not strategy.name:
                errors.append(f"Strategy {idx} missing name")
            if not strategy.description:
                errors.append(f"Strategy {idx} missing description")
            if not strategy.prerequisite_actions:
                errors.append(f"Strategy {idx} missing prerequisite_actions")
            if not strategy.assumptions:
                errors.append(f"Strategy {idx} missing assumptions")
        
        # Confidence constraints
        if self.confidence_level < 60 and not self.confidence_explanation:
            errors.append("Low confidence (<60%) requires explanation")
        
        if self.requires_human_decision and not self.decision_required_for:
            errors.append("If requires_human_decision, must specify decision_required_for")
        
        # Content length constraints
        if len(self.problem_statement) > 500:
            errors.append(f"problem_statement too long ({len(self.problem_statement)} > 500)")
        if len(self.risk_explanation) > 1000:
            errors.append(f"risk_explanation too long ({len(self.risk_explanation)} > 1000)")
        if len(self.root_cause_hypothesis) > 500:
            errors.append(f"root_cause_hypothesis too long ({len(self.root_cause_hypothesis)} > 500)")
        
        return errors

    def to_ledger_event(self) -> Dict[str, Any]:
        """
        Convert proposal to immutable ledger event format.
        This is what gets recorded in the append-only ledger.
        """
        return {
            "event_type": "INTELLIGENCE_PROPOSAL",
            "sequence": None,  # Will be assigned by ledger
            "timestamp": self.timestamp.isoformat(),
            "actor": "intelligence",
            "actor_role": "Analyzer",
            "phase": "analysis",
            "payload": self.to_dict(),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "proposal_id": self.proposal_id,
            "timestamp": self.timestamp.isoformat(),
            "repository_url": self.repository_url,
            "branch": self.branch,
            "analyzer_name": self.analyzer_name,  # Phase 11.3: Ledger recording
            "bug_class": self.bug_class.value,
            "problem_statement": self.problem_statement,
            "affected_files": [
                {
                    "path": f.path,
                    "line_range": f.line_range,
                    "severity": f.severity.value,
                }
                for f in self.affected_files
            ],
            "severity": self.severity.value,
            "risk_explanation": self.risk_explanation,
            "root_cause_hypothesis": self.root_cause_hypothesis,
            "suggested_strategies": [s.to_dict() for s in self.suggested_strategies],
            "confidence_level": self.confidence_level,
            "confidence_explanation": self.confidence_explanation,
            "conflicting_analysis_ids": self.conflicting_analysis_ids,
            "requires_human_decision": self.requires_human_decision,
            "decision_required_for": self.decision_required_for,
            "analysis_duration_ms": self.analysis_duration_ms,
            "files_scanned": self.files_scanned,
            "lines_analyzed": self.lines_analyzed,
            "patterns_matched": self.patterns_matched,
        }
