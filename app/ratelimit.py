"""Optional per-client rate limiting for the REST and MCP servers."""

from __future__ import annotations

import threading
import time


class RateLimiter:
    """Fixed-window limiter keyed by client address; disabled when the limit is 0."""

    def __init__(self, limit_per_minute: int = 0) -> None:
        self.limit = max(0, int(limit_per_minute))
        self._lock = threading.Lock()
        self._windows: dict[str, tuple[int, int]] = {}

    @property
    def enabled(self) -> bool:
        return self.limit > 0

    def allow(self, key: str) -> bool:
        """Return True while ``key`` stays under the per-minute limit."""
        if not self.enabled:
            return True
        window = int(time.monotonic() // 60)
        with self._lock:
            stored_window, count = self._windows.get(key, (window, 0))
            if stored_window != window:
                count = 0
            count += 1
            self._windows[key] = (window, count)
            if len(self._windows) > 4096:
                self._windows = {
                    item: value for item, value in self._windows.items() if value[0] == window
                }
            return count <= self.limit
