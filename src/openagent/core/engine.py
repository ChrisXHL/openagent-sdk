"""OpenAgent Engine - Main entry point for the SDK."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .state import AgentState


@dataclass
class EngineConfig:
    """Configuration for the OpenAgent Engine."""
    
    workspace: str = "."
    auto_save: bool = True


class OpenAgentEngine:
    """Main engine for OpenAgent SDK.
    
    Provides a high-level interface for managing agent state and tools.
    
    Example:
        engine = OpenAgentEngine(workspace="./my_project")
        engine.create_plan("Build a web app", phases=["Design", "Implement", "Test"])
        engine.complete_phase("Design")
    """
    
    def __init__(self, config: Optional[EngineConfig] = None):
        """Initialize the engine.
        
        Args:
            config: Optional engine configuration
        """
        self.config = config or EngineConfig()
        self.state = AgentState(workspace_dir=self.config.workspace)
    
    def create_plan(self, goal: str, phases: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create a new task plan.
        
        Args:
            goal: The main goal of the task
            phases: Optional list of phase names
            
        Returns:
            The created plan as a dictionary
        """
        return self.state.create_plan(goal=goal, phases=phases)
    
    def complete_phase(self, phase_name: str) -> Dict[str, Any]:
        """Complete a phase and start the next if available.
        
        Args:
            phase_name: Name of the phase to complete
            
        Returns:
            The updated plan as a dictionary
        """
        return self.state.complete_phase(phase_name=phase_name)
    
    def start_phase(self, phase_name: str) -> Dict[str, Any]:
        """Start a specific phase.
        
        Args:
            phase_name: Name of the phase to start
            
        Returns:
            The updated plan as a dictionary
        """
        return self.state.start_phase(phase_name=phase_name)
    
    def add_decision(self, decision: str, rationale: str) -> Dict[str, Any]:
        """Record a key decision.
        
        Args:
            decision: The decision made
            rationale: Why this decision was made
            
        Returns:
            The created decision as a dictionary
        """
        return self.state.add_decision(decision=decision, rationale=rationale)
    
    def log_error(self, error: str, resolution: str = "") -> Dict[str, Any]:
        """Log an error with optional resolution.
        
        Args:
            error: The error message
            resolution: How the error was resolved
            
        Returns:
            The created error log as a dictionary
        """
        return self.state.log_error(error=error, resolution=resolution)
    
    def add_note(self, content: str, section: Optional[str] = None) -> Dict[str, Any]:
        """Add a note.
        
        Args:
            content: The note content
            section: Optional section/category
            
        Returns:
            The created note as a dictionary
        """
        return self.state.add_note(content=content, section=section)
    
    def get_notes(self, section: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get notes, optionally filtered by section.
        
        Args:
            section: Optional section to filter by
            
        Returns:
            List of note dictionaries
        """
        return self.state.get_notes(section=section)
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the agent.
        
        Returns:
            Status dictionary with plan, notes, decisions, and errors counts
        """
        return self.state.get_status()
    
    def get_decisions(self) -> List[Dict[str, Any]]:
        """Get all recorded decisions.
        
        Returns:
            List of decision dictionaries
        """
        return self.state.get_decisions()
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """Get all logged errors.
        
        Returns:
            List of error log dictionaries
        """
        return self.state.get_errors()
