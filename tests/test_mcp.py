"""Tests for the MCP server tools and auth middleware."""

import asyncio
import importlib

import pytest

from app.cache import SnapshotCache
from app.config import Camera, Config

mcp_mod = importlib.import_module("app.mcp_server")

CAMERAS = {
    "kuh": Camera(
        code="kuh",
        ip="10.0.0.5",
        stream="554/s1",
        name="Kitchen",
        url="rtsp://u:p@10.0.0.5:554/s1",
        username="u",
        password="p",
    )
}


@pytest.fixture(autouse=True)
def configured():
    mcp_mod.configure(
        cameras=dict(CAMERAS),
        i18n={"kuh": {"ru": "Кухня", "en": "Kitchen"}},
        cache=SnapshotCache(9999),
    )


def _run(coro):
    return asyncio.run(coro)


def test_list_rooms_is_localized():
    assert mcp_mod.list_rooms("en") == {"kuh": "Kitchen"}
    assert mcp_mod.list_rooms("ru") == {"kuh": "Кухня"}


def test_get_snapshot_returns_jpeg_image(monkeypatch):
    monkeypatch.setattr(mcp_mod, "capture_snapshot", lambda *a, **k: b"\xff\xd8jpeg")
    content = mcp_mod.get_snapshot("kuh")
    assert content is not None
    assert content.type == "image"
    assert content.mime_type == "image/jpeg"


def test_get_snapshot_unknown_room_returns_none():
    assert mcp_mod.get_snapshot("xyz") is None


def test_get_snapshot_uses_cache(monkeypatch):
    calls = []

    def capture(*args, **kwargs):
        calls.append(1)
        return b"jpeg"

    monkeypatch.setattr(mcp_mod, "capture_snapshot", capture)
    mcp_mod.get_snapshot("kuh")
    mcp_mod.get_snapshot("kuh")
    assert len(calls) == 1


def test_room_info_masks_url():
    info = mcp_mod.room_info("kuh")
    assert info["name"] == "Kitchen"
    assert info["url"] == "rtsp://***:***@10.0.0.5:554/s1"


def test_health_reflects_probes(monkeypatch):
    monkeypatch.setattr(mcp_mod, "probe_camera", lambda *a, **k: False)
    body = mcp_mod.health()
    assert body["status"] == "unhealthy"
    assert body["cameras"]["kuh"]["reachable"] is False


def test_build_server_registers_tools():
    server = mcp_mod.build_server()
    tools = _run(server.list_tools())
    names = {tool.name for tool in tools}
    assert {"list_rooms", "get_snapshot", "room_info", "health"} <= names


class _DummyApp:
    def __init__(self):
        self.called = False

    async def __call__(self, scope, receive, send):
        self.called = True
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})


async def _invoke(middleware, scope):
    messages = []

    async def send(message):
        messages.append(message)

    async def receive():
        return {"type": "http.request"}

    await middleware(scope, receive, send)
    return messages


def test_middleware_rejects_request_without_key():
    app = _DummyApp()
    middleware = mcp_mod.ApiKeyMiddleware(app, "secret")
    messages = _run(_invoke(middleware, {"type": "http", "headers": []}))
    assert messages[0]["status"] == 401
    assert app.called is False


def test_middleware_allows_request_with_key():
    app = _DummyApp()
    middleware = mcp_mod.ApiKeyMiddleware(app, "secret")
    scope = {"type": "http", "headers": [(b"x-api-key", b"secret")]}
    messages = _run(_invoke(middleware, scope))
    assert app.called is True
    assert messages[0]["status"] == 200


def test_create_asgi_app_requires_key(monkeypatch):
    monkeypatch.setattr(Config, "API_KEY", "")
    with pytest.raises(RuntimeError):
        mcp_mod.create_asgi_app()
