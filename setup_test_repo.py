# setup_test_repo.py
import os
import tempfile
import shutil
import subprocess
import sys

def create_test_repo():
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp(prefix="test_repo_")
    print(f"📁 Created test repository at: {temp_dir}")
    
    # Initialize git repo
    subprocess.run(["git", "init"], cwd=temp_dir, capture_output=True)
    
    # Create multiple Python files with various issues
    files = {
        "module1.py": """#!/usr/bin/env python3
import os
import sys  # unused
import json  # unused
import re

def function1():
    return os.name
    
    
# Extra blank lines

def function2():
    pass
""",
        
        "module2.py": """#!/usr/bin/env python3
from typing import List, Dict  # unused
import datetime

print("Hello")

# Bad import order
import sys
import os

x = 1
y = 2
""",
        
        "module3.py": """#!/usr/bin/env python3
# Multiple issues in one file
import pandas as pd  # unused
import numpy as np   # unused
import matplotlib.pyplot as plt  # unused

def calculate():
    result = 1 + 2
    return result
    
# Unused variable
unused_var = 42
"""
    }
    
    # Write files
    for filename, content in files.items():
        filepath = os.path.join(temp_dir, filename)
        with open(filepath, "w") as f:
            f.write(content)
        print(f"  Created: {filename}")
    
    # Add and commit
    subprocess.run(["git", "add", "."], cwd=temp_dir, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit with issues"], cwd=temp_dir, capture_output=True)
    
    return temp_dir

def test_ruff_on_repo(repo_path):
    print(f"\n🔍 Testing Ruff on repository...")
    
    # Test 1: Check for F401 issues
    print("\n1. Checking for F401 (unused imports):")
    result = subprocess.run(
        ["ruff", "check", ".", "--select", "F401"],
        cwd=repo_path,
        capture_output=True,
        text=True
    )
    print(f"   Exit code: {result.returncode}")
    if result.stdout:
        print(f"   Found {len(result.stdout.strip().split('\\n'))} F401 issues")
        for line in result.stdout.strip().split('\n')[:5]:
            print(f"     {line}")
    else:
        print("   No F401 issues found")
    
    # Test 2: Check all issues
    print("\n2. Checking for all issues:")
    result = subprocess.run(
        ["ruff", "check", "."],
        cwd=repo_path,
        capture_output=True,
        text=True
    )
    print(f"   Exit code: {result.returncode}")
    if result.stdout:
        issues = [l for l in result.stdout.strip().split('\n') if l]
        print(f"   Found {len(issues)} total issues")
        for line in issues[:5]:
            print(f"     {line}")
        if len(issues) > 5:
            print(f"     ... and {len(issues) - 5} more")
    else:
        print("   No issues found")
    
    return result.returncode, result.stdout

def main():
    print("🚀 Setting up test repository with known issues")
    print("=" * 60)
    
    # Create test repo
    test_repo = create_test_repo()
    
    try:
        # Test Ruff
        exit_code, output = test_ruff_on_repo(test_repo)
        
        # Now test your analyzer
        print(f"\n🤖 Testing your analyzer function...")
        
        # Add agent directory to path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        agent_dir = os.path.join(current_dir, "agent")
        if agent_dir not in sys.path:
            sys.path.insert(0, agent_dir)
        
        from analyze import run_ruff as your_run_ruff
        
        issues = your_run_ruff(test_repo)
        print(f"   Your analyzer found: {len(issues)} issues")
        
        if issues:
            print("\n   First 5 issues found by your analyzer:")
            for i, issue in enumerate(issues[:5]):
                print(f"     {i+1}. {issue['filename']}:{issue['line']} {issue['code']}: {issue['message']}")
        
        print(f"\n✅ Test repository ready at: {test_repo}")
        print(f"\nTo test your main script, update REPO_PATH in main.py to:")
        print(f'REPO_PATH = "{test_repo}"')
        
        # Create a simple test
        print(f"\n📋 Quick test script:")
        print(f'''# quick_test.py
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
agent_dir = os.path.join(current_dir, "agent")
sys.path.insert(0, agent_dir)

from analyze import run_ruff
from fixer import generate_patch
from file_reader import read_file
from apply_patch import apply_patch

repo_path = "{test_repo}"
issues = run_ruff(repo_path)
print(f"Found {{len(issues)}} issues")

if issues:
    # Test on first F401 issue
    f401_issues = [i for i in issues if i["code"] == "F401"]
    if f401_issues:
        issue = f401_issues[0]
        file_path = os.path.join(repo_path, issue["filename"])
        code = read_file(file_path)
        patch = generate_patch(file_path, code, issue["message"])
        if patch:
            print(f"Generated patch for {{issue['filename']}}")
            print(f"Patch preview:\\n{{patch[:200]}}...")
            success, error = apply_patch(repo_path, patch)
            if success:
                print("✅ Patch applied successfully!")
            else:
                print(f"❌ Patch failed: {{error}}")
        else:
            print("No patch generated")
''')
        
    finally:
        print(f"\n💡 Note: Test repository will NOT be automatically deleted.")
        print(f"   Location: {test_repo}")
        print(f"   You can delete it manually when done: rm -rf {test_repo}")

if __name__ == "__main__":
    main()