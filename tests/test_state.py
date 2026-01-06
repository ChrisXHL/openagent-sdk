"""Unit tests for OpenAgent SDK state management."""

import json
import tempfile
from pathlib import Path
from typing import List

import pytest

from openagent.core.state import (
    AgentState,
    Decision,
    ErrorLog,
    JSONStorage,
    Note,
    PhaseStatus,
    PlanStatus,
    StateChangeEvent,
    StateNotifier,
    StorageBackend,
    TaskPhase,
    TaskPlan,
    migrate_data,
    register_migrator,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def agent_state(temp_dir):
    """Create an AgentState instance for testing."""
    return AgentState(workspace_dir=str(temp_dir))


# =============================================================================
# Enum Tests
# =============================================================================

class TestPhaseStatus:
    """Tests for PhaseStatus enum."""
    
    def test_phase_status_values(self):
        """Test that all expected status values exist."""
        assert PhaseStatus.PENDING.value == "pending"
        assert PhaseStatus.IN_PROGRESS.value == "in_progress"
        assert PhaseStatus.COMPLETED.value == "completed"
        assert PhaseStatus.FAILED.value == "failed"


class TestPlanStatus:
    """Tests for PlanStatus enum."""
    
    def test_plan_status_values(self):
        """Test that all expected status values exist."""
        assert PlanStatus.ACTIVE.value == "active"
        assert PlanStatus.COMPLETED.value == "completed"
        assert PlanStatus.CANCELLED.value == "cancelled"


# =============================================================================
# Data Class Tests
# =============================================================================

class TestTaskPhase:
    """Tests for TaskPhase class."""
    
    def test_create_phase(self):
        """Test creating a task phase."""
        phase = TaskPhase(name="Test Phase")
        assert phase.name == "Test Phase"
        assert phase.status == PhaseStatus.PENDING
        assert phase.description == ""
    
    def test_phase_to_dict(self):
        """Test converting phase to dictionary."""
        phase = TaskPhase(
            name="Test",
            description="Test description",
            status=PhaseStatus.IN_PROGRESS,
        )
        data = phase.to_dict()
        assert data["name"] == "Test"
        assert data["status"] == "in_progress"
    
    def test_phase_from_dict(self):
        """Test creating phase from dictionary."""
        data = {
            "name": "Test",
            "description": "Desc",
            "status": "completed",
            "started_at": "2024-01-01T00:00:00",
            "completed_at": "2024-01-01T00:01:00",
            "error_message": None,
        }
        phase = TaskPhase.from_dict(data)
        assert phase.name == "Test"
        assert phase.status == PhaseStatus.COMPLETED
        assert phase.started_at == "2024-01-01T00:00:00"


class TestTaskPlan:
    """Tests for TaskPlan class."""
    
    def test_create_plan(self):
        """Test creating a task plan."""
        plan = TaskPlan(goal="Build something")
        assert plan.goal == "Build something"
        assert plan.status == PlanStatus.ACTIVE
        assert len(plan.phases) == 0
    
    def test_plan_with_phases(self):
        """Test creating a plan with phases."""
        phases = [TaskPhase(name="Phase 1"), TaskPhase(name="Phase 2")]
        plan = TaskPlan(goal="Test", phases=phases)
        assert len(plan.phases) == 2
    
    def test_get_current_phase(self):
        """Test getting the current phase."""
        p1 = TaskPhase(name="P1", status=PhaseStatus.COMPLETED)
        p2 = TaskPhase(name="P2", status=PhaseStatus.IN_PROGRESS)
        p3 = TaskPhase(name="P3", status=PhaseStatus.PENDING)
        plan = TaskPlan(goal="Test", phases=[p1, p2, p3])
        
        current = plan.get_current_phase()
        assert current is not None
        assert current.name == "P2"
    
    def test_get_next_phase(self):
        """Test getting the next phase."""
        p1 = TaskPhase(name="P1", status=PhaseStatus.COMPLETED)
        p2 = TaskPhase(name="P2", status=PhaseStatus.IN_PROGRESS)
        p3 = TaskPhase(name="P3", status=PhaseStatus.PENDING)
        plan = TaskPlan(goal="Test", phases=[p1, p2, p3])
        
        next_phase = plan.get_next_phase()
        assert next_phase is not None
        assert next_phase.name == "P3"


# =============================================================================
# Storage Tests
# =============================================================================

class TestJSONStorage:
    """Tests for JSONStorage class."""
    
    def test_save_and_load(self, temp_dir):
        """Test saving and loading data."""
        storage = JSONStorage(temp_dir / "test.json")
        data = {"key": "value", "number": 42}
        
        storage.save(data)
        assert storage.exists()
        
        loaded = storage.load()
        assert loaded["key"] == "value"
        assert loaded["number"] == 42
    
    def test_clear(self, temp_dir):
        """Test clearing storage."""
        storage = JSONStorage(temp_dir / "test.json")
        storage.save({"data": "test"})
        assert storage.exists()
        
        storage.clear()
        assert not storage.exists()
    
    def test_load_nonexistent(self, temp_dir):
        """Test loading from nonexistent file."""
        storage = JSONStorage(temp_dir / "nonexistent.json")
        assert storage.load() is None


# =============================================================================
# AgentState Tests
# =============================================================================

class TestAgentState:
    """Tests for AgentState class."""
    
    def test_create_plan(self, agent_state):
        """Test creating a plan."""
        result = agent_state.create_plan("Test Goal", phases=["Phase 1", "Phase 2"])
        assert result["goal"] == "Test Goal"
        assert len(result["phases"]) == 2
        assert agent_state.plan is not None
    
    def test_start_phase(self, agent_state):
        """Test starting a phase."""
        agent_state.create_plan("Test", phases=["P1", "P2"])
        result = agent_state.start_phase("P1")
        assert result["phases"][0]["status"] == "in_progress"
    
    def test_complete_phase(self, agent_state):
        """Test completing a phase."""
        agent_state.create_plan("Test", phases=["P1", "P2"])
        agent_state.start_phase("P1")
        result = agent_state.complete_phase("P1")
        
        # First phase should be completed
        assert result["phases"][0]["status"] == "completed"
        # Second phase should be in progress
        assert result["phases"][1]["status"] == "in_progress"
    
    def test_add_decision(self, agent_state):
        """Test adding a decision."""
        result = agent_state.add_decision("Use Python", "It's flexible")
        assert result["decision"] == "Use Python"
        assert len(agent_state.decisions) == 1
    
    def test_log_error(self, agent_state):
        """Test logging an error."""
        result = agent_state.log_error("Connection failed", "Retry")
        assert result["error"] == "Connection failed"
        assert result["resolution"] == "Retry"
    
    def test_add_note(self, agent_state):
        """Test adding a note."""
        result = agent_state.add_note("Test note", section="test")
        assert result["content"] == "Test note"
        assert result["section"] == "test"
    
    def test_get_status(self, agent_state):
        """Test getting status."""
        agent_state.create_plan("Test", phases=["P1", "P2"])
        agent_state.start_phase("P1")
        
        status = agent_state.get_status()
        assert status["has_plan"]
        assert status["notes_count"] == 0
        assert status["decisions_count"] == 0
        assert status["progress"] == 0.0  # No completed phases yet
    
    def test_clear(self, agent_state):
        """Test clearing state."""
        agent_state.create_plan("Test", phases=["P1"])
        agent_state.add_note("Test")
        
        agent_state.clear()
        
        assert agent_state.plan is None
        assert len(agent_state.notes) == 0
    
    def test_progress_calculation(self, agent_state):
        """Test progress calculation."""
        agent_state.create_plan("Test", phases=["P1", "P2", "P3", "P4"])
        agent_state.start_phase("P1")
        agent_state.complete_phase("P1")
        agent_state.complete_phase("P2")
        
        status = agent_state.get_status()
        assert status["progress"] == 50.0  # 2 out of 4 phases completed


# =============================================================================
# Observer Tests
# =============================================================================

class MockObserver:
    """Mock observer for testing."""
    
    def __init__(self):
        self.events: List[StateChangeEvent] = []
    
    def on_state_change(self, event: StateChangeEvent) -> None:
        self.events.append(event)


class TestStateNotifier:
    """Tests for StateNotifier mixin."""
    
    def test_add_and_remove_observer(self):
        """Test adding and removing observers."""
        notifier = StateNotifier()
        observer = MockObserver()
        
        notifier.add_observer(observer)
        assert len(notifier._observers) == 1
        
        notifier.remove_observer(observer)
        assert len(notifier._observers) == 0
    
    def test_notification(self):
        """Test that observers receive notifications."""
        notifier = StateNotifier()
        observer = MockObserver()
        
        notifier.add_observer(observer)
        notifier._notify("test_event", {"key": "value"})
        
        assert len(observer.events) == 1
        assert observer.events[0].event_type == "test_event"
        assert observer.events[0].data["key"] == "value"


# =============================================================================
# Version Migration Tests
# =============================================================================

class TestVersionMigration:
    """Tests for version migration."""
    
    def test_current_version(self):
        """Test that current version is 1."""
        from openagent.core.state import CURRENT_VERSION
        assert CURRENT_VERSION == 1
    
    def test_migrate_none(self):
        """Test migrating None data."""
        result = migrate_data(None)
        assert result is None
    
    def test_migrate_v0_to_v1(self):
        """Test migrating from version 0 to 1."""
        v0_data = {
            "goal": "Test",
            "phases": [{"name": "P1", "status": "pending"}],
            "decisions": [],
            "notes": [],
            "errors": [],
        }
        result = migrate_data(v0_data)
        assert result["version"] == 1


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for the complete workflow."""
    
    def test_full_task_workflow(self, temp_dir):
        """Test a complete task workflow."""
        state = AgentState(workspace_dir=str(temp_dir))
        
        # Create plan
        state.create_plan("Build API", phases=["Design", "Implement", "Test"])
        
        # Add some decisions
        state.add_decision("Use FastAPI", "High performance")
        state.add_decision("Use PostgreSQL", "Reliable")
        
        # Start working
        state.start_phase("Design")
        
        # Add notes
        state.add_note("API endpoints defined", section="Design")
        
        # Complete phase
        state.complete_phase("Design")
        
        # Check status
        status = state.get_status()
        assert status["has_plan"]
        assert status["decisions_count"] == 2
        assert status["notes_count"] == 1
        assert status["progress"] == 33.33333333333333  # 1/3 phases
        
        # Verify data persisted
        state2 = AgentState(workspace_dir=str(temp_dir))
        assert state2.get_status()["has_plan"]
        assert state2.get_decisions()[0]["decision"] == "Use FastAPI"
    
    def test_observer_receives_events(self, temp_dir):
        """Test that observers receive state change events."""
        state = AgentState(workspace_dir=str(temp_dir))
        observer = MockObserver()
        
        state.add_observer(observer)
        
        state.create_plan("Test", phases=["P1"])
        
        # create_plan triggers: state_saved (from _load_state), plan_created, state_saved
        assert len(observer.events) >= 1
        # Last event should be plan_created
        assert observer.events[-1].event_type == "plan_created"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
