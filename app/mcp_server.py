"""MCP server exposing camera tools to AI agents over streamable HTTP."""

from __future__ import annotations

import base64
import logging

from mcp.server import MCPServer
from mcp.types import ImageContent

from .auth import extract_api_key, is_authorized
from .cache import SnapshotCache
from .capture import capture_snapshot, check_ffmpeg
from .config import Camera, Config
from .health import camera_state, overall_status
from .i18n import resolve_lang, room_name, room_names, supported_languages

logger = logging.getLogger(__name__)

_cameras: dict[str, Camera] | None = None
_i18n: dict[str, dict[str, str]] | None = None
_cache: SnapshotCache | None = None
_ffmpeg: bool | None = None


def configure(
    cameras: dict[str, Camera] | None = None,
    i18n: dict[str, dict[str, str]] | None = None,
    cache: SnapshotCache | None = None,
) -> None:
    """Override server state (used by tests)."""
    global _cameras, _i18n, _cache, _ffmpeg
    _ffmpeg = None
    if cameras is not None:
        _cameras = cameras
    if i18n is not None:
        _i18n = i18n
    if cache is not None:
        _cache = cache


def _state() -> tuple[dict[str, Camera], dict[str, dict[str, str]], SnapshotCache]:
    global _cameras, _i18n, _cache
    if _cameras is None:
        _cameras = Config.load_cameras()
    if _i18n is None:
        _i18n = Config.load_i18n()
    if _cache is None:
        _cache = SnapshotCache(Config.SNAPSHOT_CACHE_TTL)
    return _cameras, _i18n, _cache


def _resolve(lang: str | None, i18n: dict[str, dict[str, str]]) -> str:
    supported = supported_languages(i18n, Config.DEFAULT_LANG)
    return resolve_lang(lang, None, Config.DEFAULT_LANG, supported)


def _ffmpeg_available() -> bool:
    global _ffmpeg
    if _ffmpeg is None:
        _ffmpeg = check_ffmpeg()
    return _ffmpeg


def list_rooms(lang: str | None = None) -> dict[str, str]:
    """List every camera room and its name in the requested language."""
    cameras, i18n, _ = _state()
    resolved = _resolve(lang, i18n)
    return {code: room_name(code, resolved, cameras, i18n) for code in cameras}


def get_snapshot(room: str, width: int | None = None, lang: str | None = None):
    """Capture the current JPEG frame from a room camera. Returns image content or None."""
    cameras, _, cache = _state()
    code = room.lower()
    camera = cameras.get(code)
    if camera is None:
        return None
    key = (code, width)
    data = cache.get(key)
    if data is None:
        data = capture_snapshot(camera.url, Config.SNAPSHOT_TIMEOUT, width)
        if not data:
            return None
        cache.set(key, data)
    return ImageContent(
        type="image",
        data=base64.b64encode(data).decode("ascii"),
        mime_type="image/jpeg",
    )


def room_info(room: str, lang: str | None = None) -> dict | None:
    """Return details for a room (code, localized name, all names, ip, stream, masked url)."""
    cameras, i18n, _ = _state()
    code = room.lower()
    camera = cameras.get(code)
    if camera is None:
        return None
    resolved = _resolve(lang, i18n)
    return {
        "code": code,
        "name": room_name(code, resolved, cameras, i18n),
        "names": room_names(code, cameras, i18n),
        "ip": camera.ip,
        "stream": camera.stream,
        "url": camera.masked_url(),
    }


def health() -> dict:
    """Report camera reachability and ffmpeg availability."""
    cameras, _, _ = _state()
    states = camera_state(cameras, 1.0)
    return {
        "status": overall_status(states),
        "cameras_loaded": len(cameras),
        "ffmpeg_available": _ffmpeg_available(),
        "cameras": states,
    }


def build_server() -> MCPServer:
    """Create the MCP server with all camera tools registered."""
    server = MCPServer("Room Snapshot API")
    server.add_tool(list_rooms, description="List all rooms and their localized names.")
    server.add_tool(
        get_snapshot,
        description="Capture the current JPEG frame from a room camera.",
        structured_output=False,
    )
    server.add_tool(room_info, description="Return details for a single room.")
    server.add_tool(health, description="Report camera reachability and ffmpeg availability.")
    return server


class ApiKeyMiddleware:
    """ASGI middleware enforcing the shared API key on MCP HTTP requests."""

    def __init__(self, app, api_key: str) -> None:
        self.app = app
        self.api_key = api_key

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        headers = {key.decode(): value.decode() for key, value in scope.get("headers", [])}
        if not is_authorized(extract_api_key(headers), self.api_key):
            body = b'{"error": "Unauthorized"}'
            await send(
                {
                    "type": "http.response.start",
                    "status": 401,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode()),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return
        await self.app(scope, receive, send)


def create_asgi_app():
    """Build the API-key protected ASGI application for the MCP server."""
    if not Config.API_KEY:
        raise RuntimeError("API_KEY is required to run the MCP server")
    server = build_server()
    return ApiKeyMiddleware(server.streamable_http_app(host="0.0.0.0"), Config.API_KEY)


def main() -> None:
    import uvicorn

    uvicorn.run(create_asgi_app(), host="0.0.0.0", port=Config.MCP_PORT)


if __name__ == "__main__":
    main()
