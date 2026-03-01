"""
Phase 15.3: Automated Fix Candidate Generation from Analyzer Findings

Core service for converting intelligence proposals into CodeFix records.

Key Guarantees:
- Deterministic: Same findings → same fixes (ordered by file_path, line, type)
- Deduplication: Hash-based duplicate detection
- Risk scoring: Automated LOW/MEDIUM/HIGH classification
- Ledger integration: All generation events recorded (non-fatal)
- No auto-approval: Fixes always start in PROPOSED status
- Replayable: All operations deterministic and reproducible

Architecture:
- Consumes IntelligenceProposal objects from orchestrator
- Produces CodeFix records with governance metadata
- Emits FIX_CANDIDATES_GENERATED ledger event
- Does NOT modify analyzer behavior
- Does NOT bypass approval workflow
"""

from typing import List, Optional, Dict, Set, Any
from dataclasses import dataclass
import hashlib
import logging
from datetime import datetime
from sqlalchemy.orm import Session

# Import models
from app.models.code_fix import CodeFix, FixStatus
from app.models.analysis_result import AnalysisResult

# Import ledger (optional)
from agent.run_ledger import RunLedgerWriter
from agent.intelligence.proposal import IntelligenceProposal, Severity

logger = logging.getLogger(__name__)


@dataclass
class RiskAssessment:
    """Risk assessment for a fix candidate."""
    risk_level: str  # LOW | MEDIUM | HIGH
    confidence: float  # 0.0 - 1.0
    factors: List[str]  # Reasons for risk level
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "risk_level": self.risk_level,
            "confidence": self.confidence,
            "factors": self.factors,
        }


class FixGenerationService:
    """
    Service for generating fix candidates from analyzer findings.
    
    Phase 15.3: Automated fix generation with governance.
    
    Process:
    1. Accept IntelligenceProposal objects from orchestrator
    2. Convert to CodeFix records with deterministic ordering
    3. Deduplicate based on content hash
    4. Assign risk scores
    5. Generate patches (deterministic)
    6. Persist to database
    7. Emit ledger event (non-fatal)
    
    Guarantees:
    - Same input → same output (deterministic)
    - All fixes start in PROPOSED status (no auto-approval)
    - Ledger failures do not crash execution
    - Replayable from ledger events
    """
    
    def __init__(self, db: Session):
        """
        Initialize fix generation service.
        
        Args:
            db: Database session for persistence
        """
        self.db = db
        self._seen_hashes: Set[str] = set()  # Deduplication tracking
    
    def generate_from_findings(
        self,
        run_id: str,
        findings: List[IntelligenceProposal],
        repository_path: str,
        ledger: Optional[RunLedgerWriter] = None,
        result_id: Optional[int] = None,
    ) -> List[CodeFix]:
        """
        Generate fix candidates from analyzer findings.
        
        Core method for Phase 15.3 implementation.
        
        Args:
            run_id: Run ID for ledger association
            findings: List of IntelligenceProposal objects from orchestrator
            repository_path: Path to repository root
            ledger: Optional RunLedgerWriter for audit trail
            result_id: Optional AnalysisResult ID for linkage
        
        Returns:
            List of created CodeFix records (already persisted)
        
        Process:
            1. Sort findings deterministically
            2. Convert each finding to fix candidate
            3. Deduplicate by content hash
            4. Assign risk scores
            5. Generate patches
            6. Persist to database
            7. Emit ledger event
        
        Guarantees:
            - Deterministic ordering (file_path, line_number, finding_type)
            - Deduplication (same location + type = same fix)
            - Risk scoring (LOW/MEDIUM/HIGH based on size/complexity)
            - Ledger recording (non-fatal failures)
            - No auto-approval (all fixes start PROPOSED)
        """
        logger.info(f"Generating fix candidates from {len(findings)} findings for run {run_id}")
        
        # Step 1: Sort findings deterministically
        sorted_findings = self._sort_findings_deterministically(findings)
        
        # Step 2: Convert findings to fix candidates
        fix_candidates = []
        for finding in sorted_findings:
            try:
                candidate = self._convert_finding_to_candidate(
                    finding=finding,
                    run_id=run_id,
                    result_id=result_id,
                    repository_path=repository_path,
                )
                if candidate:
                    fix_candidates.append(candidate)
            except Exception as e:
                logger.warning(f"Failed to convert finding {finding.proposal_id} to candidate: {e}")
                continue
        
        # Step 3: Deduplicate
        unique_candidates = self._deduplicate_candidates(fix_candidates)
        
        logger.info(f"Generated {len(unique_candidates)} unique fix candidates (from {len(fix_candidates)} total)")
        
        # Step 4: Persist to database
        created_fixes = self._persist_fixes(unique_candidates)
        
        # Step 5: Emit ledger event (non-fatal)
        if ledger:
            self._emit_ledger_event(
                ledger=ledger,
                run_id=run_id,
                fixes=created_fixes,
            )
        
        return created_fixes
    
    def _sort_findings_deterministically(
        self,
        findings: List[IntelligenceProposal]
    ) -> List[IntelligenceProposal]:
        """
        Sort findings to ensure deterministic ordering.
        
        Sort key: (file_path, line_number, bug_class)
        
        This guarantees that:
        - Same findings always produce same order
        - Replay from ledger produces identical results
        - Fix IDs are stable across runs
        
        Args:
            findings: List of IntelligenceProposal objects
        
        Returns:
            Sorted list of findings
        """
        def sort_key(finding: IntelligenceProposal) -> tuple:
            # Get first affected file (or empty string)
            file_path = ""
            line_number = 0
            
            if finding.affected_files:
                file_path = finding.affected_files[0].path
                # Extract line number from line_range (format: "10-20" or "10")
                line_range = finding.affected_files[0].line_range or "0"
                try:
                    line_number = int(line_range.split('-')[0])
                except (ValueError, AttributeError):
                    line_number = 0
            
            # Sort by: file_path, line_number, bug_class
            bug_class = finding.bug_class.value if finding.bug_class else "unknown"
            
            return (file_path, line_number, bug_class)
        
        return sorted(findings, key=sort_key)
    
    def _convert_finding_to_candidate(
        self,
        finding: IntelligenceProposal,
        run_id: str,
        result_id: Optional[int],
        repository_path: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Convert IntelligenceProposal to fix candidate dictionary.
        
        Args:
            finding: IntelligenceProposal from analyzer
            run_id: Run ID for association
            result_id: Optional AnalysisResult ID
            repository_path: Repository path
        
        Returns:
            Dictionary with fix candidate data, or None if conversion fails
        """
        # Extract file information
        if not finding.affected_files:
            logger.debug(f"Finding {finding.proposal_id} has no affected files, skipping")
            return None
        
        primary_file = finding.affected_files[0]
        file_path = primary_file.path
        
        # Extract line information
        line_number = 0
        if primary_file.line_range:
            try:
                line_number = int(primary_file.line_range.split('-')[0])
            except (ValueError, AttributeError):
                line_number = 0
        
        # Generate risk assessment
        risk = self._assess_risk(finding)
        
        # Generate patch (deterministic)
        patch = self._generate_patch(finding, repository_path)
        
        # Extract fix strategies as explanation
        explanation = self._extract_explanation(finding)
        
        # Create candidate dictionary
        candidate = {
            "file_path": file_path,
            "original_code": finding.risk_explanation or "",
            "fixed_code": self._extract_fixed_code(finding),
            "explanation": explanation,
            "patch": patch,
            "status": FixStatus.PROPOSED,  # Always start as PROPOSED
            
            # Phase 15.3: New governance fields
            "risk_level": risk.risk_level,
            "confidence": int(risk.confidence * 100),  # Convert 0.0-1.0 to 0-100
            "generated_by_run": True,
            "finding_id": finding.proposal_id,
            
            # Ledger tracking
            "ledger_run_id": run_id,
            
            # Metadata
            "ai_provider": "intelligence-orchestrator",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            
            # Link to AnalysisResult if provided
            "result_id": result_id,
        }
        
        return candidate
    
    def _assess_risk(self, finding: IntelligenceProposal) -> RiskAssessment:
        """
        Assess risk level for a fix candidate.
        
        Risk Model:
        - LOW: Single file, small change (<10 lines), simple fix
        - MEDIUM: Multiple changes OR 10-50 lines OR medium complexity
        - HIGH: Multiple files OR >50 lines OR structural change
        
        Phase 16: Prioritize reliability findings (crash risks, resource leaks)
        - CRITICAL reliability bugs get automatic HIGH risk classification
        - Reliability fixes have higher confidence due to production impact
        
        Args:
            finding: IntelligenceProposal to assess
        
        Returns:
            RiskAssessment with level, confidence, and factors
        """
        factors = []
        risk_score = 0.0  # 0.0 = low, 1.0 = high
        
        # Phase 16: Special handling for reliability findings
        is_reliability = finding.bug_class.value in [
            'crash_risks',
            'resource_leaks',
            'reliability_anti_patterns',
            'scalability_risks',
            'edge_case_vulnerabilities',
        ]
        
        if is_reliability:
            factors.append("reliability bug (production-critical)")
            # Boost risk score for reliability issues - they affect live users
            risk_score += 0.3
        
        # Factor 1: Number of affected files
        file_count = len(finding.affected_files)
        if file_count == 1:
            factors.append("single file")
            risk_score += 0.0
        elif file_count <= 3:
            factors.append(f"{file_count} files")
            risk_score += 0.3
        else:
            factors.append(f"{file_count} files (multi-file)")
            risk_score += 0.6
        
        # Factor 2: Severity level
        if finding.severity == Severity.CRITICAL:
            factors.append("critical severity")
            risk_score += 0.4
            # Critical + Reliability = definitely HIGH risk
            if is_reliability:
                risk_score = max(risk_score, 0.7)
        elif finding.severity == Severity.HIGH:
            factors.append("high severity")
            risk_score += 0.2
        elif finding.severity == Severity.MEDIUM:
            factors.append("medium severity")
            risk_score += 0.1
        else:
            factors.append("low severity")
            risk_score += 0.0
        
        # Factor 3: Estimated patch size (heuristic based on problem statement length)
        problem_length = len(finding.problem_statement)
        if problem_length < 100:
            factors.append("small change")
            risk_score += 0.0
        elif problem_length < 300:
            factors.append("medium change")
            risk_score += 0.2
        else:
            factors.append("large change")
            risk_score += 0.4
        
        # Factor 4: Number of strategies (more strategies = more complexity)
        strategy_count = len(finding.suggested_strategies)
        if strategy_count > 3:
            factors.append(f"{strategy_count} strategies (complex)")
            risk_score += 0.2
        
        # Determine risk level
        if risk_score < 0.3:
            risk_level = "LOW"
            confidence = 0.8
        elif risk_score < 0.7:
            risk_level = "MEDIUM"
            confidence = 0.7
        else:
            risk_level = "HIGH"
            confidence = 0.6
        
        # Phase 16: Boost confidence for reliability findings
        # These are well-understood patterns with clear production impact
        if is_reliability and finding.severity in [Severity.CRITICAL, Severity.HIGH]:
            confidence = min(0.95, confidence + 0.15)
            factors.append("high confidence (known reliability pattern)")
        
        return RiskAssessment(
            risk_level=risk_level,
            confidence=confidence,
            factors=factors,
        )
    
    def _generate_patch(
        self,
        finding: IntelligenceProposal,
        repository_path: str
    ) -> str:
        """
        Generate unified diff patch for a finding.
        
        Deterministic: Same finding → same patch.
        
        For Phase 15.3, we generate a placeholder patch based on the
        first fix strategy. In production, this would integrate with
        actual code transformation tools.
        
        Args:
            finding: IntelligenceProposal with fix strategies
            repository_path: Repository root path
        
        Returns:
            Unified diff patch string
        """
        # For now, generate placeholder patch
        # In production, this would use actual code transformation
        
        if not finding.affected_files:
            return ""
        
        file_path = finding.affected_files[0].path
        line_range = finding.affected_files[0].line_range or "1"
        
        # Use first strategy as basis for patch
        strategy_description = ""
        if finding.suggested_strategies:
            strategy_description = finding.suggested_strategies[0].description
        
        # Generate deterministic patch format
        patch = f"""--- a/{file_path}
+++ b/{file_path}
@@ -{line_range},1 +{line_range},1 @@
-{finding.risk_explanation[:100] if finding.risk_explanation else '# existing code'}
+# Fixed: {strategy_description[:100]}
"""
        
        return patch
    
    def _extract_explanation(self, finding: IntelligenceProposal) -> str:
        """
        Extract fix explanation from finding.
        
        Combines problem statement with fix strategies.
        
        Args:
            finding: IntelligenceProposal
        
        Returns:
            Human-readable explanation string
        """
        explanation_parts = []
        
        # Problem statement
        explanation_parts.append(f"Problem: {finding.problem_statement}")
        
        # Add strategies
        if finding.suggested_strategies:
            explanation_parts.append("\nProposed Strategies:")
            for i, strategy in enumerate(finding.suggested_strategies[:3], 1):
                explanation_parts.append(f"{i}. {strategy.name}: {strategy.description[:200]}")
        
        return "\n".join(explanation_parts)
    
    def _extract_fixed_code(self, finding: IntelligenceProposal) -> str:
        """
        Extract fixed code representation from finding.
        
        For Phase 15.3, this is a placeholder based on the first strategy.
        In production, this would contain actual transformed code.
        
        Args:
            finding: IntelligenceProposal
        
        Returns:
            Fixed code string
        """
        if finding.suggested_strategies:
            # Use first strategy description as fixed code placeholder
            return f"# Proposed fix: {finding.suggested_strategies[0].description}"
        
        return "# Fix to be determined"
    
    def _deduplicate_candidates(
        self,
        candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Deduplicate fix candidates using content-based hashing.
        
        Deduplication key: hash(file_path + line_number + finding_id)
        
        Args:
            candidates: List of candidate dictionaries
        
        Returns:
            Deduplicated list of candidates
        """
        unique_candidates = []
        
        for candidate in candidates:
            # Generate hash key
            hash_key = self._generate_candidate_hash(candidate)
            
            # Skip if already seen
            if hash_key in self._seen_hashes:
                logger.debug(f"Skipping duplicate candidate: {candidate.get('file_path')}:{candidate.get('line_number')}")
                continue
            
            # Add to unique set
            self._seen_hashes.add(hash_key)
            unique_candidates.append(candidate)
        
        return unique_candidates
    
    def _generate_candidate_hash(self, candidate: Dict[str, Any]) -> str:
        """
        Generate deterministic hash for candidate deduplication.
        
        Hash key: file_path + line_number + finding_id
        
        Args:
            candidate: Candidate dictionary
        
        Returns:
            SHA256 hash string
        """
        hash_input = (
            f"{candidate.get('file_path', '')}:"
            f"{candidate.get('line_number', 0)}:"
            f"{candidate.get('finding_id', '')}"
        )
        
        return hashlib.sha256(hash_input.encode()).hexdigest()
    
    def _persist_fixes(self, candidates: List[Dict[str, Any]]) -> List[CodeFix]:
        """
        Persist fix candidates to database.
        
        Args:
            candidates: List of candidate dictionaries
        
        Returns:
            List of created CodeFix records
        """
        created_fixes = []
        
        for candidate in candidates:
            try:
                # Create CodeFix record
                fix = CodeFix(**candidate)
                
                # Add to session
                self.db.add(fix)
                self.db.flush()  # Get ID without committing
                
                created_fixes.append(fix)
                
            except Exception as e:
                logger.error(f"Failed to persist fix candidate: {e}")
                continue
        
        # Commit all fixes
        try:
            self.db.commit()
            logger.info(f"Successfully persisted {len(created_fixes)} fix candidates")
        except Exception as e:
            logger.error(f"Failed to commit fix candidates: {e}")
            self.db.rollback()
            return []
        
        return created_fixes
    
    def _emit_ledger_event(
        self,
        ledger: RunLedgerWriter,
        run_id: str,
        fixes: List[CodeFix],
    ) -> None:
        """
        Emit FIX_CANDIDATES_GENERATED ledger event.
        
        Non-fatal: Failures do not crash execution.
        
        Args:
            ledger: RunLedgerWriter instance
            run_id: Run ID for association
            fixes: List of created CodeFix records
        """
        try:
            # Calculate risk distribution
            risk_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
            for fix in fixes:
                risk_level = fix.risk_level or "MEDIUM"
                risk_counts[risk_level] = risk_counts.get(risk_level, 0) + 1
            
            # Prepare payload
            payload = {
                "run_id": run_id,
                "fix_count": len(fixes),
                "low_risk": risk_counts["LOW"],
                "medium_risk": risk_counts["MEDIUM"],
                "high_risk": risk_counts["HIGH"],
                "fix_ids": [fix.id for fix in fixes],
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            # Emit event
            success = ledger.append_event(
                event_type="FIX_CANDIDATES_GENERATED",
                summary=f"Generated {len(fixes)} fix candidates from analyzer findings",
                actor="SYSTEM",
                actor_role="FIX_GENERATOR",
                phase="INTELLIGENCE",
                payload_ref=payload,
            )
            
            if success:
                logger.info(f"Successfully recorded fix generation event to ledger")
            else:
                logger.warning(f"Failed to record fix generation event to ledger (non-fatal)")
                
        except Exception as e:
            # Ledger failure is non-fatal
            logger.warning(f"Error recording fix generation to ledger: {e}", exc_info=True)
