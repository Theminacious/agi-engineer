"""Health check and status endpoints."""

from fastapi import APIRouter

from app.services.cleanup import cleanup_stats

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


@router.get("/status/cleanup")
async def cleanup_status() -> dict:
    """Temp-resource cleanup counters.

    PRODUCTION_READINESS_AUDIT.md P2 #4: a failed rmtree used to be logged and
    forgotten, so leaked clone directories were invisible until the disk filled.
    Exposing the counters here gives that failure mode somewhere to show up.

    `failures` is the number to alert on — it is non-zero only when a directory
    is still on disk with nothing left to remove it.
    """
    stats = cleanup_stats()
    return {
        "cleanup": stats,
        "healthy": stats["failures"] == 0,
    }
