"""Compatibility wrapper for OpenFlight FastAPI application.

This module re-exports the app and create_app from app.main to preserve
imports like `uvicorn main:app` and `from main import app` used by tests.
"""


from app.main import app, create_app  # noqa: F401

__all__ = ["app", "create_app"]
