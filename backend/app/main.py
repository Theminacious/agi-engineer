"""FastAPI application factory and main entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import health, oauth, webhooks, installations, analysis, websockets, fixes, analytics, teams

# Create FastAPI app
app = FastAPI(
    title="AGI Engineer V2",
    description="GitHub App for automated code quality analysis",
    version="2.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
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


@app.get("/")
async def root() -> dict:
    """Root endpoint."""
    return {
        "message": "AGI Engineer V2 Backend",
        "docs": "/docs",
        "health": "/health",
    }
