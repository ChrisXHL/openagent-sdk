"""REST API Server for OpenAgent SDK.

Provides RESTful interface for agent state management.

Requirements:
    pip install (no extra dependencies - uses stdlib http.server)

Example:
    from openagent.api import run_server

    # Start REST API server
    run_server(host='0.0.0.0', port=8080)
"""

from .server import OpenAgentAPI, run_server

__all__ = ["OpenAgentAPI", "run_server"]
