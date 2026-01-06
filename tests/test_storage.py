"""Additional tests for storage backends."""

import tempfile
from pathlib import Path

import pytest

from openagent.core.storage import (
    MemoryStorage,
    SQLiteStorage,
    SQLiteStorageWithHistory,
    StorageBackend,
)


class TestStorageBackend:
    """Tests for storage backends."""
    
    def test_storage_backend_protocol(self):
        """Test that all backends implement the protocol."""
        storage = MemoryStorage()
        assert isinstance(storage, StorageBackend)
    
    def test_memory_storage_basic_operations(self):
        """Test MemoryStorage basic operations."""
        storage = MemoryStorage()
        
        # Initially empty
        assert storage.exists() is False
        assert storage.load() is None
        
        # Save data
        data = {"key": "value", "number": 42}
        storage.save(data)
        
        # Now exists and can load
        assert storage.exists() is True
        loaded = storage.load()
        assert loaded["key"] == "value"
        assert loaded["number"] == 42
        
        # Clear
        storage.clear()
        assert storage.exists() is False
    
    def test_sqlite_storage_basic_operations(self, temp_dir):
        """Test SQLiteStorage basic operations."""
        storage = SQLiteStorage(db_path=temp_dir / "test.db")
        
        # Initially empty
        assert storage.exists() is False
        assert storage.load() is None
        
        # Save data
        data = {"key": "value", "number": 42}
        storage.save(data)
        
        # Now exists and can load
        assert storage.exists() is True
        loaded = storage.load()
        assert loaded["key"] == "value"
        assert loaded["number"] == 42
        
        # Clear
        storage.clear()
        assert storage.exists() is False
    
    def test_sqlite_storage_data_persistence(self, temp_dir):
        """Test that SQLite data persists after recreation."""
        db_path = temp_dir / "persist.db"
        
        # Create and save
        storage1 = SQLiteStorage(db_path=db_path)
        storage1.save({"test": "data"})
        
        # Create new instance (simulating restart)
        storage2 = SQLiteStorage(db_path=db_path)
        loaded = storage2.load()
        assert loaded["test"] == "data"
    
    def test_sqlite_storage_with_history(self, temp_dir):
        """Test SQLiteStorageWithHistory tracks history."""
        storage = SQLiteStorageWithHistory(
            db_path=temp_dir / "history.db",
            max_history=10,
        )
        
        # Save initial data
        storage.save({"version": 1, "data": "first"})
        
        # Update data
        storage.save({"version": 2, "data": "second"})
        
        # Get history
        history = storage.get_history(limit=10)
        assert len(history) >= 1
        
        # History should contain the previous state (version 1)
        # The version field represents the version BEFORE this state was current
        # So when saving v2, we save v1 to history with version=2
        latest = history[0]
        assert latest["data"]["data"] == "first"
    
    def test_concurrent_save(self, temp_dir):
        """Test that concurrent saves are thread-safe."""
        import threading
        
        storage = SQLiteStorage(db_path=temp_dir / "concurrent.db")
        errors = []
        
        def save_data(thread_id: int):
            try:
                for i in range(10):
                    storage.save({"thread": thread_id, "iteration": i})
            except Exception as e:
                errors.append(e)
        
        # Run multiple threads
        threads = [threading.Thread(target=save_data, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # No errors should occur
        assert len(errors) == 0
        
        # Data should be saved successfully
        assert storage.exists()
        data = storage.load()
        assert data is not None


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
