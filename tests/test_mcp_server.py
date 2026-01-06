"""Tests for MCP Server functionality."""

import pytest
import json
from openagent import OpenAgentEngine, EngineConfig, MemoryStorage
from openagent.mcp.server import MCPServer, MCPServerConfig, create_mcp_server


class TestMCPServerConfig:
    """Test MCP Server configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = MCPServerConfig()
        assert config.name == "openagent-sdk"
        assert config.version == "0.3.0"
        assert "Context Engineering" in config.description

    def test_custom_config(self):
        """Test custom configuration values."""
        config = MCPServerConfig(
            name="my-server",
            version="1.0.0",
            description="My custom server",
        )
        assert config.name == "my-server"
        assert config.version == "1.0.0"


class TestMCPServerInitialization:
    """Test MCP Server initialization."""

    def test_create_server_without_engine(self):
        """Test creating server without engine."""
        server = MCPServer()
        assert server.config.name == "openagent-sdk"
        assert len(server.get_tools()) == 10  # All default tools

    def test_create_server_with_engine(self):
        """Test creating server with engine."""
        config = EngineConfig(workspace="/tmp/test")
        engine = OpenAgentEngine(config=config)
        server = MCPServer(engine=engine)

        assert server._engine is engine
        assert len(server.get_tools()) == 10

    def test_create_mcp_server_helper(self):
        """Test the create_mcp_server helper function."""
        server = create_mcp_server()
        assert isinstance(server, MCPServer)
        assert len(server.get_tools()) == 10


class TestMCPToolsList:
    """Test MCP tools list functionality."""

    def test_tools_have_required_fields(self):
        """Test that all tools have required fields."""
        server = create_mcp_server()
        tools = server.get_tools()

        assert len(tools) == 10

        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool

    def test_create_plan_tool(self):
        """Test create_plan tool schema."""
        server = create_mcp_server()
        tools = server.get_tools()

        create_plan = next(t for t in tools if t["name"] == "create_plan")
        schema = create_plan["inputSchema"]

        assert "goal" in schema["properties"]
        assert schema["properties"]["goal"]["type"] == "string"
        assert "goal" in schema["required"]

        assert "phases" in schema["properties"]
        assert schema["properties"]["phases"]["type"] == "array"

    def test_get_status_tool(self):
        """Test get_status tool schema (no parameters)."""
        server = create_mcp_server()
        tools = server.get_tools()

        get_status = next(t for t in tools if t["name"] == "get_status")
        schema = get_status["inputSchema"]

        assert schema["properties"] == {}
        assert schema["required"] == []


class TestMCPRequests:
    """Test MCP request processing."""

    def test_initialize_request(self):
        """Test initialize request."""
        server = create_mcp_server()

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {},
        }

        response = server.process_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert response["result"]["serverInfo"]["name"] == "openagent-sdk"

    def test_tools_list_request(self):
        """Test tools/list request."""
        server = create_mcp_server()

        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        }

        response = server.process_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 2
        assert "tools" in response["result"]
        assert len(response["result"]["tools"]) == 10

    def test_tools_call_request_unknown_tool(self):
        """Test calling unknown tool."""
        server = create_mcp_server()

        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "unknown_tool",
                "arguments": {},
            },
        }

        response = server.process_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 3
        assert response["result"]["isError"] is True
        assert "Unknown tool" in response["result"]["content"][0]["text"]

    def test_tools_call_request_placeholder_mode(self):
        """Test calling tool in placeholder mode (no engine)."""
        server = create_mcp_server()  # No engine

        request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "get_status",
                "arguments": {},
            },
        }

        response = server.process_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 4
        assert response["result"]["isError"] is False

    def test_tools_call_with_engine(self):
        """Test calling tool with real engine."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            config = EngineConfig(workspace=tmpdir)
            engine = OpenAgentEngine(config=config)
        server = MCPServer(engine=engine)

        # Create a plan first
        request = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "create_plan",
                "arguments": {
                    "goal": "Build a web app",
                    "phases": ["Design", "Implement", "Test"],
                },
            },
        }

        response = server.process_request(request)
        assert response["result"]["isError"] is False

        # Get status
        request = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "get_status",
                "arguments": {},
            },
        }

        response = server.process_request(request)
        assert response["result"]["isError"] is False

        status = json.loads(response["result"]["content"][0]["text"])
        assert status["plan"]["goal"] == "Build a web app"

    def test_add_note_and_get_notes(self):
        """Test adding and retrieving notes."""
        import tempfile
        import os
        with tempfile.TemporaryDirectory() as tmpdir:
            config = EngineConfig(workspace=tmpdir)
            engine = OpenAgentEngine(config=config)
        server = MCPServer(engine=engine)

        # Add a note
        request = {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "add_note",
                "arguments": {
                    "content": "This is a test note",
                    "section": "Testing",
                },
            },
        }

        response = server.process_request(request)
        assert response["result"]["isError"] is False

        # Get notes
        request = {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {
                "name": "get_notes",
                "arguments": {
                    "section": "Testing",
                },
            },
        }

        response = server.process_request(request)
        assert response["result"]["isError"] is False

        notes = json.loads(response["result"]["content"][0]["text"])
        assert len(notes) == 1
        assert notes[0]["content"] == "This is a test note"

    def test_add_decision_and_get_decisions(self):
        """Test adding and retrieving decisions."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            config = EngineConfig(workspace=tmpdir)
            engine = OpenAgentEngine(config=config)
        server = MCPServer(engine=engine)

        # Add a decision
        request = {
            "jsonrpc": "2.0",
            "id": 9,
            "method": "tools/call",
            "params": {
                "name": "add_decision",
                "arguments": {
                    "decision": "Use FastAPI",
                    "rationale": "High performance and easy to use",
                },
            },
        }

        response = server.process_request(request)
        assert response["result"]["isError"] is False

        # Get decisions
        request = {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {
                "name": "get_decisions",
                "arguments": {},
            },
        }

        response = server.process_request(request)
        assert response["result"]["isError"] is False

        decisions = json.loads(response["result"]["content"][0]["text"])
        assert len(decisions) == 1
        assert decisions[0]["decision"] == "Use FastAPI"

    def test_resources_list_request(self):
        """Test resources/list request."""
        config = EngineConfig(workspace="/tmp/test")
        engine = OpenAgentEngine(config=config)
        server = MCPServer(engine=engine)

        request = {
            "jsonrpc": "2.0",
            "id": 11,
            "method": "resources/list",
            "params": {},
        }

        response = server.process_request(request)

        assert response["jsonrpc"] == "2.0"
        assert len(response["result"]["resources"]) == 1
        assert response["result"]["resources"][0]["uri"] == "agent://status"

    def test_prompts_list_request(self):
        """Test prompts/list request."""
        server = create_mcp_server()

        request = {
            "jsonrpc": "2.0",
            "id": 12,
            "method": "prompts/list",
            "params": {},
        }

        response = server.process_request(request)

        assert response["jsonrpc"] == "2.0"
        assert len(response["result"]["prompts"]) == 1
        assert response["result"]["prompts"][0]["name"] == "review_progress"

    def test_method_not_found(self):
        """Test unknown method."""
        server = create_mcp_server()

        request = {
            "jsonrpc": "2.0",
            "id": 13,
            "method": "unknown/method",
            "params": {},
        }

        response = server.process_request(request)

        assert response["error"]["code"] == -32601
        assert "Method not found" in response["error"]["message"]


class TestMCPFullWorkflow:
    """Test full MCP workflow."""

    def test_complete_task_workflow(self):
        """Test complete task workflow through MCP."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            config = EngineConfig(workspace=tmpdir)
            engine = OpenAgentEngine(config=config)
        server = MCPServer(engine=engine)

        # 1. Create plan
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "create_plan",
                "arguments": {
                    "goal": "Build a REST API",
                    "phases": ["Design", "Implement", "Test", "Deploy"],
                },
            },
        }
        response = server.process_request(request)
        assert response["result"]["isError"] is False

        # 2. Add decisions
        for decision, rationale in [
            ("Use FastAPI", "High performance async framework"),
            ("Use Pydantic", "Data validation and serialization"),
        ]:
            request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "add_decision",
                    "arguments": {"decision": decision, "rationale": rationale},
                },
            }
            response = server.process_request(request)
            assert response["result"]["isError"] is False

        # 3. Start phase
        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "start_phase",
                "arguments": {"phase_name": "Design"},
            },
        }
        response = server.process_request(request)
        assert response["result"]["isError"] is False

        # 4. Add notes
        request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "add_note",
                "arguments": {
                    "content": "API endpoints defined",
                    "section": "Design",
                },
            },
        }
        response = server.process_request(request)
        assert response["result"]["isError"] is False

        # 5. Get status
        request = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "get_status",
                "arguments": {},
            },
        }
        response = server.process_request(request)
        assert response["result"]["isError"] is False

        status = json.loads(response["result"]["content"][0]["text"])
        assert status["plan"]["goal"] == "Build a REST API"
        assert status["current_phase"] == "Design"
        assert status["progress"] == 0.0  # 0% - progress based on COMPLETED phases

        # 6. Complete phase
        request = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "complete_phase",
                "arguments": {"phase_name": "Design"},
            },
        }
        response = server.process_request(request)
        assert response["result"]["isError"] is False

        # Get status after completing phase
        request = {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "get_status",
                "arguments": {},
            },
        }
        response = server.process_request(request)
        status = json.loads(response["result"]["content"][0]["text"])
        assert status["progress"] == 25.0  # 25% - 1/4 phases completed

        # 8. Get decisions
        request = {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {
                "name": "get_decisions",
                "arguments": {},
            },
        }
        response = server.process_request(request)
        assert response["result"]["isError"] is False

        decisions = json.loads(response["result"]["content"][0]["text"])
        assert len(decisions) == 2
