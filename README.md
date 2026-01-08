# �� AGI Engineer v1 - Complete Python Code Fixer

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

---

## 📊 How It Works (Visual Guide)

### The Process Flow

```
Your Python Code
      ↓
   [Ruff Scanner] ← Finds 36 issues
      ↓
[AI Analyzer] ← Understands what's wrong (uses Groq)
      ↓
[Rule Classifier] ← Sorts into: Safe, Review, Suggestions
      ↓
[Safety Checker] ← Tests if fixes break anything
      ↓
[Auto-Fixer] ← Applies fixes to code
      ↓
[Git Integration] ← Creates PR for review
      ↓
Clean, Fixed Code ✨
```

### Example: What It Finds

**Your Code:**
```python
import os          # ← Unused (imported but never used)
import json

msg = f"hello"     # ← f-string without variables (wastes CPU)

x = 5              # ← Unused variable (confusing)
print(x + 1)

if x == None:      # ← Wrong comparison (should use 'is None')
    pass
```

**What AGI Engineer Does:**

| Issue | Type | Why Bad | Fix |
|-------|------|--------|-----|
| Unused `os` import | Safe ✅ | Clutter, slower load | Remove |
| Useless f-string | Safe ✅ | Wasted memory | Change to normal string |
| Unused variable `x` | Review ⚠️ | Confusing code | Maybe remove? (need human check) |
| `== None` comparison | Safe ✅ | Python best practice | Use `is None` |

---

## 🎁 What's Included in V1 (7 Major Features)

### ✅ V1.1: Error Handling (Won't Crash on Problems)

**What it means:** When things go wrong (no internet, wrong path, API fails), AGI Engineer **doesn't crash** — it tells you what happened clearly.

**Problems it solves:**
- ❌ Code crashes on network error → ✅ Shows helpful message
- ❌ Confusing error messages → ✅ Clear explanation of issue
- ❌ Lost work on failure → ✅ Saves state before risky operations

**Example:**
```bash
$ python3 agi_engineer_v3.py https://github.com/invalid/url --pr

❌ Failed to clone: Invalid repository URL
   Try: https://github.com/username/repo
   Or:  /path/to/local/repo
```

---

### ✅ V1.2: Configuration (Customize Everything)

**What it means:** You can create a file (`.agi-engineer.yml`) that tells AGI Engineer exactly what rules to use, which files to skip, and how to behave.

**Problems it solves:**
- ❌ One-size-fits-all doesn't work → ✅ Customize per project
- ❌ Have to change code for every project → ✅ Use config file
- ❌ Fixing unwanted files → ✅ Skip patterns (e.g., skip `__pycache__`)

**Example Config File (.agi-engineer.yml):**
```yaml
# What rules to enforce
rules:
  enabled:
    - F401  # Unused imports - always safe to remove
    - F541  # Useless f-strings - always safe to remove
    - W291  # Trailing whitespace - always safe to remove
    - E711  # Comparison to None - always safe to remove
  disabled: []
  safe_only: true  # Only auto-fix things we're 100% sure about

# AI settings
ai:
  enabled: true
  provider: groq  # Which AI to use (groq is free!)
  max_files_to_analyze: 5  # Don't analyze huge repos

# What to skip
skip_patterns:
  - __pycache__    # Python cache files (pointless to check)
  - .git           # Git internal files (not code)
  - venv           # Virtual environment (not your code)
  - node_modules   # JS packages (not your code)
  - dist/          # Built/compiled files (not your code)

# How to behave
max_issues_per_run: 1000    # Stop after 1000 issues (huge repos)
create_pr: false            # Don't auto-create PRs (safer)
branch_prefix: "agi-engineer/fixes"  # PR branch name
```

**Translation:** "Hey AGI, for THIS project, check these rules, skip these folders, use Groq AI, and create a nice branch name."

---

### ✅ V1.3: Rate Limiting (Don't Waste Your Free Credits)

**What it means:** You get 10 FREE AI requests per hour. Once you hit that, AGI Engineer waits and tells you to try again later. This **prevents accidentally spending money**.

**Problems it solves:**
- ❌ Accidentally use $100 in AI credits → ✅ Capped at free tier
- ❌ No idea how many times I've used AI → ✅ Tracks usage per project
- ❌ Different AI providers have different limits → ✅ Supports all of them

**How it works:**
```
Run 1: ✅ 1/10 calls used
Run 2: ✅ 2/10 calls used
Run 3: ✅ 3/10 calls used
...
Run 10: ✅ 10/10 calls used (LIMIT HIT)
Run 11: ⏳ "Try again in 45 minutes"
         (counter resets after 1 hour)
```

**Customize limits** in `.agi-engineer.yml`:
```yaml
ai:
  rate_limit:
    limit: 10              # Up to 10 calls
    window_seconds: 3600   # Per 1 hour (3600 seconds)
    storage_path: ~/.agi-engineer/usage.json  # Track here
```

**Check your usage:**
```bash
cat ~/.agi-engineer/usage.json
```

---

### ✅ V1.4: Automated Tests (19 Passing Tests)

**What it means:** We have 19 automatic tests that check if AGI Engineer works correctly. When you make changes, these tests verify nothing broke.

**Problems it solves:**
- ❌ Fix one thing, break something else → ✅ Tests catch regressions
- ❌ "Does this actually work?" → ✅ Proven with tests
- ❌ Can't modify code safely → ✅ Tests protect changes

**Test Coverage:**
```
✅ Rule Classifier Tests (7)
   - Classifies safe rules correctly
   - Classifies risky rules correctly
   - Groups by category
   - Handles multiple issues

✅ Fix Orchestrator Tests (6)
   - Plans fixes correctly
   - Respects safety mode
   - Executes without errors
   - Produces correct summary

✅ Safety Checker Tests (6)
   - Records before/after states
   - Detects regressions
   - Formats reports correctly
```

**Run tests yourself:**
```bash
pytest tests/ -v
```

---

### ✅ V1.5: Metrics & Logging (Track Everything)

**What it means:** Every time you run AGI Engineer, it records:
- When you ran it
- How many issues it found
- How many it fixed
- Any errors that happened
- How long it took

**Problems it solves:**
- ❌ "How many issues did we fix last month?" → ✅ Check logs
- ❌ "Why did it fail?" → ✅ Error logged with timestamp
- ❌ No way to improve → ✅ Metrics show trends

**Check your stats:**
```bash
cat ~/.agi-engineer/runs.json
```

---

### ✅ V1.6: Multi-Language Support (Python + JavaScript/TypeScript)

**What it means:** AGI Engineer supports Python, JavaScript, AND TypeScript. Automatic language detection!

**Problems it solves:**
- ❌ Only works on Python projects → ✅ Works on mixed codebases
- ❌ Have to use different tools for JS/TS → ✅ One tool for all
- ❌ Can't analyze full-stack projects → ✅ Can now

**Usage:**
```bash
python3 agi_engineer_v3.py /path/to/full-stack-project --smart --ai
```

---

### ✅ V1.7: Complete Documentation

**What it means:** Everything is documented with examples, diagrams, and clear explanations.

**What's Included:**
- 📖 **README.md** (this file!) - Overview and examples
- 📋 **CONTRIBUTING.md** - How developers can help
- 💻 **In-code docstrings** - Every function explained
- 🧪 **Test examples** - Shows how to use components

---

## 🎓 Real-World Examples

### Example 1: Fix Your Own Project
```bash
cd ~/my-python-project
python3 /path/to/agi-engineer/agi_engineer_v3.py . --smart --ai

# Result: 5 safe issues fixed, 20 for review, 11 suggestions
# Time: ~10 seconds
```

### Example 2: Fix a GitHub Repo and Create PR
```bash
python3 agi_engineer_v3.py https://github.com/pallets/flask \
  --smart \
  --ai \
  --pr \
  --push

# Result: GitHub PR created ready for review!
```

### Example 3: Just Analyze (No Changes)
```bash
python3 agi_engineer_v3.py . --smart --analyze-only --ai
```

---

## 🛠️ AI Providers

| Provider | Speed | Cost | Best For |
|----------|-------|------|----------|
| 🟢 **Groq** | ⚡ Fastest | FREE | Everyone (start here!) |
| 🔵 **Together AI** | ⚡ Fast | $💰 Cheap | Heavy users |
| 🟡 **OpenRouter** | 🟡 Moderate | $💰 Medium | Model variety |
| 🟣 **Anthropic** | 🟡 Moderate | $💰💰 Premium | Best quality |

**Getting Groq (FREE):**
```bash
# 1. Go to https://console.groq.com/
# 2. Sign up free (no credit card!)
# 3. Copy your API key
export GROQ_API_KEY=gsk_...
```

---

## 📈 Performance

| Repo Size | Time | Issues | Fixes |
|-----------|------|--------|-------|
| Small (< 100 issues) | 5-10s | 36 | 5 |
| Medium (100-500) | 30-60s | 240 | 85 |
| Large (500+) | 2-5m | 1200+ | 400+ |

---

## 🔧 Advanced Usage

```bash
# Show all options
python3 agi_engineer_v3.py --help

# Analyze only (safe)
python3 agi_engineer_v3.py . --analyze-only

# Smart mode (classify issues)
python3 agi_engineer_v3.py . --smart

# With AI analysis
python3 agi_engineer_v3.py . --smart --ai

# Auto-fix
python3 agi_engineer_v3.py . --smart

# Create PR
python3 agi_engineer_v3.py . --smart --pr --push

# Custom branch name
python3 agi_engineer_v3.py . --smart --branch my-fixes

# Don't clean up cloned repo
python3 agi_engineer_v3.py https://github.com/user/repo --no-cleanup
```

---

## 🚨 Safety Features

### 1: Before/After Comparison
Verifies fixes don't break code.

### 2: Safe-Mode Only
Only fixes things it's 100% confident about.

### 3: Git-Based
Everything uses git branches - reversible anytime.

### 4: History Preserved
Every change is traceable in git log.

---

## 💡 Common Questions

**Q: Will it delete my code?**
A: No! Creates git branch, everything is reversible.

**Q: Do I need AI?**
A: No! Works without AI, just less detailed.

**Q: Is Groq really free?**
A: Yes! No credit card needed.

**Q: Can it break my code?**
A: Very unlikely. Only fixes safe things.

**Q: How do I see what changed?**
A: Use `--analyze-only` first to see everything.

---

## 🔗 Resources

- **GitHub**: https://github.com/Theminacious/agi-engineer
- **Issues**: https://github.com/Theminacious/agi-engineer/issues
- **Groq**: https://console.groq.com/
- **Ruff**: https://docs.astral.sh/ruff/
- **ESLint**: https://eslint.org/

---

## 📝 License

MIT License - Free to use and modify!

---

**Ready to clean up your code? Start in 5 minutes!** 🚀
