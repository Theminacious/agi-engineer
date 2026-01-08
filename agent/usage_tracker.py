"""
Usage tracking and rate limiting for AI calls.
Stores timestamps in a local JSON file (~/.agi-engineer/usage.json).
"""
import os
import json
import time
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

DEFAULT_LIMIT = 10  # max calls per window
DEFAULT_WINDOW = 3600  # 1 hour in seconds
DEFAULT_STORAGE = os.path.expanduser("~/.agi-engineer/usage.json")


class UsageTracker:
    def __init__(self, limit: int = DEFAULT_LIMIT, window_seconds: int = DEFAULT_WINDOW, storage_path: str = DEFAULT_STORAGE):
        self.limit = limit
        self.window_seconds = window_seconds
        self.storage_path = storage_path
        self.data = self._load()

    def _load(self) -> dict:
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, "r") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load usage data: {e}")
        return {}

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            with open(self.storage_path, "w") as f:
                json.dump(self.data, f)
        except Exception as e:
            logger.warning(f"Failed to save usage data: {e}")

    def check_and_increment(self, key: str) -> Tuple[bool, int]:
        """Return (allowed, remaining). If allowed, increments the counter."""
        now = time.time()
        timestamps = self.data.get(key, [])
        # keep only events within window
        timestamps = [ts for ts in timestamps if now - ts < self.window_seconds]

        if len(timestamps) >= self.limit:
            remaining = int(self.window_seconds - (now - timestamps[0]))
            return False, remaining

        timestamps.append(now)
        self.data[key] = timestamps
        self._save()
        remaining = self.limit - len(timestamps)
        return True, remaining
