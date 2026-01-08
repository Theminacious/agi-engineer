"""Shared test fixtures"""
import pytest
import tempfile
import os
import sys

# Add agent module to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_DIR = os.path.join(BASE_DIR, "agent")
if AGENT_DIR not in sys.path:
    sys.path.insert(0, AGENT_DIR)


@pytest.fixture
def temp_repo():
    """Create a temporary test repository"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create sample Python files with various issues
        os.makedirs(os.path.join(tmpdir, "src"), exist_ok=True)
        
        # File with unused import
        with open(os.path.join(tmpdir, "src", "unused.py"), "w") as f:
            f.write("import os\nimport json\nprint('hello')\n")
        
        # File with f-string issue
        with open(os.path.join(tmpdir, "src", "fstring.py"), "w") as f:
            f.write("msg = f'static'\nprint(msg)\n")
        
        # File with trailing whitespace
        with open(os.path.join(tmpdir, "src", "whitespace.py"), "w") as f:
            f.write("x = 1 \ny = 2  \n")
        
        # File with comparison to None
        with open(os.path.join(tmpdir, "src", "compare.py"), "w") as f:
            f.write("def check(val):\n    if val == None:\n        return True\n")
        
        yield tmpdir


@pytest.fixture
def sample_issues():
    """Sample Ruff issues for testing"""
    return [
        {'code': 'F401', 'message': 'Unused import', 'filename': 'src/unused.py', 'line': 1, 'severity': 'low'},
        {'code': 'F541', 'message': 'f-string without placeholder', 'filename': 'src/fstring.py', 'line': 1, 'severity': 'low'},
        {'code': 'W291', 'message': 'Trailing whitespace', 'filename': 'src/whitespace.py', 'line': 1, 'severity': 'low'},
        {'code': 'E711', 'message': 'Comparison to None', 'filename': 'src/compare.py', 'line': 2, 'severity': 'medium'},
        {'code': 'F841', 'message': 'Unused variable', 'filename': 'src/unused.py', 'line': 1, 'severity': 'medium'},
    ]
