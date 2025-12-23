"""
Configuration for AGI Engineer
"""

# Rules to auto-fix
ENABLED_RULES = [
    "F401",  # Unused imports
    "F541",  # Useless f-string (no interpolation)
    "W291",  # Trailing whitespace
    "W292",  # No newline at end of file
]

# Patterns to skip (files/directories)
SKIP_PATTERNS = [
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "env",
    ".tox",
    ".eggs",
    "build",
    "dist",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
    "/var/",
    "/tmp/",
]

# Skip __init__.py files (they often have intentional unused imports for public API)
SKIP_INIT_FILES = True

# Maximum number of issues to fix per run
MAX_FIXES = 1000

# Commit message template
COMMIT_MESSAGE_TEMPLATE = "🤖 Auto-fix: Resolved {count} code issues\n\nFixed by AGI Engineer Bot"

# PR title template
PR_TITLE_TEMPLATE = "🤖 Auto-fix: Resolved {count} code issues"

# Branch name prefix
BRANCH_PREFIX = "fix/auto-fixes"
