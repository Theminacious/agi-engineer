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
    """
    
    @staticmethod
    def adjust_severity(base_severity: str, confidence: int) -> str:
        """
        Adjust severity based on confidence.
        
        Args:
            base_severity: Initial severity (CRITICAL, HIGH, MEDIUM, LOW)
            confidence: Confidence score (0-100)
        
        Returns:
            Adjusted severity
        """
        # If low confidence in supposedly critical issue, reduce to high
        # because it might be false positive
        
        if confidence < 40:
            # Low confidence: reduce severity by one level
            if base_severity == "CRITICAL":
                return "HIGH"
            elif base_severity == "HIGH":
                return "MEDIUM"
            elif base_severity == "MEDIUM":
                return "LOW"
            else:
                return "LOW"
        
        elif confidence < 60:
            # Moderate-low confidence: slight reduction
            if base_severity == "CRITICAL":
                return "HIGH"
            else:
                return base_severity
        
        else:
            # High confidence: keep severity as-is
            return base_severity
    
    @staticmethod
    def calculate_risk_score(severity: str, confidence: int) -> int:
        """
        Calculate overall risk score (0-100).
        
        Risk = severity × confidence
        
        Args:
            severity: Issue severity (CRITICAL/HIGH/MEDIUM/LOW)
            confidence: Confidence score (0-100)
        
        Returns:
            Risk score (0-100)
        """
        severity_weight = {
            "CRITICAL": 100,
            "HIGH": 75,
            "MEDIUM": 50,
            "LOW": 25,
        }
        
        weight = severity_weight.get(severity, 50)
        
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
