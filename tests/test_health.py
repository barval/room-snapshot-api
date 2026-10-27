"""Tests for the shared camera health aggregation."""

import importlib

from app.config import Camera

health_mod = importlib.import_module("app.health")


def test_overall_status_healthy():
    assert health_mod.overall_status({"a": {"reachable": True}}) == "healthy"


def test_overall_status_degraded():
    states = {"a": {"reachable": True}, "b": {"reachable": False}}
    assert health_mod.overall_status(states) == "degraded"


def test_overall_status_unhealthy():
    assert health_mod.overall_status({"a": {"reachable": False}}) == "unhealthy"


def test_overall_status_empty_is_unhealthy():
    assert health_mod.overall_status({}) == "unhealthy"


def test_camera_state_empty():
    assert health_mod.camera_state({}) == {}


def test_camera_state_marks_bad_stream_unreachable(monkeypatch):
    monkeypatch.setattr(health_mod, "probe_camera", lambda *a, **k: True)
    cameras = {"bad": Camera("bad", "10.0.0.9", "notaport", "Bad", "rtsp://10.0.0.9:notaport")}
    assert health_mod.camera_state(cameras)["bad"]["reachable"] is False
