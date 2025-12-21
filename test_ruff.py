# test_ruff.py - Create in your main directory
import subprocess
import os

# Test Ruff detection
test_code = """
import os
import sys
import json  # This should be detected as unused
import re

def test():
    print("Hello")
    return os.name
"""

# Write test file
with open("test_unused.py", "w") as f:
    f.write(test_code)

# Run Ruff on it
print("Testing Ruff on a file with unused imports...")
result = subprocess.run(
    ["ruff", "check", "test_unused.py", "--select", "F401"],
    capture_output=True,
    text=True
)

print(f"Exit code: {result.returncode}")
print(f"Output:\n{result.stdout}")
print(f"Error:\n{result.stderr}")

# Clean up
os.remove("test_unused.py")