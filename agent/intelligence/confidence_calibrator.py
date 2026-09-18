"""
PHASE 12: Confidence Calibration System

Improves confidence scoring for all intelligence proposals.
Tracks evidence quality and provides risk-based severity adjustment.

Key principles:
- Confidence is not 0-100 arbitrary score
- Confidence is evidence quality: how certain can we be of this issue?
- Risk is severity: if this is a real issue, how bad is it?
- These are orthogonal: high confidence in low-severity issue is different from
  low confidence in critical issue.

All calibration is deterministic and stateless.
"""

from typing import List, Dict, Optional
from enum import Enum


class ConfidenceSource(Enum):
    """Type of evidence contributing to confidence score."""
    STATIC_PATTERN = "static_pattern"  # Code pattern detected (high confidence)
    HEURISTIC = "heuristic"  # Heuristic analysis (medium confidence)
    NAMING_CONVENTION = "naming_convention"  # Based on naming (low confidence)
    RUNTIME_ASSUMPTION = "runtime_assumption"  # Requires runtime info (low confidence)


class ConfidenceCalibrator:
    """
    Calibrates confidence scores for intelligence proposals.
    
    Approach:
    1. Track what evidence led to proposal
    2. Assess quality/reliability of each evidence source
    3. Combine evidence for overall confidence
    4. Provide explanation of confidence reasoning
    
    Deterministic: same evidence → same confidence score
    """
    
    # Evidence quality scores (0-100)
    EVIDENCE_WEIGHT = {
        ConfidenceSource.STATIC_PATTERN: 95,      # Very reliable
        ConfidenceSource.HEURISTIC: 70,           # Reasonably reliable
        ConfidenceSource.NAMING_CONVENTION: 50,   # Unreliable
        ConfidenceSource.RUNTIME_ASSUMPTION: 40,  # Unreliable
    }
    
    def __init__(self):
        """Initialize calibrator."""
        self.evidence_sources: List[ConfidenceSource] = []
        self.evidence_details: List[str] = []
        self.conflicting_evidence: List[str] = []
    
    def add_evidence(
        self,
        source: ConfidenceSource,
        detail: str,
    ) -> None:
        """
        Add evidence contributing to confidence.
        
        Args:
            source: Type of evidence
            detail: Description of evidence
        """
        self.evidence_sources.append(source)
        self.evidence_details.append(detail)
    
    def add_conflicting_evidence(self, detail: str) -> None:
        """Add evidence that contradicts the proposal (reduces confidence)."""
        self.conflicting_evidence.append(detail)
    
    def calculate_confidence(self) -> int:
        """
        Calculate overall confidence score (0-100).
        
        Deterministic: same evidence sources → same score
        """
        if not self.evidence_sources:
            return 50  # No evidence = neutral confidence
        
        # Calculate weighted average of evidence sources
        total_weight = 0
        total_score = 0
        
        for source in self.evidence_sources:
            weight = self.EVIDENCE_WEIGHT[source]
            total_score += weight
            total_weight += 1
        
        # Average confidence from evidence
        avg_confidence = total_score // total_weight if total_weight > 0 else 50
        
        # Reduce confidence for conflicting evidence
        penalty = len(self.conflicting_evidence) * 10
        final_confidence = max(0, avg_confidence - penalty)
        
        return min(100, final_confidence)
    
    def get_explanation(self) -> str:
        """
        Get human-readable explanation of confidence score.
        
        Includes:
        - What evidence supports the proposal
        - What evidence contradicts it
        - Why overall confidence is what it is
        """
        if not self.evidence_sources:
            return "No evidence collected. Confidence score is neutral."
        
        explanation_parts = []
        
        # Summarize supporting evidence
        explanation_parts.append("Supporting evidence:")
        for source, detail in zip(self.evidence_sources, self.evidence_details):
            explanation_parts.append(f"  - {source.value}: {detail}")
        
        # Summarize conflicting evidence
        if self.conflicting_evidence:
            explanation_parts.append("\nConflicting evidence:")
            for conflict in self.conflicting_evidence:
                explanation_parts.append(f"  - {conflict}")
        
        # Overall assessment
        confidence = self.calculate_confidence()
        if confidence >= 80:
            assessment = "High confidence: Evidence is strong and reliable."
        elif confidence >= 60:
            assessment = "Moderate confidence: Evidence is reasonable but has some limitations."
        elif confidence >= 40:
            assessment = "Lower confidence: Evidence is based on heuristics; manual review recommended."
        else:
            assessment = "Low confidence: Evidence is limited; treat as exploratory."
        
        explanation_parts.append(f"\nOverall: {assessment}")
        
        return "\n".join(explanation_parts)


class RiskBasedSeverityAdjuster:
    """
    Adjusts severity based on confidence and actual risk.

    Key insight: Severity should reflect:
    - Likelihood of issue occurring (confidence)
    - Severity if issue occurs (inherent severity)

    Combined risk = likelihood × severity

    Example:
    - High confidence + High severity = CRITICAL
    - Low confidence + High severity = HIGH (could be critical, needs verification)
    - High confidence + Low severity = MEDIUM
    - Low confidence + Low severity = LOW

    INTEGRATION STATUS — not wired into the analysis pipeline.

    No analyzer, service, or router calls `adjust_severity` or
    `calculate_risk_score`; the only references are tests and the commented
    example at the bottom of this module. All 19 registered analyzers set
    `proposal.severity` and `proposal.confidence_level` directly (125 literal
    severity assignments), so severity logic already lives with each detector.

    Wiring this in would currently be a **no-op**, which is the substantive
    reason it stays unwired rather than an oversight: `adjust_severity` only
    changes a severity when `confidence < 60`, and every `confidence_level`
    assigned anywhere in the codebase is >= 60 (the minimum used is exactly 60).
    `TestSeverityAdjusterIsNotWired` in
    tests/test_intelligence_evidence.py pins both facts, so if a
    lower-confidence detector is ever added the tripwire fires and the
    integration decision surfaces at that moment.

    Whether risk-adjusted severity *should* re-grade findings is a product
    decision, not a cleanup: it would change severity across all 19 analyzers
    and everything keyed on severity (plan tiers, insights dashboard counts,
    reliability metrics, fix generation).
    """

    # Ordered least to most severe. Index arithmetic on this ladder replaces the
    # per-severity if/elif chains, so "reduce one level" cannot drift between
    # bands and cannot fall through to an unintended default.
    _LADDER = ("LOW", "MEDIUM", "HIGH", "CRITICAL")

    @classmethod
    def _canonical_name(cls, severity) -> str:
        """
        Uppercase ladder name for a severity given as an Enum or a string.

        Accepting both matters because the callers this class is written for
        hold `Severity` enum members whose *values are lowercase* ('high'),
        while the band logic is expressed in uppercase names. Comparing an
        unnormalised value against "HIGH" silently missed every branch and
        returned the floor, so `Severity.HIGH` at confidence 30 produced LOW
        where the contract says MEDIUM — a severity being *understated* by two
        rungs, the least safe direction for a reliability product.

        An unrecognised severity raises rather than defaulting, for the same
        reason: quietly grading unknown input as LOW hides the problem.
        """
        raw = severity.value if isinstance(severity, Enum) else severity
        name = str(raw).strip().upper()
        if name not in cls._LADDER:
            raise ValueError(
                f"unrecognised severity {severity!r}; expected one of "
                f"{cls._LADDER} (any case, or an Enum whose value matches)"
            )
        return name

    @classmethod
    def _in_original_form(cls, original, canonical_name: str):
        """Return `canonical_name` shaped like `original` was.

        An Enum in gives the corresponding Enum member out, so a caller can
        assign the result straight back to `proposal.severity` without it
        turning into a bare string and breaking `severity.value` in
        `to_dict()`. Lowercase in gives lowercase out; anything else gives the
        canonical uppercase name.
        """
        if isinstance(original, Enum):
            for member in type(original):
                if str(member.value).strip().upper() == canonical_name:
                    return member
            raise ValueError(
                f"{type(original).__name__} has no member for {canonical_name}"
            )
        if isinstance(original, str) and original.strip().islower():
            return canonical_name.lower()
        return canonical_name

    @classmethod
    def adjust_severity(cls, base_severity, confidence: int):
        """
        Adjust severity based on confidence.

        Args:
            base_severity: Initial severity, as a CRITICAL/HIGH/MEDIUM/LOW
                string (any case) or an Enum member whose value is one of those.
            confidence: Confidence score (0-100)

        Returns:
            Adjusted severity, in the same form as `base_severity`.

        Deterministic and pure: same inputs always yield the same output.
        """
        name = cls._canonical_name(base_severity)
        index = cls._LADDER.index(name)

        if confidence < 40:
            # Low confidence: reduce severity by one level, floored at LOW.
            index = max(0, index - 1)
        elif confidence < 60:
            # Moderate-low confidence: reduce CRITICAL only.
            # Deliberately narrower than the <40 band. If this band dropped
            # every severity one level it would behave identically to that one,
            # leaving a branch with no distinct meaning; HIGH/MEDIUM/LOW are
            # therefore passed through unchanged here.
            if name == "CRITICAL":
                index -= 1
        # confidence >= 60: high confidence, keep severity as-is.

        return cls._in_original_form(base_severity, cls._LADDER[index])

    @classmethod
    def calculate_risk_score(cls, severity, confidence: int) -> int:
        """
        Calculate overall risk score (0-100).

        Risk = severity × confidence

        Args:
            severity: Issue severity (CRITICAL/HIGH/MEDIUM/LOW, any case, or a
                matching Enum member)
            confidence: Confidence score (0-100)

        Returns:
            Risk score (0-100)

        Severity is normalised the same way as in `adjust_severity`. The
        previous `severity_weight.get(severity, 50)` scored a lowercase
        'critical' as MEDIUM, so an enum-holding caller silently halved the risk
        of its worst findings.
        """
        severity_weight = {
            "CRITICAL": 100,
            "HIGH": 75,
            "MEDIUM": 50,
            "LOW": 25,
        }

        weight = severity_weight[cls._canonical_name(severity)]

        # Risk = severity weight × (confidence / 100)
        risk = (weight * confidence) // 100

        return min(100, risk)


def create_calibrated_proposal_explanation(
    base_explanation: str,
    calibrator: ConfidenceCalibrator,
) -> str:
    """
    Create proposal explanation with confidence reasoning.
    
    Args:
        base_explanation: Original explanation
        calibrator: Confidence calibrator with evidence
    
    Returns:
        Enhanced explanation with confidence details
    """
    return base_explanation + "\n\n" + "Confidence Analysis:\n" + calibrator.get_explanation()


# Example usage for analyzers:
#
# def _detect_issue(self, ...):
#     calibrator = ConfidenceCalibrator()
#     
#     # Add evidence as analysis progresses
#     calibrator.add_evidence(
#         ConfidenceSource.STATIC_PATTERN,
#         "Circular import detected through graph traversal"
#     )
#     
#     # If you find conflicting evidence
#     if certain_conditions:
#         calibrator.add_conflicting_evidence(
#             "Module only imported in tests, not production code"
#         )
#     
#     # Calculate final confidence
#     confidence = calibrator.calculate_confidence()
#     explanation = calibrator.get_explanation()
#     
#     # Adjust severity based on confidence
#     adjusted_severity = RiskBasedSeverityAdjuster.adjust_severity(
#         base_severity=Severity.HIGH,
#         confidence=confidence
#     )
#     
#     # Create proposal with calibrated values
#     proposal = IntelligenceProposal()
#     proposal.confidence_level = confidence
#     proposal.confidence_explanation = explanation
#     proposal.severity = adjusted_severity
#     ...
