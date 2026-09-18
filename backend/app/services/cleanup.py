"""Temp-resource cleanup with failure accounting.

PRODUCTION_READINESS_AUDIT.md P2 #4 asks for a counter on cleanup failures.
Today a failed `rmtree` is logged at WARNING and nothing else, so a host slowly
filling with abandoned repository clones is indistinguishable from a healthy one
until it runs out of disk.

Two rules this module exists to enforce:

1. A cleanup failure is never hidden. `shutil.rmtree(path, ignore_errors=True)`
   discards the reason, the path, and the fact that it happened at all. Every
   call here records and logs instead.

2. A cleanup failure never replaces the caller's exception. These calls run in
   `finally` blocks, where raising would mask whatever sent us there, so
   `safe_rmtree` returns False rather than propagating.

Counters are in-process: there is no prometheus_client dependency in this
project, and adding one to satisfy an audit note would be a heavier change than
the note asks for. `cleanup_stats()` is exposed on `/health` so an operator can
scrape the same numbers, and swapping the body of `record_*` for a Prometheus
Counter later touches only this file.
"""

import logging
import os
import shutil
import threading
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# How many recent failures to describe in detail. Bounded on purpose: this
# module exists to stop a leak, so it must not grow one of its own on a host
# where cleanup fails repeatedly.
MAX_RETAINED_FAILURES = 20


class CleanupTracker:
    """Counts temp-resource cleanup attempts and failures.

    Cleanup runs from FastAPI background tasks and Celery workers, so the
    counters are guarded by a lock rather than relying on the GIL to make
    read-modify-write of the totals atomic.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._attempts = 0
        self._failures = 0
        self._failures_by_kind: Dict[str, int] = {}
        self._recent: List[Dict[str, str]] = []

    def record_success(self, kind: str) -> None:
        with self._lock:
            self._attempts += 1

    def record_failure(self, kind: str, path: str, error: str) -> None:
        with self._lock:
            self._attempts += 1
            self._failures += 1
            self._failures_by_kind[kind] = self._failures_by_kind.get(kind, 0) + 1
            self._recent.append({"kind": kind, "path": path, "error": error})
            # Keep the newest; older ones are already reflected in the totals.
            if len(self._recent) > MAX_RETAINED_FAILURES:
                del self._recent[:-MAX_RETAINED_FAILURES]

    def snapshot(self) -> Dict[str, Any]:
        """Current counters, safe to serialise into a health response."""
        with self._lock:
            return {
                "attempts": self._attempts,
                "failures": self._failures,
                "failures_by_kind": dict(self._failures_by_kind),
                "recent_failures": [dict(entry) for entry in self._recent],
            }

    def reset(self) -> None:
        """Clear all counters. For tests; not called by application code."""
        with self._lock:
            self._attempts = 0
            self._failures = 0
            self._failures_by_kind = {}
            self._recent = []


# Process-wide tracker. Module-level so every cleanup site reports to one place.
TRACKER = CleanupTracker()


def cleanup_stats() -> Dict[str, Any]:
    """Counters for the monitoring surface (see routers/health.py)."""
    return TRACKER.snapshot()


def safe_rmtree(path: Optional[str], kind: str) -> bool:
    """Remove a directory tree, recording the outcome. Never raises.

    Args:
        path: Directory to remove. None or a nonexistent path is a no-op that
            counts as neither success nor failure — nothing leaked.
        kind: Short label for what the directory was, so the counter can
            distinguish a failing PR clone from a failing v3 analysis workspace.

    Returns:
        True if the tree is gone (or was never there), False if it remains.
        False means disk was leaked and the counter has been incremented.
    """
    if not path:
        return True

    if not os.path.exists(path):
        return True

    try:
        shutil.rmtree(path)
    except Exception as exc:
        # ERROR, not WARNING: the tree is still on disk and nothing else will
        # come back for it, so this needs to reach whoever watches logs.
        TRACKER.record_failure(kind=kind, path=str(path), error=str(exc))
        logger.error(
            f"Cleanup failed ({kind}): {path} could not be removed and has "
            f"leaked: {exc}"
        )
        return False

    TRACKER.record_success(kind)
    logger.debug(f"Cleaned up ({kind}): {path}")
    return True
