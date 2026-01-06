"""Tests for Redis storage backend."""

import pytest
import json
from openagent.core.redis_storage import (
    RedisStorage,
    RedisStorageWithHistory,
    create_redis_storage,
)


class TestRedisStorage:
    """Test basic Redis storage functionality."""

    @pytest.fixture
    def storage(self):
        """Create a test storage instance."""
        # Use a unique key prefix for tests
        storage = RedisStorage(
            host="localhost",
            port=6379,
            key_prefix="openagent:test:",
        )
        yield storage
        # Cleanup after test
        storage.clear()

    def test_save_and_load(self, storage):
        """Test basic save and load operations."""
        test_data = {"goal": "Test task", "phases": ["A", "B", "C"]}

        storage.save(test_data)
        loaded = storage.load()

        assert loaded is not None
        assert loaded["goal"] == "Test task"
        assert loaded["phases"] == ["A", "B", "C"]

    def test_load_empty_storage(self, storage):
        """Test loading from empty storage."""
        loaded = storage.load()
        assert loaded is None

    def test_exists(self, storage):
        """Test exists check."""
        assert storage.exists() is False

        storage.save({"test": True})
        assert storage.exists() is True

    def test_clear(self, storage):
        """Test clearing storage."""
        storage.save({"test": True})
        assert storage.exists() is True

        storage.clear()
        assert storage.exists() is False
        assert storage.load() is None

    def test_save_multiple_times(self, storage):
        """Test saving multiple times overwrites."""
        storage.save({"version": 1})
        storage.save({"version": 2})
        storage.save({"version": 3})

        loaded = storage.load()
        assert loaded["version"] == 3

    def test_nested_data(self, storage):
        """Test saving nested data structures."""
        test_data = {
            "plan": {
                "goal": "Complex task",
                "phases": [
                    {"name": "A", "status": "completed"},
                    {"name": "B", "status": "in_progress"},
                ],
            },
            "notes": [
                {"content": "Note 1", "section": "Design"},
                {"content": "Note 2", "section": "Design"},
            ],
        }

        storage.save(test_data)
        loaded = storage.load()

        assert loaded["plan"]["goal"] == "Complex task"
        assert len(loaded["plan"]["phases"]) == 2
        assert len(loaded["notes"]) == 2

    def test_special_characters(self, storage):
        """Test saving data with special characters."""
        test_data = {
            "text": "Hello 世界 🌍",
            "emoji": "🚀",
            "quotes": "He said 'hello'",
        }

        storage.save(test_data)
        loaded = storage.load()

        assert loaded["text"] == "Hello 世界 🌍"
        assert loaded["emoji"] == "🚀"
        assert loaded["quotes"] == "He said 'hello'"


class TestRedisStorageWithHistory:
    """Test Redis storage with history tracking."""

    @pytest.fixture
    def storage(self):
        """Create a test storage with history."""
        storage = RedisStorageWithHistory(
            host="localhost",
            port=6379,
            key_prefix="openagent:test:history:",
            max_history=10,
        )
        yield storage
        storage.clear()

    def test_history_created_on_save(self, storage):
        """Test that history is created when saving."""
        storage.save({"version": 1})

        history = storage.get_history()
        assert len(history) == 1
        assert history[0]["change_type"] == "create"

    def test_history_updated_on_save(self, storage):
        """Test that history is updated on subsequent saves."""
        storage.save({"version": 1})
        storage.save({"version": 2})

        history = storage.get_history()
        assert len(history) == 2
        assert history[0]["change_type"] == "update"
        assert history[1]["change_type"] == "create"

    def test_history_trimmed_to_max(self, storage):
        """Test that history is trimmed to max size."""
        # Save more than max_history entries
        for i in range(15):
            storage.save({"version": i})

        history = storage.get_history()
        assert len(history) == 10  # max_history is 10

    def test_old_data_tracked(self, storage):
        """Test that old data is preserved in history."""
        storage.save({"value": 1})
        storage.save({"value": 2})

        history = storage.get_history(limit=2)
        assert len(history) == 2

        # Most recent entry should have old_data
        assert history[0]["old_data"] is not None
        old_data = history[0]["old_data"]
        if isinstance(old_data, str):
            old_data = json.loads(old_data)
        assert old_data["value"] == 1

    def test_clear_clears_history(self, storage):
        """Test that clear removes history too."""
        storage.save({"test": True})
        assert storage.get_history_count() > 0

        storage.clear()
        assert storage.get_history_count() == 0


class TestCreateRedisStorage:
    """Test the create_redis_storage factory function."""

    def test_create_basic_storage(self):
        """Test creating basic Redis storage."""
        storage = create_redis_storage(
            host="localhost",
            port=6379,
            key_prefix="openagent:factory:",
        )

        assert isinstance(storage, RedisStorage)
        assert storage.key_prefix == "openagent:factory:"

        storage.clear()

    def test_create_storage_with_history(self):
        """Test creating Redis storage with history."""
        storage = create_redis_storage(
            host="localhost",
            port=6379,
            key_prefix="openagent:factory:",
            with_history=True,
            max_history=500,
        )

        assert isinstance(storage, RedisStorageWithHistory)
        assert storage.max_history == 500

        storage.clear()


class TestRedisStorageEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_dict(self):
        """Test saving empty dictionary."""
        storage = RedisStorage(
            host="localhost",
            port=6379,
            key_prefix="openagent:empty:",
        )

        storage.save({})
        loaded = storage.load()

        assert loaded == {}

        storage.clear()

    def test_unicode_data(self):
        """Test saving Unicode data."""
        storage = RedisStorage(
            host="localhost",
            port=6379,
            key_prefix="openagent:unicode:",
        )

        test_data = {
            "chinese": "中文",
            "japanese": "日本語",
            "korean": "한국어",
            "arabic": "العربية",
            "emoji": "😀🎉🔥",
        }

        storage.save(test_data)
        loaded = storage.load()

        assert loaded["chinese"] == "中文"
        assert loaded["emoji"] == "😀🎉🔥"

        storage.clear()

    def test_large_data(self):
        """Test saving large data structures."""
        storage = RedisStorage(
            host="localhost",
            port=6379,
            key_prefix="openagent:large:",
        )

        # Create large data
        test_data = {
            "items": [{"id": i, "name": f"Item {i}"} for i in range(1000)],
            "metadata": {"total": 1000, "page": 1},
        }

        storage.save(test_data)
        loaded = storage.load()

        assert len(loaded["items"]) == 1000
        assert loaded["metadata"]["total"] == 1000

        storage.clear()


@pytest.mark.skipif(
    True,  # Skip if Redis is not available
    reason="Redis server not available. Start Redis and remove this skip to run tests.",
)
class TestRedisIntegration:
    """Integration tests that require a running Redis server."""

    def test_ping(self):
        """Test Redis connection."""
        storage = RedisStorage(host="localhost", port=6379)
        assert storage.ping() is True

    def test_ttl_functionality(self):
        """Test TTL functionality."""
        storage = RedisStorage(
            host="localhost",
            port=6379,
            key_prefix="openagent:ttl:",
            ttl=60,  # 60 seconds
        )

        storage.save({"test": True})

        # TTL should be set
        ttl = storage.get_ttl()
        assert ttl is not None
        assert ttl <= 60

        storage.clear()

    def test_concurrent_operations(self):
        """Test concurrent save operations."""
        import threading

        storage = RedisStorage(
            host="localhost",
            port=6379,
            key_prefix="openagent:concurrent:",
        )

        results = []

        def save_version(v):
            storage.save({"version": v})
            results.append(v)

        # Create multiple threads
        threads = [threading.Thread(target=save_version, args=(i,)) for i in range(10)]

        # Start all threads
        for t in threads:
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Final state should have one of the versions
        loaded = storage.load()
        assert "version" in loaded

        storage.clear()
