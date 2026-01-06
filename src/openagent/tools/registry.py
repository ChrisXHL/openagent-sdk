"""Tool registry for OpenAgent SDK.

Provides MCP (Model Context Protocol) server integration.
"""

import json
from typing import Any, Dict, List, Optional

from ..core.engine import EngineConfig, OpenAgentEngine

# YouTube tools are optional - only import if yt-dlp is available
_YOUTUBE_AVAILABLE = False
try:
    from .youtube import YouTubeDownloader, create_youtube_tool
    _YOUTUBE_AVAILABLE = True
except ImportError:
    YouTubeDownloader = None
    create_youtube_tool = None


def create_server(workspace_dir: str = ".") -> Dict[str, Any]:
    """Create an MCP server with OpenAgent tools.
    
    This function returns a server configuration that can be used with
    Claude Agent SDK's mcp_servers parameter.
    
    Args:
        workspace_dir: Directory for state persistence
        
    Returns:
        Dictionary with server configuration for MCP integration
    """
    config = EngineConfig(workspace=workspace_dir)
    engine = OpenAgentEngine(config=config)
    
    def task_planner(
        action: str,
        goal: Optional[str] = None,
        phases: Optional[List[str]] = None,
        phase_name: Optional[str] = None,
        decision: Optional[str] = None,
        rationale: Optional[str] = None,
        error: Optional[str] = None,
        resolution: Optional[str] = "",
    ) -> str:
        """Task planning and management tool.
        
        Actions:
        - create_plan: Create a new task plan with goal and phases
        - complete_phase: Complete a phase and start next
        - start_phase: Start a specific phase
        """
        if action == "create_plan":
            if not goal:
                return json.dumps({"error": "goal is required for create_plan"})
            result = engine.create_plan(goal=goal, phases=phases)
            return json.dumps(result, indent=2)
        
        elif action == "complete_phase":
            if not phase_name:
                return json.dumps({"error": "phase_name is required for complete_phase"})
            result = engine.complete_phase(phase_name=phase_name)
            return json.dumps(result, indent=2)
        
        elif action == "start_phase":
            if not phase_name:
                return json.dumps({"error": "phase_name is required for start_phase"})
            result = engine.start_phase(phase_name=phase_name)
            return json.dumps(result, indent=2)
        
        else:
            return json.dumps({"error": f"Unknown action: {action}"})
    
    def notes_manager(
        action: str,
        content: Optional[str] = None,
        section: Optional[str] = None,
    ) -> str:
        """Notes management tool.
        
        Actions:
        - add: Add a new note
        - list: List all notes, optionally filtered by section
        """
        if action == "add":
            if not content:
                return json.dumps({"error": "content is required for add"})
            result = engine.add_note(content=content, section=section)
            return json.dumps(result, indent=2)
        
        elif action == "list":
            results = engine.get_notes(section=section)
            return json.dumps(results, indent=2)
        
        else:
            return json.dumps({"error": f"Unknown action: {action}"})
    
    def progress_tracker() -> str:
        """Get the current progress and status."""
        status = engine.get_status()
        return json.dumps(status, indent=2)
    
    def decision_tracker(
        action: str,
        decision: Optional[str] = None,
        rationale: Optional[str] = None,
    ) -> str:
        """Decision tracking tool.
        
        Actions:
        - add: Record a new decision
        - list: List all decisions
        """
        if action == "add":
            if not decision or not rationale:
                return json.dumps({"error": "decision and rationale are required for add"})
            result = engine.add_decision(decision=decision, rationale=rationale)
            return json.dumps(result, indent=2)
        
        elif action == "list":
            results = engine.get_decisions()
            return json.dumps(results, indent=2)
        
        else:
            return json.dumps({"error": f"Unknown action: {action}"})
    
    def error_tracker(
        action: str,
        error: Optional[str] = None,
        resolution: Optional[str] = None,
    ) -> str:
        """Error tracking tool.
        
        Actions:
        - log: Log an error with optional resolution
        - list: List all logged errors
        """
        if action == "log":
            if not error:
                return json.dumps({"error": "error is required for log"})
            result = engine.log_error(error=error, resolution=resolution or "")
            return json.dumps(result, indent=2)
        
        elif action == "list":
            results = engine.get_errors()
            return json.dumps(results, indent=2)
        
        else:
            return json.dumps({"error": f"Unknown action: {action}"})
    
    # YouTube tools (if yt-dlp is available)
    youtube_tools = {}
    if _YOUTUBE_AVAILABLE and create_youtube_tool:
        yt_tool_config = create_youtube_tool(workspace_dir)
        youtube_tools = yt_tool_config.get("tools", {})
    
    return {
        "mcp_server_openagent": {
            "command": "python",
            "args": ["-c", ""],
            "disabled": True,
        },
        "tools": {
            "task_planner": {
                "function": task_planner,
                "description": "Create and manage task plans with phases",
            },
            "notes_manager": {
                "function": notes_manager,
                "description": "Add and retrieve notes",
            },
            "progress_tracker": {
                "function": progress_tracker,
                "description": "Track current progress and status",
            },
            "decision_tracker": {
                "function": decision_tracker,
                "description": "Record and track key decisions",
            },
            "error_tracker": {
                "function": error_tracker,
                "description": "Log and track errors with resolutions",
            },
            **youtube_tools,
        },
    }


def get_tools_list() -> List[str]:
    """Get the list of available tool names.
    
    Returns:
        List of tool names for Claude Agent SDK allowed_tools
    """
    return [
        "mcp__openagent__task_planner",
        "mcp__openagent__notes_manager",
        "mcp__openagent__progress_tracker",
        "mcp__openagent__decision_tracker",
        "mcp__openagent__error_tracker",
    ]


def create_mcp_server(workspace_dir: str = "."):
    """Create an MCP server instance for direct use.
    
    This returns a server that can be run as a standalone MCP server.
    
    Args:
        workspace_dir: Directory for state persistence
        
    Returns:
        MCP server instance
    """
    # This is a placeholder for future MCP server implementation
    # For now, use create_server() with Claude Agent SDK
    raise NotImplementedError(
        "MCP server mode not yet implemented. "
        "Use create_server() with Claude Agent SDK's mcp_servers parameter."
    )
