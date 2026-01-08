# V2.0 Phase 3: Analysis Integration

## Overview

Phase 3 integrates the V1 analysis engine into the V2 backend. This phase enables real-time code analysis triggered by GitHub webhooks, running Ruff (Python) and ESLint (JavaScript/TypeScript) analyses in background jobs, and persisting results to the database.

**Duration**: 4 files, ~800 lines of code  
**Deliverables**: V1 engine wrapper, background jobs, analysis API, results storage  
**Commit**: e979b19

---

## Architecture

### Analysis Workflow

```
GitHub Event (push/PR)
    ↓
POST /webhooks/github (Phase 2)
    ↓
AnalysisRun created (status=pending)
    ↓
POST /api/runs/{id}/execute triggered
    ↓
Background Task Started (non-blocking)
    ├─ Repository Cloned to /tmp/agi-analysis-XXX
    ├─ V1 AnalysisEngine Initialized
    ├─ Ruff Analysis (*.py files)
    ├─ ESLint Analysis (*.js, *.ts, *.jsx, *.tsx)
    ├─ Issues Normalized to V2 Schema
    ├─ AnalysisResult records created in DB
    └─ Run Status Updated (completed/failed)
    ↓
Frontend Polls /api/runs/{id}
    ↓
Results Displayed in Dashboard
```

---

## New Files (4 total)

### 1. `backend/app/v1_engine.py` (300+ lines)

Wrapper around V1 analysis tools.

```python
class V1AnalysisEngine:
    """Wrapper for V1 analysis engine."""
    
    def __init__(self, groq_api_key: Optional[str] = None):
        """Initialize engine with optional Groq API key."""
    
    def analyze_repository(
        self,
        repo_url: str,
        branch: str,
        commit_sha: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze entire repository.
        
        Returns:
        {
            "status": "completed",
            "repository": "https://github.com/user/repo",
            "total_issues": 42,
            "ruff_count": 25,
            "eslint_count": 17,
            "issues": [
                {
                    "file_path": "src/main.py",
                    "line_number": 15,
                    "issue_code": "E501",
                    "category": "safe",
                    "message": "line too long"
                },
                ...
            ]
        }
        """
    
    def _run_ruff_analysis(self, repo_path: str) -> List[Dict]:
        """Run Ruff on Python files."""
    
    def _run_eslint_analysis(self, repo_path: str) -> List[Dict]:
        """Run ESLint on JS/TS files."""
    
    def _normalize_issues(self, ruff_issues, eslint_issues) -> List[Dict]:
        """Normalize Ruff and ESLint issues to V2 schema."""
```

**Key Methods:**

| Method | Purpose |
|--------|---------|
| `analyze_repository()` | Main entry point - runs all analyses |
| `_run_ruff_analysis()` | Execute Ruff on Python files |
| `_run_eslint_analysis()` | Execute ESLint on JS/TS files |
| `_normalize_issues()` | Convert tool output to V2 format |
| `_cleanup_temp_dir()` | Remove temporary repository clone |

**Features:**
- Repository cloning to /tmp
- Multi-language support (Python, JavaScript, TypeScript)
- Result normalization
- Error handling
- Automatic cleanup

### 2. `backend/app/routers/analysis.py` (250+ lines)

Analysis API endpoints.

```python
@router.post("/api/runs/{run_id}/execute")
async def execute_analysis(
    run_id: int,
    token: str = Depends(get_jwt_token),
    db: Session = Depends(get_db)
) -> dict:
    """
    Trigger analysis execution (returns immediately).
    Actual analysis runs in background.
    """

@router.get("/api/runs")
async def list_runs(
    limit: int = 50,
    status: Optional[str] = None,
    repository_id: Optional[int] = None,
    branch: Optional[str] = None,
    token: str = Depends(get_jwt_token),
    db: Session = Depends(get_db)
) -> List[AnalysisRunResponse]:
    """List analysis runs with optional filters."""

@router.get("/api/runs/{run_id}")
async def get_run_detail(
    run_id: int,
    token: str = Depends(get_jwt_token),
    db: Session = Depends(get_db)
) -> AnalysisRunDetailResponse:
    """Get run details with all results."""

@router.get("/api/repositories/{repo_id}/health")
async def get_repository_health(
    repo_id: int,
    token: str = Depends(get_jwt_token),
    db: Session = Depends(get_db)
) -> RepositoryHealthResponse:
    """Get repository health metrics."""

async def _execute_analysis_background(run_id: int) -> None:
    """Background task - runs analysis and stores results."""
```

**Endpoints:**

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/runs/{id}/execute` | Trigger analysis (queues background job) |
| GET | `/api/runs` | List runs (with filters) |
| GET | `/api/runs/{id}` | Get run details + results |
| GET | `/api/repositories/{id}/health` | Repository metrics |

**Features:**
- FastAPI BackgroundTasks for non-blocking execution
- Optional filtering (status, repository, branch)
- Pagination support
- Real-time status updates
- Health metrics calculation

### 3. `backend/app/models/analysis_run.py` (additions)

Enhanced AnalysisRun model.

```python
class RunStatus(str, Enum):
    """Analysis run status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisRun(Base):
    """Analysis execution record."""
    __tablename__ = "analysis_run"
    
    id: int
    repository_id: int
    github_event: str          # push, pull_request, pull_request_review
    github_branch: str
    github_commit_sha: Optional[str]
    pull_request_number: Optional[int]
    status: RunStatus           # pending, in_progress, completed, failed
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    
    # Relationships
    repository: Repository
    results: List[AnalysisResult]
```

### 4. `backend/app/models/analysis_result.py` (additions)

Enhanced AnalysisResult model.

```python
class IssueCategory(str, Enum):
    """Issue severity/category."""
    SAFE = "safe"               # Auto-fix safe
    REVIEW = "review"           # Requires review
    SUGGESTION = "suggestion"   # Nice to have


class AnalysisResult(Base):
    """Individual issue found during analysis."""
    __tablename__ = "analysis_result"
    
    id: int
    run_id: int
    file_path: str
    line_number: int
    code: str                   # E501, no-unused-vars, etc
    category: IssueCategory     # safe, review, suggestion
    message: str
    is_fixed: bool = False
    created_at: datetime = datetime.utcnow()
    
    # Relationships
    run: AnalysisRun
```

---

## API Endpoints

### Analysis Execution (1)

#### `POST /api/runs/{id}/execute`
Trigger analysis execution (non-blocking).

**Headers:**
```
Authorization: Bearer {jwt_token}
```

**Response:**
```json
{
  "status": "queued",
  "run_id": 1,
  "message": "Analysis queued for execution"
}
```

### Analysis Queries (3)

#### `GET /api/runs?limit=50&status=completed&repository_id=1&branch=main`
List runs with optional filters.

**Query Parameters:**
- `limit` - Number of results (default: 50)
- `status` - Filter by status (pending, in_progress, completed, failed)
- `repository_id` - Filter by repository
- `branch` - Filter by branch

**Response:**
```json
[
  {
    "id": 1,
    "event": "push",
    "branch": "main",
    "status": "completed",
    "total_results": 5,
    "created_at": "2026-01-09T12:00:00Z"
  },
  {
    "id": 2,
    "event": "pull_request",
    "branch": "feature/new-api",
    "status": "in_progress",
    "total_results": 0,
    "created_at": "2026-01-09T12:05:00Z"
  }
]
```

#### `GET /api/runs/{id}`
Get run details with all results.

**Response:**
```json
{
  "id": 1,
  "repository": "user/repo",
  "event": "push",
  "branch": "main",
  "commit_sha": "abc123def456",
  "status": "completed",
  "total_results": 5,
  "created_at": "2026-01-09T12:00:00Z",
  "started_at": "2026-01-09T12:00:10Z",
  "completed_at": "2026-01-09T12:01:00Z",
  "error": null,
  "results": [
    {
      "id": 1,
      "file_path": "src/main.py",
      "line_number": 15,
      "code": "E501",
      "category": "review",
      "message": "line too long (120 > 88 characters)"
    },
    {
      "id": 2,
      "file_path": "src/utils.js",
      "line_number": 42,
      "code": "no-unused-vars",
      "category": "suggestion",
      "message": "unused variable 'temp'"
    }
  ]
}
```

#### `GET /api/repositories/{id}/health`
Repository health metrics.

**Response:**
```json
{
  "repository": "user/repo",
  "total_runs": 10,
  "completed_runs": 9,
  "failed_runs": 1,
  "success_rate": 90.0,
  "total_issues": 42,
  "issues_by_category": {
    "safe": 20,
    "review": 15,
    "suggestion": 7
  }
}
```

---

## Analysis Tools

### Ruff (Python)

Analyzes Python files for:
- PEP 8 style violations
- Unused imports
- Undefined names
- And 500+ other rules

Example issues:
```
E501: line too long
W292: no newline at end of file
F841: assigned to but never used
```

### ESLint (JavaScript/TypeScript)

Analyzes JS/TS files for:
- Syntax errors
- Unused variables
- Style violations
- Best practices

Example issues:
```
no-unused-vars: unused variable 'x'
no-console: unexpected console statement
eqeqeq: expected === instead of ==
```

---

## Background Job Processing

### FastAPI BackgroundTasks

```python
@router.post("/api/runs/{run_id}/execute")
async def execute_analysis(run_id: int, background_tasks: BackgroundTasks):
    """Trigger analysis - runs in background."""
    
    # Queue background task
    background_tasks.add_task(
        _execute_analysis_background,
        run_id=run_id
    )
    
    # Return immediately
    return {"status": "queued"}


async def _execute_analysis_background(run_id: int):
    """Background task implementation."""
    try:
        # Update status to in_progress
        run.status = RunStatus.IN_PROGRESS
        run.started_at = datetime.utcnow()
        db.commit()
        
        # Initialize V1 engine
        engine = V1AnalysisEngine(groq_api_key=settings.groq_api_key)
        
        # Run analysis
        result = engine.analyze_repository(
            repo_url=repository.repo_url,
            branch=run.github_branch,
            commit_sha=run.github_commit_sha
        )
        
        # Store results
        for issue in result['issues']:
            analysis_result = AnalysisResult(
                run_id=run_id,
                file_path=issue['file_path'],
                line_number=issue['line_number'],
                code=issue['code'],
                category=issue['category'],
                message=issue['message']
            )
            db.add(analysis_result)
        
        # Update run status
        run.status = RunStatus.COMPLETED
        run.completed_at = datetime.utcnow()
        
    except Exception as e:
        run.status = RunStatus.FAILED
        run.error_message = str(e)
    
    finally:
        db.commit()
```

**Benefits:**
- Non-blocking - request returns immediately
- Tasks run in thread pool
- Automatic cleanup
- Error handling
- Status tracking

---

## Result Normalization

### V1 Output → V2 Schema

Ruff output:
```
src/main.py:15:1: E501 line too long (120 > 88 characters)
```

Normalized to V2:
```json
{
  "file_path": "src/main.py",
  "line_number": 15,
  "code": "E501",
  "category": "review",
  "message": "line too long (120 > 88 characters)"
}
```

ESLint output:
```json
{
  "filePath": "src/utils.js",
  "line": 42,
  "ruleId": "no-unused-vars",
  "message": "unused variable 'temp'"
}
```

Normalized to V2:
```json
{
  "file_path": "src/utils.js",
  "line_number": 42,
  "code": "no-unused-vars",
  "category": "suggestion",
  "message": "unused variable 'temp'"
}
```

### Category Mapping

| Category | Meaning | Example |
|----------|---------|---------|
| `safe` | Auto-fix safe | Whitespace, unused import |
| `review` | Requires manual review | Logic error, style |
| `suggestion` | Nice to have | Code improvement |

---

## Error Handling

### Analysis Failures

If analysis fails:
1. Exception caught
2. Run status set to FAILED
3. Error message stored
4. Database committed
5. Frontend displays error

```python
try:
    result = engine.analyze_repository(...)
except Exception as e:
    run.status = RunStatus.FAILED
    run.error_message = str(e)
finally:
    db.commit()
```

### Cleanup

Temporary directories always cleaned up:
```python
try:
    # Clone and analyze
    analysis_result = engine.analyze_repository(repo_url, branch)
finally:
    # Always cleanup
    engine._cleanup_temp_dir()
```

---

## Database Changes

### New Enums
```sql
-- Run status
CREATE TYPE run_status AS ENUM (
    'pending',
    'in_progress',
    'completed',
    'failed'
);

-- Issue category
CREATE TYPE issue_category AS ENUM (
    'safe',
    'review',
    'suggestion'
);
```

### Updated Tables
```sql
-- analysis_run
ALTER TABLE analysis_run
ADD COLUMN status run_status DEFAULT 'pending',
ADD COLUMN started_at TIMESTAMP,
ADD COLUMN completed_at TIMESTAMP,
ADD COLUMN error_message TEXT;

-- analysis_result
ALTER TABLE analysis_result
ADD COLUMN category issue_category,
ADD COLUMN is_fixed BOOLEAN DEFAULT FALSE;
```

---

## Data Flow Example

### Complete Analysis Workflow

```
1. User pushes to GitHub (main branch)

2. GitHub sends webhook to POST /webhooks/github

3. Backend validates signature and creates AnalysisRun
   - status: pending
   - repository_id: 1
   - github_event: push
   - github_branch: main

4. Frontend calls POST /api/runs/1/execute
   - Returns immediately: { status: "queued" }

5. Background task starts
   - Updates AnalysisRun.status = in_progress
   - Updates AnalysisRun.started_at = now

6. V1 Engine clones repository
   - git clone --depth 1 --branch main repo_url /tmp/agi-analysis-xyz

7. Ruff analysis runs
   - Finds 25 Python issues
   - Returns: file_path, line_number, code, message

8. ESLint analysis runs
   - Finds 17 JS/TS issues
   - Returns: file_path, line_number, code, message

9. Results normalized
   - All issues converted to V2 schema
   - Categories assigned (safe/review/suggestion)

10. Results stored in database
    - 42 AnalysisResult records created

11. Cleanup runs
    - /tmp/agi-analysis-xyz directory removed

12. Run status updated
    - AnalysisRun.status = completed
    - AnalysisRun.completed_at = now

13. Frontend polls /api/runs/1
    - Gets updated status and results
    - Displays 42 issues to user
```

---

## Performance Considerations

### Repository Cloning
- Uses `git clone --depth 1` for speed
- Only fetches specific branch
- Temp directory in /tmp (fast local storage)

### Analysis Tools
- Ruff: Fast Rust-based linter
- ESLint: Fast Node.js linter
- Both can analyze thousands of files in seconds

### Database
- Results stored with run_id foreign key
- Indexed for fast querying
- Paginated results (default limit 50)

### Memory
- Background tasks run in thread pool
- Each task independent
- No memory leaks from temp files (cleanup guaranteed)

---

## Testing

### Test Analysis Execution
```bash
# Queue analysis for run 1
curl -X POST http://localhost:8000/api/runs/1/execute \
  -H "Authorization: Bearer {jwt_token}"

# Get run status
curl http://localhost:8000/api/runs/1 \
  -H "Authorization: Bearer {jwt_token}"

# List all runs
curl "http://localhost:8000/api/runs?status=completed" \
  -H "Authorization: Bearer {jwt_token}"
```

### Unit Tests
```bash
cd backend
pytest tests/test_analysis.py -v
```

---

## What This Phase Enables

✅ Real-time code analysis triggered by webhooks  
✅ Multi-language support (Python, JavaScript, TypeScript)  
✅ Background job execution (non-blocking)  
✅ Results persisted to database  
✅ Run status tracking (pending → in_progress → completed)  
✅ Error handling and reporting  
✅ Health metrics calculation  
✅ Filtering and pagination  

---

## What's Not Yet Included

⏳ Dashboard display (Phase 4)  
⏳ Production deployment (Phase 5)  

---

## Summary

Phase 3 integrates the analysis engine and enables real-time code quality analysis:

- ✅ V1 engine wrapper (Ruff + ESLint)
- ✅ Background job processing
- ✅ Result normalization and storage
- ✅ 4 analysis endpoints (execute, list, detail, health)
- ✅ Error handling and cleanup
- ✅ Database models (RunStatus, IssueCategory)
- ✅ Non-blocking execution
- ✅ Performance optimized

Phase 3 is production-ready for analysis execution. Phase 4 adds the web dashboard.

---

## Next Phase

→ [Phase 4: Dashboard](./04-PHASE4-DASHBOARD.md)

Build the frontend dashboard to display analysis results, runs history, and repository health metrics.
