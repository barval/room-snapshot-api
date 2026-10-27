"""Tests for configuration loading."""

import json

import pytest

from app.config import Camera, Config, build_rtsp_url, resolve_config_path


def _write(path, text):
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_build_rtsp_url_no_auth():
    assert build_rtsp_url("1.2.3.4", "554/s1", "") == "rtsp://1.2.3.4:554/s1"


def test_build_rtsp_url_with_auth():
    assert build_rtsp_url("1.2.3.4", "554/s1", "u:p") == "rtsp://u:p@1.2.3.4:554/s1"


def test_build_rtsp_url_encodes_special_characters():
    assert build_rtsp_url("1.2.3.4", "554/s1", "a@b:/#c") == "rtsp://a%40b:%2F%23c@1.2.3.4:554/s1"


def test_masked_url_hides_credentials():
    camera = Camera(
        code="kuh",
        ip="1.2.3.4",
        stream="554/s1",
        name="Kitchen",
        url="rtsp://u:p@1.2.3.4:554/s1",
        username="u",
        password="p",
    )
    assert camera.masked_url() == "rtsp://***:***@1.2.3.4:554/s1"


def test_masked_url_without_auth_is_unchanged():
    camera = Camera(code="kuh", ip="1.2.3.4", stream="554/s1", name="Kitchen", url="rtsp://1.2.3.4:554/s1")
    assert camera.masked_url() == "rtsp://1.2.3.4:554/s1"


def test_load_cameras_parses_and_falls_back_to_global_auth(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "RTSP_AUTH", "admin:x")
    conf = _write(tmp_path / "cameras.conf", "kuh=10.0.0.5:554/s1:Kitchen\n")
    cameras = Config.load_cameras(conf, str(tmp_path / "missing.auth"))
    assert cameras["kuh"].url == "rtsp://admin:x@10.0.0.5:554/s1"
    assert cameras["kuh"].name == "Kitchen"


def test_load_cameras_per_camera_auth_wins(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "RTSP_AUTH", "admin:x")
    conf = _write(tmp_path / "cameras.conf", "kuh=10.0.0.5:554/s1:Kitchen\n")
    auth = _write(tmp_path / "cameras.auth", "kuh=u2:p2\n")
    cameras = Config.load_cameras(conf, auth)
    assert cameras["kuh"].url == "rtsp://u2:p2@10.0.0.5:554/s1"


def test_load_cameras_without_credentials_has_no_userinfo(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "RTSP_AUTH", "")
    conf = _write(tmp_path / "cameras.conf", "kuh=10.0.0.5:554/s1:Kitchen\n")
    cameras = Config.load_cameras(conf, str(tmp_path / "missing.auth"))
    assert cameras["kuh"].url == "rtsp://10.0.0.5:554/s1"


def test_load_cameras_ignores_comments_and_blank_lines(tmp_path):
    conf = _write(tmp_path / "cameras.conf", "# comment\n\nkuh=10.0.0.5:554/s1:Kitchen\n")
    cameras = Config.load_cameras(conf, str(tmp_path / "missing.auth"))
    assert list(cameras) == ["kuh"]


def test_load_cameras_skips_invalid_line(tmp_path):
    conf = _write(tmp_path / "cameras.conf", "broken-line\nkuh=10.0.0.5:554/s1:Kitchen\n")
    cameras = Config.load_cameras(conf, str(tmp_path / "missing.auth"))
    assert list(cameras) == ["kuh"]


def test_load_cameras_missing_file_returns_empty(tmp_path):
    assert Config.load_cameras(str(tmp_path / "nope.conf"), str(tmp_path / "missing.auth")) == {}


def test_load_i18n_missing_file_returns_empty(tmp_path):
    assert Config.load_i18n(str(tmp_path / "nope.json")) == {}


def test_load_i18n_parses_and_lowercases(tmp_path):
    data = {"KUH": {"RU": "Кухня", "EN": "Kitchen"}}
    path = _write(tmp_path / "rooms.i18n.json", json.dumps(data))
    assert Config.load_i18n(path) == {"kuh": {"ru": "Кухня", "en": "Kitchen"}}


def test_load_i18n_broken_json_returns_empty(tmp_path):
    path = _write(tmp_path / "rooms.i18n.json", "{not json")
    assert Config.load_i18n(path) == {}


def test_resolve_config_path_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("CAMERAS_CONF", "/tmp/override.conf")
    assert resolve_config_path("CAMERAS_CONF", "cameras.conf") == "/tmp/override.conf"


def test_resolve_config_path_falls_back_to_repo_config(monkeypatch):
    monkeypatch.delenv("CAMERAS_CONF", raising=False)
    path = resolve_config_path("CAMERAS_CONF", "cameras.conf")
    assert path.endswith("/config/cameras.conf")


@pytest.mark.parametrize("value", ["no-colon", ""])
def test_load_camera_auth_handles_odd_values(tmp_path, value):
    auth = _write(tmp_path / "cameras.auth", f"kuh={value}\n")
    result = Config.load_camera_auth(auth)
    if value:
        assert result == {"kuh": value}
    else:
        assert result == {}
