"""In-memory TTL cache for captured snapshots."""

from __future__ import annotations

import hashlib
import threading
import time


def make_etag(data: bytes) -> str:
    """Return a short, quoted ETag for the given bytes."""
    return f'"{hashlib.sha256(data).hexdigest()[:16]}"'


class SnapshotCache:
    """Thread-safe TTL cache keyed by ``(room, width)``."""

    def __init__(self, ttl: float, max_items: int = 128) -> None:
        self._ttl = ttl
        self._max_items = max_items
        self._lock = threading.Lock()
        self._store: dict[tuple, tuple[float, bytes]] = {}

    def get(self, key: tuple) -> bytes | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            stored_at, data = entry
            if time.monotonic() - stored_at > self._ttl:
                del self._store[key]
                return None
            return data

    def set(self, key: tuple, data: bytes) -> None:
        with self._lock:
            self._store[key] = (time.monotonic(), data)
            while len(self._store) > self._max_items:
                oldest = min(self._store, key=lambda item: self._store[item][0])
                del self._store[oldest]

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
