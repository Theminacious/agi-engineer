# AI Integration - New Features

## 🤖 What is AI Integration?

AI Integration adds **intelligent, context-aware code analysis** using Large Language Models (LLMs). It goes beyond rule-based linting to understand code semantically and provide human-like suggestions.

## 🆕 What AI Adds

### Beyond Rule-Based Linting

**Ruff (v3) finds:**
- Syntax errors
- Unused imports/variables
- Trailing whitespace
- Style violations

**AI finds:**
- Poor variable/function names
- Missing docstrings
- Complex nested logic
- Performance opportunities
- Code smells
- Best practice violations
- Unclear code structure

## 🎯 New AI Features

### 1. AI-Powered Code Quality Analysis

**What it does:** Analyzes entire files for semantic issues that rule-based tools miss.

**Finds:**
- **Bad naming:** Variables like `func`, `a`, `b`, `temp` → suggests descriptive names
- **Shadows builtins:** Variable named `list`, `dict`, `sum` → warns and suggests alternatives
- **Missing docs:** Functions without docstrings → identifies what needs documentation
- **Code complexity:** Deeply nested logic → suggests simplification
- **Performance:** Inefficient patterns → suggests optimizations

**Example output:**
```
🤖 AI ANALYSIS
📄 handlers.py

1. Poor function name (line 3)
   Current: handle
   Suggestion: handle_event
   Reason: More descriptive of purpose

2. Shadows builtin (line 9)
   Variable: list
   Issue: Shadows Python builtin
   Suggestion: Rename to result_list or items

3. Missing docstring (line 3)
   Function: handle_event
   Impact: No documentation of purpose/params

4. Code complexity (line 10)
   Issue: Nested if statements (3 levels)
   Suggestion: Use early returns
```

**Module:** `agent/ai_analyzer.py` → `analyze_code_quality()`

### 2. Intelligent Naming Suggestions

**What it does:** Reads code logic and suggests meaningful names based on what the code actually does.

**Example:**
```python
# Bad code
def func(a, b, c):
    d = a + b
    e = d * c
    f = e / 2
    return f
```

**Ruff says:** ✅ No issues

**AI says:** 
```
❌ Function name 'func' is not descriptive
💡 Suggested: calculate_weighted_average
📝 Reason: Calculates (a+b)*c/2 which is a weighted average
```

**Module:** `agent/ai_analyzer.py` → `suggest_better_name()`

### 3. Automatic Docstring Generation

**What it does:** Reads function code and generates proper Google-style docstrings with descriptions, args, and returns.

**Example:**
```python
# Before
def complex_function(x, y, z):
    if x > 0:
        if y > 0:
            if z > 0:
                return x + y + z
            else:
                return x + y
        else:
            return x
    else:
        return 0
```

**AI generates:**
```python
"""
Returns the sum of positive input values.

This function takes three numbers as input and returns their sum, but only
if all numbers are positive. If any number is non-positive, it is excluded.

Args:
    x (int/float): The first number to consider
    y (int/float): The second number to consider
    z (int/float): The third number to consider

Returns:
    int/float: The sum of the positive input values
"""
```

**Module:** `agent/ai_analyzer.py` → `generate_docstring()`

### 4. Complex Code Explanation

**What it does:** Explains what complex code does in simple, human-readable terms.

**Use case:** Understanding legacy code or code written by others.

**Example:**
```python
result = [x for x in data if x > threshold and validate(x)]
```

**AI explains:**
```
This filters the data list to include only items that are both 
greater than the threshold value and pass the validate() function,
returning them as a new list.
```

**Module:** `agent/ai_analyzer.py` → `explain_complex_code()`

### 5. Refactoring Suggestions

**What it does:** Identifies opportunities to improve code structure, remove duplication, and simplify logic.

**Suggests:**
- Extract methods from long functions
- Remove code duplication
- Simplify nested conditions
- Use list comprehensions
- Apply design patterns

**Example:**
```python
# Current code
def get_evens(numbers):
    result = []
    for num in numbers:
        if num % 2 == 0:
            result.append(num)
    return result
```

**AI suggests:**
```python
# Better: Use list comprehension
def get_evens(numbers):
    return [num for num in numbers if num % 2 == 0]

Reason: More Pythonic, faster, clearer intent
```

**Module:** `agent/ai_analyzer.py` → `suggest_refactoring()`

## 🔌 Multi-Provider Support

AI analyzer supports multiple LLM providers with automatic fallback:

### 1. Groq (Recommended - FREE) ⭐
- ✅ Completely free, no credit card
- ✅ Very fast (sub-second responses)
- ✅ Generous rate limits
- ✅ Model: llama-3.3-70b-versatile

**Setup:**
```bash
export GROQ_API_KEY='your_key_here'
```

Get key: https://console.groq.com/keys

### 2. Together AI
- ✅ $25 free credits on signup
- ✅ Many open-source models
- Model: meta-llama/Llama-3-70b-chat-hf

**Setup:**
```bash
export TOGETHER_API_KEY='your_key_here'
```

### 3. OpenRouter
- ✅ Access to multiple providers
- ✅ Some free models
- Model: meta-llama/llama-3-70b-instruct

**Setup:**
```bash
export OPENROUTER_API_KEY='your_key_here'
```

### 4. Anthropic Claude
- ❌ Paid (but high quality)
- Model: claude-3-5-sonnet-20241022

**Setup:**
```bash
export ANTHROPIC_API_KEY='your_key_here'
```

**Priority:** Groq → Together → OpenRouter → Anthropic

## 🚀 How to Use AI Features

### 1. Install Dependencies

```bash
# For Groq (recommended)
pip install groq

# For Anthropic
pip install anthropic

# For Together AI / OpenRouter
pip install requests
```

Or install all:
```bash
pip install -r requirements.txt
```

### 2. Set API Key

**Option 1: Free Groq (Recommended)**
```bash
# Get key from: https://console.groq.com/keys
export GROQ_API_KEY='gsk_your_key_here'
```

**Option 2: Environment file**
```bash
echo 'export GROQ_API_KEY="your_key"' >> ~/.zshrc
source ~/.zshrc
```

### 3. Use with CLI

**Analyze only (preview):**
```bash
python3 agi_engineer_v3.py repos/my-repo --smart --ai --analyze-only
```

**Fix + AI suggestions:**
```bash
python3 agi_engineer_v3.py repos/my-repo --smart --ai
```

**Output:**
```
🔍 Scanning repository with Ruff...
📊 Found 25 issues

✓ Using GROQ for AI analysis
🤖 AI analyzer enabled

📋 ISSUE CLASSIFICATION
✅ SAFE (20 issues)
⚠️  NEEDS REVIEW (5 issues)

🔧 Applying fixes...

🤖 AI SUGGESTIONS
📄 example.py
• Function 'func' → rename to 'calculate_average'
• Variable 'list' shadows builtin → use 'items'
• Missing docstring on handle_event()
• Consider using list comprehension (line 45)

✅ Fixed 20 issues
```

## 📊 Real Example

### Test File with Issues:
```python
def func(a, b, c):
    d = a + b
    e = d * c
    f = e / 2
    return f

def process_data(items):
    list = []  # Bad - shadows builtin
    for item in items:
        list.append(item * 2)
    return list
```

### What Ruff Finds:
```
✅ No issues (code is syntactically valid)
```

### What AI Finds:
```
1. Poor function name 'func'
   → Suggestion: calculate_weighted_average
   → Reason: Calculates (a+b)*c/2

2. Single-letter variables (a,b,c,d,e,f)
   → Suggestion: first_value, second_value, weight, sum, product, result
   → Reason: Improves readability

3. Variable 'list' shadows builtin
   → Suggestion: processed_items or doubled_list
   → Reason: Prevents subtle bugs

4. Missing docstrings
   → Generated proper docstrings for both functions

5. Can use list comprehension
   → [item * 2 for item in items]
   → Reason: More Pythonic and faster
```

## 🎯 Key Benefits

### 1. Context-Aware
AI understands what code does, not just syntax.

**Example:**
- Ruff: "Variable unused" ✓
- AI: "Variable `temp_result` calculated but never used. Safe to remove - no side effects detected"

### 2. Semantic Understanding
AI reads code like a human.

**Example:**
- Ruff: No issue with `def func(a, b, c)`
- AI: "Function name 'func' not descriptive. Based on logic, suggests 'calculate_scaled_sum'"

### 3. Generative
AI doesn't just find issues - it creates solutions.

**Example:**
- Ruff: Can't generate docstrings
- AI: Writes complete docstring with Args, Returns, Examples

### 4. Best Practices
AI knows modern Python conventions.

**Example:**
- Suggests type hints
- Recommends list comprehensions
- Identifies code smells
- Suggests design patterns

## 🔧 Integration Architecture

```
agi_engineer_v3.py
    │
    ├── --ai flag enabled
    │
    ├── agent/ai_analyzer.py
    │   │
    │   ├── _detect_provider()
    │   │   └── Auto-detects available API keys
    │   │
    │   ├── _call_llm()
    │   │   ├── _call_groq() (if GROQ_API_KEY)
    │   │   ├── _call_together() (if TOGETHER_API_KEY)
    │   │   ├── _call_openrouter() (if OPENROUTER_API_KEY)
    │   │   └── _call_anthropic() (if ANTHROPIC_API_KEY)
    │   │
    │   ├── analyze_code_quality()
    │   ├── suggest_better_name()
    │   ├── generate_docstring()
    │   ├── explain_complex_code()
    │   └── suggest_refactoring()
    │
    └── Displays AI suggestions after fixes
```

## 💰 Cost Comparison

| Provider | Cost | Speed | Quality |
|----------|------|-------|---------|
| Groq | **FREE** ⭐ | ⚡⚡⚡ Fast | ⭐⭐⭐⭐ Excellent |
| Together AI | $25 credit | ⚡⚡ Medium | ⭐⭐⭐⭐ Excellent |
| OpenRouter | Varies | ⚡⚡ Medium | ⭐⭐⭐⭐ Excellent |
| Anthropic | ~$0.50/repo | ⚡⚡ Medium | ⭐⭐⭐⭐⭐ Best |

**Recommendation:** Use Groq (free, fast, excellent quality)

## 🎓 When to Use AI

**Use AI when:**
- ✅ Code works but is hard to understand
- ✅ Variable/function names are unclear
- ✅ Missing documentation
- ✅ Want to learn best practices
- ✅ Reviewing someone else's code
- ✅ Refactoring legacy code

**Skip AI when:**
- ❌ Just need quick syntax fixes (use v3 without --ai)
- ❌ No API key available
- ❌ Internet connection issues
- ❌ Time-sensitive (AI adds 1-2 seconds)

## 📈 Impact

### Before AI Integration:
```
Ruff finds: 25 syntax issues
Developer must manually:
- Review code for naming
- Check for missing docs
- Look for performance issues
- Identify best practice violations
```

### With AI Integration:
```
Ruff finds: 25 syntax issues (auto-fixed)
AI finds: 15 semantic issues
- 8 naming improvements
- 4 missing docstrings
- 2 performance opportunities
- 1 code smell

All with specific suggestions and reasoning!
```

## ✅ Summary

AI Integration transforms AGI Engineer from a **syntax fixer** into an **intelligent code reviewer** that:

1. ✅ Understands code semantically
2. ✅ Suggests meaningful improvements
3. ✅ Generates documentation
4. ✅ Explains complex logic
5. ✅ Recommends refactoring
6. ✅ Teaches best practices

**Result:** Not just correct code, but **good code**! 🚀

## 🔗 Resources

- **Get Groq API Key:** https://console.groq.com/keys
- **Groq Docs:** https://console.groq.com/docs
- **Together AI:** https://together.ai
- **OpenRouter:** https://openrouter.ai
- **Anthropic:** https://console.anthropic.com

---

**Quick Start:**
```bash
# 1. Get free Groq key
# Visit: https://console.groq.com/keys

# 2. Set it
export GROQ_API_KEY='your_key'

# 3. Use it
python3 agi_engineer_v3.py repos/my-repo --smart --ai
```
