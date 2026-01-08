"""Phase 3: V1 Core Integration - Implementation Details and API Reference"""

# V2.0 Phase 3: V1 Core Integration

## Overview

Phase 3 integrates the V1 analysis engine into V2's FastAPI backend. This allows:
- Real-time code analysis triggered by webhooks
- Multi-language support (Python via Ruff, JavaScript/TypeScript via ESLint)
- Background job execution
- Result persistence to database
- Health monitoring and metrics

## Architecture

```
GitHub Event (Push/PR)
    ↓
POST /webhooks/github (Phase 2)
    ↓
AnalysisRun Created (status=pending)
    ↓
POST /api/runs/{run_id}/execute
    ↓
Background Task Started
    ├─ Repository Cloned to /tmp
    ├─ V1 Engine Initialized
    ├─ Ruff Analysis (Python)
    ├─ ESLint Analysis (JavaScript/TypeScript)
    ├─ Issues Normalized to V2 Format
    ├─ AnalysisResult Records Created
    └─ Run Status Updated (completed/failed)
    ↓
Frontend Queries /api/runs/{run_id}
    ↓
Results Displayed in Dashboard
```

## New Files

### `app/v1_engine.py` (300+ lines)
Wrapper around V1 analysis tools.

**Key Class: `V1AnalysisEngine`**

```python
engine = V1AnalysisEngine(groq_api_key=settings.groq_api_key)

# Analyze entire repository
result = engine.analyze_repository(
    repo_url="https://github.com/user/repo",
    branch="main",
    commit_sha="abc123"  # optional
)

# Result structure:
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
            "issue_name": "line too long",
            "category": "safe",
            "severity": "error",
            "message": "line is too long...",
            "language": "python"
        },
        ...
    ]
}
```

**Methods:**

- `analyze_repository(repo_url, branch, commit_sha)` - Main analysis entry point
- `_clone_repository(repo_url, target_dir, branch)` - Clone via git
- `_run_ruff_analysis(repo_dir)` - Run Python linter
- `_run_eslint_analysis(repo_dir)` - Run JavaScript linter
- `_normalize_ruff_issues(issues)` - Convert Ruff format to V2
- `_normalize_eslint_issues(files)` - Convert ESLint format to V2
- `_categorize_issue(language, code)` - Classify as safe/review/suggestion
- `cleanup()` - Remove temporary files

### `app/routers/analysis.py` (400+ lines)
Analysis API endpoints.

## New API Endpoints

### `POST /api/runs/{run_id}/execute`
Trigger analysis execution for a pending run.

**Parameters:**
- `run_id` - Analysis run ID (from webhook)

**Response:**
```json
{
  "status": "queued",
  "run_id": 1,
  "message": "Analysis queued for execution"
}
```

**How it works:**
1. Find pending AnalysisRun record
2. Queue as FastAPI background task
3. Return immediately (non-blocking)
4. Background task:
   - Clones repository
   - Runs V1 analysis (Ruff + ESLint)
   - Stores AnalysisResult records
   - Updates AnalysisRun status

### `GET /api/runs/{run_id}`
Get analysis run details and results.

**Response:**
```json
{
  "id": 1,
  "repository_id": 1,
  "event": "push",
  "branch": "main",
  "commit_sha": "abc123def",
  "pr_number": null,
  "status": "completed",
  "total_results": 42,
  "results": [
    {
      "id": 1,
      "file_path": "src/main.py",
      "line_number": 15,
      "code": "E501",
      "name": "line-too-long",
      "category": "safe",
      "message": "Line too long...",
      "is_fixed": 0
    }
  ],
  "created_at": "2026-01-09T12:00:00",
  "started_at": "2026-01-09T12:00:05",
  "completed_at": "2026-01-09T12:00:35",
  "error": null
}
```

**Status Values:**
- `pending` - Created, awaiting execution
- `in_progress` - Currently analyzing
- `completed` - Analysis finished successfully
- `failed` - Analysis encountered error

### `GET /api/runs`
List analysis runs with filtering.

**Query Parameters:**
- `repository_id` - Filter by repository (optional)
- `status` - Filter by status: pending|in_progress|completed|failed (optional)
- `limit` - Max results (default: 50, max: 500)

**Response:**
```json
[
  {
    "id": 1,
    "repository_id": 1,
    "event": "push",
    "status": "completed",
    "branch": "main",
    "results_count": 42,
    "created_at": "2026-01-09T12:00:00"
  }
]
```

### `GET /api/repositories/{repo_id}/health`
Repository health metrics.

**Response:**
```json
{
  "repository_id": 1,
  "repository_name": "user/repo",
  "is_enabled": true,
  "total_runs": 10,
  "completed_runs": 9,
  "failed_runs": 1,
  "success_rate": 0.9,
  "average_analysis_time_seconds": 30.5,
  "recent_issues": [
    {
      "file": "src/main.py",
      "line": 15,
      "code": "E501",
      "message": "Line too long (89 > 88 characters)"
    }
  ]
}
```

## Workflow Integration

### Complete Flow with Phase 2

```
1. User installs GitHub App
   → /oauth/authorize
   → /oauth/callback (JWT stored)

2. App webhook registered
   → Configuration stored in Installation

3. Developer pushes code
   → GitHub sends webhook to /webhooks/github
   → Webhook signature validated
   → AnalysisRun created (status=pending)

4. Analysis queued
   → POST /api/runs/{run_id}/execute
   → Returns immediately
   → Background task started

5. Background Analysis Runs
   → Repository cloned to /tmp/agi-analysis-XXX
   → Ruff analysis on *.py files
   → ESLint analysis on *.js, *.ts, *.jsx, *.tsx files
   → Results normalized to V2 format
   → AnalysisResult records created
   → AnalysisRun status updated to completed

6. Frontend Polls Results
   → GET /api/runs/{run_id}
   → Displays issues, categorization
   → Shows status (completed/failed)
   → Lists all findings with file/line info

7. Optional: Fix Suggestions
   → Phase 4 will add PR creation with fixes
   → Can create pull requests with auto-fixes
```

## Database Changes

### AnalysisRun Status Tracking

```python
class RunStatus(str, enum.Enum):
    PENDING = "pending"           # Webhook created, awaiting execution
    IN_PROGRESS = "in_progress"   # Currently analyzing
    COMPLETED = "completed"       # Analysis finished successfully
    FAILED = "failed"             # Analysis encountered error
    CANCELLED = "cancelled"       # Manually cancelled
```

### AnalysisResult Categorization

```python
class IssueCategory(str, enum.Enum):
    SAFE = "safe"               # Auto-fixable, safe to apply
    REVIEW = "review"           # Requires human review
    SUGGESTION = "suggestion"   # Nice-to-have, optional
```

## V1 Engine Implementation

### Ruff Analysis (Python)

Runs: `ruff check <dir> --output-format=json`

Handles:
- PEP 8 style violations (E***, W***)
- Import issues (F***)
- Complexity warnings
- Security issues

### ESLint Analysis (JavaScript/TypeScript)

Runs: `npx eslint <dir> --format=json --ext=.js,.jsx,.ts,.tsx`

Handles:
- Code style (indent, semi, quotes, etc.)
- Best practices (no-console, no-unused-vars)
- Potential bugs (no-undef, etc.)
- Security (no-eval)

### Issue Normalization

Both tools output different formats. V2 normalizes to:

```python
{
    "file_path": "src/main.py",
    "line_number": 15,
    "issue_code": "E501",           # From tool (Ruff rule ID, ESLint rule)
    "issue_name": "line-too-long",
    "category": "safe|review|suggestion",
    "severity": "error|warning|info",
    "message": "Line too long...",
    "language": "python|javascript"
}
```

## Error Handling

### Repository Cloning Fails
- Captured in try/except
- AnalysisRun marked as failed
- Error message stored: "Git clone timeout" or specific git error

### Ruff/ESLint Not Installed
- Warnings logged, analysis continues with other tools
- If both fail: AnalysisRun marked as failed with message

### Analysis Timeout
- Ruff: 120s timeout (configurable)
- ESLint: 120s timeout (configurable)
- If timeout: caught, logged, returns [] (no issues vs. crash)

### Database Errors
- Background task catches exceptions
- Updates AnalysisRun.error_message
- Marks status as failed

## Background Task Processing

FastAPI `BackgroundTasks` used for non-blocking execution:

```python
@router.post("/api/runs/{run_id}/execute")
async def execute_analysis(run_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Queue background task
    background_tasks.add_task(_execute_analysis_background, run_id)
    
    # Return immediately to client
    return {"status": "queued"}
```

Benefits:
- API returns within 1-2 seconds
- Analysis runs independently
- Frontend can poll for results
- Multiple analyses can run in parallel (worker pool)

## Dependencies

New dependencies in `pyproject.toml`:

```toml
# Already included:
"requests==2.31.0"           # HTTP calls to GitHub
"sqlalchemy==2.0.23"         # Database ORM

# System dependencies (must be installed):
ruff                         # Python linter (pip install ruff)
eslint                       # JavaScript linter (npm install -g eslint)
git                          # Repository cloning
npx                          # To run npm packages
```

## Configuration

Environment variables (in `.env`):

```env
# Analysis settings
GROQ_API_KEY=gsk_xxx        # For future AI analysis (Phase 4)

# Database
DATABASE_URL=postgresql://...  # Results storage

# API
API_ENV=development         # Logging verbosity
```

## Monitoring & Observability

### Logging

All operations logged:
```
2026-01-09T12:00:00 [INFO] Created temp directory: /tmp/agi-analysis-xyz
2026-01-09T12:00:01 [INFO] Cloned repository to /tmp/agi-analysis-xyz
2026-01-09T12:00:05 [INFO] Ruff analysis found 25 issues
2026-01-09T12:00:10 [INFO] ESLint analysis found 17 issues
2026-01-09T12:00:35 [INFO] Analysis completed for run 1: 42 issues found
2026-01-09T12:00:36 [INFO] Cleaned up temp directory: /tmp/agi-analysis-xyz
```

### Metrics (from `/api/repositories/{repo_id}/health`)

- Total runs executed
- Success rate (completed / total)
- Average analysis time
- Recent issues by file
- Enabled/disabled status

## Testing

```bash
# Start backend
cd backend
python main.py

# In another terminal, query API
curl http://localhost:8000/api/runs

# Trigger analysis (simulate webhook)
curl -X POST http://localhost:8000/api/runs/1/execute

# Poll for results
curl http://localhost:8000/api/runs/1

# Get health metrics
curl http://localhost:8000/api/repositories/1/health
```

## Performance

### Typical Analysis Times

- Clone repository: 5-15 seconds (depends on size, network)
- Ruff analysis: 5-30 seconds (depends on file count)
- ESLint analysis: 5-30 seconds (depends on file count)
- Total: 15-75 seconds per repository

### Optimization Opportunities (Future)

- Cache cloned repositories (use --depth=1 + shallow clones)
- Parallel analysis (run Ruff + ESLint concurrently)
- Incremental analysis (only changed files)
- Caching of ESLint/Ruff results
- Worker pool (run multiple analyses in parallel, not sequential)

## Next Steps

**Phase 4: Dashboard UI**
- Display analysis results in Next.js frontend
- Real-time updates (WebSockets)
- Per-repository settings
- Run history view

**Phase 5: Deployment**
- Docker Compose full stack
- Alembic migrations
- CI/CD with GitHub Actions
- Marketplace listing

## Troubleshooting

### Analysis Stuck in "in_progress"
- Check background task worker logs
- May indicate timeout or system failure
- Restart backend to resume worker queue

### Ruff/ESLint Not Found
- Install: `pip install ruff` and `npm install -g eslint`
- Check PATH: `which ruff` and `which eslint`

### Database Connection Issues
- Verify `DATABASE_URL` is correct
- Check PostgreSQL is running
- Review error logs in AnalysisRun.error_message

### Webhook Not Triggering Analysis
- Verify GitHub webhook is configured
- Check signature validation passing (see Phase 2 docs)
- Confirm WEBHOOK_SECRET matches GitHub app settings
