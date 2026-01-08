# AGI Engineer - Complete Documentation

> **Automated Code Quality Analysis Tool**  
> From CLI (V1) to GitHub App (V2)

---

## 📖 Documentation Overview

This repository contains two major versions with comprehensive documentation:

| Version | Purpose | Status | Docs |
|---------|---------|--------|------|
| **V1** | Python CLI tool with Ruff + ESLint | ✅ Complete | [V1 Docs](./docs/v1/) |
| **V2** | GitHub App with web dashboard | ✅ Complete | [V2 Docs](./docs/v2/) |

---

## 🎯 Choose Your Version

### V1: CLI Tool
Perfect for:
- Local development
- CI/CD pipelines
- One-off analysis
- Docker containers
- Terminal workflows

**Access**: `docs/v1/`

```bash
# Example usage
python main.py --repo /path/to/repo --output report.json
```

### V2: GitHub App
Perfect for:
- GitHub integration
- Team collaboration
- Real-time webhooks
- Web dashboard
- Production deployment

**Access**: `docs/v2/`

```bash
# Deployed as GitHub App
# Access via web UI at https://your-domain.com
```

---

## 📚 Documentation Structure

```
docs/
├── v1/
│   ├── README.md                    # V1 Overview
│   ├── COMPLETE.md                  # Complete feature list
│   ├── ARCHITECTURE.md              # V1 architecture
│   └── ...
│
└── v2/
    ├── README.md                    # V2 Complete Guide (⭐ Start here)
    ├── INDEX.md                     # Navigation & learning path
    ├── 01-PHASE1-FOUNDATION.md      # Database & structure
    ├── 02-PHASE2-OAUTH-WEBHOOKS.md  # Authentication & events
    ├── 03-PHASE3-ANALYSIS.md        # Analysis engine
    ├── 04-PHASE4-DASHBOARD.md       # Frontend UI
    └── 05-PHASE5-DEPLOYMENT.md      # Production setup
```

---

## 🚀 Quick Start by Version

### V1: CLI Tool

**Read**: `docs/v1/README.md` (5 minutes)

```bash
# Install
pip install -r requirements.txt

# Run
python main.py --repo /path/to/repo

# Output
{
  "total_issues": 42,
  "issues": [...]
}
```

### V2: GitHub App

**Read**: `docs/v2/README.md` (15 minutes)

```bash
# 1. Clone repository
git clone https://github.com/yourusername/agi-engineer.git
cd agi-engineer

# 2. Start backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload

# 3. Start frontend (new terminal)
cd frontend
npm install
npm run dev

# 4. Visit http://localhost:3000
```

---

## 📋 Documentation by Topic

### Getting Started
- **New to project?** → Read [V2 README](./docs/v2/README.md)
- **CLI tool?** → Read [V1 README](./docs/v1/README.md)
- **Want overview?** → Read this file
- **Learning path?** → See [V2 Index](./docs/v2/INDEX.md)

### Architecture & Design
- **V1 Architecture** → [docs/v1/ARCHITECTURE.md](./docs/v1/)
- **V2 Architecture** → [V2 README > Architecture](./docs/v2/README.md#architecture-overview)
- **Database Schema** → [Phase 1 Foundation](./docs/v2/01-PHASE1-FOUNDATION.md#database-schema)
- **Data Flow** → Each phase document has examples

### API Reference
- **V1 CLI** → [V1 Complete](./docs/v1/COMPLETE.md)
- **V2 REST API** → [V2 README > API Reference](./docs/v2/README.md#api-reference)
- **V2 Auth** → [Phase 2: OAuth & Webhooks](./docs/v2/02-PHASE2-OAUTH-WEBHOOKS.md#api-endpoints)
- **V2 Analysis** → [Phase 3: Analysis Integration](./docs/v2/03-PHASE3-ANALYSIS.md#api-endpoints)

### Setup & Configuration
- **V1 Setup** → [V1 README](./docs/v1/README.md)
- **V2 Setup** → [V2 README > Setup & Configuration](./docs/v2/README.md#setup--configuration)
- **Environment Variables** → Each phase has `.env.example`
- **Docker Setup** → [Phase 1: Foundation > Docker](./docs/v2/01-PHASE1-FOUNDATION.md#docker-configuration)

### Deployment
- **V1 Deployment** → [V1 Complete](./docs/v1/COMPLETE.md)
- **V2 Deployment** → [V2 README > Deployment](./docs/v2/README.md#deployment)
- **Docker Compose** → [Phase 1: Foundation](./docs/v2/01-PHASE1-FOUNDATION.md#docker-configuration)
- **CI/CD** → [V2 README > GitHub Actions](./docs/v2/README.md#github-actions-cicd)

### Troubleshooting
- **V1 Issues** → [V1 README](./docs/v1/README.md#troubleshooting)
- **V2 Issues** → [V2 README > Troubleshooting](./docs/v2/README.md#troubleshooting)
- **Common Errors** → See specific phase documentation

---

## 🏗️ Architecture Comparison

### V1: Standalone CLI
```
Input: Directory path
  ↓
Ruff Analysis (Python)
ESLint Analysis (JS/TS)
  ↓
Groq API Analysis (AI enhancement)
  ↓
Output: JSON report
```

### V2: GitHub App
```
GitHub Event (Push, PR)
  ↓
Webhook Receiver (HMAC validated)
  ↓
OAuth Authentication (JWT tokens)
  ↓
Background Analysis (Ruff + ESLint)
  ↓
Database Storage (PostgreSQL)
  ↓
Web Dashboard (Next.js UI)
```

---

## 📊 Statistics

### V1: CLI Tool
- **Language**: Python 3.13
- **Lines of Code**: 2,500+
- **Files**: 30+
- **Tests**: 19
- **Linters**: Ruff + ESLint
- **Status**: Production-ready ✅

### V2: GitHub App
- **Backend**: Python (FastAPI)
- **Frontend**: TypeScript (Next.js)
- **Database**: PostgreSQL
- **Lines of Code**: 2,500+
- **Files**: 50+
- **Endpoints**: 14+
- **Features**: OAuth, webhooks, analysis, dashboard
- **Status**: Production-ready ✅

### Total
- **Combined Code**: 5,000+ lines
- **Combined Files**: 80+
- **Documentation**: 3,500+ lines
- **Total**: 8,500+ lines

---

## 🔄 Migration: V1 → V2

If you have V1 working, here's how V2 builds on it:

| Aspect | V1 | V2 |
|--------|----|----|
| **Input** | Local directory | GitHub webhook |
| **Trigger** | Manual (CLI) | Automatic (webhook) |
| **Storage** | JSON file | PostgreSQL DB |
| **Display** | Console output | Web dashboard |
| **Auth** | None | GitHub OAuth |
| **Team** | Single user | Multi-user/org |
| **History** | Single run | All runs tracked |
| **Scale** | Single machine | Cloud-ready |

---

## 💡 Use Cases

### V1: CLI Tool
```bash
# Local development
python main.py --repo .

# CI/CD pipeline
python main.py --repo $GITHUB_WORKSPACE --format json

# Docker container
docker run -v $(pwd):/repo agi-engineer python main.py --repo /repo

# Custom scripting
python -c "from main import analyze; analyze('/path/to/repo')"
```

### V2: GitHub App
```
1. Install app on GitHub repository
2. Push code or create PR
3. App automatically analyzes
4. Results appear in:
   - Web dashboard
   - GitHub PR comments (future feature)
   - Database records
   - API endpoints
```

---

## 🎓 Learning Paths

### Path 1: CLI User (30 minutes)
1. Read [V1 README](./docs/v1/README.md)
2. Install V1
3. Run example: `python main.py --repo .`
4. Check output: `cat report.json`

### Path 2: V2 Web User (1 hour)
1. Read [V2 Quick Start](./docs/v2/README.md#quick-start)
2. Follow local setup guide
3. Login with GitHub
4. View dashboard
5. Check analysis results

### Path 3: V1 Developer (2 hours)
1. Read [V1 README](./docs/v1/README.md)
2. Read [V1 Architecture](./docs/v1/ARCHITECTURE.md)
3. Clone repo and run tests
4. Explore codebase
5. Understand Ruff + ESLint integration

### Path 4: V2 Developer (4 hours)
1. Read [V2 README](./docs/v2/README.md)
2. Read [V2 Index](./docs/v2/INDEX.md)
3. Read Phase 1-4 docs (1 hour each)
4. Clone repo and run locally
5. Explore backend API
6. Explore frontend components
7. Understand complete flow

### Path 5: V2 DevOps (2 hours)
1. Read [V2 Deployment](./docs/v2/README.md#deployment)
2. Understand Docker setup
3. Set up environment variables
4. Configure GitHub Actions (if deploying)
5. Deploy to your platform

---

## 🔗 External Resources

### V1 Tools
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [ESLint Documentation](https://eslint.org/)
- [Groq API Docs](https://console.groq.com/docs)

### V2 Technologies
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [TailwindCSS Documentation](https://tailwindcss.com/docs)
- [GitHub API Documentation](https://docs.github.com/en/developers)
- [GitHub Apps Documentation](https://docs.github.com/en/apps)

---

## ❓ FAQ

**Q: Should I use V1 or V2?**  
A: V1 for local CLI use. V2 for team/production use.

**Q: Can I use V1 and V2 together?**  
A: Yes! V2 internally uses V1 engine for analysis.

**Q: How do I upgrade from V1 to V2?**  
A: V2 is separate. Keep V1 for CLI, add V2 for GitHub integration.

**Q: Where's the V1 documentation?**  
A: See `docs/v1/` folder.

**Q: Where's the V2 documentation?**  
A: See `docs/v2/` folder or start with `docs/v2/README.md`.

**Q: How do I deploy V2?**  
A: See `docs/v2/README.md#deployment` section.

**Q: Are there tests?**  
A: Yes! V1 has 19 tests. V2 has tests in `backend/tests/`.

**Q: How do I contribute?**  
A: Open a PR with improvements. See CONTRIBUTING.md for details.

---

## 📞 Support

Having issues or questions?

1. **Check Documentation**: Read relevant docs/phase file
2. **Search Issues**: Look for similar problems on GitHub
3. **Open Issue**: Create new issue with details
4. **Discussion**: Use GitHub Discussions for questions

---

## 📝 Documentation Notes

All documentation is:
- ✅ Comprehensive (complete coverage)
- ✅ Clear (plain English, examples)
- ✅ Organized (logical structure)
- ✅ Current (updated with code)
- ✅ Searchable (descriptive headers)
- ✅ Accessible (beginner-friendly)

---

## 📜 License

All code and documentation is MIT licensed - free to use and modify.

---

## 🎯 Next Steps

**First time here?**
→ Go to [V2 README](./docs/v2/README.md)

**Want CLI tool?**
→ Go to [V1 README](./docs/v1/README.md)

**Learning to develop?**
→ Go to [V2 Index](./docs/v2/INDEX.md)

**Ready to deploy?**
→ Go to [V2 Deployment](./docs/v2/README.md#deployment)

---

**Last Updated**: January 9, 2026  
**Current Versions**: V1 Complete ✅ | V2 Complete ✅  
**Documentation Status**: Comprehensive ✅  
**Production Ready**: Yes ✅
