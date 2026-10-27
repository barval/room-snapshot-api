"""Tests for API key authentication."""

from flask import Flask

from app.auth import extract_api_key, install_api_key_guard, is_authorized


def test_extract_prefers_x_api_key():
    headers = {"X-API-Key": "k", "Authorization": "Bearer x"}
    assert extract_api_key(headers) == "k"


def test_extract_from_bearer_header():
    assert extract_api_key({"Authorization": "Bearer abc"}) == "abc"


def test_extract_returns_none_when_absent():
    assert extract_api_key({}) is None


def test_extract_ignores_non_bearer_authorization():
    assert extract_api_key({"Authorization": "Basic abc"}) is None


def test_is_authorized_true_for_matching_key():
    assert is_authorized("k", "k") is True


def test_is_authorized_false_for_missing_or_wrong_key():
    assert is_authorized(None, "k") is False
    assert is_authorized("x", "k") is False


def test_is_authorized_false_when_expected_empty():
    assert is_authorized("", "") is False
    assert is_authorized("x", "") is False


def _guarded_app(api_key):
    app = Flask(__name__)
    install_api_key_guard(app, api_key)

    @app.route("/rooms")
    def rooms():
        return "ok"

    return app


def test_guard_returns_401_without_key():
    client = _guarded_app("secret").test_client()
    response = client.get("/rooms")
    assert response.status_code == 401
    assert response.get_json()["error"] == "Unauthorized"


def test_guard_allows_request_with_key():
    client = _guarded_app("secret").test_client()
    assert client.get("/rooms", headers={"X-API-Key": "secret"}).status_code == 200


def test_guard_allows_bearer_token():
    client = _guarded_app("secret").test_client()
    assert client.get("/rooms", headers={"Authorization": "Bearer secret"}).status_code == 200


def test_guard_allows_cors_preflight():
    client = _guarded_app("secret").test_client()
    response = client.options(
        "/rooms",
        headers={"Origin": "http://example.com", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code != 401


def test_is_authorized_handles_non_ascii_keys():
    assert is_authorized("café", "secret") is False
    assert is_authorized("ключ", "ключ") is True


def test_guard_allows_all_in_debug_without_key():
    app = Flask(__name__)
    app.config["DEBUG"] = True
    install_api_key_guard(app, "")

    @app.route("/rooms")
    def rooms():
        return "ok"

    assert app.test_client().get("/rooms").status_code == 200
