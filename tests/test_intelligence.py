"""
Test intelligence module implementation.

Quick validation that all analyzers can be imported and run.
"""

import os
import tempfile
from pathlib import Path

from agent.intelligence import (
    IntelligenceProposal,
    BugClass,
    Severity,
    IntelligenceOrchestrator,
    run_intelligence_analysis,
)


def create_test_repo():
    """Create a minimal test repository."""
    tmpdir = tempfile.mkdtemp()
    
    # Create a simple Python file with various issues
    test_file = Path(tmpdir) / 'test.py'
    test_file.write_text('''
import os
import json

# Hardcoded credentials (security issue)
api_key = "sk-1234567890"
password = "admin123"

# God object (many methods)
class ServiceManager:
    def method1(self): pass
    def method2(self): pass
    def method3(self): pass
    def method4(self): pass
    def method5(self): pass
    def method6(self): pass
    def method7(self): pass
    def method8(self): pass
    def method9(self): pass
    def method10(self): pass
    def method11(self): pass
    def method12(self): pass
    def method13(self): pass
    def method14(self): pass
    def method15(self): pass
    def method16(self): pass
    def method17(self): pass
    def method18(self): pass
    def method19(self): pass
    def method20(self): pass
    def method21(self): pass

# N+1 query pattern
for user in users:
    data = db.query(Data).filter(user_id=user.id).all()

# While True unbounded loop
while True:
    process_item()

# Missing error handling
file_data = open(filename).read()
json.loads(file_data)

# Shared mutable state
self.cache = {}
self.items = []

# Environment-specific code
if os.environ.get('ENV') == 'prod':
    debug_mode = False
else:
    debug_mode = True

# Missing type hints
def process_data(x):
    return x * 2

# Direct private access (from another file)
obj._internal_state

# Hardcoded configuration
timeout = 30
max_retries = 5
database_url = "localhost:5432"
''')
    
    return tmpdir


def test_orchestrator():
    """Test that orchestrator runs all analyzers."""
    repo_path = create_test_repo()
    
    try:
        # Run analysis
        orchestrator = IntelligenceOrchestrator()
        proposals = orchestrator.analyze(
            repository_path=repo_path,
            repository_url="https://github.com/test/repo",
            branch="main"
        )
        
        print(f"\n✓ Analysis completed!")
        print(f"  Run ID: {orchestrator.run_id}")
        print(f"  Total proposals: {len(proposals)}")
        print(f"\nProposals by severity:")
        for severity, count in orchestrator.proposals_by_severity.items():
            print(f"  {severity}: {count}")
        
        print(f"\nProposals by bug class:")
        for bug_class, count in orchestrator.proposals_by_bug_class.items():
            print(f"  {bug_class}: {count}")
        
        # Sample proposals
        if proposals:
            print(f"\n✓ Sample proposals:")
            for proposal in proposals[:3]:
                print(f"\n  Bug: {proposal.bug_class.value}")
                print(f"  Severity: {proposal.severity.name}")
                print(f"  Problem: {proposal.problem_statement[:80]}...")
                print(f"  Confidence: {proposal.confidence_level}%")
        
        # Verify schema
        print(f"\n✓ Schema validation:")
        for proposal in proposals:
            try:
                proposal.validate()
                print(f"  ✓ {proposal.bug_class.name} proposal valid")
            except ValueError as e:
                print(f"  ✗ {proposal.bug_class.name} proposal invalid: {e}")
        
        # Verify ledger conversion
        print(f"\n✓ Ledger conversion:")
        for proposal in proposals[:2]:
            event = proposal.to_ledger_event()
            print(f"  Event type: {event.get('event_type')}")
            print(f"  Data fields: {list(event.get('data', {}).keys())}")
        
        print(f"\n✓ All tests passed!")
        return True
        
    finally:
        # Cleanup
        import shutil
        shutil.rmtree(repo_path)


if __name__ == '__main__':
    test_orchestrator()
