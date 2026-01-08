# 🤖 AGI Engineer - Automated Code Fixer

An autonomous AI agent that clones repositories, finds code issues, fixes them automatically, and creates pull requests - just like a real engineer!

## Features

- 🔍 **Automatic Issue Detection** - Scans repositories using Ruff static analyzer
- 🔧 **Smart Auto-Fixing** - Fixes multiple rule violations automatically
- 🌿 **Git Integration** - Clone, branch, commit, and push changes
- 🚀 **PR Creation** - Automatically creates pull requests with detailed descriptions
- ⚙️ **Configurable** - Customize rules, skip patterns, and behavior

## Supported Rules

Auto-fixes **ALL** rules that Ruff can fix automatically, including:
- **F401** - Remove unused imports
- **F541** - Remove useless f-string prefixes
- **W291** - Remove trailing whitespace  
- **W292** - Add newline at end of file
- **E711** - Comparison to None
- **UP** - Pyupgrade rules (Python syntax modernization)
- **I** - isort rules (import sorting)
- And many more!

See [Ruff Rules](https://docs.astral.sh/ruff/rules/) for the complete list.

## Installation

```bash
# Clone this repo
git clone https://github.com/yourusername/agi-engineer.git
cd agi-engineer

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# For PR creation, install GitHub CLI (optional)
# macOS: brew install gh
# Linux: https://github.com/cli/cli#installation
# Then authenticate: gh auth login
```

## Usage

### Automated GitHub Actions Workflow

The easiest way to use AGI Engineer is via GitHub Actions - it runs automatically on every pull request!

**Setup (one-time):**

1. Add `GROQ_API_KEY` secret to your repo:
   - Go to Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Name: `GROQ_API_KEY`
   - Value: Your Groq API key (get free key at https://console.groq.com)

2. The workflow will then automatically:
   - Run on every PR targeting `main` or `master`
   - Analyze code with Ruff + AI
   - Post detailed findings as PR comments
   - Classify issues by safety (auto-fixable vs needs review)
   - Suggest improvements with AI reasoning

**Example PR Comment:**
```
🤖 AGI Engineer Analysis Results
Total Issues Found: 21
✅ Safe to Auto-Fix: 10 issues
⚠️ Needs Review: 1 issues

📋 ISSUE CLASSIFICATION
✅ SAFE TO AUTO-FIX (10 issues)
   • F401: Unused import (8)
   • F541: Useless f-string (2)

⚠️ NEEDS REVIEW (1 issues)
   • F841: Unused variable (1)

🤖 AI ANALYSIS
[Claude-powered code review suggestions...]
```

### Manual Usage - Fix Local Repository

```bash
python3 agi_engineer_v3.py /path/to/your/repo --smart --ai
```

### Analyze Only (No Fixes)

```bash
python3 agi_engineer_v3.py /path/to/repo --smart --ai --analyze-only
```

## Command Line Options

```
positional arguments:
  repo                  Repository path or Git URL to clone

options:
  --branch BRANCH       Branch name for fixes (auto-generated if not provided)
  --pr                  Create a pull request after fixing
  --push                Push changes to remote
  --rules RULES         Comma-separated Ruff rules to fix (e.g., F401,F541)
  --no-cleanup          Keep cloned repository after completion
```

## How It Works

1. **Clone/Open Repository** - Clones from URL or opens local path
2. **Create Branch** - Creates a new fix branch (if pushing/PR)
3. **Scan for Issues** - Runs Ruff to find code quality issues
4. **Generate Fixes** - Creates patches for supported rules
5. **Apply Changes** - Safely applies patches using git
6. **Commit & Push** - Commits fixes and pushes to remote
7. **Create PR** - Opens pull request with detailed description

## Example Output

```
🤖 AGI Engineer v2 - Automated Code Fixer
============================================================
📁 Repository: /Users/you/repos/myproject
🌿 Branch: main
🔗 Remote: https://github.com/user/myproject

🔍 Scanning repository...
📊 Found 42 issues

🔧 Applying automatic fixes...
✅ Fixed 42 issues
📊 Remaining: 0 issues

✅ Committed: 🤖 Auto-fix: Resolved 42 code issues
✅ Pushed branch: fix/auto-fixes-20231224-120000
🎉 Pull Request: https://github.com/user/myproject/pull/123

✨ Done!
```

## Configuration

Edit `agent/config.py` to customize:

- Enabled rules to fix
- Skip patterns (files/directories to ignore)
- Commit message templates
- Branch naming

## Requirements

- Python 3.8+
- Git installed
- GitHub CLI (for PR creation)
- Ruff (installed via pip)

## Architecture

```
agi-engineer/
├── agi_engineer.py      # Main entry point
├── agent/
│   ├── analyze.py       # Ruff integration
│   ├── fixer.py         # Fix generators for each rule
│   ├── apply_patch.py   # Safe patch application
│   ├── git_ops.py       # Git operations
│   ├── file_reader.py   # File utilities
│   └── config.py        # Configuration
└── requirements.txt     # Dependencies
```

## Contributing

Want to add support for more Ruff rules? 

1. Add fixer function in `agent/fixer.py`
2. Update `generate_fix()` routing
3. Add rule to `ENABLED_RULES` in `agent/config.py`
4. Test and submit PR!

## Roadmap

- [ ] Support more Ruff rules (E, W, C, N categories)
- [ ] AI-powered fixes using LLMs for complex issues
- [ ] Multi-language support (JavaScript, TypeScript, etc.)
- [ ] Integration with CI/CD pipelines
- [ ] Web interface for monitoring
- [ ] Slack/Discord notifications

## License

MIT License - See LICENSE file

## Credits

Built with ❤️ using:
- [Ruff](https://github.com/astral-sh/ruff) - Lightning-fast Python linter
- [GitPython](https://github.com/gitpython-developers/GitPython) - Git integration
- [GitHub CLI](https://cli.github.com/) - PR creation

---

**Made by AGI Engineer Bot 🤖**
