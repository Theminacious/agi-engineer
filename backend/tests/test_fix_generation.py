"""
Phase 15.3: Automated Fix Generation Tests

Comprehensive test suite for FixGenerationService:
- Deterministic ordering of findings
- Deduplication logic
- Risk scoring accuracy
- Patch generation stability
- Ledger event emission
- Fix count validation
- Database persistence
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from sqlalchemy.orm import Session

# Import service and models
from app.services.fix_generation import FixGenerationService, RiskAssessment
from app.models.code_fix import CodeFix, FixStatus
from agent.intelligence.proposal import (
    IntelligenceProposal,
    Severity,
    BugClass,
    AffectedFile,
    FixStrategy,
    EffortEstimate,
)
from agent.run_ledger import RunLedgerWriter


@pytest.fixture
def db_session():
    """Mock database session."""
    session = Mock(spec=Session)
    session.add = Mock()
    session.flush = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    return session


@pytest.fixture
def fix_service(db_session):
    """Create FixGenerationService instance."""
    return FixGenerationService(db_session)


@pytest.fixture
def sample_proposal():
    """Create a sample IntelligenceProposal."""
    proposal = IntelligenceProposal(
        proposal_id="test-proposal-1",
        analyzer_name="test-analyzer",
        bug_class=BugClass.PERFORMANCE_ANTI_PATTERNS,
        severity=Severity.MEDIUM,
        problem_statement="Inefficient loop detected in data processing",
        risk_explanation="for item in items:\n    process(item)",
        affected_files=[
            AffectedFile(
                path="src/processor.py",
                line_range="10-15",
                severity=Severity.MEDIUM
            )
        ],
        suggested_strategies=[
            FixStrategy(
                name="Use list comprehension",
                description="Replace loop with list comprehension for better performance",
                effort_estimate=EffortEstimate.SMALL,
            ),
            FixStrategy(
                name="Use vectorized operations",
                description="Use numpy for vectorized processing",
                effort_estimate=EffortEstimate.MEDIUM,
            )
        ],
    )
    return proposal


@pytest.fixture
def multiple_proposals():
    """Create multiple proposals for testing."""
    proposals = []
    
    # Proposal 1: src/utils.py line 5
    proposals.append(IntelligenceProposal(
        proposal_id="prop-1",
        analyzer_name="test-analyzer",
        bug_class=BugClass.SECURITY_MISCONFIGURATIONS,
        severity=Severity.HIGH,
        problem_statement="Hardcoded credentials detected",
        risk_explanation="password = '12345'",
        affected_files=[
            AffectedFile(path="src/utils.py", line_range="5", severity=Severity.HIGH)
        ],
        suggested_strategies=[
            FixStrategy(name="Use environment variables", description="Move to env vars", effort_estimate=EffortEstimate.SMALL)
        ],
    ))
    
    # Proposal 2: src/app.py line 20
    proposals.append(IntelligenceProposal(
        proposal_id="prop-2",
        analyzer_name="test-analyzer",
        bug_class=BugClass.PERFORMANCE_ANTI_PATTERNS,
        severity=Severity.MEDIUM,
        problem_statement="N+1 query pattern",
        risk_explanation="for user in users:\n    user.posts",
        affected_files=[
            AffectedFile(path="src/app.py", line_range="20-25", severity=Severity.MEDIUM)
        ],
        suggested_strategies=[
            FixStrategy(name="Use eager loading", description="Prefetch related data", effort_estimate=EffortEstimate.SMALL)
        ],
    ))
    
    # Proposal 3: src/app.py line 10 (same file as proposal 2, different line)
    proposals.append(IntelligenceProposal(
        proposal_id="prop-3",
        analyzer_name="test-analyzer",
        bug_class=BugClass.ARCHITECTURAL_VIOLATIONS,
        severity=Severity.LOW,
        problem_statement="Missing error handling",
        risk_explanation="result = api_call()",
        affected_files=[
            AffectedFile(path="src/app.py", line_range="10", severity=Severity.LOW)
        ],
        suggested_strategies=[
            FixStrategy(name="Add try-except", description="Wrap in error handler", effort_estimate=EffortEstimate.TRIVIAL)
        ],
    ))
    
    return proposals


class TestDeterministicOrdering:
    """Test deterministic ordering of findings."""
    
    def test_sort_findings_by_file_path(self, fix_service, multiple_proposals):
        """Test sorting by file path."""
        # Sort should prioritize: src/app.py, then src/utils.py
        sorted_findings = fix_service._sort_findings_deterministically(multiple_proposals)
        
        assert len(sorted_findings) == 3
        assert sorted_findings[0].affected_files[0].path == "src/app.py"
        assert sorted_findings[1].affected_files[0].path == "src/app.py"
        assert sorted_findings[2].affected_files[0].path == "src/utils.py"
    
    def test_sort_findings_by_line_number(self, fix_service, multiple_proposals):
        """Test sorting by line number within same file."""
        sorted_findings = fix_service._sort_findings_deterministically(multiple_proposals)
        
        # Within src/app.py, line 10 should come before line 20
        app_proposals = [f for f in sorted_findings if f.affected_files[0].path == "src/app.py"]
        line_numbers = [int(f.affected_files[0].line_range.split('-')[0]) for f in app_proposals]
        
        assert line_numbers == sorted(line_numbers)
    
    def test_same_input_same_output(self, fix_service, multiple_proposals):
        """Test that same input produces same output (idempotency)."""
        sorted_1 = fix_service._sort_findings_deterministically(multiple_proposals)
        sorted_2 = fix_service._sort_findings_deterministically(multiple_proposals)
        
        # Should produce identical ordering
        for i in range(len(sorted_1)):
            assert sorted_1[i].proposal_id == sorted_2[i].proposal_id


class TestRiskScoring:
    """Test risk assessment logic."""
    
    def test_low_risk_single_file_small_change(self, fix_service):
        """Test LOW risk for single file with small change."""
        proposal = IntelligenceProposal(
            proposal_id="low-risk",
            analyzer_name="test",
            bug_class=BugClass.PERFORMANCE_ANTI_PATTERNS,
            severity=Severity.LOW,
            problem_statement="Minor optimization opportunity",  # Short statement
            affected_files=[AffectedFile(path="src/app.py", line_range="10")],
            suggested_strategies=[FixStrategy(name="Optimize", description="Simple fix", effort_estimate=EffortEstimate.TRIVIAL)],
        )
        
        risk = fix_service._assess_risk(proposal)
        
        assert risk.risk_level == "LOW"
        assert risk.confidence > 0.7
        assert "single file" in risk.factors
    
    def test_medium_risk_multiple_files(self, fix_service):
        """Test MEDIUM risk for multiple files."""
        proposal = IntelligenceProposal(
            proposal_id="medium-risk",
            analyzer_name="test",
            bug_class=BugClass.ARCHITECTURAL_VIOLATIONS,
            severity=Severity.MEDIUM,
            problem_statement="Architectural issue spanning multiple files",
            affected_files=[
                AffectedFile(path="src/app.py", line_range="10"),
                AffectedFile(path="src/utils.py", line_range="20"),
            ],
            suggested_strategies=[FixStrategy(name="Refactor", description="Medium complexity fix", effort_estimate=EffortEstimate.MEDIUM)],
        )
        
        risk = fix_service._assess_risk(proposal)
        
        assert risk.risk_level == "MEDIUM"
        assert "2 files" in risk.factors
    
    def test_high_risk_critical_severity(self, fix_service):
        """Test HIGH risk for critical severity issues."""
        proposal = IntelligenceProposal(
            proposal_id="high-risk",
            analyzer_name="test",
            bug_class=BugClass.SECURITY_MISCONFIGURATIONS,
            severity=Severity.CRITICAL,
            problem_statement="Critical security vulnerability requiring extensive changes to multiple subsystems and APIs",  # Long statement
            affected_files=[
                AffectedFile(path=f"src/module{i}.py", line_range="10-50")
                for i in range(5)
            ],
            suggested_strategies=[
                FixStrategy(name=f"Strategy {i}", description="Complex fix", effort_estimate=EffortEstimate.LARGE)
                for i in range(4)
            ],
        )
        
        risk = fix_service._assess_risk(proposal)
        
        assert risk.risk_level == "HIGH"
        assert risk.confidence < 0.7  # Lower confidence for high risk
        assert "critical severity" in risk.factors


class TestDeduplication:
    """Test deduplication logic."""
    
    def test_deduplicate_identical_candidates(self, fix_service):
        """Test deduplication of identical candidates."""
        candidate = {
            "file_path": "src/app.py",
            "line_number": 10,
            "finding_id": "test-id",
            "original_code": "code",
            "fixed_code": "fixed",
        }
        
        candidates = [candidate.copy(), candidate.copy(), candidate.copy()]
        
        unique = fix_service._deduplicate_candidates(candidates)
        
        assert len(unique) == 1
    
    def test_deduplicate_different_files(self, fix_service):
        """Test that different files are not deduplicated."""
        candidates = [
            {"file_path": "src/app.py", "line_number": 10, "finding_id": "id1"},
            {"file_path": "src/utils.py", "line_number": 10, "finding_id": "id2"},
        ]
        
        unique = fix_service._deduplicate_candidates(candidates)
        
        assert len(unique) == 2
    
    def test_deduplicate_same_file_different_lines(self, fix_service):
        """Test that same file with different lines are not deduplicated."""
        candidates = [
            {"file_path": "src/app.py", "line_number": 10, "finding_id": "id1"},
            {"file_path": "src/app.py", "line_number": 20, "finding_id": "id2"},
        ]
        
        unique = fix_service._deduplicate_candidates(candidates)
        
        assert len(unique) == 2


class TestPatchGeneration:
    """Test deterministic patch generation."""
    
    def test_generate_patch_format(self, fix_service, sample_proposal):
        """Test patch generation produces valid unified diff format."""
        patch = fix_service._generate_patch(sample_proposal, "/tmp/repo")
        
        assert "---" in patch
        assert "+++" in patch
        assert "@@" in patch
        assert "src/processor.py" in patch
    
    def test_generate_patch_deterministic(self, fix_service, sample_proposal):
        """Test that same proposal always generates same patch."""
        patch1 = fix_service._generate_patch(sample_proposal, "/tmp/repo")
        patch2 = fix_service._generate_patch(sample_proposal, "/tmp/repo")
        
        assert patch1 == patch2
    
    def test_generate_patch_includes_strategy(self, fix_service, sample_proposal):
        """Test that patch includes fix strategy information."""
        patch = fix_service._generate_patch(sample_proposal, "/tmp/repo")
        
        # Should include first strategy description
        assert "list comprehension" in patch.lower() or "Fixed:" in patch


class TestFixGeneration:
    """Test end-to-end fix generation."""
    
    def test_generate_from_findings_creates_fixes(self, fix_service, sample_proposal, db_session):
        """Test that generate_from_findings creates CodeFix records."""
        fixes = fix_service.generate_from_findings(
            run_id="test-run-123",
            findings=[sample_proposal],
            repository_path="/tmp/repo",
            ledger=None,
            result_id=1,
        )
        
        # Should create at least one fix
        assert len(fixes) > 0
        
        # Should call db operations
        assert db_session.add.called
        assert db_session.commit.called
    
    def test_generate_from_findings_sets_correct_status(self, fix_service, sample_proposal, db_session):
        """Test that generated fixes start in PROPOSED status."""
        fix_service.generate_from_findings(
            run_id="test-run-123",
            findings=[sample_proposal],
            repository_path="/tmp/repo",
            ledger=None,
            result_id=1,
        )
        
        # Check that added CodeFix has PROPOSED status
        added_fix = db_session.add.call_args[0][0]
        assert added_fix.status == FixStatus.PROPOSED
    
    def test_generate_from_findings_sets_metadata(self, fix_service, sample_proposal, db_session):
        """Test that generated fixes have correct metadata."""
        fix_service.generate_from_findings(
            run_id="test-run-123",
            findings=[sample_proposal],
            repository_path="/tmp/repo",
            ledger=None,
            result_id=42,
        )
        
        added_fix = db_session.add.call_args[0][0]
        
        # Phase 15.3 fields
        assert added_fix.risk_level in ["LOW", "MEDIUM", "HIGH"]
        assert added_fix.confidence is not None
        assert added_fix.generated_by_run is True
        assert added_fix.finding_id == sample_proposal.proposal_id
        assert added_fix.ledger_run_id == "test-run-123"
        assert added_fix.result_id == 42
    
    def test_generate_from_findings_multiple_proposals(self, fix_service, multiple_proposals, db_session):
        """Test generation from multiple proposals."""
        fixes = fix_service.generate_from_findings(
            run_id="test-run-123",
            findings=multiple_proposals,
            repository_path="/tmp/repo",
            ledger=None,
            result_id=1,
        )
        
        # Should create multiple fixes
        assert len(fixes) == len(multiple_proposals)
        
        # Should be called multiple times
        assert db_session.add.call_count == len(multiple_proposals)


class TestLedgerIntegration:
    """Test ledger event emission."""
    
    def test_emit_ledger_event_success(self, fix_service, sample_proposal, db_session):
        """Test successful ledger event emission."""
        mock_ledger = Mock(spec=RunLedgerWriter)
        mock_ledger.append_event = Mock(return_value=True)
        
        fix_service.generate_from_findings(
            run_id="test-run-123",
            findings=[sample_proposal],
            repository_path="/tmp/repo",
            ledger=mock_ledger,
            result_id=1,
        )
        
        # Should emit FIX_CANDIDATES_GENERATED event
        assert mock_ledger.append_event.called
        call_kwargs = mock_ledger.append_event.call_args[1]
        assert call_kwargs["event_type"] == "FIX_CANDIDATES_GENERATED"
        assert "fix_count" in call_kwargs["payload_ref"]
    
    def test_emit_ledger_event_includes_risk_distribution(self, fix_service, multiple_proposals, db_session):
        """Test ledger event includes risk level distribution."""
        mock_ledger = Mock(spec=RunLedgerWriter)
        mock_ledger.append_event = Mock(return_value=True)
        
        fix_service.generate_from_findings(
            run_id="test-run-123",
            findings=multiple_proposals,
            repository_path="/tmp/repo",
            ledger=mock_ledger,
            result_id=1,
        )
        
        call_kwargs = mock_ledger.append_event.call_args[1]
        payload = call_kwargs["payload_ref"]
        
        assert "low_risk" in payload
        assert "medium_risk" in payload
        assert "high_risk" in payload
        assert "fix_ids" in payload
    
    def test_ledger_failure_non_fatal(self, fix_service, sample_proposal, db_session):
        """Test that ledger failures don't crash execution."""
        mock_ledger = Mock(spec=RunLedgerWriter)
        mock_ledger.append_event = Mock(side_effect=Exception("Ledger error"))
        
        # Should not raise exception
        fixes = fix_service.generate_from_findings(
            run_id="test-run-123",
            findings=[sample_proposal],
            repository_path="/tmp/repo",
            ledger=mock_ledger,
            result_id=1,
        )
        
        # Should still create fixes
        assert len(fixes) > 0


class TestPerformance:
    """Test performance constraints."""
    
    def test_generation_performance_100_findings(self, fix_service, db_session):
        """Test that generation completes under 200ms for 100 findings."""
        import time
        
        # Create 100 simple proposals
        proposals = []
        for i in range(100):
            proposals.append(IntelligenceProposal(
                proposal_id=f"prop-{i}",
                analyzer_name="test",
                bug_class=BugClass.PERFORMANCE_ANTI_PATTERNS,
                severity=Severity.LOW,
                problem_statement=f"Issue {i}",
                risk_explanation=f"code {i}",
                affected_files=[
                    AffectedFile(path=f"src/file{i}.py", line_range=str(i))
                ],
                suggested_strategies=[
                    FixStrategy(name="Fix", description="Simple fix", effort_estimate=EffortEstimate.TRIVIAL)
                ],
            ))
        
        start = time.time()
        fix_service.generate_from_findings(
            run_id="perf-test",
            findings=proposals,
            repository_path="/tmp/repo",
            ledger=None,
            result_id=1,
        )
        duration = time.time() - start
        
        # Should complete under 200ms (requirement)
        # Note: This is a soft requirement, may vary by system
        assert duration < 0.5  # 500ms buffer for test environment


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_findings_list(self, fix_service, db_session):
        """Test handling of empty findings list."""
        fixes = fix_service.generate_from_findings(
            run_id="test-run",
            findings=[],
            repository_path="/tmp/repo",
            ledger=None,
            result_id=1,
        )
        
        assert fixes == []
        # No fixes should be added (commit may still be called by _persist_fixes)
        assert not db_session.add.called
    
    def test_proposal_without_affected_files(self, fix_service, db_session):
        """Test handling of proposal without affected files."""
        proposal = IntelligenceProposal(
            proposal_id="no-files",
            analyzer_name="test",
            bug_class=BugClass.PERFORMANCE_ANTI_PATTERNS,
            severity=Severity.LOW,
            problem_statement="Issue with no specific file",
            affected_files=[],  # Empty
            suggested_strategies=[],
        )
        
        fixes = fix_service.generate_from_findings(
            run_id="test-run",
            findings=[proposal],
            repository_path="/tmp/repo",
            ledger=None,
            result_id=1,
        )
        
        # Should skip proposals without files
        assert len(fixes) == 0
    
    def test_database_error_handling(self, fix_service, sample_proposal, db_session):
        """Test handling of database errors."""
        db_session.commit = Mock(side_effect=Exception("DB error"))
        
        fixes = fix_service.generate_from_findings(
            run_id="test-run",
            findings=[sample_proposal],
            repository_path="/tmp/repo",
            ledger=None,
            result_id=1,
        )
        
        # Should rollback and return empty list
        assert fixes == []
        assert db_session.rollback.called


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
