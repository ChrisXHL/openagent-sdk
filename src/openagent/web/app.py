"""Web UI for OpenAgent SDK.

Provides a simple web interface for task management.

Requirements:
    pip install flask

Example:
    from openagent.web import create_app
    app = create_app(workspace="./data")
    app.run(host="0.0.0.0", port=5000)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Union

from flask import Flask, Response, jsonify, render_template, request


def create_app(
    workspace: str = ".",
    static_folder: Optional[str] = None,
    template_folder: Optional[str] = None,
) -> Flask:
    """Create a Flask web application.

    Args:
        workspace: Workspace directory for state storage
        static_folder: Path to static files
        template_folder: Path to templates

    Returns:
        Flask application instance
    """
    # Determine paths
    if static_folder is None:
        static_folder = str(Path(__file__).parent / "static")
    if template_folder is None:
        template_folder = str(Path(__file__).parent / "templates")

    app = Flask(
        __name__,
        static_folder=static_folder,
        template_folder=template_folder,
    )

    # Store workspace in app config
    app.config["WORKSPACE"] = workspace

    # Import here to avoid circular imports
    from openagent import OpenAgentEngine, EngineConfig

    def get_engine() -> OpenAgentEngine:
        """Get or create the OpenAgent engine."""
        if "engine" not in app.config:
            config = EngineConfig(workspace=app.config["WORKSPACE"])
            app.config["engine"] = OpenAgentEngine(config=config)
        return app.config["engine"]

    # =========================================================================
    # API Routes
    # =========================================================================

    @app.route("/api/status")
    def api_status() -> Response:
        """Get current agent status."""
        engine = get_engine()
        return jsonify(engine.get_status())

    @app.route("/api/plan", methods=["GET", "POST"])
    def api_plan() -> Response:
        """Get or create a plan."""
        engine = get_engine()

        if request.method == "POST":
            data = request.get_json() or {}
            goal = data.get("goal", "")
            phases = data.get("phases", [])
            result = engine.create_plan(goal=goal, phases=phases)
            return jsonify(result)
        else:
            status = engine.get_status()
            if status["has_plan"]:
                return jsonify(status["plan"])
            return jsonify(None)

    @app.route("/api/phase/start", methods=["POST"])
    def api_start_phase() -> Response:
        """Start a phase."""
        engine = get_engine()
        data = request.get_json() or {}
        phase_name = data.get("phase_name", "")
        result = engine.start_phase(phase_name=phase_name)
        return jsonify(result)

    @app.route("/api/phase/complete", methods=["POST"])
    def api_complete_phase() -> Response:
        """Complete a phase."""
        engine = get_engine()
        data = request.get_json() or {}
        phase_name = data.get("phase_name", "")
        result = engine.complete_phase(phase_name=phase_name)
        return jsonify(result)

    @app.route("/api/notes", methods=["GET", "POST"])
    def api_notes() -> Response:
        """Get or create notes."""
        engine = get_engine()

        if request.method == "POST":
            data = request.get_json() or {}
            content = data.get("content", "")
            section = data.get("section")
            result = engine.add_note(content=content, section=section)
            return jsonify(result)
        else:
            section = request.args.get("section")
            notes = engine.get_notes(section=section)
            return jsonify(notes)

    @app.route("/api/decisions", methods=["GET", "POST"])
    def api_decisions() -> Response:
        """Get or create decisions."""
        engine = get_engine()

        if request.method == "POST":
            data = request.get_json() or {}
            decision = data.get("decision", "")
            rationale = data.get("rationale", "")
            result = engine.add_decision(decision=decision, rationale=rationale)
            return jsonify(result)
        else:
            decisions = engine.get_decisions()
            return jsonify(decisions)

    @app.route("/api/errors", methods=["GET"])
    def api_errors() -> Response:
        """Get logged errors."""
        engine = get_engine()
        errors = engine.get_errors()
        return jsonify(errors)

    @app.route("/api/errors", methods=["POST"])
    def api_log_error() -> Response:
        """Log an error."""
        engine = get_engine()
        data = request.get_json() or {}
        error = data.get("error", "")
        resolution = data.get("resolution", "")
        result = engine.log_error(error=error, resolution=resolution)
        return jsonify(result)

    @app.route("/api/clear", methods=["POST"])
    def api_clear() -> Response:
        """Clear all state data."""
        engine = get_engine()
        engine.state.clear()
        return jsonify({"success": True})

    # =========================================================================
    # Page Routes
    # =========================================================================

    @app.route("/")
    def index() -> str:
        """Render the main dashboard."""
        return render_template("index.html")

    @app.route("/plan")
    def plan_page() -> str:
        """Render the plan page."""
        return render_template("plan.html")

    @app.route("/notes")
    def notes_page() -> str:
        """Render the notes page."""
        return render_template("notes.html")

    @app.route("/decisions")
    def decisions_page() -> str:
        """Render the decisions page."""
        return render_template("decisions.html")

    return app


def run_server(
    host: str = "0.0.0.0",
    port: int = 5000,
    workspace: str = ".",
    debug: bool = False,
) -> None:
    """Run the web server.

    Args:
        host: Host to bind to
        port: Port to listen on
        workspace: Workspace directory
        debug: Enable debug mode
    """
    app = create_app(workspace=workspace)
    app.run(host=host, port=port, debug=debug)
