"""Async Message Queue - v5.0 ENTERPRISE EDITION
- Thread-safe async SQLite implementation
- Optional Redis backend for distributed deployments
- Atomic operations with proper transaction management
- Comprehensive error handling
"""

import sqlite3
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any, Protocol, Tuple
from datetime import datetime
from filelock import FileLock, Timeout

from .common import log_event, hash_message
from .config import config


class DatabaseError(Exception):
    """Base exception for database operations"""

    pass


class ValidationError(Exception):
    """Raised when input validation fails"""

    pass


class QueueInterface(Protocol):
    """Protocol defining the queue interface"""

    async def add_message(self, sender: str, content: str, metadata: Optional[Dict] = None) -> Dict:
        """Add a message to the queue"""
        ...

    async def get_context(self, max_messages: int = 10) -> List[Dict]:
        """Get recent conversation context"""
        ...

    async def get_last_sender(self) -> Optional[str]:
        """Get the sender of the last message"""
        ...

    async def is_terminated(self) -> bool:
        """Check if conversation is terminated"""
        ...

    async def mark_terminated(self, reason: str) -> None:
        """Mark conversation as terminated"""
        ...

    async def get_termination_reason(self) -> str:
        """Get termination reason"""
        ...

    async def load(self) -> Dict:
        """Load all messages and metadata"""
        ...


class SQLiteQueue:
    """Async SQLite-based message queue with atomic operations"""

    def __init__(self, filepath: Path, logger, lock_timeout: int = 30) -> None:
        self.filepath = Path(filepath)
        self.logger = logger
        self.lock_timeout = lock_timeout

        # File-based lock for inter-process synchronization
        self.lock = FileLock(f"{filepath}.lock", timeout=lock_timeout)

        # Initialize database
        self._init_db()

        log_event(
            self.logger,
            "queue_initialized",
            {"filepath": str(self.filepath), "type": "sqlite"},
        )

    def _init_db(self) -> None:
        """Initialize database schema"""
        conn = sqlite3.connect(str(self.filepath), timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                hash TEXT NOT NULL,
                metadata TEXT
            )
        """)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_sender ON messages(sender)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON messages(timestamp DESC)")

        # Initialize metadata if not exists
        existing = conn.execute("SELECT value FROM metadata WHERE key='conversation_id'").fetchone()

        if existing is None:
            conv_id = f"conv_{int(time.time())}"
            initial_metadata = {
                "conversation_id": conv_id,
                "started_at": datetime.now().isoformat(),
                "total_turns": "0",
                "claude_turns": "0",
                "chatgpt_turns": "0",
                "gemini_turns": "0",
                "grok_turns": "0",
                "perplexity_turns": "0",
                "total_tokens": "0",
                "terminated": "0",
                "termination_reason": "null",
                "version": "5.0",
            }

            for key, value in initial_metadata.items():
                conn.execute("INSERT INTO metadata (key, value) VALUES (?, ?)", (key, value))

        conn.commit()
        conn.close()

    def _validate_message(self, sender: str, content: str) -> Tuple[str, str]:
        """Validate and normalize inputs"""
        sender_map = {
            "claude": "Claude",
            "chatgpt": "ChatGPT",
            "gemini": "Gemini",
            "grok": "Grok",
            "perplexity": "Perplexity",
            "simulator": "Simulator",
        }
        sender_normalized = sender_map.get(sender.strip().lower(), sender.strip())

        if not content or len(content.strip()) == 0:
            raise ValidationError("Message content cannot be empty")

        if len(content) > config.MAX_MESSAGE_LENGTH:
            raise ValidationError(f"Message too long (max {config.MAX_MESSAGE_LENGTH} chars)")

        return sender_normalized, content.strip()

    async def add_message(
        self, sender: str, content: str, metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Atomically add a message - ALL OPERATIONS IN ONE TRANSACTION
        This eliminates race conditions
        """
        await asyncio.sleep(0)  # Yield to event loop

        sender, content = self._validate_message(sender, content)

        msg: Dict[str, Any] = {
            "sender": sender,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "hash": hash_message(content),
            "metadata": json.dumps(metadata or {}),
        }

        try:
            with self.lock:
                conn = sqlite3.connect(str(self.filepath))
                conn.execute("BEGIN IMMEDIATE")

                try:
                    # Insert message
                    cursor = conn.execute(
                        """
                        INSERT INTO messages (sender, content, timestamp, hash, metadata)
                        VALUES (?, ?, ?, ?, ?)
                    """,
                        (
                            msg["sender"],
                            msg["content"],
                            msg["timestamp"],
                            msg["hash"],
                            msg["metadata"],
                        ),
                    )
                    msg_id = cursor.lastrowid

                    # Update total turns
                    conn.execute("""
                        UPDATE metadata 
                        SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT)
                        WHERE key='total_turns'
                    """)

                    # Update sender-specific counter
                    sender_key = f"{sender.lower()}_turns"
                    conn.execute(
                        """
                        UPDATE metadata 
                        SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT)
                        WHERE key=?
                    """,
                        (sender_key,),
                    )

                    # Update token counter if provided
                    if metadata and "tokens" in metadata:
                        conn.execute(
                            """
                            UPDATE metadata 
                            SET value = CAST(CAST(value AS INTEGER) + ? AS TEXT)
                            WHERE key='total_tokens'
                        """,
                            (int(metadata["tokens"]),),
                        )

                    conn.commit()

                    log_event(
                        self.logger,
                        "message_added",
                        {"id": msg_id, "sender": sender, "length": len(content)},
                    )

                    return {**msg, "id": msg_id}

                except Exception as e:
                    conn.rollback()
                    raise DatabaseError(f"Failed to add message: {e}")
                finally:
                    conn.close()

        except Timeout:
            log_event(self.logger, "lock_timeout", {"action": "add_message"})
            raise DatabaseError("Failed to acquire lock")

    async def get_context(self, max_messages: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversation context"""
        await asyncio.sleep(0)

        conn = sqlite3.connect(str(self.filepath))
        conn.row_factory = sqlite3.Row

        try:
            rows = conn.execute(
                "SELECT * FROM messages ORDER BY id DESC LIMIT ?", (max_messages,)
            ).fetchall()

            # convert rows into plain dicts (typing-friendly)
            messages: List[Dict[str, Any]] = [dict(row) for row in reversed(rows)]

            # Parse metadata JSON
            for msg in messages:
                try:
                    raw_meta = msg.get("metadata")
                    if isinstance(raw_meta, str) and raw_meta:
                        msg["metadata"] = json.loads(raw_meta)
                    else:
                        msg["metadata"] = {}
                except json.JSONDecodeError:
                    msg["metadata"] = {}

            return messages
        finally:
            conn.close()

    async def get_last_sender(self) -> Optional[str]:
        """Get the sender of the last message"""
        await asyncio.sleep(0)

        conn = sqlite3.connect(str(self.filepath))
        try:
            row = conn.execute("SELECT sender FROM messages ORDER BY id DESC LIMIT 1").fetchone()
            if row is None:
                return None
            # sqlite3.Row supports mapping access; convert to dict for mypy
            row_dict = dict(row)
            sender = row_dict.get("sender")
            return sender if isinstance(sender, str) else None
        finally:
            conn.close()

    async def is_terminated(self) -> bool:
        """Check if conversation is terminated"""
        await asyncio.sleep(0)

        conn = sqlite3.connect(str(self.filepath))
        try:
            row = conn.execute("SELECT value FROM metadata WHERE key='terminated'").fetchone()
            if row is None:
                return False
            row_dict = dict(row)
            val = row_dict.get("value")
            return str(val) == "1"
        finally:
            conn.close()

    async def mark_terminated(self, reason: str) -> None:
        """Mark conversation as terminated"""
        await asyncio.sleep(0)

        try:
            with self.lock:
                conn = sqlite3.connect(str(self.filepath))
                try:
                    now = datetime.now().isoformat()
                    conn.execute("UPDATE metadata SET value = '1' WHERE key='terminated'")
                    conn.execute(
                        "UPDATE metadata SET value = ? WHERE key='termination_reason'",
                        (reason,),
                    )
                    conn.execute(
                        "INSERT OR REPLACE INTO metadata (key, value) VALUES ('ended_at', ?)",
                        (now,),
                    )
                    conn.commit()

                    log_event(self.logger, "conversation_terminated", {"reason": reason})
                finally:
                    conn.close()
        except Exception as e:
            log_event(self.logger, "termination_failed", {"error": str(e)})

    async def get_termination_reason(self) -> str:
        """Get termination reason"""
        await asyncio.sleep(0)

        conn = sqlite3.connect(str(self.filepath))
        try:
            row = conn.execute(
                "SELECT value FROM metadata WHERE key='termination_reason'"
            ).fetchone()
            if row is None:
                return "unknown"
            row_dict = dict(row)
            val = row_dict.get("value")
            if val is None or str(val) == "null":
                return "unknown"
            return str(val)
        finally:
            conn.close()

    async def load(self) -> Dict[str, Any]:
        """Load all messages and metadata"""
        await asyncio.sleep(0)

        conn = sqlite3.connect(str(self.filepath))
        conn.row_factory = sqlite3.Row

        try:
            messages = [
                dict(row) for row in conn.execute("SELECT * FROM messages ORDER BY id").fetchall()
            ]

            metadata_rows = conn.execute("SELECT key, value FROM metadata").fetchall()
            metadata: Dict[str, Any] = {}
            for row in metadata_rows:
                row_dict = dict(row)
                k = row_dict.get("key")
                v = row_dict.get("value")
                # normalize "null" to None
                if k is not None:
                    if isinstance(v, str) and v == "null":
                        metadata[k] = None
                    elif isinstance(v, str) and v.isdigit():
                        metadata[k] = int(v)
                    else:
                        metadata[k] = v
            return {"messages": messages, "metadata": metadata}
        finally:
            conn.close()

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        await asyncio.sleep(0)

        health: Dict[str, Any] = {
            "healthy": True,
            "checks": {},
            "timestamp": datetime.now().isoformat(),
        }

        # Database connectivity
        try:
            conn = sqlite3.connect(str(self.filepath))
            conn.execute("SELECT 1").fetchone()
            conn.close()
            health["checks"]["database"] = "ok"
        except Exception as e:
            health["checks"]["database"] = f"error: {e}"
            health["healthy"] = False

        # Lock availability
        try:
            # FileLock.acquire() returns None on success; use a boolean style check for clarity
            acquired = False
            try:
                self.lock.acquire(timeout=1)
                acquired = True
            except Timeout:
                acquired = False

            if acquired:
                try:
                    self.lock.release()
                except Exception:
                    pass
                health["checks"]["lock"] = "ok"
            else:
                health["checks"]["lock"] = "timeout"
                health["healthy"] = False
        except Exception as e:
            health["checks"]["lock"] = f"error: {e}"
            health["healthy"] = False

        return health


class RedisQueue:
    """Redis-based message queue for distributed deployments"""

    def __init__(self, url: str, logger) -> None:
        try:
            import redis.asyncio as redis  # type: ignore[import-untyped]
        except ImportError:
            raise ImportError("redis package required for RedisQueue. Install: pip install redis")

        self.r = redis.from_url(url, decode_responses=True)
        self.logger = logger
        self.conv_id = f"conv:{int(time.time())}"

        log_event(self.logger, "queue_initialized", {"type": "redis", "conv_id": self.conv_id})

    async def add_message(
        self, sender: str, content: str, metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Add message to Redis stream"""
        msg: Dict[str, Any] = {
            "sender": sender,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": json.dumps(metadata or {}),
        }

        msg_id = await self.r.xadd(f"{self.conv_id}:messages", msg)

        # Update counters
        await self.r.hincrby(f"{self.conv_id}:meta", "total_turns", 1)
        await self.r.hincrby(f"{self.conv_id}:meta", f"{sender.lower()}_turns", 1)

        if metadata and "tokens" in metadata:
            await self.r.hincrby(f"{self.conv_id}:meta", "total_tokens", int(metadata["tokens"]))

        log_event(self.logger, "message_added", {"sender": sender, "stream_id": msg_id})

        return {**msg, "id": msg_id}

    async def get_context(self, max_messages: int = 10) -> List[Dict[str, Any]]:
        """Get recent messages from Redis stream"""
        entries = await self.r.xrevrange(f"{self.conv_id}:messages", count=max_messages)
        messages: List[Dict[str, Any]] = []

        for stream_id, fields in reversed(entries):
            msg = dict(fields)
            msg["id"] = stream_id
            try:
                msg["metadata"] = json.loads(msg.get("metadata", "{}"))
            except json.JSONDecodeError:
                msg["metadata"] = {}
            messages.append(msg)

        return messages

    async def get_last_sender(self) -> Optional[str]:
        """Get last sender from Redis"""
        entries = await self.r.xrevrange(f"{self.conv_id}:messages", count=1)
        if entries:
            sender = entries[0][1].get("sender")
            return str(sender) if sender is not None else None
        return None

    async def is_terminated(self) -> bool:
        """Check if conversation terminated"""
        value = await self.r.get(f"{self.conv_id}:terminated")
        return str(value) == "1"

    async def mark_terminated(self, reason: str) -> None:
        """Mark conversation as terminated"""
        await self.r.set(f"{self.conv_id}:terminated", "1")
        await self.r.set(f"{self.conv_id}:reason", reason)
        await self.r.hset(f"{self.conv_id}:meta", "ended_at", datetime.now().isoformat())

        log_event(self.logger, "conversation_terminated", {"reason": reason})

    async def get_termination_reason(self) -> str:
        """Get termination reason"""
        reason = await self.r.get(f"{self.conv_id}:reason")
        return reason or "unknown"

    async def load(self) -> Dict[str, Any]:
        """Load all messages and metadata"""
        # Get all messages
        entries = await self.r.xrange(f"{self.conv_id}:messages")
        messages = [dict(fields) for _, fields in entries]

        # Get metadata
        metadata = await self.r.hgetall(f"{self.conv_id}:meta")

        return {"messages": messages, "metadata": metadata}

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        health: Dict[str, Any] = {
            "healthy": True,
            "checks": {},
            "timestamp": datetime.now().isoformat(),
        }

        try:
            await self.r.ping()
            health["checks"]["redis"] = "ok"
        except Exception as e:
            health["checks"]["redis"] = f"error: {e}"
            health["healthy"] = False

        return health


def create_queue(filepath_or_url: str, logger, use_redis: bool = False) -> QueueInterface:
    """Factory function to create appropriate queue"""
    if use_redis or filepath_or_url.startswith("redis://"):
        return RedisQueue(filepath_or_url, logger)
    else:
        return SQLiteQueue(Path(filepath_or_url), logger)
