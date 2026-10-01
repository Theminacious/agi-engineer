"""FastAPI application factory and main entry point."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import SettingsValidationError, settings
from app.routers import health, oauth, webhooks, installations, analysis, websockets, fixes, analytics, teams, repositories, github_webhooks, insights

logger = logging.getLogger(__name__)

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
    if settings.is_production:
        missing = settings.missing_required_secrets()
        if missing:
            raise SettingsValidationError(
                "Refusing to start in environment "
                f"'{settings.api_env}': required secrets missing or empty: "
                + ", ".join(sorted(missing))
            )
    logger.info("Starting AGI Engineer V2 with config: %s", settings.safe_dict())
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
