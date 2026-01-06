"""State management for OpenAgent SDK.

Provides persistent state storage for task plans, notes, and progress tracking.

Key improvements in this version:
- PhaseStatus uses Enum instead of strings
- StorageBackend abstract interface for extensibility
- Observer pattern support for state change notifications
- Version management for data migration
- Multiple storage backends (JSON, SQLite, Memory)
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .storage import JSONStorage, MemoryStorage, SQLiteStorage, SQLiteStorageWithHistory, StorageBackend


# =============================================================================
# Enums
# =============================================================================

class PhaseStatus(Enum):
    """Phase status using Enum for type safety."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class PlanStatus(Enum):
    """Plan status using Enum for type safety."""
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# =============================================================================
# Helper Functions
# =============================================================================

def _generate_timestamp() -> str:
    """Generate current timestamp."""
    return datetime.now().isoformat()


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class TaskPhase:
    """Represents a phase in a task plan."""
    name: str
    description: str = ""
    status: PhaseStatus = PhaseStatus.PENDING
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None  # Track failure reason
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error_message": self.error_message,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskPhase":
        """Create from dictionary."""
        status_raw = data.get("status", "pending")
        if isinstance(status_raw, str):
            status = PhaseStatus(status_raw)
        else:
            status = PhaseStatus.PENDING
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            status=status,
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            error_message=data.get("error_message"),
        )


@dataclass
class TaskPlan:
    """Represents a task plan with phases."""
    goal: str
    phases: List[TaskPhase] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    status: PlanStatus = PlanStatus.ACTIVE
    
    def __post_init__(self):
        """Initialize timestamps if not set."""
        if not self.created_at:
            self.created_at = _generate_timestamp()
        if not self.updated_at:
            self.updated_at = _generate_timestamp()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "goal": self.goal,
            "phases": [p.to_dict() for p in self.phases],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status.value,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskPlan":
        """Create from dictionary."""
        status_raw = data.get("status", "active")
        if isinstance(status_raw, str):
            status = PlanStatus(status_raw)
        else:
            status = PlanStatus.ACTIVE
        plan = cls(
            goal=data["goal"],
            phases=[TaskPhase.from_dict(p) for p in data.get("phases", [])],
            created_at=data.get("created_at") or "",
            updated_at=data.get("updated_at") or "",
            status=status,
        )
        plan.__post_init__()
        return plan
    
    def get_current_phase(self) -> Optional[TaskPhase]:
        """Get the current active phase."""
        for phase in self.phases:
            if phase.status == PhaseStatus.IN_PROGRESS:
                return phase
        return None
    
    def get_next_phase(self) -> Optional[TaskPhase]:
        """Get the next pending phase."""
        for phase in self.phases:
            if phase.status == PhaseStatus.PENDING:
                return phase
        return None
    
    def get_completed_phases(self) -> List[TaskPhase]:
        """Get all completed phases."""
        return [p for p in self.phases if p.status == PhaseStatus.COMPLETED]


@dataclass
class Note:
    """Represents a note entry."""
    content: str
    section: Optional[str] = None
    created_at: str = ""
    
    def __post_init__(self):
        """Initialize timestamp if not set."""
        if not self.created_at:
            self.created_at = _generate_timestamp()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "content": self.content,
            "section": self.section,
            "created_at": self.created_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Note":
        """Create from dictionary."""
        note = cls(
            content=data["content"],
            section=data.get("section"),
            created_at=data.get("created_at") or "",
        )
        note.__post_init__()
        return note


@dataclass
class Decision:
    """Represents a key decision with rationale."""
    decision: str
    rationale: str
    created_at: str = ""
    
    def __post_init__(self):
        """Initialize timestamp if not set."""
        if not self.created_at:
            self.created_at = _generate_timestamp()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "decision": self.decision,
            "rationale": self.rationale,
            "created_at": self.created_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Decision":
        """Create from dictionary."""
        dec = cls(
            decision=data["decision"],
            rationale=data["rationale"],
            created_at=data.get("created_at") or "",
        )
        dec.__post_init__()
        return dec


@dataclass
class ErrorLog:
    """Represents a logged error with resolution."""
    error: str
    resolution: str = ""
    created_at: str = ""
    
    def __post_init__(self):
        """Initialize timestamp if not set."""
        if not self.created_at:
            self.created_at = _generate_timestamp()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "error": self.error,
            "resolution": self.resolution,
            "created_at": self.created_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ErrorLog":
        """Create from dictionary."""
        err = cls(
            error=data["error"],
            resolution=data.get("resolution", ""),
            created_at=data.get("created_at") or "",
        )
        err.__post_init__()
        return err


# =============================================================================
# Storage Backend Interface
# =============================================================================

class StorageBackend(ABC):
    """Abstract interface for state storage backends.
    
    Implement this protocol to add new storage backends.
    """
    
    @abstractmethod
    def save(self, data: Dict[str, Any]) -> None:
        """Save state data to storage."""
        ...
    
    @abstractmethod
    def load(self) -> Optional[Dict[str, Any]]:
        """Load state data from storage."""
        ...
    
    @abstractmethod
    def exists(self) -> bool:
        """Check if storage has data."""
        ...
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all stored data."""
        ...


class JSONStorage(StorageBackend):
    """JSON file storage backend."""
    
    def __init__(self, file_path: Path):
        """Initialize JSON storage."""
        self.file_path = file_path
    
    def save(self, data: Dict[str, Any]) -> None:
        """Save state data to JSON file."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load(self) -> Optional[Dict[str, Any]]:
        """Load state data from JSON file."""
        if not self.file_path.exists():
            return None
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, KeyError):
            return None
    
    def exists(self) -> bool:
        """Check if JSON file exists."""
        return self.file_path.exists()
    
    def clear(self) -> None:
        """Clear the JSON file."""
        if self.file_path.exists():
            self.file_path.unlink()


# =============================================================================
# Observer Pattern
# =============================================================================

class StateChangeEvent:
    """Event dispatched when state changes."""
    
    def __init__(
        self,
        event_type: str,
        data: Dict[str, Any],
        timestamp: Optional[str] = None,
    ):
        self.event_type = event_type
        self.data = data
        self.timestamp = timestamp or _generate_timestamp()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_type": self.event_type,
            "data": self.data,
            "timestamp": self.timestamp,
        }


class StateObserver(ABC):
    """Abstract base class for state change observers."""
    
    @abstractmethod
    def on_state_change(self, event: StateChangeEvent) -> None:
        """Called when state changes."""
        ...


class StateNotifier:
    """Mixin class for state change notifications."""
    
    def __init__(self, *args, **kwargs):
        """Initialize state notifier."""
        self._observers: List[StateObserver] = []
        super().__init__(*args, **kwargs)
    
    def add_observer(self, observer: StateObserver) -> None:
        """Add an observer."""
        if observer not in self._observers:
            self._observers.append(observer)
    
    def remove_observer(self, observer: StateObserver) -> None:
        """Remove an observer."""
        if observer in self._observers:
            self._observers.remove(observer)
    
    def _notify(self, event_type: str, data: Dict[str, Any]) -> None:
        """Notify all observers of state change."""
        event = StateChangeEvent(event_type=event_type, data=data)
        for observer in self._observers:
            try:
                observer.on_state_change(event)
            except Exception:
                pass


# =============================================================================
# Version Management
# =============================================================================

CURRENT_VERSION = 1

VERSION_MIGRATORS: Dict[int, Any] = {}


def register_migrator(from_version: int):
    """Decorator to register a version migrator."""
    def decorator(func):
        VERSION_MIGRATORS[from_version] = func
        return func
    return decorator


@register_migrator(0)
def _migrate_from_v0(data: Dict[str, Any]) -> Dict[str, Any]:
    """Migrate from version 0 to version 1."""
    data["version"] = 1
    if "plan" in data and data["plan"]:
        for phase in data["plan"].get("phases", []):
            status = phase.get("status")
            if status not in [s.value for s in PhaseStatus]:
                phase["status"] = PhaseStatus.PENDING.value
    return data


def migrate_data(data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Migrate data to current version."""
    if data is None:
        return None
    version = data.get("version", 0)
    while version < CURRENT_VERSION:
        migrator = VERSION_MIGRATORS.get(version)
        if migrator is None:
            break
        data = migrator(data)
        version = data.get("version", version + 1)
    return data


# =============================================================================
# Main State Manager
# =============================================================================

class AgentState(StateNotifier):
    """Manages persistent state for an AI agent."""
    
    def __init__(
        self,
        workspace_dir: str = ".",
        storage: Optional[StorageBackend] = None,
    ):
        """Initialize the agent state manager."""
        StateNotifier.__init__(self)
        self.workspace = Path(workspace_dir)
        
        if storage is None:
            self.storage: StorageBackend = JSONStorage(
                self.workspace / ".agent_state.json"
            )
        else:
            self.storage = storage
        
        self._load_state()
    
    def _load_state(self) -> None:
        """Load state from storage."""
        data = self.storage.load()
        data = migrate_data(data)
        
        if data:
            self._from_dict(data)
        else:
            self._init_state()
        
        self._notify("state_loaded", {"has_plan": self.plan is not None})
    
    def _init_state(self) -> None:
        """Initialize empty state."""
        self.plan: Optional[TaskPlan] = None
        self.notes: List[Note] = []
        self.decisions: List[Decision] = []
        self.errors: List[ErrorLog] = []
    
    def _from_dict(self, data: Dict[str, Any]) -> None:
        """Restore state from dictionary."""
        self.plan = TaskPlan.from_dict(data["plan"]) if data.get("plan") else None
        self.notes = [Note.from_dict(n) for n in data.get("notes", [])]
        self.decisions = [Decision.from_dict(d) for d in data.get("decisions", [])]
        self.errors = [ErrorLog.from_dict(e) for e in data.get("errors", [])]
    
    def _save_state(self) -> None:
        """Save state to storage."""
        data = self._to_dict()
        self.storage.save(data)
        self._notify("state_saved", {"has_plan": self.plan is not None})
    
    def _to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary."""
        return {
            "version": CURRENT_VERSION,
            "plan": self.plan.to_dict() if self.plan else None,
            "notes": [n.to_dict() for n in self.notes],
            "decisions": [d.to_dict() for d in self.decisions],
            "errors": [e.to_dict() for e in self.errors],
        }
    
    def create_plan(self, goal: str, phases: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create a new task plan."""
        phase_objects = []
        if phases:
            for i, name in enumerate(phases):
                phase = TaskPhase(
                    name=name,
                    description=f"Phase {i+1}: {name}",
                    status=PhaseStatus.PENDING,
                )
                phase_objects.append(phase)
        
        self.plan = TaskPlan(goal=goal)
        self.plan.phases = phase_objects
        self._save_state()
        
        self._notify("plan_created", {"goal": goal, "phases": len(phase_objects)})
        
        return self.plan.to_dict()
    
    def complete_phase(self, phase_name: str) -> Dict[str, Any]:
        """Complete a phase and optionally start the next."""
        if not self.plan:
            raise ValueError("No active plan. Create a plan first.")
        
        now = _generate_timestamp()
        
        for phase in self.plan.phases:
            if phase.name == phase_name:
                phase.status = PhaseStatus.COMPLETED
                phase.completed_at = now
                break
        else:
            raise ValueError(f"Phase '{phase_name}' not found in plan")
        
        next_phase = self.plan.get_next_phase()
        if next_phase:
            next_phase.status = PhaseStatus.IN_PROGRESS
            next_phase.started_at = now
        
        self.plan.updated_at = now
        self._save_state()
        
        self._notify(
            "phase_completed",
            {"phase": phase_name, "next_phase": next_phase.name if next_phase else None}
        )
        
        return self.plan.to_dict()
    
    def start_phase(self, phase_name: str) -> Dict[str, Any]:
        """Start a specific phase."""
        if not self.plan:
            raise ValueError("No active plan. Create a plan first.")
        
        now = _generate_timestamp()
        
        for phase in self.plan.phases:
            if phase.status == PhaseStatus.IN_PROGRESS:
                phase.status = PhaseStatus.PENDING
        
        for phase in self.plan.phases:
            if phase.name == phase_name:
                phase.status = PhaseStatus.IN_PROGRESS
                phase.started_at = phase.started_at or now
                break
        else:
            raise ValueError(f"Phase '{phase_name}' not found in plan")
        
        self.plan.updated_at = now
        self._save_state()
        
        self._notify("phase_started", {"phase": phase_name})
        
        return self.plan.to_dict()
    
    def fail_phase(self, phase_name: str, error_message: str) -> Dict[str, Any]:
        """Mark a phase as failed."""
        if not self.plan:
            raise ValueError("No active plan. Create a plan first.")
        
        now = _generate_timestamp()
        
        for phase in self.plan.phases:
            if phase.name == phase_name:
                phase.status = PhaseStatus.FAILED
                phase.completed_at = now
                phase.error_message = error_message
                break
        else:
            raise ValueError(f"Phase '{phase_name}' not found in plan")
        
        self.plan.updated_at = now
        self._save_state()
        
        self._notify("phase_failed", {"phase": phase_name, "error": error_message})
        
        return self.plan.to_dict()
    
    def add_decision(self, decision: str, rationale: str) -> Dict[str, Any]:
        """Record a key decision."""
        dec = Decision(decision=decision, rationale=rationale)
        self.decisions.append(dec)
        self._save_state()
        
        self._notify("decision_added", {"decision": decision[:50]})
        
        return dec.to_dict()
    
    def log_error(self, error: str, resolution: str = "") -> Dict[str, Any]:
        """Log an error with optional resolution."""
        err = ErrorLog(error=error, resolution=resolution)
        self.errors.append(err)
        self._save_state()
        
        self._notify("error_logged", {"error": error[:50]})
        
        return err.to_dict()
    
    def add_note(self, content: str, section: Optional[str] = None) -> Dict[str, Any]:
        """Add a note."""
        note = Note(content=content, section=section)
        self.notes.append(note)
        self._save_state()
        
        self._notify("note_added", {"section": section})
        
        return note.to_dict()
    
    def get_notes(self, section: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get notes, optionally filtered by section."""
        notes = self.notes
        if section:
            notes = [n for n in notes if n.section == section]
        
        return [n.to_dict() for n in notes]
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the agent."""
        status = {
            "has_plan": self.plan is not None,
            "plan": self.plan.to_dict() if self.plan else None,
            "notes_count": len(self.notes),
            "decisions_count": len(self.decisions),
            "errors_count": len(self.errors),
            "version": CURRENT_VERSION,
        }
        
        if self.plan:
            current_phase = self.plan.get_current_phase()
            if current_phase:
                status["current_phase"] = current_phase.name
                status["progress"] = self._calculate_progress()
        
        return status
    
    def _calculate_progress(self) -> float:
        """Calculate the progress percentage of the current plan."""
        if not self.plan or not self.plan.phases:
            return 0.0
        
        completed = sum(1 for p in self.plan.phases if p.status == PhaseStatus.COMPLETED)
        return (completed / len(self.plan.phases)) * 100
    
    def get_decisions(self) -> List[Dict[str, Any]]:
        """Get all recorded decisions."""
        return [d.to_dict() for d in self.decisions]
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """Get all logged errors."""
        return [e.to_dict() for e in self.errors]
    
    def clear(self) -> None:
        """Clear all state data."""
        self._init_state()
        self.storage.clear()
        self._notify("state_cleared", {})
