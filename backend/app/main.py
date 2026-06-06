"""FastAPI application factory and main entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import health, oauth, webhooks, installations, analysis, websockets, fixes, analytics, teams, repositories, github_webhooks, insights

# Create FastAPI app
app = FastAPI(
    title="AGI Engineer V2",
    description="GitHub App for automated code quality analysis",
    version="2.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "https://agi-engineer-6mcf.vercel.app",
        "https://agi-engineer-6mcf-git-main-theminacious-projects.vercel.app",
        "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(oauth.router)
app.include_router(webhooks.router)
app.include_router(installations.router)
app.include_router(analysis.router)
app.include_router(websockets.router)
app.include_router(fixes.router)
app.include_router(analytics.router)
app.include_router(teams.router)
app.include_router(repositories.router)
app.include_router(github_webhooks.router)  # Phase 17
app.include_router(insights.router)  # Phase 18


@app.get("/")
async def root() -> dict:
    """Root endpoint."""
    return {
        "message": "AGI Engineer V2 Backend",
        "docs": "/docs",
        "health": "/health",
    }
