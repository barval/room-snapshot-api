"""Flask REST API for the Room Snapshot API."""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, Response, abort, jsonify, request
from flask_cors import CORS
from flask_talisman import Talisman

from .auth import install_api_key_guard
from .cache import SnapshotCache, make_etag
from .capture import capture_snapshot, check_ffmpeg, probe_camera, stream_port
from .config import Camera, Config
from .i18n import resolve_lang, room_name, room_names, supported_languages

logger = logging.getLogger(__name__)


def parse_width(raw: str | None) -> int | None:
    """Validate the optional ``width`` query parameter."""
    if raw is None or raw == "":
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValueError("width must be an integer") from None
    if not 1 <= value <= 8000:
        raise ValueError("width must be between 1 and 8000")
    return value


def create_app(
    config_obj: type[Config] = Config,
    cameras: dict[str, Camera] | None = None,
    cache: SnapshotCache | None = None,
) -> Flask:
    """Build the Flask application. Fails closed if no API key is configured."""
    if not config_obj.API_KEY and not config_obj.DEBUG:
        raise RuntimeError("API_KEY is required (set API_KEY or enable FLASK_DEBUG)")

    app = Flask(__name__)
    app.config.from_object(config_obj)
    CORS(app, origins=config_obj.CORS_ORIGINS)
    Talisman(
        app,
        force_https=False,
        strict_transport_security=False,
        content_security_policy=False,
        frame_options="DENY",
    )
    install_api_key_guard(app, config_obj.API_KEY)

    app_cameras = cameras if cameras is not None else config_obj.load_cameras()
    app_i18n = config_obj.load_i18n()
    app_cache = cache if cache is not None else SnapshotCache(config_obj.SNAPSHOT_CACHE_TTL)
    ffmpeg_available = check_ffmpeg()

    def request_lang() -> str:
        supported = supported_languages(app_i18n, config_obj.DEFAULT_LANG)
        return resolve_lang(
            request.args.get("lang"),
            request.headers.get("Accept-Language"),
            config_obj.DEFAULT_LANG,
            supported,
        )

    @app.route("/snapshot/<room>", methods=["GET"])
    def snapshot(room: str):
        code = room.lower()
        camera = app_cameras.get(code)
        if camera is None:
            abort(404, description="Room not found")
        try:
            width = parse_width(request.args.get("width"))
        except ValueError as exc:
            abort(400, description=str(exc))

        key = (code, width)
        fresh = request.args.get("fresh") in {"1", "true", "yes"}
        data = None if fresh else app_cache.get(key)
        if data is None:
            data = capture_snapshot(camera.url, config_obj.SNAPSHOT_TIMEOUT, width)
            if not data:
                abort(502, description="Snapshot capture failed")
            app_cache.set(key, data)

        etag = make_etag(data)
        if_none_match = request.headers.get("If-None-Match", "")
        if if_none_match and etag in if_none_match:
            return Response(status=304, headers={"ETag": etag})
        response = Response(data, mimetype="image/jpeg")
        response.headers["ETag"] = etag
        response.headers["Cache-Control"] = f"public, max-age={int(config_obj.SNAPSHOT_CACHE_TTL)}"
        return response

    @app.route("/rooms", methods=["GET"])
    def list_rooms():
        lang = request_lang()
        return jsonify({code: room_name(code, lang, app_cameras, app_i18n) for code in app_cameras})

    @app.route("/rooms/<room>", methods=["GET"])
    def room_info(room: str):
        code = room.lower()
        camera = app_cameras.get(code)
        if camera is None:
            abort(404, description="Room not found")
        lang = request_lang()
        return jsonify(
            {
                "code": code,
                "name": room_name(code, lang, app_cameras, app_i18n),
                "names": room_names(code, app_cameras, app_i18n),
                "ip": camera.ip,
                "stream": camera.stream,
                "url": camera.masked_url(),
            }
        )

    @app.route("/health", methods=["GET"])
    def health_check():
        def probe(code: str) -> tuple[str, dict]:
            camera = app_cameras[code]
            reachable = probe_camera(camera.ip, stream_port(camera.stream), 1.0)
            return code, {"reachable": reachable}

        if app_cameras:
            with ThreadPoolExecutor(max_workers=min(8, len(app_cameras))) as pool:
                cameras_state = dict(pool.map(probe, list(app_cameras)))
        else:
            cameras_state = {}

        reachable = [state["reachable"] for state in cameras_state.values()]
        if not reachable or all(reachable):
            status = "healthy"
        elif any(reachable):
            status = "degraded"
        else:
            status = "unhealthy"

        return jsonify(
            {
                "status": status,
                "timestamp": time.time(),
                "cameras_loaded": len(app_cameras),
                "ffmpeg_available": ffmpeg_available,
                "cameras": cameras_state,
            }
        )

    @app.route("/info", methods=["GET"])
    def api_info():
        return jsonify(
            {
                "name": config_obj.API_TITLE,
                "version": config_obj.API_VERSION,
                "description": "API for capturing snapshots from room surveillance cameras",
                "languages": supported_languages(app_i18n, config_obj.DEFAULT_LANG),
                "endpoints": {
                    "rooms": {"method": "GET", "path": "/rooms", "description": "List all rooms"},
                    "room_info": {
                        "method": "GET",
                        "path": "/rooms/<room>",
                        "description": "Info for a single room",
                    },
                    "snapshot": {
                        "method": "GET",
                        "path": "/snapshot/<room>",
                        "description": "Capture a room snapshot (params: width, fresh, lang)",
                    },
                    "health": {"method": "GET", "path": "/health", "description": "Health check"},
                    "info": {"method": "GET", "path": "/info", "description": "API information"},
                },
            }
        )

    @app.errorhandler(400)
    def _bad_request(error):
        message = getattr(error, "description", "Bad request")
        return jsonify({"error": "Bad request", "message": message}), 400

    @app.errorhandler(401)
    def _unauthorized(error):
        return jsonify({"error": "Unauthorized"}), 401

    @app.errorhandler(404)
    def _not_found(error):
        return jsonify(
            {"error": "Not found", "message": getattr(error, "description", "Not found")}
        ), 404

    @app.errorhandler(502)
    def _bad_gateway(error):
        return jsonify(
            {"error": "Bad gateway", "message": getattr(error, "description", "Capture failed")}
        ), 502

    @app.errorhandler(500)
    def _server_error(error):
        return jsonify({"error": "Internal server error"}), 500

    return app


app = create_app()
