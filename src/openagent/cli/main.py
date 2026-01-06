"""Command-line interface for OpenAgent SDK."""

import json
from typing import Optional

import click

from .. import OpenAgentEngine


@click.group()
@click.option(
    "--workspace",
    default=".",
    help="Workspace directory for state files",
)
@click.pass_context
def cli(ctx, workspace: str):
    """OpenAgent SDK - Context Engineering Tools for AI Agents"""
    ctx.ensure_object(dict)
    ctx.obj["workspace"] = workspace


def get_engine(workspace: str) -> OpenAgentEngine:
    """Get an engine instance."""
    return OpenAgentEngine()


@cli.command()
@click.argument("goal")
@click.option(
    "--phases",
    multiple=True,
    help="Phase names for the plan",
)
@click.pass_context
def plan(ctx, goal: str, phases: tuple):
    """Create a new task plan."""
    workspace = ctx.obj["workspace"]
    engine = OpenAgentEngine()
    phases_list = list(phases) if phases else None
    result = engine.create_plan(goal=goal, phases=phases_list)
    click.echo(json.dumps(result, indent=2))


@cli.command()
@click.argument("phase_name")
@click.pass_context
def complete(ctx, phase_name: str):
    """Complete a phase and start the next."""
    engine = OpenAgentEngine()
    result = engine.complete_phase(phase_name=phase_name)
    click.echo(json.dumps(result, indent=2))


@cli.command()
@click.argument("phase_name")
@click.pass_context
def start(ctx, phase_name: str):
    """Start a specific phase."""
    engine = OpenAgentEngine()
    result = engine.start_phase(phase_name=phase_name)
    click.echo(json.dumps(result, indent=2))


@cli.command()
@click.pass_context
def status(ctx):
    """Show current status."""
    engine = OpenAgentEngine()
    result = engine.get_status()
    click.echo(json.dumps(result, indent=2))


@cli.command()
@click.argument("content")
@click.option(
    "--section",
    default=None,
    help="Section/category for the note",
)
@click.pass_context
def note(ctx, content: str, section: Optional[str]):
    """Add a note."""
    engine = OpenAgentEngine()
    result = engine.add_note(content=content, section=section)
    click.echo(json.dumps(result, indent=2))


@cli.command()
@click.option(
    "--section",
    default=None,
    help="Filter notes by section",
)
@click.pass_context
def notes(ctx, section: Optional[str]):
    """List all notes."""
    engine = OpenAgentEngine()
    results = engine.get_notes(section=section)
    click.echo(json.dumps(results, indent=2))


@cli.command()
@click.argument("decision")
@click.argument("rationale")
@click.pass_context
def decision(ctx, decision: str, rationale: str):
    """Record a key decision."""
    engine = OpenAgentEngine()
    result = engine.add_decision(decision=decision, rationale=rationale)
    click.echo(json.dumps(result, indent=2))


@cli.command()
@click.pass_context
def decisions(ctx):
    """List all decisions."""
    engine = OpenAgentEngine()
    results = engine.get_decisions()
    click.echo(json.dumps(results, indent=2))


@cli.command()
@click.argument("error")
@click.option(
    "--resolution",
    default="",
    help="How the error was resolved",
)
@click.pass_context
def error(ctx, error: str, resolution: str):
    """Log an error."""
    engine = OpenAgentEngine()
    result = engine.log_error(error=error, resolution=resolution)
    click.echo(json.dumps(result, indent=2))


@cli.command()
@click.pass_context
def errors(ctx):
    """List all logged errors."""
    engine = OpenAgentEngine()
    results = engine.get_errors()
    click.echo(json.dumps(results, indent=2))


def main():
    """Entry point for the CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
