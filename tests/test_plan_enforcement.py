"""
Test Plan Enforcement (Phase 14.2)

Verify that subscription plans are enforced correctly during orchestration:
- Correct analyzers run based on plan
- Disallowed analyzers are skipped deterministically
- Plan context is recorded in ledger
- Skipped analyzers are recorded with reasons
- Determinism and replayability preserved
"""

import pytest
import os
import tempfile
import shutil
from unittest.mock import Mock, MagicMock

# Import plans module
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../backend'))
from app.plans import (
    PlanTier,
    UserPlanContext,
    create_plan_context,
    create_default_plan_context,
    get_plan_by_tier,
    DEVELOPER_PLAN,
    TEAM_PLAN,
    ENTERPRISE_PLAN,
)

# Import orchestrator
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from agent.intelligence.orchestrator import IntelligenceOrchestrator
from agent.run_ledger import RunLedgerWriter


class TestPlanContextCreation:
    """Test UserPlanContext creation and methods."""
    
    def test_create_developer_plan_context(self):
        """Test creating developer plan context."""
        ctx = create_plan_context(PlanTier.DEVELOPER)
        
        assert ctx.plan_tier == PlanTier.DEVELOPER
        assert len(ctx.allowed_analyzer_ids) > 0
        assert ctx.snapshot_timestamp is not None
        assert 'Z' in ctx.snapshot_timestamp  # ISO 8601 with Z
        
    def test_create_team_plan_context(self):
        """Test creating team plan context."""
        ctx = create_plan_context(PlanTier.TEAM)
        
        assert ctx.plan_tier == PlanTier.TEAM
        # Team plan should have more analyzers than developer
        dev_ctx = create_plan_context(PlanTier.DEVELOPER)
        assert len(ctx.allowed_analyzer_ids) >= len(dev_ctx.allowed_analyzer_ids)
        
    def test_create_default_plan_context(self):
        """Test default plan context is developer."""
        ctx = create_default_plan_context()
        
        assert ctx.plan_tier == PlanTier.DEVELOPER
        
    def test_analyzer_allowance_check(self):
        """Test checking if analyzer is allowed."""
        dev_ctx = create_plan_context(PlanTier.DEVELOPER)
        team_ctx = create_plan_context(PlanTier.TEAM)
        
        # Basic analyzers should be in developer plan
        assert dev_ctx.is_analyzer_allowed('architectural')
        assert dev_ctx.is_analyzer_allowed('performance')
        
        # Enhanced analyzers require team plan
        assert not dev_ctx.is_analyzer_allowed('enhanced_architectural')
        assert not dev_ctx.is_analyzer_allowed('enhanced_performance')
        assert team_ctx.is_analyzer_allowed('enhanced_architectural')
        assert team_ctx.is_analyzer_allowed('enhanced_performance')
        
    def test_filter_allowed_analyzers(self):
        """Test filtering analyzers by plan."""
        dev_ctx = create_plan_context(PlanTier.DEVELOPER)
        
        all_analyzers = [
            'architectural',
            'enhanced_architectural',
            'performance',
            'enhanced_performance',
        ]
        
        allowed = dev_ctx.filter_allowed_analyzers(all_analyzers)
        
        # Should only include basic analyzers
        assert 'architectural' in allowed
        assert 'performance' in allowed
        assert 'enhanced_architectural' not in allowed
        assert 'enhanced_performance' not in allowed
        
    def test_disallowed_reason(self):
        """Test getting disallowed reason."""
        dev_ctx = create_plan_context(PlanTier.DEVELOPER)
        
        reason = dev_ctx.get_disallowed_reason('enhanced_architectural')
        
        assert 'enhanced_architectural' in reason
        assert 'developer' in reason
        assert reason != ""
        
    def test_to_dict_serialization(self):
        """Test serializing to dict for ledger."""
        ctx = create_plan_context(PlanTier.TEAM)
        
        data = ctx.to_dict()
        
        assert data['plan_tier'] == 'team'
        assert isinstance(data['allowed_analyzer_ids'], list)
        assert len(data['allowed_analyzer_ids']) > 0
        assert data['snapshot_timestamp'] is not None
        
    def test_from_dict_deserialization(self):
        """Test deserializing from dict (e.g., from ledger replay)."""
        original_ctx = create_plan_context(PlanTier.ENTERPRISE)
        data = original_ctx.to_dict()
        
        restored_ctx = UserPlanContext.from_dict(data)
        
        assert restored_ctx.plan_tier == original_ctx.plan_tier
        assert restored_ctx.allowed_analyzer_ids == original_ctx.allowed_analyzer_ids
        assert restored_ctx.snapshot_timestamp == original_ctx.snapshot_timestamp


class TestOrchestratorPlanEnforcement:
    """Test orchestrator enforces plan context correctly."""
    
    @pytest.fixture
    def temp_repo(self):
        """Create a temporary test repository."""
        tmpdir = tempfile.mkdtemp()
        # Create minimal Python file
        test_file = os.path.join(tmpdir, "test.py")
        with open(test_file, 'w') as f:
            f.write("def test(): pass\n")
        
        yield tmpdir
        
        # Cleanup
        shutil.rmtree(tmpdir, ignore_errors=True)
    
    def test_orchestrator_with_developer_plan_context(self, temp_repo):
        """Test orchestrator with developer plan context."""
        orchestrator = IntelligenceOrchestrator()
        dev_ctx = create_plan_context(PlanTier.DEVELOPER)
        
        proposals = orchestrator.analyze(
            repository_path=temp_repo,
            repository_url="test://repo",
            branch="main",
            plan_context=dev_ctx,
        )
        
        # Should execute only developer-tier analyzers
        assert len(orchestrator.analyzers) > 0
        
        # Should have skipped analyzers (those requiring team/enterprise)
        assert len(orchestrator.skipped_analyzers) > 0
        
        # Verify skipped analyzers have reasons
        for skipped in orchestrator.skipped_analyzers:
            assert 'analyzer_id' in skipped
            assert 'reason' in skipped
            assert skipped['reason'] != ""
            
    def test_orchestrator_with_team_plan_context(self, temp_repo):
        """Test orchestrator with team plan context."""
        orchestrator = IntelligenceOrchestrator()
        team_ctx = create_plan_context(PlanTier.TEAM)
        
        proposals = orchestrator.analyze(
            repository_path=temp_repo,
            repository_url="test://repo",
            branch="main",
            plan_context=team_ctx,
        )
        
        # Should execute more analyzers than developer plan
        assert len(orchestrator.analyzers) > 0
        
        # Should have no skipped analyzers (team has all analyzers)
        assert len(orchestrator.skipped_analyzers) == 0
        
    def test_orchestrator_without_plan_context_backward_compat(self, temp_repo):
        """Test orchestrator without plan context (backward compatibility)."""
        orchestrator = IntelligenceOrchestrator()
        
        proposals = orchestrator.analyze(
            repository_path=temp_repo,
            repository_url="test://repo",
            branch="main",
            # No plan_context provided
        )
        
        # Should default to developer plan
        assert len(orchestrator.analyzers) > 0
        assert len(orchestrator.skipped_analyzers) == 0  # No enforcement without plan_context
        
    def test_plan_enforcement_determinism(self, temp_repo):
        """Test that plan enforcement is deterministic."""
        dev_ctx = create_plan_context(PlanTier.DEVELOPER)
        
        # Run twice with same plan context
        orchestrator1 = IntelligenceOrchestrator()
        orchestrator1.analyze(
            repository_path=temp_repo,
            repository_url="test://repo",
            branch="main",
            plan_context=dev_ctx,
        )
        
        orchestrator2 = IntelligenceOrchestrator()
        orchestrator2.analyze(
            repository_path=temp_repo,
            repository_url="test://repo",
            branch="main",
            plan_context=dev_ctx,
        )
        
        # Should execute same analyzers
        analyzer1_names = [a.__class__.__name__ for a in orchestrator1.analyzers]
        analyzer2_names = [a.__class__.__name__ for a in orchestrator2.analyzers]
        assert analyzer1_names == analyzer2_names
        
        # Should skip same analyzers
        skipped1_ids = [s['analyzer_id'] for s in orchestrator1.skipped_analyzers]
        skipped2_ids = [s['analyzer_id'] for s in orchestrator2.skipped_analyzers]
        assert skipped1_ids == skipped2_ids


class TestPlanEnforcementLedgerIntegration:
    """Test plan enforcement records to ledger correctly."""
    
    @pytest.fixture
    def temp_repo(self):
        """Create a temporary test repository."""
        tmpdir = tempfile.mkdtemp()
        test_file = os.path.join(tmpdir, "test.py")
        with open(test_file, 'w') as f:
            f.write("def test(): pass\n")
        
        yield tmpdir
        shutil.rmtree(tmpdir, ignore_errors=True)
    
    @pytest.fixture
    def temp_ledger_dir(self):
        """Create temporary ledger directory."""
        tmpdir = tempfile.mkdtemp()
        yield tmpdir
        shutil.rmtree(tmpdir, ignore_errors=True)
    
    def test_plan_context_recorded_in_ledger(self, temp_repo, temp_ledger_dir, monkeypatch):
        """Test that plan context is recorded in ledger."""
        # Create ledger
        run_id = "test-run-plan-enforcement"
        monkeypatch.setattr('os.path.expanduser', lambda x: x.replace('~', temp_ledger_dir))
        
        ledger = RunLedgerWriter(run_id=run_id, repo_id="test/repo")
        ledger.create_ledger()
        
        # Run orchestrator with plan context
        orchestrator = IntelligenceOrchestrator()
        dev_ctx = create_plan_context(PlanTier.DEVELOPER)
        
        proposals = orchestrator.analyze(
            repository_path=temp_repo,
            repository_url="test://repo",
            branch="main",
            ledger=ledger,
            run_id=run_id,
            plan_context=dev_ctx,
        )
        
        # Check ledger events
        events_file = os.path.join(temp_ledger_dir, '.agi-engineer', 'ledger', run_id, 'events.jsonl')
        assert os.path.exists(events_file)
        
        # Read events
        import json
        with open(events_file, 'r') as f:
            events = [json.loads(line) for line in f if line.strip()]
        
        # Should have PLAN_CONTEXT_CAPTURED event
        plan_events = [e for e in events if e.get('event_type') == 'PLAN_CONTEXT_CAPTURED']
        assert len(plan_events) == 1
        
        plan_event = plan_events[0]
        assert plan_event['payload_ref']['plan_tier'] == 'developer'
        assert 'allowed_analyzer_ids' in plan_event['payload_ref']
        
    def test_skipped_analyzers_recorded_in_ledger(self, temp_repo, temp_ledger_dir, monkeypatch):
        """Test that skipped analyzers are recorded in ledger."""
        run_id = "test-run-skipped-analyzers"
        monkeypatch.setattr('os.path.expanduser', lambda x: x.replace('~', temp_ledger_dir))
        
        ledger = RunLedgerWriter(run_id=run_id, repo_id="test/repo")
        ledger.create_ledger()
        
        # Run orchestrator with developer plan (will skip team-tier analyzers)
        orchestrator = IntelligenceOrchestrator()
        dev_ctx = create_plan_context(PlanTier.DEVELOPER)
        
        proposals = orchestrator.analyze(
            repository_path=temp_repo,
            repository_url="test://repo",
            branch="main",
            ledger=ledger,
            run_id=run_id,
            plan_context=dev_ctx,
        )
        
        # Check ledger events
        events_file = os.path.join(temp_ledger_dir, '.agi-engineer', 'ledger', run_id, 'events.jsonl')
        assert os.path.exists(events_file)
        
        # Read events
        import json
        with open(events_file, 'r') as f:
            events = [json.loads(line) for line in f if line.strip()]
        
        # Should have ANALYZERS_SKIPPED event
        skip_events = [e for e in events if e.get('event_type') == 'ANALYZERS_SKIPPED']
        assert len(skip_events) == 1
        
        skip_event = skip_events[0]
        assert 'skipped' in skip_event['payload_ref']
        assert len(skip_event['payload_ref']['skipped']) > 0
        
        # Each skipped analyzer should have reason
        for skipped in skip_event['payload_ref']['skipped']:
            assert 'analyzer_id' in skipped
            assert 'reason' in skipped


class TestPlanHierarchy:
    """Test plan tier hierarchy and analyzer availability."""
    
    def test_developer_plan_has_basic_analyzers(self):
        """Test developer plan includes basic analyzers."""
        plan = get_plan_by_tier(PlanTier.DEVELOPER)
        analyzer_ids = plan.get_all_analyzer_ids()
        
        assert 'architectural' in analyzer_ids
        assert 'performance' in analyzer_ids
        assert 'concurrency' in analyzer_ids
        assert 'security' in analyzer_ids
        
    def test_team_plan_has_enhanced_analyzers(self):
        """Test team plan includes enhanced analyzers."""
        plan = get_plan_by_tier(PlanTier.TEAM)
        analyzer_ids = plan.get_all_analyzer_ids()
        
        # Should have basic analyzers
        assert 'architectural' in analyzer_ids
        assert 'performance' in analyzer_ids
        
        # Should also have enhanced analyzers
        assert 'enhanced_architectural' in analyzer_ids
        assert 'enhanced_performance' in analyzer_ids
        assert 'enhanced_concurrency' in analyzer_ids
        
    def test_enterprise_plan_has_all_analyzers(self):
        """Test enterprise plan has same as team (all analyzers)."""
        team_plan = get_plan_by_tier(PlanTier.TEAM)
        enterprise_plan = get_plan_by_tier(PlanTier.ENTERPRISE)
        
        # Both should have same analyzers (no analyzer exclusivity beyond team)
        team_ids = set(team_plan.get_all_analyzer_ids())
        enterprise_ids = set(enterprise_plan.get_all_analyzer_ids())
        
        assert team_ids == enterprise_ids


class TestSummaryWithSkippedAnalyzers:
    """Test orchestrator summary includes skipped analyzers."""
    
    @pytest.fixture
    def temp_repo(self):
        tmpdir = tempfile.mkdtemp()
        test_file = os.path.join(tmpdir, "test.py")
        with open(test_file, 'w') as f:
            f.write("def test(): pass\n")
        yield tmpdir
        shutil.rmtree(tmpdir, ignore_errors=True)
    
    def test_summary_includes_skipped_count(self, temp_repo):
        """Test get_summary includes skipped analyzer count."""
        orchestrator = IntelligenceOrchestrator()
        dev_ctx = create_plan_context(PlanTier.DEVELOPER)
        
        orchestrator.analyze(
            repository_path=temp_repo,
            repository_url="test://repo",
            branch="main",
            plan_context=dev_ctx,
        )
        
        summary = orchestrator.get_summary()
        
        assert 'skipped_analyzers' in summary
        assert 'skipped_count' in summary
        assert summary['skipped_count'] > 0
        assert summary['skipped_count'] == len(summary['skipped_analyzers'])


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
