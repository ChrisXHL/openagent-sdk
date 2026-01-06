"""Storage backends for OpenAgent SDK.

Provides multiple storage implementations:
- JSONStorage: Simple JSON file storage
- SQLiteStorage: Robust SQLite storage with transactions
- SQLiteStorageWithHistory: SQLite with version history
- MemoryStorage: In-memory storage for testing
"""

from __future__ import annotations

import json
import sqlite3
import threading
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# =============================================================================
# Abstract Storage Backend
# =============================================================================

class StorageBackend(ABC):
    """Abstract interface for state storage backends.
    
    Implement this to add new storage backends.
    
    Example:
        class S3Storage(StorageBackend):
            def __init__(self, bucket: str):
                self.bucket = bucket
                
            def save(self, data: Dict[str, Any]) -> None:
                # Upload to S3
                pass
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


# =============================================================================
# JSON Storage
# =============================================================================

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
# SQLite Storage
# =============================================================================

class SQLiteStorage(StorageBackend):
    """SQLite-based storage backend.
    
    Features:
    - Thread-safe with write lock
    - Automatic schema creation
    - Transaction support
    - WAL mode for better concurrency
    
    Args:
        db_path: Path to SQLite database file
        table_name: Table name for state data
        timeout: Connection timeout in seconds
    """
    
    def __init__(
        self,
        db_path: Path,
        table_name: str = "agent_state",
        timeout: float = 30.0,
    ):
        """Initialize SQLite storage."""
        self.db_path = db_path
        self.table_name = table_name
        self.timeout = timeout
        self._write_lock = threading.Lock()
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=self.timeout,
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn
    
    def _init_db(self) -> None:
        """Initialize database schema."""
        with self._get_connection() as conn:
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    key TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    version INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_updated_at 
                ON {self.table_name}(updated_at)
            """)
            conn.commit()
    
    def save(self, data: Dict[str, Any]) -> None:
        """Save state data to SQLite."""
        with self._write_lock:
            json_data = json.dumps(data, ensure_ascii=False)
            now = datetime.now().isoformat()
            
            with self._get_connection() as conn:
                conn.execute(f"""
                    INSERT INTO {self.table_name} (key, data, version, updated_at)
                    VALUES ('state', ?, 1, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        data = excluded.data,
                        updated_at = excluded.updated_at
                """, (json_data, now))
                conn.commit()
    
    def load(self) -> Optional[Dict[str, Any]]:
        """Load state data from SQLite."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                f"SELECT data FROM {self.table_name} WHERE key = 'state'"
            )
            row = cursor.fetchone()
            
            if row:
                try:
                    return json.loads(row["data"])
                except (json.JSONDecodeError, KeyError):
                    return None
            return None
    
    def exists(self) -> bool:
        """Check if storage has data."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                f"SELECT 1 FROM {self.table_name} WHERE key = 'state' LIMIT 1"
            )
            return cursor.fetchone() is not None
    
    def clear(self) -> None:
        """Clear all stored data."""
        with self._write_lock:
            with self._get_connection() as conn:
                conn.execute(f"DELETE FROM {self.table_name}")
                conn.commit()
    
    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get history of state changes."""
        return []


class SQLiteStorageWithHistory(SQLiteStorage):
    """SQLite storage with history tracking."""
    
    def __init__(
        self,
        db_path: Path,
        table_name: str = "agent_state",
        history_table_name: str = "agent_state_history",
        max_history: int = 1000,
        timeout: float = 30.0,
    ):
        """Initialize storage with history."""
        self.history_table_name = history_table_name
        self.max_history = max_history
        super().__init__(db_path, table_name, timeout)
    
    def _init_db(self) -> None:
        """Initialize database with history table."""
        with self._get_connection() as conn:
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    key TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    version INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.history_table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL,
                    data TEXT NOT NULL,
                    version INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    change_type TEXT DEFAULT 'update'
                )
            """)
            
            conn.commit()
    
    def save(self, data: Dict[str, Any]) -> None:
        """Save state data with history tracking."""
        old_data = self.load()
        
        with self._write_lock:
            json_data = json.dumps(data, ensure_ascii=False)
            now = datetime.now().isoformat()
            
            with self._get_connection() as conn:
                cursor = conn.execute(
                    f"SELECT version FROM {self.table_name} WHERE key = 'state'"
                )
                row = cursor.fetchone()
                version = (row["version"] + 1) if row else 1
                
                if old_data:
                    conn.execute(f"""
                        INSERT INTO {self.history_table_name} 
                        (key, data, version, created_at, change_type)
                        VALUES ('state', ?, ?, ?, 'update')
                    """, (json.dumps(old_data, ensure_ascii=False), version, now))
                
                conn.execute(f"""
                    INSERT INTO {self.table_name} (key, data, version, updated_at)
                    VALUES ('state', ?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        data = excluded.data,
                        version = excluded.version,
                        updated_at = excluded.updated_at
                """, (json_data, version, now))
                
                conn.execute(f"""
                    DELETE FROM {self.history_table_name}
                    WHERE id NOT IN (
                        SELECT id FROM {self.history_table_name}
                        ORDER BY id DESC
                        LIMIT ?
                    )
                """, (self.max_history,))
                
                conn.commit()
    
    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get history of state changes."""
        with self._get_connection() as conn:
            cursor = conn.execute(f"""
                SELECT data, version, created_at, change_type
                FROM {self.history_table_name}
                ORDER BY id DESC
                LIMIT ?
            """, (limit,))
            
            return [
                {
                    "data": json.loads(row["data"]),
                    "version": row["version"],
                    "created_at": row["created_at"],
                    "change_type": row["change_type"],
                }
                for row in cursor.fetchall()
            ]


# =============================================================================
# Memory Storage (for testing)
# =============================================================================

class MemoryStorage(StorageBackend):
    """In-memory storage for testing and development."""
    
    def __init__(self):
        """Initialize memory storage."""
        self._data: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    def save(self, data: Dict[str, Any]) -> None:
        """Save data to memory."""
        with self._lock:
            self._data = data.copy()
    
    def load(self) -> Optional[Dict[str, Any]]:
        """Load data from memory."""
        with self._lock:
            if self._data:
                return self._data.copy()
            return None
    
    def exists(self) -> bool:
        """Check if data exists."""
        with self._lock:
            return bool(self._data)
    
    def clear(self) -> None:
        """Clear all data."""
        with self._lock:
            self._data = {}
