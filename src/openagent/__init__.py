"""OpenAgent SDK - Context Engineering Tools for AI Agents

This SDK provides tools for AI agents to plan, track, and manage
complex tasks with persistent state management.

Example:
    from openagent import OpenAgentEngine, create_server, SQLiteStorage
    
    # Use with default JSON storage
    engine = OpenAgentEngine(workspace="./my_project")
    
    # Use with SQLite storage for better performance
    storage = SQLiteStorage(db_path="./data/agent.db")
    engine = OpenAgentEngine(storage=storage)
    
    # Use encrypted storage for sensitive data
    from openagent.core.encryption import EncryptedJSONStorage
    storage = EncryptedJSONStorage(file_path="./secret.json", password="secure123")
    
    # Use Redis storage for distributed scenarios
    from openagent.core.redis_storage import RedisStorage
    storage = RedisStorage(host="localhost", port=6379, key_prefix="myagent:")
    
    # Start REST API server
    from openagent.api import run_server
    run_server(host="localhost", port=8080)
    
    # Start Web UI
    from openagent.web import run_server as run_web
    run_web(host="localhost", port=5000)
"""

__version__ = "0.2.0"

from .core.engine import OpenAgentEngine, EngineConfig
from .core.storage import (
    JSONStorage,
    MemoryStorage,
    SQLiteStorage,
    SQLiteStorageWithHistory,
    StorageBackend,
)
from .tools.registry import create_server, get_tools_list
from .api.server import OpenAgentAPI, run_server
from .core.encryption import EncryptedJSONStorage, generate_key, generate_password
from .mcp.server import MCPServer, create_mcp_server
from .web import create_app, run_server as run_web_server

__all__ = [
    "OpenAgentEngine",
    "EngineConfig",
    "create_server",
    "get_tools_list",
    # Storage backends
    "StorageBackend",
    "JSONStorage",
    "MemoryStorage",
    "SQLiteStorage",
    "SQLiteStorageWithHistory",
    # API
    "OpenAgentAPI",
    "run_server",
    # Encryption
    "EncryptedJSONStorage",
    "generate_key",
    "generate_password",
    # MCP
    "MCPServer",
    "create_mcp_server",
    # Web UI
    "create_app",
    "run_web_server",
]
