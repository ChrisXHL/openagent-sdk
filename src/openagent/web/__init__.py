"""Web UI module for OpenAgent SDK.

Provides Flask-based web interface for task management.
"""

from .app import create_app, run_server

__all__ = ["create_app", "run_server"]
