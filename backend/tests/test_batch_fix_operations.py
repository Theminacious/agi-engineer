"""
Phase 15.2: Batch Fix Operations Tests

Comprehensive test suite for batch fix functionality:
- Validation logic (conflicts, risk levels)
- Batch approval/rejection/application
- Ledger event recording
- Deterministic patch generation
- Plan enforcement
- Partial success handling
"""

import pytest
import hashlib
from unittest.mock import Mock, MagicMock
from sqlalchemy.orm import Session

from app.models.code_fix import CodeFix, FixStatus
from app.services.batch_fix import BatchFixService
from app.plans import PlanTier, create_plan_context


@pytest.fixture
def db_session():
    """Mock database session."""
    return MagicMock(spec=Session)


@pytest.fixture
def batch_service(db_session):
    """Create BatchFixService instance with mocked sub-services."""
    service = BatchFixService(db_session)
    # Replace sub-services with mocks so we control them directly
    service.approval_service = Mock()
    service.application_service = Mock()
    return service


@pytest.fixture
def sample_fixes():
    """Create sample fix objects."""
    fix1 = Mock(spec=CodeFix)
    fix1.id = 1
    fix1.file_path = "src/app.py"
    fix1.status = FixStatus.PROPOSED
    fix1.patch = "--- a/src/app.py\n+++ b/src/app.py\n@@ -1,1 +1,1 @@\n-old\n+new"
    fix1.original_code = "old"
    fix1.fixed_code = "new"
    fix1.to_dict.return_value = {"id": 1, "status": "proposed", "file_path": "src/app.py"}

    fix2 = Mock(spec=CodeFix)
    fix2.id = 2
    fix2.file_path = "src/utils.py"
    fix2.status = FixStatus.PROPOSED
    fix2.patch = "--- a/src/utils.py\n+++ b/src/utils.py\n@@ -1,1 +1,1 @@\n-old\n+new"
    fix2.original_code = "old"
    fix2.fixed_code = "new"
    fix2.to_dict.return_value = {"id": 2, "status": "proposed", "file_path": "src/utils.py"}

    fix3 = Mock(spec=CodeFix)
    fix3.id = 3
    fix3.file_path = "src/app.py"  # Conflict with fix1
    fix3.status = FixStatus.PROPOSED
    fix3.patch = "--- a/src/app.py\n+++ b/src/app.py\n@@ -5,1 +5,1 @@\n-old2\n+new2"
    fix3.original_code = "old2"
    fix3.fixed_code = "new2"
    fix3.to_dict.return_value = {"id": 3, "status": "proposed", "file_path": "src/app.py"}

    return [fix1, fix2, fix3]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
class TestBatchValidation:
    """Test batch validation logic."""

    def test_validate_batch_success(self, batch_service, db_session, sample_fixes):
        """Test successful validation with no conflicts."""
        db_session.query.return_value.filter.return_value.all.return_value = sample_fixes[:2]
        plan_context = create_plan_context(PlanTier.TEAM)

        result = batch_service.validate_batch(
            fix_ids=[1, 2],
            plan_context=plan_context,
            operation="approve",
        )

        assert result["valid"] is True
        assert result["metadata"]["batch_size"] == 2
        assert result["metadata"]["files_affected"] == 2

    def test_validate_batch_missing_fixes(self, batch_service, db_session):
        """Test validation with missing fix IDs."""
        db_session.query.return_value.filter.return_value.all.return_value = []
        plan_context = create_plan_context(PlanTier.TEAM)

        result = batch_service.validate_batch(
            fix_ids=[999],
            plan_context=plan_context,
        )

        assert result["valid"] is False
        assert any("not found" in err.lower() for err in result["errors"])

    def test_validate_batch_file_conflicts(self, batch_service, db_session, sample_fixes):
        """Test detection of file conflicts in apply mode."""
        conflicting = [sample_fixes[0], sample_fixes[2]]
        for f in conflicting:
            f.status = FixStatus.APPROVED
        db_session.query.return_value.filter.return_value.all.return_value = conflicting
        plan_context = create_plan_context(PlanTier.TEAM)

        result = batch_service.validate_batch(
            fix_ids=[1, 3],
            plan_context=plan_context,
            operation="apply",
        )

        assert result["valid"] is True
        assert len(result["warnings"]) >= 1
        assert any("src/app.py" in w for w in result["warnings"])

    def test_validate_batch_wrong_status(self, batch_service, db_session, sample_fixes):
        """Test validation rejects fixes in wrong status for apply."""
        fix = sample_fixes[0]
        fix.status = FixStatus.PROPOSED  # Must be APPROVED for apply
        db_session.query.return_value.filter.return_value.all.return_value = [fix]
        plan_context = create_plan_context(PlanTier.TEAM)

        result = batch_service.validate_batch(
            fix_ids=[1],
            plan_context=plan_context,
            operation="apply",
        )

        assert result["valid"] is False
        assert any("proposed" in err.lower() for err in result["errors"])

    def test_validate_batch_high_risk(self, batch_service, db_session):
        """Test metadata populated for large batch."""
        many_fixes = []
        for i in range(15):
            f = Mock(spec=CodeFix)
            f.id = i
            f.file_path = f"file{i}.py"
            f.status = FixStatus.PROPOSED
            f.to_dict.return_value = {"id": i}
            many_fixes.append(f)
        db_session.query.return_value.filter.return_value.all.return_value = many_fixes
        plan_context = create_plan_context(PlanTier.TEAM)

        result = batch_service.validate_batch(
            fix_ids=list(range(15)),
            plan_context=plan_context,
        )

        assert result["valid"] is True
        assert result["metadata"]["batch_size"] == 15
        assert result["metadata"]["files_affected"] == 15
        assert "risk_level" in result["metadata"]


# ---------------------------------------------------------------------------
# Approval
# ---------------------------------------------------------------------------
class TestBatchApproval:
    """Test batch approval operations."""

    def test_approve_many_success(self, batch_service, db_session, sample_fixes):
        """Test successful batch approval."""
        db_session.query.return_value.filter.return_value.all.return_value = sample_fixes[:2]
        plan_context = create_plan_context(PlanTier.TEAM)

        batch_service.approval_service.can_approve_fixes.return_value = True
        batch_service.approval_service.approve_fix.return_value = {
            "success": True,
            "fix": {"id": 1},
        }

        result = batch_service.approve_many(
            fix_ids=[1, 2],
            user_id="test@example.com",
            plan_context=plan_context,
            ledger_writer=None,
        )

        assert result["success"] is True
        assert result["summary"]["approved"] == 2
        assert result["summary"]["failed"] == 0

    def test_approve_many_partial_failure(self, batch_service, db_session, sample_fixes):
        """Test batch approval with partial failures."""
        db_session.query.return_value.filter.return_value.all.return_value = sample_fixes[:2]
        plan_context = create_plan_context(PlanTier.TEAM)

        batch_service.approval_service.can_approve_fixes.return_value = True
        batch_service.approval_service.approve_fix.side_effect = [
            {"success": True, "fix": {"id": 1}},
            {"success": False, "error": "invalid_state", "message": "already applied"},
        ]

        result = batch_service.approve_many(
            fix_ids=[1, 2],
            user_id="test@example.com",
            plan_context=plan_context,
            ledger_writer=None,
        )

        assert result["success"] is True
        assert result["summary"]["approved"] == 1
        assert result["summary"]["failed"] == 1

    def test_approve_many_plan_restriction(self, batch_service, db_session, sample_fixes):
        """Test batch approval blocked by plan restriction."""
        db_session.query.return_value.filter.return_value.all.return_value = sample_fixes[:2]
        plan_context = create_plan_context(PlanTier.DEVELOPER)

        batch_service.approval_service.can_approve_fixes.return_value = False

        result = batch_service.approve_many(
            fix_ids=[1, 2],
            user_id="test@example.com",
            plan_context=plan_context,
            ledger_writer=None,
        )

        assert result["success"] is False
        assert result.get("error") == "plan_restriction"


# ---------------------------------------------------------------------------
# Rejection
# ---------------------------------------------------------------------------
class TestBatchRejection:
    """Test batch rejection operations."""

    def test_reject_many_success(self, batch_service, db_session, sample_fixes):
        """Test successful batch rejection."""
        db_session.query.return_value.filter.return_value.all.return_value = sample_fixes[:2]
        plan_context = create_plan_context(PlanTier.TEAM)

        batch_service.approval_service.can_approve_fixes.return_value = True
        batch_service.approval_service.reject_fix.return_value = {
            "success": True,
            "fix": {"id": 1},
        }

        result = batch_service.reject_many(
            fix_ids=[1, 2],
            user_id="test@example.com",
            reason="Not needed",
            plan_context=plan_context,
            ledger_writer=None,
        )

        assert result["success"] is True
        assert result["summary"]["rejected"] == 2
        assert result["summary"]["failed"] == 0


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
class TestBatchApplication:
    """Test batch application operations."""

    def test_apply_many_success(self, batch_service, db_session, sample_fixes):
        """Test successful batch application."""
        for f in sample_fixes[:2]:
            f.status = FixStatus.APPROVED
        db_session.query.return_value.filter.return_value.all.return_value = sample_fixes[:2]
        plan_context = create_plan_context(PlanTier.TEAM)

        batch_service.application_service.can_apply_fix.return_value = True
        batch_service.application_service.apply_fix.return_value = {
            "success": True,
            "fix": {"id": 1},
            "file_path": "src/app.py",
        }

        result = batch_service.apply_many(
            fix_ids=[1, 2],
            user_id="test@example.com",
            plan_context=plan_context,
            ledger_writer=None,
        )

        assert result["success"] is True
        assert result["summary"]["applied"] == 2
        assert "combined_patch_hash" in result

    def test_apply_many_wrong_status(self, batch_service, db_session, sample_fixes):
        """Test application fails for non-approved fixes."""
        # sample_fixes[0].status is PROPOSED by default (not APPROVED)
        db_session.query.return_value.filter.return_value.all.return_value = [sample_fixes[0]]
        plan_context = create_plan_context(PlanTier.TEAM)

        result = batch_service.apply_many(
            fix_ids=[1],
            user_id="test@example.com",
            plan_context=plan_context,
            ledger_writer=None,
        )

        assert result["success"] is False
        assert result.get("error") == "validation_failed"


# ---------------------------------------------------------------------------
# Patch Generation
# ---------------------------------------------------------------------------
class TestPatchGeneration:
    """Test deterministic patch generation."""

    def test_generate_combined_patch_deterministic(self, batch_service, db_session, sample_fixes):
        """Test patch generation is deterministic (sorted by file path)."""
        db_session.query.return_value.filter.return_value.all.return_value = sample_fixes[:2]

        result = batch_service.generate_combined_patch(fix_ids=[1, 2])

        assert isinstance(result, str)
        # src/app.py should come before src/utils.py
        idx_app = result.index("src/app.py")
        idx_utils = result.index("src/utils.py")
        assert idx_app < idx_utils

    def test_generate_combined_patch_hash(self, batch_service, db_session, sample_fixes):
        """Test patch hash calculation."""
        db_session.query.return_value.filter.return_value.all.return_value = sample_fixes[:1]

        combined = batch_service.generate_combined_patch(fix_ids=[1])
        computed_hash = hashlib.sha256(combined.encode()).hexdigest()

        assert len(computed_hash) == 64


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------
class TestBatchPreview:
    """Test batch preview functionality."""

    def test_get_batch_preview_success(self, batch_service, db_session, sample_fixes):
        """Test preview generation without execution."""
        db_session.query.return_value.filter.return_value.all.return_value = sample_fixes[:2]
        plan_context = create_plan_context(PlanTier.TEAM)

        result = batch_service.get_batch_preview(
            fix_ids=[1, 2],
            plan_context=plan_context,
        )

        assert "validation" in result
        assert "combined_patch" in result
        assert "patch_hash" in result
        assert result["validation"]["metadata"]["batch_size"] == 2


# ---------------------------------------------------------------------------
# Ledger Integration
# ---------------------------------------------------------------------------
class TestLedgerIntegration:
    """Test ledger event recording."""

    def test_batch_approved_ledger_event(self, batch_service, db_session, sample_fixes):
        """Test BATCH_APPROVED event is recorded."""
        db_session.query.return_value.filter.return_value.all.return_value = sample_fixes[:2]
        plan_context = create_plan_context(PlanTier.TEAM)

        batch_service.approval_service.can_approve_fixes.return_value = True
        batch_service.approval_service.approve_fix.return_value = {
            "success": True,
            "fix": {"id": 1},
        }

        mock_ledger = Mock()

        result = batch_service.approve_many(
            fix_ids=[1, 2],
            user_id="test@example.com",
            plan_context=plan_context,
            ledger_writer=mock_ledger,
        )

        assert result["success"] is True
        mock_ledger.append_event.assert_called_once()
        call_kwargs = mock_ledger.append_event.call_args[1]
        assert call_kwargs["event_type"] == "BATCH_APPROVED"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
