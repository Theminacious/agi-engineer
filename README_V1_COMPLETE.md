# 🤖 AGI Engineer v1 - Complete Python Code Fixer

> **What is this?** Imagine a robot that reads your Python code, finds all the problems (unused imports, bad spacing, etc.), explains WHY they're problems, and then **automatically fixes them**. That's AGI Engineer!

Think of it like **Grammarly for code** 📝 — but smarter, faster, and with AI.

---

## 🎯 What Problem Does It Solve?

### Before AGI Engineer ❌
```
Manual code review = Time-consuming
❌ Find bad variable names manually
❌ Hunt for unused imports one by one
❌ Fix formatting issues by hand
❌ Worry about breaking things
❌ Days of tedious work
```

### After AGI Engineer ✅
```
Automated with verification = Fast & Safe
✅ AI finds issues automatically
✅ Shows why each issue matters
✅ Fixes them instantly (with safety checks)
✅ Tests for regressions
✅ Done in seconds
```

---

## 🚀 Quick Start (5 minutes)

### Step 1: Install
```bash
# Clone the project
git clone https://github.com/Theminacious/agi-engineer.git
cd agi-engineer

# Create virtual environment (isolated Python space)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Get Free AI (Groq)
Groq gives you **FREE** AI inference - no credit card needed!

```bash
# Option A: Set environment variable
export GROQ_API_KEY=gsk_YOUR_KEY_HERE

# Option B: Create .env file (easier)
echo "GROQ_API_KEY=gsk_YOUR_KEY_HERE" > .env
source .env
```

Get your free key: https://console.groq.com/

### Step 3: Run It!
```bash
# Just analyze (no changes)
python3 agi_engineer_v3.py /path/to/your/python/project --ai --smart --analyze-only

# Analyze and fix
python3 agi_engineer_v3.py /path/to/your/python/project --smart

# Or fix a GitHub repo directly
python3 agi_engineer_v3.py https://github.com/user/repo --smart --pr
```

## Features

### ✅ V1.1: Error Handling & Resilience
- Graceful failure handling for network issues, API failures, invalid repos
- Detailed error messages for debugging
- Safe mode prevents destructive changes

### ✅ V1.2: Configuration System
- `.agi-engineer.yml` for per-repo customization
- Customize enabled rules, AI provider, skip patterns
- Example config: `.agi-engineer.example.yml`

### ✅ V1.3: Rate Limiting & Usage Tracking
- Free tier: 10 AI calls/hour (configurable)
- Per-repository tracking
- Per-provider limits
- Configurable in `.agi-engineer.yml`

### ✅ V1.4: Automated Tests
- 20+ unit tests for core components
- Test fixtures for Python/JS/TS
- Run: `pytest tests/`

### ✅ V1.5: Basic Metrics & Logging
- RunLogger: tracks each analysis run
- Metrics: issues found, fixes applied, errors
- Stored in `~/.agi-engineer/runs.json`

### ✅ V1.6: Multi-Language Support
- Python: Full support via Ruff
- JavaScript/TypeScript: Via ESLint (when available)
- Automatic language detection

### ✅ V1.7: Documentation
- Complete README with examples
- CONTRIBUTING.md for developers
- In-code docstrings

## Configuration

Create `.agi-engineer.yml` in your repo root:

```yaml
rules:
  enabled:
    - F401  # Unused imports
    - F541  # Useless f-strings
    - W291  # Trailing whitespace
    - E711  # Comparison to None
  disabled: []
  safe_only: true  # Only auto-fix safe rules

ai:
  enabled: true
  provider: groq  # groq, together, openrouter, anthropic
  max_files_to_analyze: 5
  rate_limit:
    limit: 10            # calls per window
    window_seconds: 3600 # 1 hour
    storage_path: ~/.agi-engineer/usage.json

skip_patterns:
  - __pycache__
  - .git
  - venv
  - node_modules
  - dist/
  - build/

max_issues_per_run: 1000
create_pr: false
branch_prefix: "agi-engineer/fixes"
```

## AI Providers

### Groq (Recommended - FREE)
- **Speed**: Fastest inference
- **Cost**: Free with generous rate limits
- **Setup**: `export GROQ_API_KEY=gsk_...`

### Together AI
- **Speed**: Very fast
- **Cost**: Paid, competitive pricing
- **Setup**: `export TOGETHER_API_KEY=...`

### OpenRouter
- **Speed**: Fast
- **Cost**: Paid, supports many models
- **Setup**: `export OPENROUTER_API_KEY=...`

### Anthropic Claude
- **Speed**: Moderate
- **Cost**: Paid
- **Setup**: `export ANTHROPIC_API_KEY=...`

## Usage Examples

### Smart Analysis Only (No Fixes)
```bash
python3 agi_engineer_v3.py /path/to/repo --smart --analyze-only
```

Output:
- Classification: Safe, Needs Review, Suggestions
- Explanations for each issue type
- AI suggestions for complex issues

### Auto-Fix Safe Issues
```bash
python3 agi_engineer_v3.py /path/to/repo --smart
```

- Applies fixes for safe rules (F401, F541, W291, W292, etc.)
- Checks for regressions
- Shows before/after comparison

### Create Pull Request
```bash
python3 agi_engineer_v3.py https://github.com/user/repo \
  --smart \
  --pr \
  --push
```

- Clones repo
- Analyzes
- Creates branch (e.g., `agi-engineer/fixes/abc123`)
- Commits fixes
- Creates PR on GitHub

### Analyze Git URL
```bash
python3 agi_engineer_v3.py https://github.com/pallets/flask \
  --smart \
  --analyze-only
```

- Clones to temp directory
- Analyzes
- Cleans up (unless `--no-cleanup`)

## Architecture

```
agi-engineer/
├── agi_engineer_v3.py          # CLI entry point
├── agent/
│   ├── ai_analyzer.py          # LLM-powered analysis
│   ├── analyze.py              # Ruff scanner
│   ├── config_loader.py        # YAML config
│   ├── exceptions.py           # Custom exceptions
│   ├── explainer.py            # Why explanations
│   ├── file_reader.py          # Safe file reading
│   ├── fix_orchestrator.py    # Fix planning & execution
│   ├── git_ops.py              # Git operations
│   ├── multi_language.py       # JS/TS support
│   ├── rule_classifier.py      # Rule safety classification
│   ├── run_logger.py           # Metrics & logging
│   ├── safety_checker.py       # Regression detection
│   └── usage_tracker.py        # Rate limiting
├── tests/
│   ├── conftest.py            # Test fixtures
│   ├── test_rule_classifier.py
│   ├── test_fix_orchestrator.py
│   └── test_safety_checker.py
└── README.md
```

## Performance

- **Small repos** (< 100 issues): ~5-10 seconds
- **Medium repos** (100-500 issues): ~30-60 seconds
- **Large repos** (500+ issues): ~2-5 minutes
- AI analysis: ~2-5 seconds per file

## Limitations

- JS/TS analysis requires ESLint installed globally or via npx
- Rate limiting is per-machine (uses local JSON storage)
- PR creation requires GitHub permissions
- Currently Python 3.10+ only

## Troubleshooting

### "API key not found"
```bash
# Check environment variable
echo $GROQ_API_KEY

# Or set in .env
echo "GROQ_API_KEY=gsk_..." > .env
source .env
```

### "Rate limit exceeded"
- Increase limit in config: `ai.rate_limit.limit: 20`
- Or wait 1 hour for counter to reset
- Check usage: `~/.agi-engineer/usage.json`

### "ESLint not found" (for JS/TS)
```bash
# Install globally
npm install -g eslint prettier

# Or in project
npm install eslint prettier --save-dev
```

### Tests failing
```bash
# Install pytest
pip install pytest

# Run with verbose output
pytest tests/ -v
```

## Roadmap

### V2.0: GitHub App Foundation
- GitHub App with OAuth
- Webhook-based PR analysis
- One-click install from Marketplace

### V2.1: Web Dashboard
- Next.js frontend
- Supabase backend
- Team analytics
- Historical trends

### V2.2: Database & Backend
- PostgreSQL
- User/org/repo schema
- Historical data
- Advanced metrics

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development setup
- Running tests
- Code style guidelines
- Submitting PRs
- Reporting bugs

## License

MIT - See LICENSE file

## Support

- **Issues**: [GitHub Issues](https://github.com/Theminacious/agi-engineer/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Theminacious/agi-engineer/discussions)
- **Email**: contact@example.com

---

**Ready to move to V2? Let's build the GitHub App!** 🚀
