"""Tests for the snapshot TTL cache."""

import time

from app.cache import SnapshotCache, make_etag


def test_get_missing_returns_none():
    cache = SnapshotCache(ttl=5)
    assert cache.get(("kuh", None)) is None


def test_set_then_get_returns_bytes():
    cache = SnapshotCache(ttl=5)
    cache.set(("kuh", None), b"jpeg")
    assert cache.get(("kuh", None)) == b"jpeg"


def test_entry_expires_after_ttl():
    cache = SnapshotCache(ttl=0.01)
    cache.set(("kuh", None), b"jpeg")
    time.sleep(0.02)
    assert cache.get(("kuh", None)) is None


def test_clear_removes_entries():
    cache = SnapshotCache(ttl=5)
    cache.set(("kuh", None), b"jpeg")
    cache.clear()
    assert cache.get(("kuh", None)) is None


def test_distinct_keys_are_isolated():
    cache = SnapshotCache(ttl=5)
    cache.set(("kuh", None), b"full")
    cache.set(("kuh", 320), b"small")
    assert cache.get(("kuh", None)) == b"full"
    assert cache.get(("kuh", 320)) == b"small"


def test_make_etag_is_stable_and_quoted():
    assert make_etag(b"x") == make_etag(b"x")
    assert make_etag(b"x").startswith('"')
    assert make_etag(b"x").endswith('"')


def test_make_etag_differs_for_different_data():
    assert make_etag(b"x") != make_etag(b"y")
