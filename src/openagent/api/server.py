"""REST API Server for OpenAgent SDK.

Provides a RESTful interface to interact with the agent state.
Useful for remote agents and web interfaces.

Endpoints:
- GET  /api/health           - Health check
- GET  /api/status           - Get current status
- POST /api/plan             - Create a new plan
- POST /api/phase/start      - Start a phase
- POST /api/phase/complete   - Complete a phase
- POST /api/note             - Add a note
- GET  /api/notes            - Get all notes
- POST /api/decision         - Add a decision
- GET  /api/decisions        - Get all decisions
- POST /api/error            - Log an error
- GET  /api/errors           - Get all errors
- DELETE /api/clear          - Clear all state
"""

from __future__ import annotations

import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, Optional

from ..core.state import AgentState
from ..core.storage import JSONStorage


class OpenAgentAPI:
    """REST API server for OpenAgent SDK."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8080,
        workspace: str = ".",
        cors_origins: Optional[list] = None,
    ):
        """Initialize the API server.
        
        Args:
            host: Host to bind to
            port: Port to listen on
            workspace: Workspace directory for state
            cors_origins: List of allowed CORS origins
        """
        self.host = host
        self.port = port
        self.workspace = workspace
        self.cors_origins = cors_origins or []
        self.state = AgentState(workspace_dir=workspace)
        self._server: Optional[HTTPServer] = None
        self._running = False
    
    def create_handler(self):
        """Create the request handler class."""
        state = self.state
        cors_origins = self.cors_origins
        
        class RequestHandler(BaseHTTPRequestHandler):
            def _set_headers(self, status_code: int = 200, content_type: str = "application/json"):
                self.send_response(status_code)
                self.send_header("Content-Type", content_type)
                if cors_origins:
                    self.send_header("Access-Control-Allow-Origin", ", ".join(cors_origins))
                    self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
                    self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.end_headers()
            
            def _send_json(self, data: Any, status_code: int = 200):
                self._set_headers(status_code)
                self.wfile.write(json.dumps(data, ensure_ascii=False).encode())
            
            def _get_json(self) -> Dict[str, Any]:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length)
                if body:
                    return json.loads(body.decode())
                return {}
            
            def do_OPTIONS(self):
                self._set_headers(200)
            
            def do_GET(self):
                path = self.path.split("?")[0]
                
                if path == "/api/health":
                    self._send_json({"status": "ok", "version": "0.2.0"})
                
                elif path == "/api/status":
                    self._send_json(state.get_status())
                
                elif path == "/api/notes":
                    section = self.path.split("?")[-1].split("=")[-1] if "?" in self.path else None
                    self._send_json(state.get_notes(section=section))
                
                elif path == "/api/decisions":
                    self._send_json(state.get_decisions())
                
                elif path == "/api/errors":
                    self._send_json(state.get_errors())
                
                else:
                    self._send_json({"error": "Not found"}, 404)
            
            def do_POST(self):
                path = self.path.split("?")[0]
                data = self._get_json()
                
                if path == "/api/plan":
                    goal = data.get("goal")
                    phases = data.get("phases")
                    if not goal:
                        self._send_json({"error": "goal is required"}, 400)
                        return
                    result = state.create_plan(goal=goal, phases=phases)
                    self._send_json(result, 201)
                
                elif path == "/api/phase/start":
                    phase_name = data.get("phase_name")
                    if not phase_name:
                        self._send_json({"error": "phase_name is required"}, 400)
                        return
                    try:
                        result = state.start_phase(phase_name)
                        self._send_json(result)
                    except ValueError as e:
                        self._send_json({"error": str(e)}, 404)
                
                elif path == "/api/phase/complete":
                    phase_name = data.get("phase_name")
                    if not phase_name:
                        self._send_json({"error": "phase_name is required"}, 400)
                        return
                    try:
                        result = state.complete_phase(phase_name)
                        self._send_json(result)
                    except ValueError as e:
                        self._send_json({"error": str(e)}, 404)
                
                elif path == "/api/note":
                    content = data.get("content")
                    section = data.get("section")
                    if not content:
                        self._send_json({"error": "content is required"}, 400)
                        return
                    result = state.add_note(content=content, section=section)
                    self._send_json(result, 201)
                
                elif path == "/api/decision":
                    decision = data.get("decision")
                    rationale = data.get("rationale")
                    if not decision or not rationale:
                        self._send_json({"error": "decision and rationale are required"}, 400)
                        return
                    result = state.add_decision(decision=decision, rationale=rationale)
                    self._send_json(result, 201)
                
                elif path == "/api/error":
                    error = data.get("error")
                    resolution = data.get("resolution", "")
                    if not error:
                        self._send_json({"error": "error is required"}, 400)
                        return
                    result = state.log_error(error=error, resolution=resolution)
                    self._send_json(result, 201)
                
                else:
                    self._send_json({"error": "Not found"}, 404)
            
            def do_DELETE(self):
                path = self.path.split("?")[0]
                
                if path == "/api/clear":
                    state.clear()
                    self._send_json({"message": "State cleared"})
                
                else:
                    self._send_json({"error": "Not found"}, 404)
            
            def log_message(self, format: str, *args):
                """Custom log format."""
                print(f"[API] {self.address_string()} - {format % args}")
        
        return RequestHandler
    
    def start(self, blocking: bool = True) -> None:
        """Start the API server.
        
        Args:
            blocking: Whether to block the main thread
        """
        handler_class = self.create_handler()
        self._server = HTTPServer((self.host, self.port), handler_class)
        self._running = True
        
        print(f"🚀 OpenAgent API Server running on http://{self.host}:{self.port}")
        print("📋 Available endpoints:")
        print("   GET  /api/health          - Health check")
        print("   GET  /api/status          - Get current status")
        print("   POST /api/plan            - Create a new plan")
        print("   POST /api/phase/start     - Start a phase")
        print("   POST /api/phase/complete  - Complete a phase")
        print("   POST /api/note            - Add a note")
        print("   GET  /api/notes           - Get all notes")
        print("   POST /api/decision        - Add a decision")
        print("   GET  /api/decisions       - Get all decisions")
        print("   POST /api/error           - Log an error")
        print("   GET  /api/errors          - Get all errors")
        print("   DELETE /api/clear         - Clear all state")
        
        if blocking:
            try:
                self._server.serve_forever()
            except KeyboardInterrupt:
                print("\n🛑 Shutting down...")
                self.stop()
    
    def stop(self) -> None:
        """Stop the API server."""
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._running = False
            print("✅ Server stopped")


def run_server(
    host: str = "localhost",
    port: int = 8080,
    workspace: str = ".",
):
    """Run the API server from command line.
    
    Args:
        host: Host to bind to
        port: Port to listen on
        workspace: Workspace directory
    """
    server = OpenAgentAPI(host=host, port=port, workspace=workspace)
    server.start()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="OpenAgent SDK REST API Server")
    parser.add_argument("--host", default="localhost", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on")
    parser.add_argument("--workspace", default=".", help="Workspace directory")
    
    args = parser.parse_args()
    
    run_server(host=args.host, port=args.port, workspace=args.workspace)
