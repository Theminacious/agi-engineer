# V1 Architecture & Design

## System Overview

AGI Engineer V1 is a modular Python CLI tool with three main components:

```
┌─────────────────────────────────────────────────────┐
│                    Command Line                     │
│                   (main.py / CLI args)              │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│                 Configuration                       │
│           (Config file + Env vars + CLI args)       │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│              Analysis Engine (agent/)                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐  │
│  │  File Reader │  │  Ruff        │  │ ESLint   │  │
│  │              │  │  Integration │  │ Wrapper  │  │
│  └──────────────┘  └──────────────┘  └──────────┘  │
│  ┌──────────────────────────────────────────────┐   │
│  │        AI Enhancement (Groq API)             │   │
│  └──────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────┐   │
│  │        Result Aggregation & Formatting       │   │
│  └──────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│                Output Generation                    │
│         (JSON Report + Console Output)              │
└─────────────────────────────────────────────────────┘
```

---

## Component Architecture

### 1. Main Entry Point (`main.py`)

**Responsibility**: Orchestrate the entire analysis pipeline

**Functions**:
- Parse command-line arguments
- Load configuration
- Validate inputs
- Call analysis engine
- Handle output

**Key Variables**:
```python
args: dict              # Parsed CLI arguments
config: Config          # Configuration object
analyzer: Analyzer      # Main analyzer instance
report: Report          # Final report object
```

**Error Handling**:
```python
try:
    # Parse arguments
except argparse.ArgumentError as e:
    # Invalid arguments
    
try:
    # Load config
except ConfigError as e:
    # Invalid configuration
    
try:
    # Run analysis
except AnalysisError as e:
    # Analysis failed
```

---

### 2. Configuration System

**File**: `agent/config.py` (if exists) or inline

**Configuration Priority** (highest to lowest):
```
1. CLI Arguments      (--exclude, --include, etc.)
2. Environment Vars   (GROQ_API_KEY, etc.)
3. Config File        (.agi-engineer.yml)
4. Defaults           (hardcoded values)
```

**Configuration Structure**:
```yaml
ruff:
  enabled: true
  max_line_length: 88
  rules:
    - E       # PEP 8 errors
    - W       # PEP 8 warnings
    - F       # PyFlakes
  exclude:
    - venv
    - .git
    - __pycache__

eslint:
  enabled: true
  rules:
    - no-unused-vars
    - eqeqeq
    - semi
  exclude:
    - node_modules
    - dist
    - build

groq:
  enabled: true
  api_key: ${GROQ_API_KEY}
  model: mixtral-8x7b-32768
  timeout: 30

output:
  format: json
  pretty: true
  include_metrics: true
```

**Configuration Classes**:
```python
@dataclass
class RuffConfig:
    enabled: bool
    max_line_length: int
    rules: List[str]
    exclude: List[str]

@dataclass
class ESLintConfig:
    enabled: bool
    rules: List[str]
    exclude: List[str]

@dataclass
class GroqConfig:
    enabled: bool
    api_key: str
    model: str
    timeout: int

@dataclass
class Config:
    ruff: RuffConfig
    eslint: ESLintConfig
    groq: GroqConfig
    output: Dict[str, Any]
```

---

### 3. File Reader Module (`agent/file_reader.py`)

**Responsibility**: Discover and read files from repository

**Key Functions**:

#### `discover_files(repo_path: str, include_patterns: List[str], exclude_patterns: List[str]) -> List[str]`
```python
def discover_files(repo_path, include_patterns=None, exclude_patterns=None):
    """
    Recursively discover files matching patterns
    
    Args:
        repo_path: Root directory to scan
        include_patterns: List of glob patterns to include (*.py, *.js, etc.)
        exclude_patterns: List of glob patterns to exclude
    
    Returns:
        List of file paths matching criteria
    
    Algorithm:
        1. Walk directory tree
        2. For each file, check if matches include patterns
        3. Check if matches exclude patterns
        4. Return matching files
    """
```

#### `get_files_by_type(repo_path: str) -> Dict[str, List[str]]`
```python
def get_files_by_type(repo_path):
    """
    Group files by type for parallel processing
    
    Returns:
        {
            'python': [list of .py files],
            'javascript': [list of .js/.ts files],
            'other': [list of other files]
        }
    """
```

#### `read_file_content(file_path: str) -> str`
```python
def read_file_content(file_path):
    """
    Read file content with error handling
    
    Args:
        file_path: Path to file to read
    
    Returns:
        File contents as string
    
    Error Handling:
        - File not found
        - Permission denied
        - Encoding errors
    """
```

**Data Structure**:
```python
@dataclass
class FileInfo:
    path: str                   # Absolute path
    relative_path: str          # Relative to repo root
    size: int                   # File size in bytes
    type: str                   # 'python', 'javascript', 'other'
    last_modified: datetime     # Modification time
    is_binary: bool             # Binary or text file
    content: Optional[str]      # File contents (lazy loaded)
```

**Algorithm: File Discovery**
```
Input: repo_path, include_patterns, exclude_patterns

1. Initialize empty list: results = []
2. For each root, dirs, files in os.walk(repo_path):
   a. Filter directories by exclude patterns
   b. For each file in files:
      - If matches include patterns AND
      - NOT matches exclude patterns:
        - Add to results
3. Return results sorted by path
4. Return: sorted list of file paths
```

---

### 4. Analysis Engine (`agent/analyze.py`)

**Responsibility**: Coordinate linters and aggregate results

**Key Class**: `Analyzer`

```python
class Analyzer:
    def __init__(self, config: Config):
        self.config = config
        self.ruff_issues = []
        self.eslint_issues = []
        self.ai_insights = []
    
    def analyze(self, repo_path: str) -> Report:
        """Main analysis orchestrator"""
        
        # 1. Discover files
        python_files = self._discover_python_files(repo_path)
        js_files = self._discover_js_files(repo_path)
        
        # 2. Run linters
        if self.config.ruff.enabled:
            self.ruff_issues = self._run_ruff(python_files)
        
        if self.config.eslint.enabled:
            self.eslint_issues = self._run_eslint(js_files)
        
        # 3. AI Enhancement
        if self.config.groq.enabled:
            self.ai_insights = self._enhance_with_ai()
        
        # 4. Aggregate
        report = self._aggregate_results()
        
        return report
```

**Ruff Integration**:
```python
def _run_ruff(self, python_files: List[str]) -> List[Issue]:
    """
    Run Ruff on Python files
    
    Steps:
        1. Build ruff command with configuration
        2. Run Ruff process
        3. Parse JSON output
        4. Convert to Issue objects
        5. Return aggregated results
    """
    issues = []
    for file_path in python_files:
        # Run: ruff check --select=E,W,F file_path --output-format=json
        result = subprocess.run([
            'ruff', 'check', 
            '--select=' + ','.join(self.config.ruff.rules),
            '--line-length=' + str(self.config.ruff.max_line_length),
            file_path,
            '--output-format=json'
        ], capture_output=True, text=True)
        
        # Parse JSON output
        data = json.loads(result.stdout)
        
        # Convert to Issue objects
        for violation in data:
            issue = Issue(
                file=file_path,
                line=violation['location']['row'],
                column=violation['location']['column'],
                code=violation['code'],
                message=violation['message'],
                severity=self._map_severity(violation['code']),
                tool='ruff',
                category=self._categorize_ruff_issue(violation['code'])
            )
            issues.append(issue)
    
    return issues
```

**ESLint Integration**:
```python
def _run_eslint(self, js_files: List[str]) -> List[Issue]:
    """
    Run ESLint on JavaScript/TypeScript files
    
    Similar to Ruff but for JavaScript
    """
```

**Data Structure: Issue**
```python
@dataclass
class Issue:
    file: str                   # File path
    line: int                   # Line number (1-indexed)
    column: int                 # Column number (1-indexed)
    code: str                   # Issue code (E501, no-unused-vars, etc.)
    message: str                # Human-readable message
    severity: str               # 'error', 'warning', 'info'
    tool: str                   # 'ruff', 'eslint', 'ai'
    category: str               # 'style', 'unused', 'logic', 'security'
    ai_analysis: Optional[str]  # AI enhancement (if available)
    suggested_fix: Optional[str] # Suggested fix (if available)
```

---

### 5. AI Enhancement (`agent/analyze.py` - groq integration)

**Provider**: Groq API (mixtral-8x7b-32768)

**Function**: `_enhance_with_ai(self, issues: List[Issue]) -> List[Issue]`

```python
def _enhance_with_ai(self, issues: List[Issue]) -> List[Issue]:
    """
    Enhance issues with AI analysis
    
    For each significant issue:
        1. Extract code context
        2. Call Groq API
        3. Parse response
        4. Add to issue
    
    Rate limiting: Batch calls to API
    """
    from groq import Groq
    
    client = Groq(api_key=self.config.groq.api_key)
    enhanced_issues = []
    
    for issue in issues:
        if issue.severity != 'error':
            continue  # Only enhance errors
        
        # Build prompt
        prompt = f"""
        Issue: {issue.message}
        File: {issue.file}
        Line: {issue.line}
        Code: {self._get_code_context(issue)}
        
        Please provide:
        1. Why this is a problem
        2. How to fix it
        3. Best practice
        """
        
        # Call Groq API
        response = client.messages.create(
            model="mixtral-8x7b-32768",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200
        )
        
        # Add enhancement
        issue.ai_analysis = response.content[0].text
        enhanced_issues.append(issue)
    
    return enhanced_issues
```

**Cost Optimization**:
- Only analyze error-level issues
- Batch multiple issues in one call (future)
- Cache results
- Fallback gracefully if API unavailable

---

### 6. Result Aggregation

**Function**: `_aggregate_results(self) -> Report`

```python
def _aggregate_results(self) -> Report:
    """
    Combine all results into structured report
    
    Steps:
        1. Merge all issues
        2. Sort by file, line
        3. Calculate metrics
        4. Create summary
    """
    all_issues = self.ruff_issues + self.eslint_issues
    
    # Calculate summary
    summary = {
        'total_issues': len(all_issues),
        'ruff_issues': len(self.ruff_issues),
        'eslint_issues': len(self.eslint_issues),
        'by_severity': self._count_by_severity(all_issues),
        'by_category': self._count_by_category(all_issues)
    }
    
    # Calculate metrics
    metrics = {
        'analysis_duration_seconds': self.duration,
        'files_analyzed': len(self.all_files),
        'python_files': len(self.python_files),
        'javascript_files': len(self.js_files),
        'avg_issues_per_file': len(all_issues) / len(self.all_files)
    }
    
    return Report(
        repository=self.repo_path,
        timestamp=datetime.now(),
        summary=summary,
        issues=sorted(all_issues, key=lambda x: (x.file, x.line)),
        metrics=metrics
    )
```

**Data Structure: Report**
```python
@dataclass
class Report:
    repository: str             # Repository path
    timestamp: datetime         # Analysis timestamp
    summary: Dict[str, Any]     # Summary statistics
    issues: List[Issue]         # All detected issues
    metrics: Dict[str, Any]     # Performance metrics
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
```

---

### 7. Output Generation

**Responsibilities**:
- Format report for output
- Write to file or console
- Support multiple formats (JSON, text)

**Functions**:

#### `_output_json(report: Report) -> str`
```python
def _output_json(report: Report) -> str:
    """Generate JSON output"""
    return json.dumps({
        'repository': report.repository,
        'timestamp': report.timestamp.isoformat(),
        'summary': report.summary,
        'issues': [
            {
                'file': issue.file,
                'line': issue.line,
                'column': issue.column,
                'code': issue.code,
                'message': issue.message,
                'severity': issue.severity,
                'tool': issue.tool,
                'category': issue.category
            }
            for issue in report.issues
        ],
        'metrics': report.metrics
    }, indent=2)
```

#### `_output_console(report: Report) -> str`
```python
def _output_console(report: Report) -> str:
    """Generate human-readable console output"""
    lines = []
    lines.append("AGI Engineer V1 - Analysis Report")
    lines.append("=" * 40)
    lines.append(f"Repository: {report.repository}")
    lines.append(f"Time: {report.timestamp}")
    lines.append(f"Total Issues: {report.summary['total_issues']}")
    # ... more formatting
    return "\n".join(lines)
```

---

## Data Flow Diagram

### Analysis Pipeline

```
Input Repository Path
          ↓
   ┌──────────────────────────┐
   │  Configuration Loading   │
   │  (config.yml + CLI args) │
   └──────────┬───────────────┘
              ↓
   ┌──────────────────────────┐
   │   File Discovery         │
   │ (Find .py, .js, .ts)     │
   └──────────┬───────────────┘
              ↓
        ┌─────────────┐
        │             ↓
    ┌──────────┐  ┌──────────┐  ┌────────────┐
    │ Ruff     │  │ ESLint   │  │ File List  │
    │ Analysis │  │ Analysis │  │ Storage    │
    └────┬─────┘  └────┬─────┘  └────────────┘
         │             │
         └─────┬───────┘
               ↓
   ┌──────────────────────────┐
   │  Result Merging          │
   │  (Consolidate all issues)│
   └──────────┬───────────────┘
              ↓
   ┌──────────────────────────┐
   │  AI Enhancement          │
   │  (Groq API)              │
   └──────────┬───────────────┘
              ↓
   ┌──────────────────────────┐
   │  Report Generation       │
   │  (JSON + Summary)        │
   └──────────┬───────────────┘
              ↓
   ┌──────────────────────────┐
   │  Output                  │
   │ (File + Console)         │
   └──────────────────────────┘
```

---

## Class Relationships

```
┌─────────────────────────────────────┐
│         Analyzer                    │
│                                     │
│ - config: Config                    │
│ - report: Report                    │
│                                     │
│ + analyze(): Report                 │
│ + _run_ruff(): Issue[]              │
│ + _run_eslint(): Issue[]            │
│ + _enhance_with_ai(): Issue[]       │
│ + _aggregate_results(): Report      │
└────────────┬────────────────────────┘
             │ uses
     ┌───────┴────────┬─────────────┐
     │                │             │
     ▼                ▼             ▼
┌─────────┐  ┌──────────────┐  ┌─────────┐
│ Config  │  │ FileReader   │  │ Groq    │
│         │  │              │  │ Client  │
│ + ruff  │  │ + discover   │  │         │
│ + eslint│  │ + read       │  │ + call  │
│ + groq  │  │ + filter     │  │ API     │
└─────────┘  └──────────────┘  └─────────┘
     │                │
     │ contains       │ returns
     │                │
     ▼                ▼
┌──────────────┐  ┌──────────────┐
│ RuffConfig   │  │ FileInfo[]   │
│ ESLintConfig │  │              │
│ GroqConfig   │  │ + path       │
│              │  │ + type       │
│              │  │ + content    │
└──────────────┘  └──────────────┘
                       │
                       │ aggregated into
                       │
                       ▼
                  ┌──────────────┐
                  │ Report       │
                  │              │
                  │ + issues     │
                  │ + summary    │
                  │ + metrics    │
                  └──────────────┘
                       │
                       │ contains
                       │
                       ▼
                  ┌──────────────┐
                  │ Issue        │
                  │              │
                  │ + file       │
                  │ + line       │
                  │ + message    │
                  │ + severity   │
                  │ + ai_analysis│
                  └──────────────┘
```

---

## Performance Considerations

### Time Complexity
```
File discovery:     O(n)     - n = total files
Ruff analysis:      O(f)     - f = Python files
ESLint analysis:    O(j)     - j = JS files
AI enhancement:     O(i*t)   - i = issues, t = API time
Total:              O(n + i*t)
```

### Optimization Strategies

1. **Lazy Loading**
   - Don't read file content until needed
   - Parse issues incrementally

2. **Batching**
   - Batch file discovery by type
   - Batch AI API calls

3. **Caching**
   - Cache file list
   - Cache configuration
   - Cache AI responses

4. **Parallelization** (Future)
   - Run Ruff and ESLint in parallel
   - Batch AI calls

### Memory Optimization
```
Issue object size: ~500 bytes
1000 issues: ~500KB
Typical repo: 100-1000 issues
Peak memory: < 200MB
```

---

## Error Handling Strategy

### Error Types

#### Configuration Errors
```python
class ConfigError(Exception):
    """Invalid configuration"""
    pass
```

#### Analysis Errors
```python
class AnalysisError(Exception):
    """Error during analysis"""
    pass
```

#### Tool Errors
```python
class ToolError(Exception):
    """Ruff/ESLint execution error"""
    pass
```

#### API Errors
```python
class APIError(Exception):
    """Groq API error"""
    pass
```

### Error Recovery
```python
try:
    analyze()
except ToolError:
    # Ruff not installed - skip tool
    continue
except APIError:
    # Groq unavailable - skip AI
    continue
except ConfigError:
    # Invalid config - use defaults
    use_default_config()
```

---

## Testing Strategy

### Unit Tests
- Individual function testing
- Mocked external dependencies
- Edge cases and error handling

### Integration Tests
- End-to-end analysis
- Real linters (Ruff, ESLint)
- Real files and repositories

### Performance Tests
- Analysis time benchmarks
- Memory usage monitoring
- Scalability testing

---

## Extension Points

### 1. Add New Analyzer
```python
class CustomAnalyzer:
    def run(self, files):
        # Custom analysis
        return issues
```

### 2. Add New Output Format
```python
def _output_html(report):
    # Generate HTML report
    pass
```

### 3. Add Custom Rules
```python
config.ruff.rules = ['E', 'W', 'F', 'CUSTOM']
```

---

## Future Architecture

### V1.5 - Auto-fix
```
Report (with issues)
    ↓
Fixer (auto-fix safe issues)
    ├─ Identify safe fixes
    ├─ Apply patches
    └─ Verify changes
    ↓
Updated Code
```

### V2 - Web Dashboard
```
Analyzer (V1 logic reused)
    ↓
FastAPI Backend
    ├─ Store results
    ├─ Track history
    └─ Expose API
    ↓
React Frontend
    ├─ View reports
    ├─ Track trends
    └─ Configure analysis
```

---

## Implementation Checklist

- ✅ File discovery and reading
- ✅ Ruff integration
- ✅ ESLint integration
- ✅ Result aggregation
- ✅ JSON output
- ✅ Configuration system
- ✅ CLI argument parsing
- ✅ Error handling
- ✅ AI enhancement (Groq)
- ✅ Testing framework
- ✅ Console output

---

## Summary

V1 architecture is:
- **Modular**: Each component has single responsibility
- **Extensible**: Easy to add new analyzers
- **Efficient**: Linear time complexity
- **Robust**: Comprehensive error handling
- **Tested**: 19 passing tests

The design supports future evolution to V2 while maintaining simplicity and reliability.

---

**Version**: 1.0  
**Status**: Production Ready ✅  
**Last Updated**: January 9, 2026
