"""Tests for the Flask REST API."""

import importlib

import pytest

from app.app import create_app, parse_width
from app.cache import SnapshotCache
from app.config import Camera, Config

app_mod = importlib.import_module("app.app")

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
KEY = {"X-API-Key": "secret"}


class TestConfig(Config):
    API_KEY = "secret"
    DEBUG = False
    CORS_ORIGINS = []
    DEFAULT_LANG = "en"
    SNAPSHOT_CACHE_TTL = 5
    SNAPSHOT_TIMEOUT = 5
    RTSP_AUTH = ""

    @staticmethod
    def load_cameras(cameras_path=None, auth_path=None):
        return dict(CAMERAS)

    @staticmethod
    def load_i18n(path=None):
        return {"kuh": {"ru": "Кухня", "en": "Kitchen"}}


def make_client(monkeypatch, capture=None, probe=None):
    monkeypatch.setattr(app_mod, "check_ffmpeg", lambda: True)
    if capture is not None:
        monkeypatch.setattr(app_mod, "capture_snapshot", capture)
    if probe is not None:
        monkeypatch.setattr(app_mod, "probe_camera", probe)
    application = create_app(TestConfig, cameras=dict(CAMERAS), cache=SnapshotCache(9999))
    application.testing = True
    return application.test_client()


def test_all_endpoints_require_api_key(monkeypatch):
    client = make_client(monkeypatch, capture=lambda *a, **k: b"jpeg")
    for path in ("/rooms", "/info", "/health"):
        assert client.get(path).status_code == 401


def test_rooms_default_language_is_english(monkeypatch):
    client = make_client(monkeypatch)
    assert client.get("/rooms", headers=KEY).get_json() == {"kuh": "Kitchen"}


def test_rooms_lang_query(monkeypatch):
    client = make_client(monkeypatch)
    assert client.get("/rooms?lang=ru", headers=KEY).get_json() == {"kuh": "Кухня"}


def test_rooms_accept_language_header(monkeypatch):
    client = make_client(monkeypatch)
    response = client.get("/rooms", headers={**KEY, "Accept-Language": "ru"})
    assert response.get_json() == {"kuh": "Кухня"}


def test_room_info_has_names_and_masked_url(monkeypatch):
    client = make_client(monkeypatch)
    body = client.get("/rooms/kuh", headers=KEY).get_json()
    assert body["name"] == "Kitchen"
    assert body["names"]["en"] == "Kitchen"
    assert body["names"]["ru"] == "Кухня"
    assert body["url"] == "rtsp://***:***@10.0.0.5:554/s1"


def test_room_info_unknown_room_404(monkeypatch):
    client = make_client(monkeypatch)
    assert client.get("/rooms/xyz", headers=KEY).status_code == 404


def test_snapshot_returns_jpeg(monkeypatch):
    client = make_client(monkeypatch, capture=lambda *a, **k: b"\xff\xd8jpeg")
    response = client.get("/snapshot/kuh", headers=KEY)
    assert response.status_code == 200
    assert response.mimetype == "image/jpeg"
    assert response.data == b"\xff\xd8jpeg"


def test_snapshot_unknown_room_404(monkeypatch):
    client = make_client(monkeypatch)
    assert client.get("/snapshot/xyz", headers=KEY).status_code == 404


def test_snapshot_capture_failure_502(monkeypatch):
    client = make_client(monkeypatch, capture=lambda *a, **k: None)
    assert client.get("/snapshot/kuh", headers=KEY).status_code == 502


def test_snapshot_etag_returns_304(monkeypatch):
    client = make_client(monkeypatch, capture=lambda *a, **k: b"jpeg")
    etag = client.get("/snapshot/kuh", headers=KEY).headers["ETag"]
    response = client.get("/snapshot/kuh", headers={**KEY, "If-None-Match": etag})
    assert response.status_code == 304


def test_snapshot_uses_cache(monkeypatch):
    calls = []

    def capture(*args, **kwargs):
        calls.append(1)
        return b"jpeg"

    client = make_client(monkeypatch, capture=capture)
    client.get("/snapshot/kuh", headers=KEY)
    client.get("/snapshot/kuh", headers=KEY)
    assert len(calls) == 1


def test_snapshot_fresh_bypasses_cache(monkeypatch):
    calls = []

    def capture(*args, **kwargs):
        calls.append(1)
        return b"jpeg"

    client = make_client(monkeypatch, capture=capture)
    client.get("/snapshot/kuh", headers=KEY)
    client.get("/snapshot/kuh?fresh=1", headers=KEY)
    assert len(calls) == 2


def test_snapshot_width_validation(monkeypatch):
    client = make_client(monkeypatch, capture=lambda *a, **k: b"jpeg")
    assert client.get("/snapshot/kuh?width=abc", headers=KEY).status_code == 400
    assert client.get("/snapshot/kuh?width=0", headers=KEY).status_code == 400


def test_health_always_200_when_cameras_down(monkeypatch):
    client = make_client(monkeypatch, capture=lambda *a, **k: b"jpeg", probe=lambda *a, **k: False)
    response = client.get("/health", headers=KEY)
    assert response.status_code == 200
    assert response.get_json()["status"] == "unhealthy"


def test_health_healthy_when_cameras_reachable(monkeypatch):
    client = make_client(monkeypatch, capture=lambda *a, **k: b"jpeg", probe=lambda *a, **k: True)
    body = client.get("/health", headers=KEY).get_json()
    assert body["status"] == "healthy"
    assert body["cameras"]["kuh"]["reachable"] is True


def test_create_app_requires_api_key():
    class NoKeyConfig(TestConfig):
        API_KEY = ""
        DEBUG = False

    with pytest.raises(RuntimeError):
        create_app(NoKeyConfig, cameras={}, cache=SnapshotCache(1))


def test_parse_width():
    assert parse_width(None) is None
    assert parse_width("") is None
    assert parse_width("320") == 320
    with pytest.raises(ValueError):
        parse_width("abc")
    with pytest.raises(ValueError):
        parse_width("0")
    with pytest.raises(ValueError):
        parse_width("99999")
