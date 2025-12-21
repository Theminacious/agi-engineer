# debug.py
import os
import sys

# Add agent directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
agent_dir = os.path.join(current_dir, "agent")
if agent_dir not in sys.path:
    sys.path.insert(0, agent_dir)

from analyze import run_ruff

REPO_PATH = os.path.abspath(os.path.join("repos", "requests"))

print(f"Repo path: {REPO_PATH}")
print(f"Repo exists: {os.path.exists(REPO_PATH)}")

if os.path.exists(REPO_PATH):
    print("Running ruff test...")
    issues = run_ruff(REPO_PATH)
    print(f"Found {len(issues)} issues")
    
    if issues:
        print("\nFirst few issues:")
        for i, issue in enumerate(issues[:5]):
            print(f"  {i+1}. {issue['filename']}:{issue['line']} - {issue['code']}: {issue['message']}")
    
    f401_issues = [i for i in issues if i["code"] == "F401"]
    print(f"\nF401 issues: {len(f401_issues)}")
    
    if f401_issues:
        print("\nFirst F401 issue:")
        issue = f401_issues[0]
        print(f"  File: {issue['filename']}")
        print(f"  Line: {issue['line']}")
        print(f"  Message: {issue['message']}")
        
        # Test reading the file
        from file_reader import read_file
        file_path = os.path.join(REPO_PATH, issue["filename"])
        if os.path.exists(file_path):
            code = read_file(file_path)
            if code:
                lines = code.splitlines()
                if issue["line"] <= len(lines):
                    print(f"  Line content: {lines[issue['line']-1]}")
else:
    print("❌ Repository not found!")