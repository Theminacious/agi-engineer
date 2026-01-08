# AGI Engineer v3 - New Features

## 🎯 What is v3?

AGI Engineer v3 is an **intelligent code fixer** that goes beyond simple linting. It classifies issues by safety, explains what it's fixing, and ensures no regressions are introduced.

## 🆕 New Features in v3

### 1. Smart Classification System

**What it does:** Automatically categorizes code issues into three levels:
- ✅ **SAFE** - Auto-fixable without risk (unused imports, trailing whitespace)
- ⚠️  **NEEDS REVIEW** - Requires human judgment (unused variables, None comparisons)
- 💡 **SUGGESTIONS** - Optional improvements (line length, complexity)

**Why it matters:** v2 fixed everything blindly. v3 only auto-fixes safe issues, preventing accidental bugs.

**Example output:**
```
📋 ISSUE CLASSIFICATION
✅ SAFE (57 issues)
   • F401: Unused imports (30)
   • F541: f-string without placeholders (15)
   • W291: Trailing whitespace (12)

⚠️  NEEDS REVIEW (18 issues)
   • F841: Unused variable (18)
```

**Module:** `agent/rule_classifier.py`

### 2. Fix Orchestration & Planning

**What it does:** Plans the optimal order to fix issues and executes fixes in a controlled manner.

**Features:**
- Analyzes all issues before fixing
- Groups by safety category
- Executes safe fixes automatically
- Flags risky changes for review
- Provides fix summary

**Example output:**
```
🔧 FIX PLAN
Will auto-fix: 57 issues
Needs review: 18 issues
Suggestions: 0 issues
```

**Module:** `agent/fix_orchestrator.py`

### 3. Explanation Engine

**What it does:** Generates human-readable explanations for every fix being applied.

**Each explanation includes:**
- Rule name and description
- Why it's safe to fix
- Impact of the change
- Example of what changes

**Example output:**
```
📝 EXPLANATIONS

✨ F401: Unused imports [SAFE]
────────────────────────────────────────
Why safe: Removing unused imports has no side effects
Impact: Cleaner code, smaller bundle size
Example: import os (unused) → removed
```

**Module:** `agent/explainer.py`

### 4. Safety Checker & Regression Detection

**What it does:** Records state before/after fixes and verifies no new issues were introduced.

**Safety checks:**
- Counts issues before fixes
- Applies fixes
- Re-scans to count issues after
- Calculates net improvement
- Detects if new issues appeared
- Generates safety report

**Example output:**
```
📊 SAFETY REPORT
Issues before: 75
Issues after: 18
Net fixed: 57
Regressions: 0 ✓
```

**Module:** `agent/safety_checker.py`

### 5. Enhanced CLI with Smart Mode

**What it does:** New `--smart` flag enables intelligent features.

**New flags:**
- `--smart` - Enable classification, explanations, safety checking
- `--analyze-only` - Preview what would be fixed without changing files
- `--branch` - Custom branch name for fixes
- `--push` - Push changes to remote
- `--pr` - Create pull request automatically

**Example usage:**
```bash
# Analyze without fixing
python3 agi_engineer_v3.py repos/my-repo --smart --analyze-only

# Fix with safety checks
python3 agi_engineer_v3.py repos/my-repo --smart

# Fix and create PR
python3 agi_engineer_v3.py https://github.com/user/repo --smart --pr
```

## 📊 Comparison: v2 vs v3

| Feature | v2 | v3 |
|---------|----|----|
| Basic fixing | ✅ | ✅ |
| Classification | ❌ | ✅ |
| Safety levels | ❌ | ✅ |
| Explanations | ❌ | ✅ |
| Regression detection | ❌ | ✅ |
| Fix planning | ❌ | ✅ |
| Smart mode | ❌ | ✅ |
| Analyze-only mode | ❌ | ✅ |

## 🏗️ Architecture

```
agi_engineer_v3.py (Main CLI)
    │
    ├── agent/rule_classifier.py
    │   └── Classifies issues: SAFE/RISKY/SUGGEST
    │
    ├── agent/fix_orchestrator.py
    │   └── Plans and executes fixes in optimal order
    │
    ├── agent/explainer.py
    │   └── Generates human-readable explanations
    │
    ├── agent/safety_checker.py
    │   └── Verifies no regressions introduced
    │
    └── agent/analyze.py
        └── Runs Ruff to scan for issues
```

## 🎯 Key Improvements

### 1. Zero Regressions
v2 could introduce bugs by fixing everything. v3 only auto-fixes safe issues and validates results.

### 2. Transparency
v2 was a black box. v3 explains every change before and after.

### 3. Control
v2 fixed everything or nothing. v3 lets you preview with `--analyze-only` and control what gets fixed.

### 4. Smarter
v2 blindly applied fixes. v3 understands which fixes are safe and plans optimal execution order.

## 📈 Results

**Test on 75 issues:**
- v2: Fixed 57 issues (76% success rate) - but no safety checks
- v3: Fixed 57 safe issues (76% success rate) + flagged 18 for review + 0 regressions

**Key difference:** v3 knows which 57 are safe to fix automatically.

## 🚀 Usage Examples

### Basic Smart Analysis
```bash
python3 agi_engineer_v3.py repos/my-repo --smart
```

**Output:**
1. Classification of all issues
2. Fix plan showing what will be fixed
3. Explanations of each fix type
4. Applies safe fixes
5. Safety report with before/after counts

### Preview Before Fixing
```bash
python3 agi_engineer_v3.py repos/my-repo --smart --analyze-only
```

**Output:**
1. Shows classification
2. Shows fix plan
3. Shows explanations
4. Does NOT modify files

### Automatic PR Creation
```bash
python3 agi_engineer_v3.py https://github.com/user/repo --smart --pr
```

**Output:**
1. Clones repo
2. Creates branch
3. Fixes safe issues
4. Commits changes
5. Pushes to GitHub
6. Creates pull request

## 🔧 How to Use v3

### Installation
```bash
# Already installed if you have the repo
cd agi-engineer
```

### Quick Test
```bash
# Test on sample repo
python3 agi_engineer_v3.py repos/test-repo --smart --analyze-only
```

### Real Usage
```bash
# Your local repo
python3 agi_engineer_v3.py path/to/your/repo --smart

# GitHub repo
python3 agi_engineer_v3.py https://github.com/user/repo --smart
```

## 💡 Best Practices

1. **Always use `--smart`** - Enables all intelligent features
2. **Try `--analyze-only` first** - Preview before fixing
3. **Review the plan** - Check what will be auto-fixed
4. **Check safety report** - Verify no regressions
5. **Review git diff** - See exactly what changed

## 🎓 When to Use v3 vs v2

**Use v3 when:**
- ✅ Working on important/production code
- ✅ Want to understand what's being fixed
- ✅ Need safety guarantees
- ✅ Want to review before applying

**Use v2 when:**
- ✅ Quick fixes on throwaway code
- ✅ Don't need explanations
- ✅ Trust all Ruff fixes blindly

## 📚 Module Documentation

### RuleClassifier
```python
from agent.rule_classifier import RuleClassifier

classifier = RuleClassifier()
category, safety = classifier.classify('F401')
# Returns: ('safe', 0.95)
```

### FixOrchestrator
```python
from agent.fix_orchestrator import FixOrchestrator

orchestrator = FixOrchestrator()
plan = orchestrator.plan_fixes(issues, safety_mode='safe')
orchestrator.execute_plan(repo_path)
```

### ExplainerEngine
```python
from agent.explainer import ExplainerEngine

explainer = ExplainerEngine()
explanation = explainer.explain('F401')
# Returns formatted explanation
```

### SafetyChecker
```python
from agent.safety_checker import SafetyChecker

checker = SafetyChecker()
checker.record_before(repo_path)
# ... apply fixes ...
checker.record_after(repo_path)
report = checker.check_regressions()
```

## ✅ Summary

v3 transforms AGI Engineer from a **simple auto-fixer** into an **intelligent code assistant** that:

1. ✅ Understands which fixes are safe
2. ✅ Explains what it's doing
3. ✅ Prevents regressions
4. ✅ Gives you control
5. ✅ Provides transparency

**Result:** Production-ready code fixing with zero regressions! 🚀
