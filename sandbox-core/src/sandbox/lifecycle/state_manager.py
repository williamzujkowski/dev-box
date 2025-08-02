"""
State Manager - Sandbox state persistence and management

Handles the persistence, retrieval, and management of sandbox state information
including configuration, runtime state, and historical data.
"""

import asyncio
import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from ..utils.serialization import StateSerializer
from ..utils.stub_modules import StateEncryption


@dataclass
class StateEntry:
    """Individual state entry"""

    key: str
    value: Any
    timestamp: float
    version: int = 1
    encrypted: bool = False
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class StateSnapshot:
    """State snapshot at a point in time"""

    snapshot_id: str
    timestamp: float
    state_entries: List[StateEntry]
    metadata: Dict[str, Any]
    size_bytes: int = 0


class StateManager:
    """
    Manages sandbox state persistence and retrieval

    Features:
    - SQLite-based state storage
    - Versioned state entries
    - Encrypted sensitive data
    - State snapshots and rollback
    - Query and filtering capabilities
    - Automatic cleanup of old data
    """

    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(f"sandbox.{config.sandbox_id}.state")

        # Initialize paths
        self.state_dir = config.workspace_path / "state"
        self.db_path = self.state_dir / "sandbox.db"

        # Initialize components
        self.serializer = StateSerializer()
        self.encryption = (
            StateEncryption()
            if config.safety_constraints.get("encrypt_state")
            else None
        )

        # Database connection
        self._db_conn: Optional[sqlite3.Connection] = None
        self._lock = asyncio.Lock()

    async def initialize(self) -> bool:
        """
        Initialize the state manager

        Returns:
            bool: True if initialization successful
        """
        try:
            self.logger.info("Initializing state manager")

            # Create state directory
            self.state_dir.mkdir(exist_ok=True, mode=0o750)

            # Initialize database
            await self._init_database()

            # Load initial configuration state
            await self._load_initial_state()

            self.logger.info("State manager initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"State manager initialization failed: {e}")
            return False

    async def set_state(
        self,
        key: str,
        value: Any,
        encrypted: bool = False,
        metadata: Dict[str, Any] = None,
    ) -> bool:
        """
        Set a state value

        Args:
            key: State key
            value: State value
            encrypted: Whether to encrypt the value
            metadata: Additional metadata

        Returns:
            bool: True if successful
        """
        try:
            async with self._lock:
                timestamp = asyncio.get_event_loop().time()

                # Get current version
                current_version = await self._get_state_version(key)
                new_version = current_version + 1

                # Serialize and optionally encrypt value
                serialized_value = await self.serializer.serialize(value)
                if encrypted and self.encryption:
                    serialized_value = await self.encryption.encrypt(serialized_value)

                # Create state entry
                entry = StateEntry(
                    key=key,
                    value=serialized_value,
                    timestamp=timestamp,
                    version=new_version,
                    encrypted=encrypted,
                    metadata=metadata or {},
                )

                # Store in database
                await self._store_state_entry(entry)

                self.logger.debug(f"State set: {key} (version {new_version})")
                return True

        except Exception as e:
            self.logger.error(f"Failed to set state {key}: {e}")
            return False

    async def get_state(
        self, key: str, version: Optional[int] = None, default: Any = None
    ) -> Any:
        """
        Get a state value

        Args:
            key: State key
            version: Specific version (None for latest)
            default: Default value if key not found

        Returns:
            State value or default
        """
        try:
            async with self._lock:
                entry = await self._get_state_entry(key, version)

                if entry is None:
                    return default

                # Decrypt if needed
                value = entry.value
                if entry.encrypted and self.encryption:
                    value = await self.encryption.decrypt(value)

                # Deserialize
                return await self.serializer.deserialize(value)

        except Exception as e:
            self.logger.error(f"Failed to get state {key}: {e}")
            return default

    async def delete_state(self, key: str) -> bool:
        """
        Delete a state key

        Args:
            key: State key to delete

        Returns:
            bool: True if successful
        """
        try:
            async with self._lock:
                cursor = self._db_conn.cursor()
                cursor.execute("DELETE FROM state_entries WHERE key = ?", (key,))
                self._db_conn.commit()

                deleted_count = cursor.rowcount
                self.logger.debug(f"Deleted {deleted_count} entries for key: {key}")
                return deleted_count > 0

        except Exception as e:
            self.logger.error(f"Failed to delete state {key}: {e}")
            return False

    async def list_keys(self, pattern: Optional[str] = None) -> List[str]:
        """
        List all state keys

        Args:
            pattern: Optional SQL LIKE pattern

        Returns:
            List of state keys
        """
        try:
            async with self._lock:
                cursor = self._db_conn.cursor()

                if pattern:
                    cursor.execute(
                        "SELECT DISTINCT key FROM state_entries WHERE key LIKE ? ORDER BY key",
                        (pattern,),
                    )
                else:
                    cursor.execute(
                        "SELECT DISTINCT key FROM state_entries ORDER BY key"
                    )

                return [row[0] for row in cursor.fetchall()]

        except Exception as e:
            self.logger.error(f"Failed to list keys: {e}")
            return []

    async def get_state_history(self, key: str, limit: int = 10) -> List[StateEntry]:
        """
        Get state history for a key

        Args:
            key: State key
            limit: Maximum number of entries

        Returns:
            List of state entries, newest first
        """
        try:
            async with self._lock:
                cursor = self._db_conn.cursor()
                cursor.execute(
                    """
                    SELECT key, value, timestamp, version, encrypted, metadata
                    FROM state_entries
                    WHERE key = ?
                    ORDER BY version DESC
                    LIMIT ?
                    """,
                    (key, limit),
                )

                entries = []
                for row in cursor.fetchall():
                    metadata = json.loads(row[5]) if row[5] else {}
                    entry = StateEntry(
                        key=row[0],
                        value=row[1],
                        timestamp=row[2],
                        version=row[3],
                        encrypted=bool(row[4]),
                        metadata=metadata,
                    )
                    entries.append(entry)

                return entries

        except Exception as e:
            self.logger.error(f"Failed to get state history for {key}: {e}")
            return []

    async def create_snapshot(
        self, snapshot_id: str, keys: Optional[List[str]] = None
    ) -> Optional[StateSnapshot]:
        """
        Create a state snapshot

        Args:
            snapshot_id: Unique snapshot identifier
            keys: Specific keys to snapshot (None for all)

        Returns:
            StateSnapshot if successful, None otherwise
        """
        try:
            async with self._lock:
                timestamp = asyncio.get_event_loop().time()

                # Get state entries
                if keys:
                    entries = []
                    for key in keys:
                        entry = await self._get_state_entry(key)
                        if entry:
                            entries.append(entry)
                else:
                    entries = await self._get_all_latest_entries()

                # Calculate snapshot size
                size_bytes = sum(len(str(entry.value)) for entry in entries)

                # Create snapshot
                snapshot = StateSnapshot(
                    snapshot_id=snapshot_id,
                    timestamp=timestamp,
                    state_entries=entries,
                    metadata={
                        "sandbox_id": self.config.sandbox_id,
                        "entry_count": len(entries),
                        "created_at": datetime.fromtimestamp(timestamp).isoformat(),
                    },
                    size_bytes=size_bytes,
                )

                # Store snapshot
                await self._store_snapshot(snapshot)

                self.logger.info(
                    f"Created state snapshot: {snapshot_id} ({len(entries)} entries)"
                )
                return snapshot

        except Exception as e:
            self.logger.error(f"Failed to create snapshot {snapshot_id}: {e}")
            return None

    async def restore_snapshot(self, snapshot_id: str) -> bool:
        """
        Restore state from a snapshot

        Args:
            snapshot_id: Snapshot identifier

        Returns:
            bool: True if successful
        """
        try:
            async with self._lock:
                # Load snapshot
                snapshot = await self._load_snapshot(snapshot_id)
                if not snapshot:
                    raise ValueError(f"Snapshot not found: {snapshot_id}")

                # Restore each state entry
                restored_count = 0
                for entry in snapshot.state_entries:
                    success = await self.set_state(
                        entry.key, entry.value, entry.encrypted, entry.metadata
                    )
                    if success:
                        restored_count += 1

                self.logger.info(
                    f"Restored {restored_count} state entries from snapshot: {snapshot_id}"
                )
                return restored_count == len(snapshot.state_entries)

        except Exception as e:
            self.logger.error(f"Failed to restore snapshot {snapshot_id}: {e}")
            return False

    async def list_snapshots(self) -> List[Dict[str, Any]]:
        """
        List all available snapshots

        Returns:
            List of snapshot metadata
        """
        try:
            async with self._lock:
                cursor = self._db_conn.cursor()
                cursor.execute(
                    """
                    SELECT snapshot_id, timestamp, metadata, size_bytes
                    FROM snapshots
                    ORDER BY timestamp DESC
                    """
                )

                snapshots = []
                for row in cursor.fetchall():
                    metadata = json.loads(row[2]) if row[2] else {}
                    snapshot_info = {
                        "snapshot_id": row[0],
                        "timestamp": row[1],
                        "created_at": datetime.fromtimestamp(row[1]).isoformat(),
                        "size_bytes": row[3],
                        "metadata": metadata,
                    }
                    snapshots.append(snapshot_info)

                return snapshots

        except Exception as e:
            self.logger.error(f"Failed to list snapshots: {e}")
            return []

    async def cleanup_old_data(self, days: int = 7) -> int:
        """
        Clean up old state data

        Args:
            days: Age threshold in days

        Returns:
            Number of entries cleaned up
        """
        try:
            async with self._lock:
                cutoff_time = asyncio.get_event_loop().time() - (days * 24 * 3600)

                cursor = self._db_conn.cursor()

                # Delete old state entries (keep latest version of each key)
                cursor.execute(
                    """
                    DELETE FROM state_entries
                    WHERE timestamp < ?
                    AND version NOT IN (
                        SELECT MAX(version)
                        FROM state_entries s2
                        WHERE s2.key = state_entries.key
                    )
                    """,
                    (cutoff_time,),
                )

                deleted_entries = cursor.rowcount

                # Delete old snapshots
                cursor.execute(
                    "DELETE FROM snapshots WHERE timestamp < ?", (cutoff_time,)
                )
                deleted_snapshots = cursor.rowcount

                self._db_conn.commit()

                self.logger.info(
                    f"Cleaned up {deleted_entries} state entries and {deleted_snapshots} snapshots"
                )
                return deleted_entries + deleted_snapshots

        except Exception as e:
            self.logger.error(f"Failed to cleanup old data: {e}")
            return 0

    async def cleanup(self) -> bool:
        """
        Clean up state manager resources

        Returns:
            bool: True if successful
        """
        try:
            if self._db_conn:
                self._db_conn.close()
                self._db_conn = None

            self.logger.info("State manager cleanup completed")
            return True

        except Exception as e:
            self.logger.error(f"State manager cleanup failed: {e}")
            return False

    # Private methods
    async def _init_database(self):
        """Initialize SQLite database"""
        self._db_conn = sqlite3.connect(str(self.db_path))
        self._db_conn.execute("PRAGMA foreign_keys = ON")

        # Create tables
        self._db_conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS state_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                timestamp REAL NOT NULL,
                version INTEGER NOT NULL,
                encrypted BOOLEAN DEFAULT FALSE,
                metadata TEXT,
                UNIQUE(key, version)
            );

            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id TEXT UNIQUE NOT NULL,
                timestamp REAL NOT NULL,
                metadata TEXT,
                size_bytes INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS snapshot_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                timestamp REAL NOT NULL,
                version INTEGER NOT NULL,
                encrypted BOOLEAN DEFAULT FALSE,
                metadata TEXT,
                FOREIGN KEY (snapshot_id) REFERENCES snapshots (snapshot_id)
            );

            CREATE INDEX IF NOT EXISTS idx_state_key ON state_entries (key);
            CREATE INDEX IF NOT EXISTS idx_state_timestamp ON state_entries (timestamp);
            CREATE INDEX IF NOT EXISTS idx_snapshot_timestamp ON snapshots (timestamp);
        """
        )

        self._db_conn.commit()

    async def _get_state_version(self, key: str) -> int:
        """Get current version for a state key"""
        cursor = self._db_conn.cursor()
        cursor.execute("SELECT MAX(version) FROM state_entries WHERE key = ?", (key,))
        result = cursor.fetchone()
        return result[0] if result[0] is not None else 0

    async def _store_state_entry(self, entry: StateEntry):
        """Store a state entry in database"""
        cursor = self._db_conn.cursor()
        cursor.execute(
            """
            INSERT INTO state_entries (key, value, timestamp, version, encrypted, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                entry.key,
                entry.value,
                entry.timestamp,
                entry.version,
                entry.encrypted,
                json.dumps(entry.metadata),
            ),
        )
        self._db_conn.commit()

    async def _get_state_entry(
        self, key: str, version: Optional[int] = None
    ) -> Optional[StateEntry]:
        """Get a state entry from database"""
        cursor = self._db_conn.cursor()

        if version is not None:
            cursor.execute(
                """
                SELECT key, value, timestamp, version, encrypted, metadata
                FROM state_entries
                WHERE key = ? AND version = ?
                """,
                (key, version),
            )
        else:
            cursor.execute(
                """
                SELECT key, value, timestamp, version, encrypted, metadata
                FROM state_entries
                WHERE key = ?
                ORDER BY version DESC
                LIMIT 1
                """,
                (key,),
            )

        row = cursor.fetchone()
        if row:
            metadata = json.loads(row[5]) if row[5] else {}
            return StateEntry(
                key=row[0],
                value=row[1],
                timestamp=row[2],
                version=row[3],
                encrypted=bool(row[4]),
                metadata=metadata,
            )
        return None

    async def _get_all_latest_entries(self) -> List[StateEntry]:
        """Get latest version of all state entries"""
        cursor = self._db_conn.cursor()
        cursor.execute(
            """
            SELECT key, value, timestamp, version, encrypted, metadata
            FROM state_entries s1
            WHERE version = (
                SELECT MAX(version)
                FROM state_entries s2
                WHERE s2.key = s1.key
            )
            ORDER BY key
            """
        )

        entries = []
        for row in cursor.fetchall():
            metadata = json.loads(row[5]) if row[5] else {}
            entry = StateEntry(
                key=row[0],
                value=row[1],
                timestamp=row[2],
                version=row[3],
                encrypted=bool(row[4]),
                metadata=metadata,
            )
            entries.append(entry)

        return entries

    async def _store_snapshot(self, snapshot: StateSnapshot):
        """Store a snapshot in database"""
        cursor = self._db_conn.cursor()

        # Store snapshot metadata
        cursor.execute(
            """
            INSERT INTO snapshots (snapshot_id, timestamp, metadata, size_bytes)
            VALUES (?, ?, ?, ?)
            """,
            (
                snapshot.snapshot_id,
                snapshot.timestamp,
                json.dumps(snapshot.metadata),
                snapshot.size_bytes,
            ),
        )

        # Store snapshot entries
        for entry in snapshot.state_entries:
            cursor.execute(
                """
                INSERT INTO snapshot_entries
                (snapshot_id, key, value, timestamp, version, encrypted, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.snapshot_id,
                    entry.key,
                    entry.value,
                    entry.timestamp,
                    entry.version,
                    entry.encrypted,
                    json.dumps(entry.metadata),
                ),
            )

        self._db_conn.commit()

    async def _load_snapshot(self, snapshot_id: str) -> Optional[StateSnapshot]:
        """Load a snapshot from database"""
        cursor = self._db_conn.cursor()

        # Load snapshot metadata
        cursor.execute(
            "SELECT timestamp, metadata, size_bytes FROM snapshots WHERE snapshot_id = ?",
            (snapshot_id,),
        )

        row = cursor.fetchone()
        if not row:
            return None

        timestamp, metadata_json, size_bytes = row
        metadata = json.loads(metadata_json) if metadata_json else {}

        # Load snapshot entries
        cursor.execute(
            """
            SELECT key, value, timestamp, version, encrypted, metadata
            FROM snapshot_entries
            WHERE snapshot_id = ?
            ORDER BY key
            """,
            (snapshot_id,),
        )

        entries = []
        for row in cursor.fetchall():
            entry_metadata = json.loads(row[5]) if row[5] else {}
            entry = StateEntry(
                key=row[0],
                value=row[1],
                timestamp=row[2],
                version=row[3],
                encrypted=bool(row[4]),
                metadata=entry_metadata,
            )
            entries.append(entry)

        return StateSnapshot(
            snapshot_id=snapshot_id,
            timestamp=timestamp,
            state_entries=entries,
            metadata=metadata,
            size_bytes=size_bytes,
        )

    async def _load_initial_state(self):
        """Load initial configuration state"""
        # Store sandbox configuration
        await self.set_state("config.sandbox_id", self.config.sandbox_id)
        await self.set_state("config.workspace_path", str(self.config.workspace_path))
        await self.set_state("config.resource_limits", self.config.resource_limits)
        await self.set_state(
            "config.safety_constraints", self.config.safety_constraints
        )
        await self.set_state("config.monitoring_config", self.config.monitoring_config)

        # Store initialization timestamp
        await self.set_state("runtime.initialized_at", asyncio.get_event_loop().time())
