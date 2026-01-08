# AGI Engineer V2.0 - Complete Documentation

> **GitHub App for Automated Code Quality Analysis and Fixing**  
> Production-ready SaaS application with OAuth, webhooks, real-time analysis, and web dashboard.

---

## 📑 Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture Overview](#architecture-overview)
3. [Project Structure](#project-structure)
4. [Features](#features)
5. [System Design](#system-design)
6. [Database Schema](#database-schema)
7. [API Reference](#api-reference)
8. [Frontend Guide](#frontend-guide)
9. [Setup & Configuration](#setup--configuration)
10. [Running Locally](#running-locally)
11. [Deployment](#deployment)
12. [Development](#development)
13. [Troubleshooting](#troubleshooting)

---

## Quick Start

### For Users
1. Install GitHub App from marketplace
2. Click "Install" on your repositories
3. Push code or create pull request
4. View analysis results on dashboard
5. Fix issues and improve code quality

### For Developers
```bash
# Clone repository
git clone https://github.com/yourusername/agi-engineer.git
cd agi-engineer

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --reload

# Frontend setup (new terminal)
cd frontend
npm install
npm run dev

# Visit http://localhost:3000
```

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────────────────┐
│                        GitHub Events                               │
│                (Push, Pull Request, Review)                        │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                    ┌────▼────┐
                    │ Webhook │
                    │ Handler │
                    └────┬────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   ┌────▼─────┐    ┌─────▼──────┐    ┌──▼────┐
   │  OAuth   │    │  Analysis  │    │ Other │
   │ Router   │    │  Engine    │    │ APIs  │
   └────┬─────┘    └─────┬──────┘    └──┬────┘
        │                │               │
        └────────────────┼───────────────┘
                         │
              ┌──────────▼──────────┐
              │  PostgreSQL DB     │
              │  (All results)     │
              └────────────────────┘
                         │
                    ┌────▼────────┐
                    │  Frontend   │
                    │  Dashboard  │
                    └─────────────┘
```

### Data Flow

1. **Installation**: User installs GitHub App → OAuth token stored
2. **Webhook Event**: Push/PR received → AnalysisRun created
3. **Analysis**: Background job runs Ruff + ESLint
4. **Storage**: Results stored in AnalysisResult table
5. **Display**: Frontend queries API and shows results

---

## Project Structure

```
agi-engineer/
├── docs/
│   ├── v1/                              # V1 Documentation
│   │   ├── README.md
│   │   ├── COMPLETE.md
│   │   └── ARCHITECTURE.md
│   └── v2/                              # V2 Documentation (You are here)
│       ├── README.md                    # This file
│       ├── 01-PHASE1-FOUNDATION.md
│       ├── 02-PHASE2-OAUTH-WEBHOOKS.md
│       ├── 03-PHASE3-ANALYSIS.md
│       ├── 04-PHASE4-DASHBOARD.md
│       ├── 05-PHASE5-DEPLOYMENT.md
│       ├── ARCHITECTURE.md
│       ├── API-REFERENCE.md
│       ├── DATABASE.md
│       ├── DEPLOYMENT.md
│       └── TROUBLESHOOTING.md
│
├── backend/
│   ├── app/
│   │   ├── main.py                      # FastAPI app factory
│   │   ├── config.py                    # Settings from .env
│   │   ├── db.py                        # Database connection
│   │   ├── security.py                  # OAuth & JWT & webhooks
│   │   ├── v1_engine.py                 # V1 analysis wrapper
│   │   │
│   │   ├── models/                      # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── installation.py          # GitHub app installations
│   │   │   ├── repository.py            # Tracked repositories
│   │   │   ├── analysis_run.py          # Analysis executions
│   │   │   └── analysis_result.py       # Individual issues
│   │   │
│   │   ├── routers/                     # API endpoint handlers
│   │   │   ├── __init__.py
│   │   │   ├── health.py                # Health check
│   │   │   ├── oauth.py                 # OAuth endpoints
│   │   │   ├── webhooks.py              # GitHub webhook handler
│   │   │   ├── installations.py         # Installation management
│   │   │   └── analysis.py              # Analysis API
│   │   │
│   │   ├── schemas.py                   # Pydantic request/response models
│   │   └── __init__.py
│   │
│   ├── tests/
│   │   ├── test_oauth.py
│   │   ├── test_webhooks.py
│   │   ├── test_analysis.py
│   │   └── conftest.py
│   │
│   ├── requirements.txt
│   ├── .env.example
│   └── main.py                          # Entry point
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx                     # Root redirect
│   │   ├── layout.tsx                   # Root layout
│   │   │
│   │   ├── auth/
│   │   │   └── page.tsx                 # OAuth login & callback
│   │   │
│   │   ├── dashboard/
│   │   │   └── page.tsx                 # Dashboard home
│   │   │
│   │   └── runs/
│   │       ├── page.tsx                 # Runs list
│   │       └── [id]/
│   │           └── page.tsx             # Run details
│   │
│   ├── components/
│   │   ├── ui.tsx                       # Shared components
│   │   │   ├── Header
│   │   │   ├── StatusBadge
│   │   │   ├── CategoryBadge
│   │   │   ├── Loading
│   │   │   ├── Error
│   │   │   └── EmptyState
│   │   └── ...
│   │
│   ├── lib/
│   │   └── api.ts                       # API client + React hooks
│   │       ├── Interfaces (AnalysisRun, Result, etc)
│   │       ├── Fetch functions
│   │       ├── useRunDetail() hook
│   │       └── useRuns() hook
│   │
│   ├── public/                          # Static assets
│   ├── styles/                          # Tailwind CSS
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── next.config.js
│   └── .env.local.example
│
├── docker-compose.yml                   # Local development stack
├── Dockerfile                           # Backend image
├── .github/
│   └── workflows/
│       └── deploy.yml                   # CI/CD pipeline
│
├── README.md                            # Root documentation
├── LICENSE
└── .gitignore
```

---

## Features

### Phase 1: Foundation ✅
- [x] FastAPI backend with PostgreSQL
- [x] Next.js frontend with TypeScript
- [x] Docker Compose for local development
- [x] Database models (Installation, Repository, AnalysisRun, AnalysisResult)
- [x] Health check endpoints

### Phase 2: OAuth & Webhooks ✅
- [x] GitHub App OAuth flow
- [x] JWT token management
- [x] HMAC-SHA256 webhook signature validation
- [x] Webhook event handlers (push, PR, review)
- [x] Installation management
- [x] Repository tracking
- [x] 15+ API endpoints
- [x] CSRF protection with state parameter

### Phase 3: Analysis Integration ✅
- [x] V1 engine wrapper (Ruff + ESLint)
- [x] Background job processing
- [x] Repository cloning and analysis
- [x] Results persistence
- [x] Analysis status tracking
- [x] Error handling and cleanup
- [x] Multi-language support

### Phase 4: Dashboard ✅
- [x] OAuth login page
- [x] Dashboard home with stats
- [x] Runs list with filtering
- [x] Run detail with results table
- [x] Auto-refresh polling
- [x] Real-time status updates
- [x] Professional UI (TailwindCSS)
- [x] Type-safe React components

### Phase 5: Deployment (Upcoming)
- [ ] Docker production image
- [ ] GitHub Actions CI/CD
- [ ] Environment configuration
- [ ] Database migrations
- [ ] GitHub Marketplace listing

---

## System Design

### Authentication Flow

```
User clicks "Login"
    ↓
GET /oauth/authorize
    ↓
Returns authorization_url to GitHub
    ↓
User logs in with GitHub
    ↓
GitHub redirects to /oauth/callback?code=XXX&state=YYY
    ↓
Backend validates code and exchanges for access token
    ↓
Backend generates JWT token
    ↓
Returns JWT to frontend
    ↓
Frontend stores JWT in localStorage
    ↓
All subsequent requests include Authorization: Bearer <JWT>
```

### Analysis Workflow

```
1. Developer pushes code to repository
2. GitHub sends webhook to POST /webhooks/github
3. Webhook signature validated with HMAC-SHA256
4. AnalysisRun created with status=pending
5. POST /api/runs/{id}/execute queued
6. Background task starts immediately
7. Repository cloned to /tmp/agi-analysis-XXX
8. V1 Engine initialized (with V2 wrapper)
9. Ruff analysis runs on Python files
10. ESLint analysis runs on JS/TS files
11. Results normalized and stored in DB
12. AnalysisRun status updated to completed
13. Temporary directory cleaned up
14. Frontend polls /api/runs/{id} for results
15. Dashboard displays results with badges
```

### Security Features

| Feature | Implementation | Purpose |
|---------|----------------|---------|
| **OAuth** | GitHub OAuth 2.0 | User authentication |
| **JWT** | HS256 signed tokens | API request authentication |
| **CSRF** | State parameter + validation | Prevent CSRF attacks |
| **Webhooks** | HMAC-SHA256 signature | Verify GitHub events |
| **CORS** | Frontend URL whitelist | Prevent unauthorized access |
| **Tokens** | localStorage (browser only) | XSS mitigation via httpOnly not available in browser context |
| **Secrets** | Environment variables | Sensitive data protection |

---

## Database Schema

### Tables

#### `installation`
GitHub App installations on user accounts/organizations.

```sql
CREATE TABLE installation (
    id SERIAL PRIMARY KEY,
    github_installation_id INTEGER UNIQUE NOT NULL,
    github_account_id INTEGER NOT NULL,
    github_account_login VARCHAR(255) NOT NULL,
    access_token VARCHAR(500) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `repository`
Repositories tracked by the app.

```sql
CREATE TABLE repository (
    id SERIAL PRIMARY KEY,
    installation_id INTEGER NOT NULL REFERENCES installation(id),
    github_repo_id INTEGER UNIQUE NOT NULL,
    repo_full_name VARCHAR(255) NOT NULL,
    repo_url VARCHAR(500) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `analysis_run`
Individual analysis executions.

```sql
CREATE TABLE analysis_run (
    id SERIAL PRIMARY KEY,
    repository_id INTEGER NOT NULL REFERENCES repository(id),
    github_event VARCHAR(50) NOT NULL,
    github_branch VARCHAR(255) NOT NULL,
    github_commit_sha VARCHAR(255),
    pull_request_number INTEGER,
    status VARCHAR(50) NOT NULL,  -- pending, in_progress, completed, failed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT
);
```

#### `analysis_result`
Individual issues found during analysis.

```sql
CREATE TABLE analysis_result (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES analysis_run(id),
    file_path VARCHAR(500) NOT NULL,
    line_number INTEGER NOT NULL,
    code VARCHAR(50) NOT NULL,
    category VARCHAR(50) NOT NULL,  -- safe, review, suggestion
    message TEXT NOT NULL,
    is_fixed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Relationships

```
Installation (1) ──── (Many) Repository
     │
     └─── (Many) AnalysisRun ──── (Many) AnalysisResult
                                        (individual issues)
```

---

## API Reference

### Authentication

#### GET `/oauth/authorize`
Initiate GitHub OAuth flow.

**Response:**
```json
{
  "authorization_url": "https://github.com/login/oauth/authorize?client_id=...",
  "state": "uuid-for-csrf"
}
```

#### GET `/oauth/callback?code=CODE&state=STATE`
GitHub OAuth callback.

**Response:**
```json
{
  "token": "jwt-token-here",
  "user": "github-username",
  "installation_id": 123,
  "message": "Successfully authenticated"
}
```

#### POST `/oauth/refresh`
Refresh JWT token.

**Request:**
```json
{
  "current_token": "existing-jwt-token"
}
```

**Response:**
```json
{
  "token": "new-jwt-token"
}
```

### Health & Status

#### GET `/health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-09T12:00:00Z"
}
```

### Webhooks

#### POST `/webhooks/github`
GitHub webhook events (push, pull_request, pull_request_review).

**Headers:**
- `X-Hub-Signature-256`: HMAC-SHA256 signature

**Response:**
```json
{
  "status": "received",
  "event": "push",
  "repository": "user/repo",
  "run_id": 1
}
```

### Installation Management

#### GET `/api/installations`
List user's installations.

**Headers:**
- `Authorization: Bearer {jwt_token}`

**Response:**
```json
[
  {
    "id": 1,
    "github_account_login": "username",
    "repositories": [
      {
        "id": 1,
        "repo_full_name": "user/repo",
        "is_active": true
      }
    ]
  }
]
```

#### PUT `/api/installations/{id}`
Update installation settings.

**Request:**
```json
{
  "is_active": true
}
```

### Analysis API

#### POST `/api/runs/{id}/execute`
Trigger analysis execution (returns immediately, runs in background).

**Headers:**
- `Authorization: Bearer {jwt_token}`

**Response:**
```json
{
  "status": "queued",
  "run_id": 1,
  "message": "Analysis queued for execution"
}
```

#### GET `/api/runs?limit=50&status=completed`
List analysis runs with optional filters.

**Headers:**
- `Authorization: Bearer {jwt_token}`

**Query Parameters:**
- `limit`: Number of runs (default: 50)
- `status`: Filter by status (pending, in_progress, completed, failed)
- `repository_id`: Filter by repository
- `branch`: Filter by branch

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
  }
]
```

#### GET `/api/runs/{id}`
Get run details with all results.

**Headers:**
- `Authorization: Bearer {jwt_token}`

**Response:**
```json
{
  "id": 1,
  "event": "push",
  "branch": "main",
  "commit_sha": "abc123",
  "status": "completed",
  "total_results": 5,
  "created_at": "2026-01-09T12:00:00Z",
  "started_at": "2026-01-09T12:00:10Z",
  "completed_at": "2026-01-09T12:01:00Z",
  "results": [
    {
      "id": 1,
      "file_path": "src/main.py",
      "line_number": 15,
      "code": "E501",
      "category": "review",
      "message": "line too long"
    }
  ]
}
```

#### GET `/api/repositories/{id}/health`
Get repository health metrics.

**Headers:**
- `Authorization: Bearer {jwt_token}`

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

## Frontend Guide

### Pages

#### `/auth` - Authentication
- GitHub OAuth login button
- Callback handler (exchanges code for JWT)
- Stores token in localStorage
- Beautiful gradient UI

#### `/dashboard` - Dashboard Home
- Welcome message
- Stats cards (total runs, completed, failed, success rate)
- Secondary metrics (total issues, pending)
- Recent runs table (last 10)
- "View All" link to runs page

#### `/runs` - Runs List
- Status filter dropdown
- Refresh button
- Full table of all runs (paginated, limit 100)
- Columns: ID, Event, Branch, Status badge, Issues, Created date, View link
- Responsive design

#### `/runs/[id]` - Run Details
- Back button
- Run summary card
- Auto-refresh toggle (for pending/in-progress runs)
- Results table with all issues
- Columns: File, Line, Code, Category badge, Message
- Real-time polling (5s interval)

### React Hooks

#### `useRunDetail(runId, token)`
Polls for run details, updates every 5 seconds for pending/in-progress runs.

```typescript
const { run, loading, error, refetch } = useRunDetail(123, jwt_token)

if (loading) return <Loading />
if (error) return <Error message={error} />
return (
  <div>
    <h1>Run #{run.id}</h1>
    <StatusBadge status={run.status} />
    <ResultsTable results={run.results} />
  </div>
)
```

#### `useRuns(params, token)`
Fetches list of runs, provides refresh function.

```typescript
const { runs, loading, error, refresh } = useRuns(
  { limit: 50, status: 'completed' },
  jwt_token
)

return (
  <>
    <button onClick={refresh}>Refresh</button>
    {runs.map(run => (
      <RunRow key={run.id} run={run} />
    ))}
  </>
)
```

### Shared Components

#### `<Header />`
- Logo and title
- Navigation links
- User menu with logout
- JWT token management

#### `<StatusBadge status={string} />`
- Pending: Yellow
- In Progress: Blue
- Completed: Green
- Failed: Red

#### `<CategoryBadge category={string} />`
- Safe: Green
- Review: Orange
- Suggestion: Blue

#### `<Loading />`
Animated spinner

#### `<Error message={string} />`
Red error box with message

#### `<EmptyState message={string} />`
Empty state message

---

## Setup & Configuration

### Environment Variables

#### Backend (`.env`)
```env
# GitHub App (create at https://github.com/settings/apps/new)
GITHUB_APP_ID=123456
GITHUB_APP_PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----
GITHUB_CLIENT_ID=abc123
GITHUB_CLIENT_SECRET=secret123

# Security
JWT_SECRET_KEY=your-super-secret-jwt-key-here
WEBHOOK_SECRET=your-webhook-secret-here

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/agi_engineer_v2

# API
API_HOST=0.0.0.0
API_PORT=8000
API_ENV=development

# Frontend
FRONTEND_URL=http://localhost:3000

# AI Analysis
GROQ_API_KEY=your-groq-api-key
```

#### Frontend (`.env.local`)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api
NEXT_PUBLIC_GITHUB_CLIENT_ID=abc123
```

### GitHub App Setup

1. Go to https://github.com/settings/apps/new
2. Fill in "Application name": `AGI Engineer`
3. Set "Homepage URL": `http://localhost:3000` (or production URL)
4. **Important**: Enable "Request user authorization during installation"
5. Set "Authorization callback URL": `http://localhost:8000/oauth/callback`
6. Under "Webhooks", enable and set URL: `http://localhost:8000/webhooks/github`
7. Under "Webhook events", select:
   - Push
   - Pull request
   - Pull request review
8. Set "Repository permissions":
   - Contents: Read
   - Pull requests: Read
9. Set "User permissions":
   - None required
10. Generate private key
11. Copy values to `.env`

---

## Running Locally

### Prerequisites
- Python 3.8+
- Node.js 18+
- PostgreSQL 12+
- Git

### Step 1: Clone Repository
```bash
git clone https://github.com/yourusername/agi-engineer.git
cd agi-engineer
```

### Step 2: Start PostgreSQL
```bash
# Using Docker
docker run -d \
  --name postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgres:15

# Or using Docker Compose
docker-compose up -d postgres
```

### Step 3: Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your values

# Run migrations (if using Alembic)
# alembic upgrade head

# Start server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 4: Frontend Setup (new terminal)
```bash
cd frontend

# Install dependencies
npm install

# Setup environment
cp .env.local.example .env.local
# Edit .env.local with your values

# Start dev server
npm run dev
```

### Step 5: Access Application
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs (Swagger)

### Step 6: Test GitHub Integration
1. Visit http://localhost:3000
2. Click "Login with GitHub"
3. Authorize the app
4. Select repositories to analyze
5. Push code and watch analysis run

---

## Deployment

### Docker Build
```bash
# Build backend image
docker build -t agi-engineer-backend:latest backend/

# Build frontend image
docker build -t agi-engineer-frontend:latest frontend/
```

### Docker Compose (Production)
```yaml
version: '3.9'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: agi_engineer_v2
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  backend:
    image: agi-engineer-backend:latest
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://postgres:${DB_PASSWORD}@postgres:5432/agi_engineer_v2
      JWT_SECRET_KEY: ${JWT_SECRET_KEY}
      WEBHOOK_SECRET: ${WEBHOOK_SECRET}
      GITHUB_APP_ID: ${GITHUB_APP_ID}
      # ... other env vars
    depends_on:
      - postgres

  frontend:
    image: agi-engineer-frontend:latest
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: https://api.example.com
      NEXT_PUBLIC_GITHUB_CLIENT_ID: ${GITHUB_CLIENT_ID}

volumes:
  postgres_data:
```

### GitHub Actions CI/CD
```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to Production
        run: |
          # Deploy backend
          # Deploy frontend
          # Run migrations
```

### Deployment Platforms

#### Heroku
```bash
heroku create agi-engineer
heroku addons:create heroku-postgresql
git push heroku main
```

#### DigitalOcean
```bash
doctl apps create --spec app.yaml
```

#### AWS
```bash
# Use ECR for images
# ECS for container orchestration
# RDS for PostgreSQL
```

---

## Development

### Running Tests

#### Backend
```bash
cd backend

# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_oauth.py -v

# With coverage
pytest tests/ --cov=app
```

#### Frontend
```bash
cd frontend

# Run tests
npm test

# Watch mode
npm test -- --watch
```

### Code Quality

#### Backend
```bash
cd backend

# Type checking
mypy app/

# Linting
ruff check app/

# Formatting
black --check app/

# Fix all
ruff check --fix app/
black app/
```

#### Frontend
```bash
cd frontend

# Type checking
tsc --noEmit

# Linting
npm run lint

# Format
npm run format
```

### Database Migrations (using Alembic)

```bash
cd backend

# Create migration
alembic revision --autogenerate -m "Add new table"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## Troubleshooting

### Common Issues

#### "OAuth callback fails with 401"
**Problem**: JWT token validation fails  
**Solution**: Check `JWT_SECRET_KEY` matches between backend and frontend

#### "Webhook signature invalid"
**Problem**: Webhook events are rejected  
**Solution**: 
1. Verify `WEBHOOK_SECRET` in GitHub App settings matches `.env`
2. Check webhook URL is correct in GitHub settings
3. Ensure GitHub can reach your backend

#### "Analysis hangs or doesn't complete"
**Problem**: Background task never finishes  
**Solution**:
1. Check `/tmp/agi-analysis-*` directories are being cleaned up
2. Verify Groq API key is valid
3. Check PostgreSQL connection
4. Look at server logs for errors

#### "Frontend can't reach backend API"
**Problem**: CORS error in browser console  
**Solution**:
1. Verify `FRONTEND_URL` in backend `.env` matches frontend URL
2. Check `NEXT_PUBLIC_API_URL` in frontend `.env.local` is correct
3. Ensure backend is running and accessible

#### "Database connection fails"
**Problem**: "cannot connect to PostgreSQL"  
**Solution**:
1. Verify PostgreSQL is running: `docker ps`
2. Check `DATABASE_URL` format: `postgresql://user:password@host:port/dbname`
3. Test connection: `psql $DATABASE_URL`

#### "Analysis results not appearing"
**Problem**: Runs stay in "pending" status  
**Solution**:
1. Check backend logs for errors
2. Verify Ruff/ESLint are installed
3. Check repository is being cloned to `/tmp/agi-analysis-*`
4. Look for temp directory cleanup issues

### Debug Mode

#### Backend Debug
```bash
export DEBUG=1
python -m uvicorn app.main:app --reload --log-level debug
```

#### Frontend Debug
```bash
export DEBUG=1
npm run dev
```

### Getting Help

1. Check logs:
   ```bash
   # Backend logs
   docker logs agi-engineer-backend
   
   # Frontend logs
   npm run dev
   ```

2. Check database:
   ```bash
   psql $DATABASE_URL
   
   # List tables
   \dt
   
   # Check runs
   SELECT * FROM analysis_run LIMIT 5;
   ```

3. Test API:
   ```bash
   # Get OAuth URL
   curl http://localhost:8000/oauth/authorize
   
   # Check health
   curl http://localhost:8000/health
   ```

4. GitHub Actions:
   - Check workflow runs in GitHub UI
   - Look at logs for deployment issues

---

## Summary

**V2.0 is a complete, production-ready GitHub App** featuring:

✅ **Backend**: FastAPI + PostgreSQL  
✅ **Frontend**: Next.js + TypeScript  
✅ **Security**: OAuth 2.0 + JWT + HMAC  
✅ **Analysis**: Ruff + ESLint integration  
✅ **Webhooks**: Real-time event handling  
✅ **Dashboard**: Professional web UI  
✅ **Deployment**: Docker + CI/CD ready

Get started today and start improving your code quality automatically!

---

## Phase Documentation

For detailed information about each phase:

- [Phase 1: Foundation](./01-PHASE1-FOUNDATION.md) - Project structure, database, config
- [Phase 2: OAuth & Webhooks](./02-PHASE2-OAUTH-WEBHOOKS.md) - Authentication, events
- [Phase 3: Analysis Integration](./03-PHASE3-ANALYSIS.md) - V1 engine, background jobs
- [Phase 4: Dashboard](./04-PHASE4-DASHBOARD.md) - Frontend pages, components
- [Phase 5: Deployment](./05-PHASE5-DEPLOYMENT.md) - Production setup & cloud deployment
- [Testing & QA](./06-TESTING-QA.md) - Unit, integration, E2E tests, API docs
- [Operations & Maintenance](./07-OPERATIONS.md) - Monitoring, maintenance, incident response

---

## Quick Links

**Getting Started:**
- [Quick Start](#quick-start) - 5 minute setup
- [Running Locally](#running-locally) - Development environment
- [API Documentation](./06-TESTING-QA.md#api-documentation) - API endpoints

**Deployment:**
- [Docker Setup](./05-PHASE5-DEPLOYMENT.md#docker-deployment) - Container deployment
- [Cloud Platforms](./05-PHASE5-DEPLOYMENT.md#cloud-platform-deployment) - AWS, Heroku, DigitalOcean
- [Production Checklist](./05-PHASE5-DEPLOYMENT.md#pre-deployment-checklist) - Before going live

**Testing:**
- [Backend Tests](./06-TESTING-QA.md#backend-testing) - pytest unit and integration
- [Frontend Tests](./06-TESTING-QA.md#frontend-testing) - Jest and React Testing Library
- [E2E Tests](./06-TESTING-QA.md#integration-testing) - Cypress full user flows

**Operations:**
- [Monitoring](./07-OPERATIONS.md#monitoring-dashboard) - Prometheus, Grafana, alerts
- [Maintenance](./07-OPERATIONS.md#maintenance-tasks) - Database, backups, certificates
- [Incidents](./07-OPERATIONS.md#incident-response) - Response playbooks, escalation
- [Performance](./05-PHASE5-DEPLOYMENT.md#performance-optimization) - Database, caching, optimization
- [Troubleshooting](./05-PHASE5-DEPLOYMENT.md#troubleshooting) - Common issues and fixes

---

## License

MIT - Free to use and modify

## Support

For issues, questions, or contributions, please open an issue or pull request on GitHub.
