"""FastAPI application factory and main entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import health, oauth, webhooks, installations, analysis, websockets, fixes, analytics, teams, repositories, github_webhooks, insights

app = FastAPI(
    title="AGI Engineer V2",
    description="GitHub App for automated code quality analysis",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "https://agi-engineer-6mcf.vercel.app",
        "https://agi-engineer-6mcf-git-main-theminacious-projects.vercel.app",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    from app.db.base import Base
    from app.db import engine
    Base.metadata.create_all(bind=engine)

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
app.include_router(github_webhooks.router)
app.include_router(insights.router)

@app.get("/")
async def root() -> dict:
    return {
        "message": "AGI Engineer V2 Backend",
        "docs": "/docs",
        "health": "/health",
    }
