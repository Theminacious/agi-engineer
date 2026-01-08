# AGI Engineer V2

**GitHub App for Automated Code Quality Analysis and Fixing**

V2.0 is the GitHub App foundation - bringing AGI Engineer from CLI to the cloud with OAuth, webhooks, and a web dashboard.

## 🚀 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Events (Push, PR)                 │
└──────────────────────────┬──────────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │   Webhook   │
                    │   Handler   │
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐      ┌──────▼──────┐     ┌────▼────┐
   │  OAuth  │      │   Analysis  │     │  API    │
   │  Router │      │   Endpoint  │     │ Routers │
   └────┬────┘      └──────┬──────┘     └────┬────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                    ┌──────▼──────────┐
                    │  V1 Core Engine │
                    │  (Ruff + ESLint)│
                    └──────┬──────────┘
                           │
                    ┌──────▼──────────┐
                    │   PostgreSQL    │
                    │   (Results DB)  │
                    └─────────────────┘
```

## 📦 Project Structure

```
agi-engineer/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── main.py         # FastAPI app factory
│   │   ├── config.py       # Settings from .env
│   │   ├── routers/        # API route handlers
│   │   │   ├── health.py   # /health endpoint
│   │   │   ├── oauth.py    # OAuth routes (TODO)
│   │   │   ├── webhooks.py # Webhook handler (TODO)
│   │   │   └── analysis.py # Analysis API (TODO)
│   │   ├── models/         # SQLAlchemy ORM models
│   │   │   ├── installation.py
│   │   │   ├── repository.py
│   │   │   ├── analysis_run.py
│   │   │   └── analysis_result.py
│   │   └── db/             # Database setup
│   ├── pyproject.toml      # Dependencies
│   ├── Dockerfile
│   └── main.py             # Entry point
│
├── frontend/               # Next.js frontend
│   ├── app/
│   │   ├── layout.tsx      # Root layout
│   │   └── page.tsx        # Home page
│   ├── components/         # React components
│   ├── package.json
│   ├── tsconfig.json
│   ├── Dockerfile
│   └── tailwind.config.ts
│
└── docker-compose.yml      # Full stack (DB + Backend + Frontend)
```

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# Clone repo
git clone https://github.com/Theminacious/agi-engineer.git
cd agi-engineer

# Copy example env
cp backend/.env.example backend/.env

# Edit with your GitHub App credentials
nano backend/.env

# Start everything
docker-compose up
```

- **Backend**: http://localhost:8000
- **Frontend**: http://localhost:3000
- **Database**: PostgreSQL on localhost:5432
- **API Docs**: http://localhost:8000/docs

### Option 2: Local Development

#### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# Setup .env
cp .env.example .env
export $(cat .env | xargs)

# Run migrations (when ready)
# alembic upgrade head

# Start API
python main.py
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

## ⚙️ Environment Variables

Create `backend/.env`:

```env
# GitHub App (register at github.com/settings/apps/new)
GITHUB_APP_ID=123456
GITHUB_APP_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----
GITHUB_CLIENT_ID=abc123def456
GITHUB_CLIENT_SECRET=your_client_secret

# Database
DATABASE_URL=postgresql://user:password@localhost/agi_engineer_v2

# Security
JWT_SECRET_KEY=your-super-secret-key-change-in-production
WEBHOOK_SECRET=your-webhook-secret-change-in-production

# AI
GROQ_API_KEY=gsk_xxx

# Frontend
FRONTEND_URL=http://localhost:3000
```

## 📚 API Endpoints

### Health

- `GET /health` - Health check
- `GET /status` - API status

### OAuth (Phase 2)

- `GET /oauth/authorize` - Start OAuth flow
- `GET /oauth/callback` - GitHub callback

### Webhooks (Phase 2)

- `POST /webhooks/github` - GitHub events

### Analysis (Phase 3)

- `POST /api/analyze` - Trigger analysis
- `GET /api/runs/{id}` - Get run results

## 🛠️ Development

### Run Tests

```bash
cd backend
pytest tests/ -v
```

### Type Checking

```bash
cd backend
mypy app/
```

### Code Quality

```bash
cd backend
ruff check .
black --check .
```

## 📋 V2 Features (Roadmap)

- [x] Phase 1: Project structure (✅ Done)
- [ ] Phase 2: GitHub OAuth + Webhooks
- [ ] Phase 3: Analysis integration (V1 core)
- [ ] Phase 4: Dashboard
- [ ] Phase 5: Deployment & marketplace

## 🔗 Related

- [V1 Documentation](./README.md) - CLI tool
- [V1 Summary](./V1_SUMMARY.md) - Complete feature list
- [Contributing](./CONTRIBUTING.md) - Development guide

## 📝 License

MIT - Free to use and modify
