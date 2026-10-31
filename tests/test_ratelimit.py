"""Tests for the optional per-client rate limiter."""

from app.ratelimit import RateLimiter


def test_disabled_when_limit_is_zero():
    limiter = RateLimiter(0)
    assert limiter.enabled is False
    assert all(limiter.allow("1.2.3.4") for _ in range(1000))


def test_allows_up_to_the_limit_per_key():
    limiter = RateLimiter(2)
    assert limiter.allow("a") is True
    assert limiter.allow("a") is True
    assert limiter.allow("a") is False
    assert limiter.allow("b") is True


def test_window_resets(monkeypatch):
    clock = {"now": 0.0}
    monkeypatch.setattr("app.ratelimit.time.monotonic", lambda: clock["now"])
    limiter = RateLimiter(1)
    assert limiter.allow("a") is True
    assert limiter.allow("a") is False
    clock["now"] = 61.0
    assert limiter.allow("a") is True
