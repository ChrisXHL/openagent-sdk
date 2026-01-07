"""MCP (Model Context Protocol) Server for OpenAgent SDK.

Provides MCP protocol support for integrating with AI agents like Claude.

Requirements:
    pip install (no extra dependencies)

Example:
    from openagent.mcp import MCPServer, create_mcp_server

    # Create MCP server
    server = create_mcp_server(engine=engine)

    # Run in stdio mode
    server.run_stdio()

    # Or process requests directly
    response = server.process_request(request)
"""

from .server import MCPServer, create_mcp_server

__all__ = ["MCPServer", "create_mcp_server"]
