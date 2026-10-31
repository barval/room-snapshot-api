"""Room Snapshot API package.

The Flask application is created on first access to ``app`` so that importing a
submodule (for example ``app.mcp_server`` for the stdio transport) does not
require ``API_KEY``.
"""

import importlib

__all__ = ["app"]


def __getattr__(name: str):
    """Build the Flask app lazily; ``gunicorn app:app`` resolves it here too."""
    if name != "app":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(".app", __name__)
    # Importing the submodule binds ``app.app`` to the module itself; replace it
    # so ``from app import app`` yields the Flask instance.
    globals()["app"] = module.app
    return module.app
