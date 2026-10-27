"""API key authentication shared by the REST and MCP servers."""

from __future__ import annotations

import hmac
from collections.abc import Mapping

from flask import Flask, jsonify, request

_HEADER = "X-API-Key"
_BEARER_PREFIX = "bearer "


def extract_api_key(headers: Mapping[str, str]) -> str | None:
    """Return the API key from ``X-API-Key`` or ``Authorization: Bearer``."""
    lowered = {key.lower(): value for key, value in headers.items()}
    key = lowered.get(_HEADER.lower())
    if key:
        return key
    authorization = lowered.get("authorization", "")
    if authorization.lower().startswith(_BEARER_PREFIX):
        return authorization[len(_BEARER_PREFIX):].strip()
    return None


def is_authorized(provided: str | None, expected: str) -> bool:
    """Constant-time comparison of the provided key against the expected one."""
    if not expected:
        return False
    if not provided:
        return False
    return hmac.compare_digest(provided, expected)


def install_api_key_guard(app: Flask, api_key: str) -> None:
    """Require a valid API key on every request to ``app``."""

    @app.before_request
    def _enforce_api_key():
        if not is_authorized(extract_api_key(request.headers), api_key):
            return jsonify({"error": "Unauthorized"}), 401
        return None
