"""Pytest configuration: provide an API key so importing the app package succeeds."""

import os

os.environ.setdefault("API_KEY", "test-key")
os.environ.setdefault("FLASK_DEBUG", "false")
