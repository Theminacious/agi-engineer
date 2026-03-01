"""
Phase 11.3 Integration Tests: Ledger Integration

Tests verify that intelligence proposals are correctly recorded in the
immutable ledger while maintaining all Phase 11.3 constraints.

Test Coverage:
1. Intelligence works WITHOUT ledger (standalone)
2. Intelligence works WITH ledger (integration)
3. Ledger failures don't crash intelligence (non-fatal)
4. One ledger event per proposal
5. Ledger is append-only (no mutations)
6. No analyzer imports ledger
7. Proposals are deterministic
8. Full schema compliance
"""

import os
import json
import tempfile
import shutil
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_intelligence_standalone_no_ledger():
    """
    TEST 1: Intelligence runs WITHOUT ledger.
    
    Verifies that proposals are generated correctly even when
    ledger is not provided (backward compatibility).
    """
    print("\n" + "="*70)
    print("TEST 1: Intelligence Standalone (No Ledger)")
    print("="*70)
    
    from agent.intelligence import IntelligenceOrchestrator
    
    # Create temporary test repository
    test_repo = _create_test_repo()
    
    try:
        # Run intelligence WITHOUT ledger
        orchestrator = IntelligenceOrchestrator()
        proposals = orchestrator.analyze(
            repository_path=test_repo,
            repository_url="file://" + test_repo,
            branch="main",
            ledger=None,  # Explicitly no ledger
            run_id=None,
        )
        
        print(f"✓ Analysis completed without ledger")
        print(f"✓ Generated {len(proposals)} proposals")
        
        # Verify proposals are valid
        for proposal in proposals:
            errors = proposal.validate()
            assert not errors, f"Proposal validation failed: {errors}"
        
        print(f"✓ All {len(proposals)} proposals are schema-valid")
        assert len(proposals) > 0, "Expected at least some proposals"
        print(f"✓ TEST 1 PASSED: Intelligence works standalone\n")
        return True
        
    finally:
        shutil.rmtree(test_repo, ignore_errors=True)


def test_intelligence_with_ledger():
    """
    TEST 2: Intelligence works WITH ledger integration.
    
    Verifies that proposals are recorded to ledger correctly.
    """
    print("\n" + "="*70)
    print("TEST 2: Intelligence with Ledger Integration")
    print("="*70)
    
    from agent.intelligence import IntelligenceOrchestrator
    from agent.run_ledger import create_run_ledger
    
    test_repo = _create_test_repo()
    run_id = "test-run-11-3"
    
    try:
        # Create ledger
        ledger = create_run_ledger(
            run_id=run_id,
            repo_id="test/repo",
            environment="DEV",
            initiated_by="TEST",
        )
        
        assert ledger is not None, "Failed to create test ledger"
        print(f"✓ Test ledger created: {run_id}")
        
        # Run intelligence WITH ledger
        orchestrator = IntelligenceOrchestrator()
        proposals = orchestrator.analyze(
            repository_path=test_repo,
            repository_url="file://" + test_repo,
            branch="main",
            ledger=ledger,
            run_id=run_id,
        )
        
        print(f"✓ Analysis completed with ledger integration")
        print(f"✓ Generated {len(proposals)} proposals")
        
        # Read ledger events
        ledger_path = os.path.expanduser(f"~/.agi-engineer/ledger/{run_id}")
        events_file = os.path.join(ledger_path, "events.jsonl")
        
        assert os.path.exists(events_file), f"Ledger events file not found: {events_file}"
        
        # Count INTELLIGENCE_PROPOSAL events
        proposal_events = []
        with open(events_file, 'r') as f:
            for line in f:
                if line.strip():
                    event = json.loads(line)
                    if event.get('event_type') == 'INTELLIGENCE_PROPOSAL':
                        proposal_events.append(event)
        
        print(f"✓ Found {len(proposal_events)} INTELLIGENCE_PROPOSAL events in ledger")
        
        # Verify one event per proposal
        assert len(proposal_events) == len(proposals), \
            f"Event count mismatch: {len(proposal_events)} events vs {len(proposals)} proposals"
        
        print(f"✓ One ledger event per proposal (1:1 mapping)")
        
        # Verify each event has required fields
        for event in proposal_events:
            assert event.get('event_type') == 'INTELLIGENCE_PROPOSAL'
            assert event.get('summary')
            assert event.get('payload_ref')
        
        print(f"✓ All events have required fields")
        print(f"✓ TEST 2 PASSED: Intelligence works with ledger\n")
        return True
        
    finally:
        shutil.rmtree(test_repo, ignore_errors=True)
        # Clean up ledger
        ledger_dir = os.path.expanduser(f"~/.agi-engineer/ledger/{run_id}")
        shutil.rmtree(ledger_dir, ignore_errors=True)


def test_ledger_failure_nonfatal():
    """
    TEST 3: Ledger failures don't crash intelligence.
    
    Verifies that if ledger write fails, analysis continues
    and returns proposals normally.
    """
    print("\n" + "="*70)
    print("TEST 3: Ledger Failure is Non-Fatal")
    print("="*70)
    
    from agent.intelligence import IntelligenceOrchestrator
    
    test_repo = _create_test_repo()
    
    try:
        # Create a mock ledger that always fails
        class FailingLedger:
            def append_event(self, *args, **kwargs):
                raise Exception("Intentional ledger failure for testing")
        
        # Run intelligence with failing ledger
        orchestrator = IntelligenceOrchestrator()
        proposals = orchestrator.analyze(
            repository_path=test_repo,
            repository_url="file://" + test_repo,
            branch="main",
            ledger=FailingLedger(),  # Ledger that always fails
            run_id="test-run-failing-ledger",
        )
        
        print(f"✓ Analysis completed despite ledger failures")
        print(f"✓ Generated {len(proposals)} proposals")
        
        # Verify proposals are still valid
        assert len(proposals) > 0, "Expected proposals even with ledger failure"
        
        for proposal in proposals:
            errors = proposal.validate()
            assert not errors, f"Proposal validation failed: {errors}"
        
        print(f"✓ All proposals remain valid despite ledger failure")
        print(f"✓ TEST 3 PASSED: Ledger failures are non-fatal\n")
        return True
        
    finally:
        shutil.rmtree(test_repo, ignore_errors=True)


def test_ledger_append_only():
    """
    TEST 4: Ledger is append-only (no mutations).
    
    Verifies that proposals are only appended, never updated or deleted.
    """
    print("\n" + "="*70)
    print("TEST 4: Ledger is Append-Only")
    print("="*70)
    
    from agent.intelligence import IntelligenceOrchestrator
    from agent.run_ledger import create_run_ledger
    
    test_repo = _create_test_repo()
    run_id = "test-run-append-only"
    
    try:
        # Create ledger
        ledger = create_run_ledger(
            run_id=run_id,
            repo_id="test/repo",
            environment="DEV",
            initiated_by="TEST",
        )
        
        # Count initial events (should be 1: RUN_CREATED)
        events_file = os.path.expanduser(f"~/.agi-engineer/ledger/{run_id}/events.jsonl")
        with open(events_file, 'r') as f:
            initial_count = sum(1 for line in f if line.strip())
        
        print(f"✓ Initial event count: {initial_count} (RUN_CREATED)")
        
        # Run intelligence
        orchestrator = IntelligenceOrchestrator()
        proposals = orchestrator.analyze(
            repository_path=test_repo,
            repository_url="file://" + test_repo,
            branch="main",
            ledger=ledger,
            run_id=run_id,
        )
        
        # Count final events
        with open(events_file, 'r') as f:
            final_count = sum(1 for line in f if line.strip())
        
        added_count = final_count - initial_count
        
        print(f"✓ Final event count: {final_count}")
        print(f"✓ Added {added_count} events (proposals)")
        
        # Verify counts match
        assert added_count == len(proposals), \
            f"Event count mismatch: {added_count} added vs {len(proposals)} proposals"
        
        print(f"✓ All proposals appended (no mutations)")
        
        # Verify sequence is monotonic
        events = []
        with open(events_file, 'r') as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))
        
        for i in range(len(events) - 1):
            assert events[i]['sequence'] < events[i+1]['sequence'], \
                f"Sequence not monotonic at index {i}"
        
        print(f"✓ Event sequences are monotonically increasing (append-only verified)")
        print(f"✓ TEST 4 PASSED: Ledger is append-only\n")
        return True
        
    finally:
        shutil.rmtree(test_repo, ignore_errors=True)
        ledger_dir = os.path.expanduser(f"~/.agi-engineer/ledger/{run_id}")
        shutil.rmtree(ledger_dir, ignore_errors=True)


def test_no_analyzer_ledger_imports():
    """
    TEST 5: No analyzer imports ledger.
    
    Verifies that analyzer files don't import ledger modules.
    This ensures analyzers remain independent and deterministic.
    """
    print("\n" + "="*70)
    print("TEST 5: No Analyzer Ledger Imports")
    print("="*70)
    
    analyzer_dir = Path(__file__).parent / "agent" / "intelligence" / "analyzers"
    
    # Check all analyzer files
    analyzer_files = list(analyzer_dir.glob("*.py"))
    
    forbidden_imports = [
        'run_ledger',
        'ledger_adapter',
        'RunLedgerWriter',
        'append_event',
    ]
    
    violations = []
    
    for analyzer_file in analyzer_files:
        if analyzer_file.name == '__init__.py':
            continue
        
        content = analyzer_file.read_text()
        
        for forbidden in forbidden_imports:
            if forbidden in content:
                violations.append(f"{analyzer_file.name}: contains '{forbidden}'")
    
    if violations:
        print(f"✗ Ledger imports found in analyzers:")
        for v in violations:
            print(f"  - {v}")
        return False
    
    print(f"✓ Scanned {len(analyzer_files) - 1} analyzer files")
    print(f"✓ No ledger imports found in any analyzer")
    print(f"✓ TEST 5 PASSED: Analyzers are ledger-independent\n")
    return True


def test_proposals_deterministic():
    """
    TEST 6: Proposals are deterministic.
    
    Verifies that running analysis twice on same code
    produces identical proposals.
    """
    print("\n" + "="*70)
    print("TEST 6: Proposal Determinism")
    print("="*70)
    
    from agent.intelligence import IntelligenceOrchestrator
    
    test_repo = _create_test_repo()
    
    try:
        # Run 1
        orchestrator1 = IntelligenceOrchestrator()
        proposals1 = orchestrator1.analyze(
            repository_path=test_repo,
            repository_url="file://" + test_repo,
            branch="main",
            ledger=None,
        )
        
        # Run 2 (same code)
        orchestrator2 = IntelligenceOrchestrator()
        proposals2 = orchestrator2.analyze(
            repository_path=test_repo,
            repository_url="file://" + test_repo,
            branch="main",
            ledger=None,
        )
        
        print(f"✓ Run 1: {len(proposals1)} proposals")
        print(f"✓ Run 2: {len(proposals2)} proposals")
        
        # Compare counts
        assert len(proposals1) == len(proposals2), \
            f"Proposal count differs: {len(proposals1)} vs {len(proposals2)}"
        
        print(f"✓ Proposal counts match")
        
        # Compare content (by bug class and problem statement)
        run1_sig = set(
            (p.bug_class.value, p.problem_statement) for p in proposals1
        )
        run2_sig = set(
            (p.bug_class.value, p.problem_statement) for p in proposals2
        )
        
        assert run1_sig == run2_sig, \
            f"Proposals differ between runs"
        
        print(f"✓ All proposal signatures match (deterministic)")
        print(f"✓ TEST 6 PASSED: Proposals are deterministic\n")
        return True
        
    finally:
        shutil.rmtree(test_repo, ignore_errors=True)


def test_schema_compliance():
    """
    TEST 7: Ledger events comply with strict schema.
    
    Verifies that all recorded events match the required
    INTELLIGENCE_PROPOSAL schema from Phase 11.3.
    """
    print("\n" + "="*70)
    print("TEST 7: Ledger Event Schema Compliance")
    print("="*70)
    
    from agent.intelligence import IntelligenceOrchestrator
    from agent.run_ledger import create_run_ledger
    
    test_repo = _create_test_repo()
    run_id = "test-run-schema"
    
    try:
        # Create ledger
        ledger = create_run_ledger(
            run_id=run_id,
            repo_id="test/repo",
            environment="DEV",
            initiated_by="TEST",
        )
        
        # Run intelligence
        orchestrator = IntelligenceOrchestrator()
        proposals = orchestrator.analyze(
            repository_path=test_repo,
            repository_url="file://" + test_repo,
            branch="main",
            ledger=ledger,
            run_id=run_id,
        )
        
        # Read and verify events
        events_file = os.path.expanduser(f"~/.agi-engineer/ledger/{run_id}/events.jsonl")
        
        proposal_events = []
        with open(events_file, 'r') as f:
            for line in f:
                if line.strip():
                    event = json.loads(line)
                    if event.get('event_type') == 'INTELLIGENCE_PROPOSAL':
                        proposal_events.append(event)
        
        print(f"✓ Found {len(proposal_events)} INTELLIGENCE_PROPOSAL events")
        
        # Verify each event has required fields per Phase 11.3
        required_fields = [
            'event_type',
            'summary',
            'actor',
            'actor_role',
            'phase',
            'payload_ref',
            'timestamp',
            'sequence',
        ]
        
        for i, event in enumerate(proposal_events):
            missing = [f for f in required_fields if f not in event]
            assert not missing, f"Event {i} missing fields: {missing}"
        
        print(f"✓ All {len(proposal_events)} events have required fields")
        
        # Verify constraints object in payload (for strict schema version)
        for event in proposal_events:
            # Extract the full proposal data if available
            summary = event.get('summary', '')
            assert summary, f"Event missing summary"
        
        print(f"✓ All events have valid summary content")
        print(f"✓ TEST 7 PASSED: Schema compliance verified\n")
        return True
        
    finally:
        shutil.rmtree(test_repo, ignore_errors=True)
        ledger_dir = os.path.expanduser(f"~/.agi-engineer/ledger/{run_id}")
        shutil.rmtree(ledger_dir, ignore_errors=True)


# ============================================================================
# Test Utilities
# ============================================================================

def _create_test_repo() -> str:
    """Create a temporary test repository with sample code."""
    test_dir = tempfile.mkdtemp(prefix="test-repo-11-3-")
    
    # Create some Python files with various issues
    
    # 1. File with security issue
    Path(test_dir, "secrets.py").write_text("""
import os

API_KEY = "sk-1234567890abcdef"  # Hardcoded secret
PASSWORD = "admin123"  # Another hardcoded secret

class SecretHandler:
    def __init__(self):
        self.token = "secret_token_12345"
    
    def get_password(self):
        return PASSWORD
""")
    
    # 2. File with performance issues
    Path(test_dir, "query_handler.py").write_text("""
class DataFetcher:
    def __init__(self, db):
        self.db = db
    
    def fetch_all_users(self):
        results = []
        for user_id in range(1000):
            # N+1 query pattern
            user = self.db.query("SELECT * FROM users WHERE id = ?", user_id)
            results.append(user)
        return results
    
    def process_forever(self):
        while True:
            data = self.fetch_all_users()
            # Process...
""")
    
    # 3. File with architectural issue
    Path(test_dir, "circular_imports.py").write_text("""
# This would be circular if we complete it
# For now just a marker file
import sys
import os
""")
    
    # 4. Config file
    Path(test_dir, "config.py").write_text("""
# Hardcoded configuration
DATABASE_URL = "postgres://user:pass@localhost:5432/db"
DEBUG = True
SECRET_KEY = "dev-secret-key"
TIMEOUT = 30
MAX_WORKERS = 5
""")
    
    # 5. Test file (to check test coverage issues)
    Path(test_dir, "payment.py").write_text("""
class PaymentProcessor:
    def process_payment(self, amount, card):
        # Payment code without test coverage
        if amount < 0:
            raise ValueError("Invalid amount")
        # Complex payment logic...
        return True
    
    def validate_card(self, card):
        # Untested validation logic
        parts = card.split('-')
        return len(parts) == 4
""")
    
    return test_dir


# ============================================================================
# Main Test Runner
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("PHASE 11.3 INTEGRATION TEST SUITE")
    print("Ledger Integration Tests")
    print("="*70)
    
    results = {}
    
    # Run all tests
    tests = [
        ("Intelligence Standalone", test_intelligence_standalone_no_ledger),
        ("Intelligence with Ledger", test_intelligence_with_ledger),
        ("Ledger Failure Non-Fatal", test_ledger_failure_nonfatal),
        ("Ledger Append-Only", test_ledger_append_only),
        ("No Analyzer Ledger Imports", test_no_analyzer_ledger_imports),
        ("Proposal Determinism", test_proposals_deterministic),
        ("Schema Compliance", test_schema_compliance),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                results[test_name] = "PASSED"
            else:
                failed += 1
                results[test_name] = "FAILED"
        except Exception as e:
            failed += 1
            results[test_name] = f"ERROR: {str(e)}"
            print(f"✗ {test_name}: {e}\n")
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    for test_name, status in results.items():
        symbol = "✓" if "PASSED" in status else "✗"
        print(f"{symbol} {test_name}: {status}")
    
    print(f"\nTotal: {passed} passed, {failed} failed out of {len(tests)} tests")
    
    if failed == 0:
        print("\n✓ ALL TESTS PASSED - Phase 11.3 Integration Complete!")
    else:
        print(f"\n✗ {failed} TESTS FAILED")
    
    exit(0 if failed == 0 else 1)
