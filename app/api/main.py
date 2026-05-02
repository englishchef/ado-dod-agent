"""Compatibility shim: expose FastAPI app from backend package path."""

from backend.api.main import app

__all__ = ["app"]
