# V2.0 Phase 1: Foundation & Project Setup

## Overview

Phase 1 establishes the complete project structure, database schema, and foundational infrastructure for V2.0. This phase creates 31 files including backend API structure, frontend framework, database models, and Docker configuration.

**Duration**: Completed in initial setup  
**Deliverables**: 31 files created  
**Commit**: 15d776c

---

## What Was Built

### Backend Architecture (FastAPI)

```
backend/
├── app/
│   ├── main.py                    # FastAPI application factory
│   ├── config.py                  # Configuration management
│   ├── db.py                      # Database connection & session
│   ├── security.py                # OAuth & JWT management
│   ├── v1_engine.py               # V1 analysis wrapper
│   ├── schemas.py                 # Pydantic models
│   │
│   ├── models/                    # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── installation.py        # GitHub app installations
│   │   ├── repository.py          # Tracked repositories
│   │   ├── analysis_run.py        # Analysis executions
│   │   └── analysis_result.py     # Individual issues found
│   │
│   ├── routers/                   # API endpoint handlers
│   │   ├── __init__.py
│   │   ├── health.py              # Health check endpoints
│   │   ├── oauth.py               # OAuth endpoints (Phase 2)
│   │   ├── webhooks.py            # Webhook handler (Phase 2)
│   │   ├── installations.py       # Installation management (Phase 2)
│   │   └── analysis.py            # Analysis API (Phase 3)
│   │
│   └── __init__.py
│
├── tests/
│   ├── conftest.py
│   ├── test_oauth.py
│   ├── test_webhooks.py
│   ├── test_analysis.py
│   └── __init__.py
│
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment template
├── main.py                        # Entry point
└── README.md
```

### Frontend Architecture (Next.js)

```
frontend/
├── app/
│   ├── page.tsx                   # Root page (redirects)
│   ├── layout.tsx                 # Root layout
│   ├── auth/
│   │   └── page.tsx               # OAuth login & callback
│   ├── dashboard/
│   │   └── page.tsx               # Dashboard home
│   └── runs/
│       ├── page.tsx               # Runs list
│       └── [id]/
│           └── page.tsx           # Run details
│
├── components/
│   ├── ui.tsx                     # Shared UI components
│   └── ...
│
├── lib/
│   └── api.ts                     # TypeScript API client
│
├── public/                        # Static files
├── styles/                        # Tailwind CSS
│
├── package.json
├── tsconfig.json
├── tailwind.config.js
├── next.config.js
├── jest.config.js
├── .env.local.example
└── README.md
```

### Database Schema

Four core tables:

#### 1. `installation`
Stores GitHub App installations on user/org accounts.

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

#### 2. `repository`
Tracks repositories within installations.

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

#### 3. `analysis_run`
Records each analysis execution.

```sql
CREATE TABLE analysis_run (
    id SERIAL PRIMARY KEY,
    repository_id INTEGER NOT NULL REFERENCES repository(id),
    github_event VARCHAR(50) NOT NULL,        -- push, pull_request, pull_request_review
    github_branch VARCHAR(255) NOT NULL,
    github_commit_sha VARCHAR(255),
    pull_request_number INTEGER,
    status VARCHAR(50) NOT NULL,              -- pending, in_progress, completed, failed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT
);
```

#### 4. `analysis_result`
Individual code issues found.

```sql
CREATE TABLE analysis_result (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES analysis_run(id),
    file_path VARCHAR(500) NOT NULL,
    line_number INTEGER NOT NULL,
    code VARCHAR(50) NOT NULL,
    category VARCHAR(50) NOT NULL,            -- safe, review, suggestion
    message TEXT NOT NULL,
    is_fixed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Configuration

#### FastAPI Setup (`app/main.py`)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AGI Engineer V2", version="2.0.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Route registration
app.include_router(health.router)
app.include_router(oauth.router)
# ... more routers
```

#### Environment Variables (`.env.example`)
```env
# GitHub App (register at https://github.com/settings/apps/new)
GITHUB_APP_ID=
GITHUB_APP_PRIVATE_KEY=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=

# Security
JWT_SECRET_KEY=
WEBHOOK_SECRET=

# Database
DATABASE_URL=postgresql://localhost/agi_engineer_v2

# API
API_HOST=0.0.0.0
API_PORT=8000
API_ENV=development

# Frontend
FRONTEND_URL=http://localhost:3000

# AI
GROQ_API_KEY=
```

#### Next.js Configuration (`next.config.js`)
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  typescript: {
    strict: true,
  },
}

module.exports = nextConfig
```

### Docker Configuration

#### `docker-compose.yml`
```yaml
version: '3.9'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: agi_engineer_v2
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    depends_on:
      - postgres
    environment:
      DATABASE_URL: postgresql://postgres:postgres@postgres:5432/agi_engineer_v2

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend

volumes:
  postgres_data:
```

#### `backend/Dockerfile`
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app/ app/
COPY main.py .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### `frontend/Dockerfile`
```dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm install

COPY . .

ENV NEXT_PUBLIC_API_URL=http://localhost:8000/api

RUN npm run build

CMD ["npm", "start"]
```

---

## Technology Stack

### Backend
- **Framework**: FastAPI 0.109.0
- **Database**: PostgreSQL 15
- **ORM**: SQLAlchemy 2.0
- **Server**: Uvicorn 0.27.0
- **Python**: 3.11+

### Frontend
- **Framework**: Next.js 15
- **Language**: TypeScript 5.3
- **UI Framework**: React 19
- **Styling**: Tailwind CSS 3.4
- **Build**: npm/webpack

### DevOps
- **Containerization**: Docker 24.0
- **Orchestration**: Docker Compose 2.20

---

## Key Concepts

### Database Relationships
```
Installation (1) ──── (Many) Repository
    │
    └─── (Many) AnalysisRun ──── (Many) AnalysisResult
```

- One installation can have multiple repositories
- One repository can have multiple analysis runs
- One run can have multiple results (issues)

### API Structure
```
/health                 → Health checks
/oauth/...              → Authentication (Phase 2)
/webhooks/...           → Event handlers (Phase 2)
/api/installations/...  → Installation management (Phase 2)
/api/runs/...           → Analysis operations (Phase 3)
/api/repositories/...   → Repository info (Phase 3)
```

### Frontend Structure
- Single Page Application (SPA)
- Client-side routing with Next.js
- Server-side rendering where needed
- Static generation for performance

---

## What's Included

✅ Complete project structure  
✅ Database schema with 4 tables  
✅ FastAPI application factory  
✅ Next.js app setup  
✅ Docker and Docker Compose  
✅ Environment configuration  
✅ Typescript setup  
✅ TailwindCSS styling  
✅ API routing structure  
✅ Health check endpoints  
✅ CORS middleware  
✅ Static file serving  
✅ Error handling middleware  

---

## What's Not Yet Included

⏳ OAuth implementation (Phase 2)  
⏳ Webhook handlers (Phase 2)  
⏳ Analysis engine (Phase 3)  
⏳ Dashboard pages (Phase 4)  
⏳ Production deployment (Phase 5)  

---

## Development

### Start Development Environment
```bash
# Terminal 1: Start database
docker-compose up postgres

# Terminal 2: Start backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload

# Terminal 3: Start frontend
cd frontend
npm install
npm run dev
```

### Access Points
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Database: localhost:5432

### Dependencies

#### Backend
- fastapi
- uvicorn
- sqlalchemy
- psycopg2
- pydantic
- python-dotenv

#### Frontend
- next
- react
- typescript
- tailwindcss
- axios

---

## Summary

Phase 1 establishes the complete foundation for V2.0:

- ✅ Scalable backend API structure
- ✅ Modern frontend framework
- ✅ Production-grade database schema
- ✅ Containerized development environment
- ✅ Environment configuration management
- ✅ Security best practices

Phase 1 is production-ready for the foundation. The next phases add OAuth, webhooks, analysis engine, and dashboard.

---

## Next Phase

→ [Phase 2: OAuth & Webhooks](./02-PHASE2-OAUTH-WEBHOOKS.md)

Add GitHub OAuth authentication and webhook event handling to enable app installation and real-time analysis triggers.
