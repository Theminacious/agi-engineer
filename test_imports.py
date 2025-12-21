# test_imports.py
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
agent_dir = os.path.join(current_dir, "agent")
sys.path.insert(0, agent_dir)

print(f"Current directory: {current_dir}")
print(f"Agent directory: {agent_dir}")
print(f"Agent exists: {os.path.exists(agent_dir)}")

if os.path.exists(agent_dir):
    print(f"Files in agent: {os.listdir(agent_dir)}")

try:
    from analyze import run_ruff
    from apply_patch import apply_patch
    from fixer import generate_patch
    from file_reader import read_file
    print("✅ All imports successful!")
except ImportError as e:
    print(f"❌ Import error: {e}")