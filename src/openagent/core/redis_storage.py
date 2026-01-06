"""Redis storage backend for OpenAgent SDK.

Provides Redis-based storage for distributed/multi-process scenarios.

Features:
- Thread-safe with connection pooling
- Automatic serialization (JSON)
- TTL support for temporary data
- Pub/Sub for real-time state synchronization
- Key prefixing to avoid collisions

Requirements:
    pip install redis

Example:
    from openagent import OpenAgentEngine
    from openagent.core.redis_storage import RedisStorage

    # Connect to Redis
    storage = RedisStorage(
        host="localhost",
        port=6379,
        db=0,
        key_prefix="myagent:",
        ttl=None,  # No expiration
    )

    engine = OpenAgentEngine(storage=storage)
"""

from __future__ import annotations

import json
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import redis
except ImportError:
    redis = None  # type: ignore


class RedisStorage:
    """Redis-based storage backend.

    Provides persistent storage for agent state using Redis.

    Args:
        host: Redis server hostname
        port: Redis server port
        db: Redis database number
        key_prefix: Prefix for all keys (prevents collisions)
        ttl: Time-to-live in seconds (None for no expiration)
        socket_timeout: Socket timeout in seconds
        connection_pool: Optional pre-configured connection pool
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        key_prefix: str = "openagent:",
        ttl: Optional[int] = None,
        socket_timeout: float = 5.0,
        connection_pool: Optional["redis.ConnectionPool"] = None,
    ):
        """Initialize Redis storage."""
        if redis is None:
            raise ImportError(
                "Redis package is required. Install with: pip install redis"
            )

        self.host = host
        self.port = port
        self.db = db
        self.key_prefix = key_prefix
        self.ttl = ttl
        self.socket_timeout = socket_timeout

        # Create connection pool if not provided
        if connection_pool is None:
            connection_pool = redis.ConnectionPool(
                host=host,
                port=port,
                db=db,
                socket_timeout=socket_timeout,
                decode_responses=True,
            )

        self._pool = connection_pool
        self._lock = threading.Lock()
        self._state_key = f"{key_prefix}state"

    def _get_client(self) -> "redis.Redis":
        """Get a Redis client from the pool."""
        return redis.Redis(connection_pool=self._pool)

    def save(self, data: Dict[str, Any]) -> None:
        """Save state data to Redis.

        Args:
            data: State data to save
        """
        with self._lock:
            client = self._get_client()
            json_data = json.dumps(data, ensure_ascii=False)

            if self.ttl is not None:
                client.setex(self._state_key, self.ttl, json_data)
            else:
                client.set(self._state_key, json_data)

    def load(self) -> Optional[Dict[str, Any]]:
        """Load state data from Redis.

        Returns:
            State data dictionary or None if not found
        """
        client = self._get_client()
        json_data = client.get(self._state_key)

        if json_data is None:
            return None

        try:
            return json.loads(json_data)
        except (json.JSONDecodeError, TypeError):
            return None

    def exists(self) -> bool:
        """Check if storage has data.

        Returns:
            True if state data exists
        """
        client = self._get_client()
        return client.exists(self._state_key) > 0

    def clear(self) -> None:
        """Clear all stored data."""
        with self._lock:
            client = self._get_client()
            # Delete state key and any related keys
            pattern = f"{self.key_prefix}*"
            keys = client.keys(pattern)
            if keys:
                client.delete(*keys)

    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get history of state changes.

        Note: RedisStorage doesn't maintain automatic history.
        Use RedisStorageWithHistory for history tracking.

        Args:
            limit: Maximum number of history entries

        Returns:
            Empty list (use RedisStorageWithHistory for history)
        """
        return []

    def get_ttl(self) -> Optional[int]:
        """Get remaining TTL for state data.

        Returns:
            TTL in seconds, None if no expiry, -1 if no TTL set, -2 if key doesn't exist
        """
        client = self._get_client()
        ttl = client.ttl(self._state_key)
        if ttl == -1:
            return None  # No expiry set
        elif ttl == -2:
            return None  # Key doesn't exist
        return ttl

    def ping(self) -> bool:
        """Check Redis connection.

        Returns:
            True if Redis is reachable
        """
        try:
            client = self._get_client()
            return client.ping()
        except Exception:
            return False


class RedisStorageWithHistory(RedisStorage):
    """Redis storage with history tracking.

    Uses a separate list to track state history.

    Features:
    - Automatic history on every save
    - Configurable max history size
    - Timestamped entries
    - Change type tracking

    Args:
        host: Redis server hostname
        port: Redis server port
        db: Redis database number
        key_prefix: Prefix for all keys
        max_history: Maximum number of history entries to keep
        ttl: Time-to-live in seconds for state (not history)
        history_ttl: TTL for history entries (None for no expiry)
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        key_prefix: str = "openagent:",
        max_history: int = 1000,
        ttl: Optional[int] = None,
        history_ttl: Optional[int] = None,
        socket_timeout: float = 5.0,
    ):
        """Initialize Redis storage with history."""
        super().__init__(
            host=host,
            port=port,
            db=db,
            key_prefix=key_prefix,
            ttl=ttl,
            socket_timeout=socket_timeout,
        )

        self.max_history = max_history
        self.history_ttl = history_ttl
        self._history_key = f"{key_prefix}history"
        self._history_lock = threading.Lock()

    def save(self, data: Dict[str, Any]) -> None:
        """Save state data and record history.

        Args:
            data: State data to save
        """
        # Get current state before update for history
        old_data = self.load()

        # Save the new state
        super().save(data)

        # Record history entry
        with self._history_lock:
            self._add_history_entry(old_data, data)

    def _add_history_entry(
        self,
        old_data: Optional[Dict[str, Any]],
        new_data: Dict[str, Any],
    ) -> None:
        """Add a history entry.

        Args:
            old_data: Previous state data
            new_data: New state data
        """
        client = self._get_client()

        # Determine change type
        if old_data is None:
            change_type = "create"
        elif not new_data:
            change_type = "clear"
        else:
            change_type = "update"

        # Create history entry
        entry = {
            "key": self._state_key,
            "data": json.dumps(new_data, ensure_ascii=False),
            "version": 1,
            "created_at": datetime.now().isoformat(),
            "change_type": change_type,
            "old_data": json.dumps(old_data, ensure_ascii=False) if old_data else None,
        }

        # Push to history list (LPUSH for most recent first)
        client.lpush(self._history_key, json.dumps(entry, ensure_ascii=False))

        # Trim to max history size
        client.ltrim(self._history_key, 0, self.max_history - 1)

        # Apply TTL to history if configured
        if self.history_ttl is not None:
            client.expire(self._history_key, self.history_ttl)

    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get history of state changes.

        Args:
            limit: Maximum number of history entries to return

        Returns:
            List of history entries (most recent first)
        """
        client = self._get_client()
        entries = client.lrange(self._history_key, 0, limit - 1)

        history = []
        for entry_json in entries:
            try:
                entry = json.loads(entry_json)
                # Parse old_data if present
                if entry.get("old_data"):
                    entry["old_data"] = json.loads(entry["old_data"])
                history.append(entry)
            except (json.JSONDecodeError, TypeError):
                continue

        return history

    def get_history_count(self) -> int:
        """Get the number of history entries.

        Returns:
            Number of history entries
        """
        client = self._get_client()
        return client.llen(self._history_key)

    def rollback(self, index: int = 0) -> Optional[Dict[str, Any]]:
        """Rollback to a previous state.

        Args:
            index: History index to rollback to (0 = most recent, 1 = second most recent, etc.)

        Returns:
            The rolled-back state data, or None if not found
        """
        history = self.get_history(limit=index + 1)

        if index >= len(history):
            return None

        target_entry = history[index]

        # Get the old_data from the entry at the specified index
        old_data = target_entry.get("old_data")
        if old_data:
            rollback_data = old_data
        else:
            # If no old_data, try to get from earlier history entry
            if index + 1 < len(history):
                rollback_data = history[index + 1].get("data")
            else:
                rollback_data = {}

        # Save the rollback data
        if isinstance(rollback_data, str):
            try:
                rollback_data = json.loads(rollback_data)
            except json.JSONDecodeError:
                rollback_data = {}

        self.save(rollback_data)
        return rollback_data

    def clear(self) -> None:
        """Clear all stored data and history."""
        with self._lock:
            client = self._get_client()
            # Delete state key and history
            client.delete(self._state_key, self._history_key)


# =============================================================================
# Redis Pub/Sub for Real-time Synchronization
# =============================================================================

class RedisPubSub:
    """Redis Pub/Sub for real-time state synchronization.

    Allows multiple agents to subscribe to state changes.

    Example:
        pubsub = RedisPubSub(key_prefix="myagent:")

        # Subscribe to changes
        pubsub.subscribe("state_updates", callback=my_callback)

        # Publish state changes
        pubsub.publish("state_updates", {"action": "phase_completed", "data": ...})
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        key_prefix: str = "openagent:",
    ):
        """Initialize Redis Pub/Sub."""
        if redis is None:
            raise ImportError(
                "Redis package is required. Install with: pip install redis"
            )

        self.host = host
        self.port = port
        self.db = db
        self.key_prefix = key_prefix
        self._pool = redis.ConnectionPool(
            host=host,
            port=port,
            db=db,
            decode_responses=True,
        )
        self._pubsub: Optional["redis.client.PubSub"] = None
        self._client: Optional["redis.Redis"] = None
        self._subscriptions: Dict[str, Any] = {}

    def _get_client(self) -> "redis.Redis":
        """Get a Redis client."""
        if self._client is None:
            self._client = redis.Redis(connection_pool=self._pool)
        return self._client

    def get_channel_name(self, channel: str) -> str:
        """Get full channel name with prefix.

        Args:
            channel: Channel name

        Returns:
            Full channel name with prefix
        """
        return f"{self.key_prefix}channel:{channel}"

    def subscribe(
        self,
        channel: str,
        callback: callable,
    ) -> None:
        """Subscribe to a channel.

        Args:
            channel: Channel name
            callback: Callback function to invoke on message
        """
        full_channel = self.get_channel_name(channel)

        if self._pubsub is None:
            self._pubsub = self._get_client().pubsub()

        self._pubsub.subscribe(**{full_channel: callback})
        self._subscriptions[channel] = callback

    def unsubscribe(self, channel: str) -> None:
        """Unsubscribe from a channel.

        Args:
            channel: Channel name
        """
        if self._pubsub:
            full_channel = self.get_channel_name(channel)
            self._pubsub.unsubscribe(full_channel)
            self._subscriptions.pop(channel, None)

    def publish(self, channel: str, message: Dict[str, Any]) -> int:
        """Publish a message to a channel.

        Args:
            channel: Channel name
            message: Message to publish

        Returns:
            Number of subscribers that received the message
        """
        full_channel = self.get_channel_name(channel)
        client = self._get_client()
        return client.publish(full_channel, json.dumps(message, ensure_ascii=False))

    def listen(self, timeout: float = 0.1) -> None:
        """Listen for messages (blocking).

        Args:
            timeout: Timeout in seconds
        """
        if self._pubsub:
            for message in self._pubsub.listen():
                if message["type"] == "message":
                    # Find the callback for this channel
                    for channel, callback in self._subscriptions.items():
                        full_channel = self.get_channel_name(channel)
                        if message["channel"] == full_channel:
                            try:
                                data = json.loads(message["data"])
                                callback(data)
                            except (json.JSONDecodeError, TypeError):
                                pass

    def close(self) -> None:
        """Close the Pub/Sub connection."""
        if self._pubsub:
            self._pubsub.close()
            self._pubsub = None


# =============================================================================
# Storage Factory
# =============================================================================

def create_redis_storage(
    host: str = "localhost",
    port: int = 6379,
    db: int = 0,
    key_prefix: str = "openagent:",
    with_history: bool = False,
    max_history: int = 1000,
    ttl: Optional[int] = None,
) -> RedisStorage:
    """Create a Redis storage backend.

    Args:
        host: Redis server hostname
        port: Redis server port
        db: Redis database number
        key_prefix: Prefix for all keys
        with_history: Whether to include history tracking
        max_history: Maximum history entries
        ttl: Time-to-live in seconds

    Returns:
        RedisStorage or RedisStorageWithHistory instance
    """
    if with_history:
        return RedisStorageWithHistory(
            host=host,
            port=port,
            db=db,
            key_prefix=key_prefix,
            max_history=max_history,
            ttl=ttl,
        )
    else:
        return RedisStorage(
            host=host,
            port=port,
            db=db,
            key_prefix=key_prefix,
            ttl=ttl,
        )
