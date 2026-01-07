"""Web UI module for OpenAgent SDK.

Provides Flask-based web interface for task management.

Requirements:
    pip install flask

Example:
    from openagent.web import create_app, run_server

    # Run web UI
    run_server(host="0.0.0.0", port=5000)

    # Or create custom app
    app = create_app(workspace="./data")
    app.run(host="0.0.0.0", port=5000)
"""

from .app import create_app, run_server

__all__ = ["create_app", "run_server"]
