"""Health check and status endpoints."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "version": "2.0.0"}


@router.get("/status")
async def status() -> dict:
    """API status endpoint."""
    return {
        "api": "agi-engineer-v2",
        "version": "2.0.0",
        "status": "running",
    }
