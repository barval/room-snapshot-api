"""API key authentication shared by the REST and MCP servers."""

from __future__ import annotations

import hmac
import logging
from collections.abc import Mapping

from flask import Flask, jsonify, request

logger = logging.getLogger(__name__)

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
    if not expected or not provided:
        return False
    return hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8"))


def install_api_key_guard(app: Flask, api_key: str) -> None:
    """Require a valid API key on every request to ``app``.

    When no key is configured and debug mode is on, authentication is skipped with
    a warning; otherwise a key-less app denies every request (fail closed).
    """
    if not api_key:
        if app.config.get("DEBUG"):
            logger.warning("API_KEY is not set; authentication is disabled (debug mode)")
            return

        @app.before_request
        def _deny_all():
            return jsonify({"error": "Unauthorized"}), 401

        return

    @app.before_request
    def _enforce_api_key():
        if request.method == "OPTIONS":
            return None
        if not is_authorized(extract_api_key(request.headers), api_key):
            return jsonify({"error": "Unauthorized"}), 401
        return None
