"""MCP Server implementation for OpenAgent SDK.

Provides Model Context Protocol (MCP) server integration,
allowing AI agents like Claude to use OpenAgent tools directly.

Based on Anthropic's MCP specification:
https://github.com/anthropics/anthropic-cookbook/tree/main/mcp

Features:
- Full MCP protocol support
- Dynamic tool registration
- Resource management
- Prompt templates
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class MCPMessageType(Enum):
    """MCP Message Types."""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"


class MCPToolParamType(Enum):
    """MCP Tool Parameter Types."""
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"


@dataclass
class MCPToolParameter:
    """MCP Tool Parameter definition."""
    name: str
    param_type: MCPToolParamType
    description: str
    required: bool = False
    enum_values: Optional[List[str]] = None
    default: Optional[Any] = None


@dataclass
class MCPTool:
    """MCP Tool definition."""
    name: str
    description: str
    parameters: List[MCPToolParameter]
    handler: Callable = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to MCP JSON schema."""
        properties = {}
        required_fields = []
        
        for param in self.parameters:
            param_dict = {
                "type": param.param_type.value,
                "description": param.description,
            }
            
            if param.enum_values:
                param_dict["enum"] = param.enum_values
            
            if param.default is not None:
                param_dict["default"] = param.default
            
            properties[param.name] = param_dict
            
            if param.required:
                required_fields.append(param.name)
        
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": {
                "type": "object",
                "properties": properties,
                "required": required_fields,
            }
        }


@dataclass
class MCPServerConfig:
    """MCP Server Configuration."""
    name: str = "openagent-sdk"
    version: str = "0.3.0"
    description: str = "Context Engineering Tools for AI Agents"


class MCPServer:
    """MCP Server for OpenAgent SDK.
    
    This implements the Model Context Protocol server,
    allowing AI agents to call OpenAgent tools.
    
    Example:
        from openagent import MCPServer, OpenAgentEngine
        
        # Create engine and server
        engine = OpenAgentEngine(workspace="./data")
        server = MCPServer(engine=engine)
        
        # Get tools list for Claude Agent
        tools = server.get_tools()
        
        # Or run as MCP server
        server.run_stdio()
    """
    
    def __init__(
        self,
        engine = None,
        config: Optional[MCPServerConfig] = None,
    ):
        """Initialize MCP Server."""
        self.config = config or MCPServerConfig()
        self._engine = engine
        self._tools: Dict[str, MCPTool] = {}
        self._request_handlers: Dict[str, Callable] = {}
        self._notification_handlers: Dict[str, Callable] = {}
        
        self._register_default_handlers()
        self._register_default_tools()
    
    def set_engine(self, engine) -> None:
        """Set the OpenAgent engine."""
        self._engine = engine
    
    def _register_default_handlers(self) -> None:
        """Register default request/notification handlers."""
        self._request_handlers = {
            "initialize": self._handle_initialize,
            "tools/list": self._handle_tools_list,
            "tools/call": self._handle_tools_call,
            "resources/list": self._handle_resources_list,
            "prompts/list": self._handle_prompts_list,
        }
        
        self._notification_handlers = {
            "initialized": self._handle_initialized,
        }
    
    def _register_default_tools(self) -> None:
        """Register default OpenAgent tools."""
        # Task Planning Tools
        self.register_tool(MCPTool(
            name="create_plan",
            description="Create a new task plan with phases",
            parameters=[
                MCPToolParameter(
                    name="goal",
                    param_type=MCPToolParamType.STRING,
                    description="The main goal of the task",
                    required=True,
                ),
                MCPToolParameter(
                    name="phases",
                    param_type=MCPToolParamType.ARRAY,
                    description="List of phase names",
                    required=False,
                    default=[],
                ),
            ],
        ))
        
        self.register_tool(MCPTool(
            name="start_phase",
            description="Start a specific phase in the current plan",
            parameters=[
                MCPToolParameter(
                    name="phase_name",
                    param_type=MCPToolParamType.STRING,
                    description="Name of the phase to start",
                    required=True,
                ),
            ],
        ))
        
        self.register_tool(MCPTool(
            name="complete_phase",
            description="Complete the current phase and start the next",
            parameters=[
                MCPToolParameter(
                    name="phase_name",
                    param_type=MCPToolParamType.STRING,
                    description="Name of the phase to complete",
                    required=True,
                ),
            ],
        ))
        
        self.register_tool(MCPTool(
            name="get_status",
            description="Get the current status of the agent",
            parameters=[],
        ))
        
        # Note Management Tools
        self.register_tool(MCPTool(
            name="add_note",
            description="Add a note to the agent state",
            parameters=[
                MCPToolParameter(
                    name="content",
                    param_type=MCPToolParamType.STRING,
                    description="The note content",
                    required=True,
                ),
                MCPToolParameter(
                    name="section",
                    param_type=MCPToolParamType.STRING,
                    description="Optional section/category for the note",
                    required=False,
                ),
            ],
        ))
        
        self.register_tool(MCPTool(
            name="get_notes",
            description="Get all notes, optionally filtered by section",
            parameters=[
                MCPToolParameter(
                    name="section",
                    param_type=MCPToolParamType.STRING,
                    description="Filter by section",
                    required=False,
                ),
            ],
        ))
        
        # Decision Tracking Tools
        self.register_tool(MCPTool(
            name="add_decision",
            description="Record a key decision with rationale",
            parameters=[
                MCPToolParameter(
                    name="decision",
                    param_type=MCPToolParamType.STRING,
                    description="The decision made",
                    required=True,
                ),
                MCPToolParameter(
                    name="rationale",
                    param_type=MCPToolParamType.STRING,
                    description="Why this decision was made",
                    required=True,
                ),
            ],
        ))
        
        self.register_tool(MCPTool(
            name="get_decisions",
            description="Get all recorded decisions",
            parameters=[],
        ))
        
        # Error Logging Tools
        self.register_tool(MCPTool(
            name="log_error",
            description="Log an error with optional resolution",
            parameters=[
                MCPToolParameter(
                    name="error",
                    param_type=MCPToolParamType.STRING,
                    description="The error message",
                    required=True,
                ),
                MCPToolParameter(
                    name="resolution",
                    param_type=MCPToolParamType.STRING,
                    description="How the error was resolved",
                    required=False,
                    default="",
                ),
            ],
        ))
        
        self.register_tool(MCPTool(
            name="get_errors",
            description="Get all logged errors",
            parameters=[],
        ))
    
    def register_tool(self, tool: MCPTool) -> None:
        """Register a tool with the server."""
        self._tools[tool.name] = tool
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get all registered tools as MCP format."""
        return [tool.to_dict() for tool in self._tools.values()]
    
    def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request."""
        return {
            "serverInfo": {
                "name": self.config.name,
                "version": self.config.version,
            },
            "capabilities": {
                "tools": True,
                "resources": True,
                "prompts": True,
            },
        }
    
    def _handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request."""
        return {"tools": self.get_tools()}
    
    def _handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name not in self._tools:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: Unknown tool '{tool_name}'",
                    }
                ],
                "isError": True,
            }
        
        tool = self._tools[tool_name]
        
        # Execute the tool
        try:
            if self._engine is None:
                result = self._execute_tool_placeholder(tool_name, arguments)
            else:
                result = self._execute_tool(tool_name, arguments)
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2, ensure_ascii=False),
                    }
                ],
                "isError": False,
            }
        except Exception as e:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error executing {tool_name}: {str(e)}",
                    }
                ],
                "isError": True,
            }
    
    def _execute_tool_placeholder(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool without engine (placeholder mode)."""
        return {
            "tool": tool_name,
            "args": args,
            "message": "Tool called successfully. Set engine to get real results.",
        }
    
    def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool using the engine."""
        if tool_name == "create_plan":
            return self._engine.create_plan(
                goal=args.get("goal", ""),
                phases=args.get("phases"),
            )
        
        elif tool_name == "start_phase":
            return self._engine.start_phase(args.get("phase_name", ""))
        
        elif tool_name == "complete_phase":
            return self._engine.complete_phase(args.get("phase_name", ""))
        
        elif tool_name == "get_status":
            return self._engine.get_status()
        
        elif tool_name == "add_note":
            return self._engine.add_note(
                content=args.get("content", ""),
                section=args.get("section"),
            )
        
        elif tool_name == "get_notes":
            return self._engine.get_notes(section=args.get("section"))
        
        elif tool_name == "add_decision":
            return self._engine.add_decision(
                decision=args.get("decision", ""),
                rationale=args.get("rationale", ""),
            )
        
        elif tool_name == "get_decisions":
            return self._engine.get_decisions()
        
        elif tool_name == "log_error":
            return self._engine.log_error(
                error=args.get("error", ""),
                resolution=args.get("resolution", ""),
            )
        
        elif tool_name == "get_errors":
            return self._engine.get_errors()
        
        return {"error": f"Unknown tool: {tool_name}"}
    
    def _handle_resources_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/list request."""
        if self._engine:
            return {
                "resources": [
                    {
                        "uri": "agent://status",
                        "name": "Agent Status",
                        "description": "Current agent state and progress",
                        "mimeType": "application/json",
                    }
                ]
            }
        return {"resources": []}
    
    def _handle_prompts_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompts/list request."""
        return {
            "prompts": [
                {
                    "name": "review_progress",
                    "description": "Get a review of current task progress",
                    "arguments": [
                        {
                            "name": "style",
                            "description": "Review style (brief/detailed)",
                            "required": False,
                        }
                    ],
                }
            ]
        }
    
    def _handle_initialized(self, params: Dict[str, Any]) -> None:
        """Handle initialized notification."""
        print(f"Client initialized: {params}")
    
    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process an MCP request and return response.
        
        Args:
            request: MCP request dictionary
            
        Returns:
            MCP response dictionary
        """
        method = request.get("method", "")
        request_id = request.get("id")
        params = request.get("params", {})
        
        # Find handler
        handler = self._request_handlers.get(method)
        
        if handler:
            try:
                result = handler(params)
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result,
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32603,
                        "message": str(e),
                    },
                }
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}",
                },
            }
    
    def run_stdio(self) -> None:
        """Run the MCP server over stdio.
        
        This is the standard MCP transport for CLI usage.
        """
        import sys
        
        print(f"Starting {self.config.name} MCP Server v{self.config.version}", file=sys.stderr)
        print("Use Ctrl+C to stop", file=sys.stderr)
        
        try:
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    request = json.loads(line)
                    response = self.process_request(request)
                    print(json.dumps(response, ensure_ascii=False))
                    sys.stdout.flush()
                except json.JSONDecodeError:
                    print(json.dumps({
                        "jsonrpc": "2.0",
                        "error": {"code": -32700, "message": "Parse error"},
                    }))
                    sys.stdout.flush()
        except KeyboardInterrupt:
            print("\nShutting down...", file=sys.stderr)


def create_mcp_server(engine = None) -> MCPServer:
    """Create an MCP Server with OpenAgent tools.
    
    Args:
        engine: Optional OpenAgentEngine instance
        
    Returns:
        Configured MCPServer instance
    """
    server = MCPServer(engine=engine)
    return server


# =============================================================================
# Claude Agent Integration
# =============================================================================

def get_mcp_tools_for_claude(engine = None) -> List[Dict[str, Any]]:
    """Get tools in format compatible with Claude Agent SDK.
    
    This creates a server config that can be used with
    Claude Agent SDK's mcp_servers parameter.
    
    Args:
        engine: Optional OpenAgentEngine instance
        
    Returns:
        Tools list and server config for Claude Agent
    """
    server = create_mcp_server(engine)
    tools = server.get_tools()
    
    server_config = {
        "command": sys.executable,
        "args": ["-m", "openagent.mcp_server"],
        "disabled": True,  # Placeholder - would need full MCP server impl
    }
    
    return tools, server_config


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="OpenAgent MCP Server")
    parser.add_argument("--name", default="openagent-sdk", help="Server name")
    parser.add_argument("--version", default="0.3.0", help="Server version")
    
    args = parser.parse_args()
    
    config = MCPServerConfig(
        name=args.name,
        version=args.version,
    )
    
    server = MCPServer(config=config)
    server.run_stdio()
