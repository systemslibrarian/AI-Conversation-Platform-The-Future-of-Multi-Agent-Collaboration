"""
Comprehensive Queue Tests – One-File Edition
- Merges basic & comprehensive SQLite/Redis tests
- Adds Redis shim (so tests run without redis installed)
- Adds extra edge-case tests for stubborn branches
Target: 100% coverage for core/queue.py
"""

# --- Redis shim for environments WITHOUT the redis package ---
# Keep this BEFORE has_redis detection and any 'redis.asyncio' import.
try:
    import redis.asyncio  # type: ignore
except Exception:  # pragma: no cover - only used when redis isn't available
    import types, sys

    class _DummyRedis:
        async def xadd(self, *args, **kwargs): return "1-0"
        async def xrevrange(self, *args, **kwargs): return []
        async def xrange(self, *args, **kwargs): return []
        async def get(self, *args, **kwargs): return None
        async def hgetall(self, *args, **kwargs): return {}
        async def hget(self, *args, **kwargs): return None
        async def ping(self, *args, **kwargs): return True
        async def set(self, *args, **kwargs): return True
        async def hset(self, *args, **kwargs): return 1
        async def hincrby(self, *args, **kwargs): return 1

    shim_mod = types.ModuleType("redis.asyncio")
    def from_url(url, decode_responses=True):  # noqa: D401
        """Return dummy Redis client."""
        return _DummyRedis()
    shim_mod.from_url = from_url

    sys.modules["redis"] = types.ModuleType("redis")
    sys.modules["redis.asyncio"] = shim_mod
# --- End shim ---

import pytest
import asyncio
import tempfile
import json
from pathlib import Path
import logging
from unittest.mock import AsyncMock, patch, MagicMock
import builtins
import sqlite3
from filelock import Timeout

# Import exception types with a safe fallback so test expectations don't break
from core.queue import SQLiteQueue, RedisQueue, create_queue, DatabaseError
try:
    from core.queue import ValidationError  # preferred if your code defines it
except Exception:  # pragma: no cover
    # Fallback: alias to DatabaseError so tests still validate behavior
    class ValidationError(DatabaseError):  # type: ignore
        pass

from core.config import config

# === Detect if redis is available (shim makes this True even without real redis) ===
has_redis = True
try:
    import redis.asyncio  # noqa: F401
except ImportError:
    has_redis = False


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_db():
    """Create temporary database"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    if db_path.exists():
        db_path.unlink()
    lock_file = Path(f"{db_path}.lock")
    if lock_file.exists():
        lock_file.unlink()


@pytest.fixture
def logger():
    """Create test logger"""
    return logging.getLogger("test_queue")


@pytest.fixture
def mock_redis():
    """Create mock Redis client"""
    redis_mock = AsyncMock()
    redis_mock.xadd.return_value = "1234567890-0"
    redis_mock.xrevrange.return_value = []
    redis_mock.xrange.return_value = []
    redis_mock.get.return_value = None
    redis_mock.hgetall.return_value = {}
    redis_mock.hget.return_value = None
    redis_mock.ping.return_value = True
    redis_mock.set.return_value = True
    redis_mock.hset.return_value = 1
    redis_mock.hincrby.return_value = 1
    return redis_mock


# ============================================================================
# SQLITE QUEUE – BASIC TESTS
# ============================================================================

class TestSQLiteQueueBasic:
    """Basic SQLite queue functionality tests"""

    @pytest.mark.asyncio
    async def test_queue_initialization(self, temp_db, logger):
        """Test queue initialization"""
        queue = SQLiteQueue(temp_db, logger)
        data = await queue.load()
        assert "messages" in data
        assert "metadata" in data
        assert data["metadata"]["version"] == "5.0"

    @pytest.mark.asyncio
    async def test_add_and_context(self, temp_db, logger):
        """Test adding messages and retrieving context"""
        queue = SQLiteQueue(temp_db, logger)

        await queue.add_message("Claude", "Hello, world!", {"tokens": 10})
        await queue.add_message("ChatGPT", "Second message", {"tokens": 5})

        ctx = await queue.get_context(2)
        assert len(ctx) == 2
        assert ctx[0]["sender"] == "Claude"
        assert ctx[1]["sender"] == "ChatGPT"

        last = await queue.get_last_sender()
        assert last == "ChatGPT"

    @pytest.mark.asyncio
    async def test_termination(self, temp_db, logger):
        """Test conversation termination"""
        queue = SQLiteQueue(temp_db, logger)

        assert not await queue.is_terminated()

        await queue.mark_terminated("done")
        assert await queue.is_terminated()
        assert (await queue.get_termination_reason()) == "done"

    @pytest.mark.asyncio
    async def test_concurrent_writes(self, temp_db, logger):
        """Test concurrent message writes"""
        queue = SQLiteQueue(temp_db, logger)

        async def add(sender):
            for i in range(10):
                await queue.add_message(sender, f"m{i}", {"tokens": 1})

        await asyncio.gather(add("Claude"), add("ChatGPT"))

        data = await queue.load()
        assert len(data["messages"]) == 20
        assert data["metadata"]["total_turns"] == 20


# ============================================================================
# SQLITE QUEUE – COMPREHENSIVE TESTS
# ============================================================================

class TestSQLiteQueueComprehensive:
    """Comprehensive SQLite queue tests"""

    @pytest.mark.asyncio
    async def test_empty_content_rejected(self, temp_db, logger):
        """Test empty content is rejected"""
        queue = SQLiteQueue(temp_db, logger)

        with pytest.raises(ValidationError, match="Message content cannot be empty"):
            await queue.add_message("Agent1", "", {})

        with pytest.raises(ValidationError, match="Message content cannot be empty"):
            await queue.add_message("Agent1", "   ", {})

    @pytest.mark.asyncio
    async def test_message_too_long_rejected(self, temp_db, logger):
        """Test messages exceeding max length are rejected"""
        queue = SQLiteQueue(temp_db, logger)
        long_message = "x" * (config.MAX_MESSAGE_LENGTH + 1)
        with pytest.raises(ValidationError, match="Message too long"):
            await queue.add_message("Agent1", long_message, {})

    @pytest.mark.asyncio
    async def test_sender_normalization(self, temp_db, logger):
        """Test sender names are normalized"""
        queue = SQLiteQueue(temp_db, logger)

        await queue.add_message("claude", "Message 1", {})
        await queue.add_message("CLAUDE", "Message 2", {})
        await queue.add_message("Claude", "Message 3", {})
        await queue.add_message("simulAtor", "Message 4", {})

        data = await queue.load()
        messages = data["messages"]
        assert messages[3]["sender"] == "Simulator"
        assert all(msg["sender"] in {"Claude", "Simulator"} for msg in messages)

    @pytest.mark.asyncio
    async def test_token_accumulation(self, temp_db, logger):
        """Test token counts accumulate correctly"""
        queue = SQLiteQueue(temp_db, logger)

        await queue.add_message("Agent1", "Message 1", {"tokens": 50})
        await queue.add_message("Agent2", "Message 2", {"tokens": 75})
        await queue.add_message("Agent1", "Message 3", {"tokens": 100})
        await queue.add_message("Agent1", "Message 4", None)  # No tokens

        data = await queue.load()
        assert data["metadata"]["total_tokens"] == 225

    @pytest.mark.asyncio
    async def test_agent_turn_counting(self, temp_db, logger):
        """Test individual agent turn counting"""
        queue = SQLiteQueue(temp_db, logger)

        await queue.add_message("Agent1", "M1", {"tokens": 10})
        await queue.add_message("Agent2", "M2", {"tokens": 10})
        await queue.add_message("Agent1", "M3", {"tokens": 10})
        await queue.add_message("Agent1", "M4", {"tokens": 10})
        await queue.add_message("Agent2", "M5", {"tokens": 10})

        data = await queue.load()

        agent1_turns = sum(1 for msg in data["messages"] if msg["sender"] == "Agent1")
        agent2_turns = sum(1 for msg in data["messages"] if msg["sender"] == "Agent2")

        assert agent1_turns == 3
        assert agent2_turns == 2
        assert data["metadata"]["total_turns"] == 5

    @pytest.mark.asyncio
    async def test_context_limit(self, temp_db, logger):
        """Test context retrieval respects max messages"""
        queue = SQLiteQueue(temp_db, logger)

        for i in range(20):
            await queue.add_message("Agent1", f"Message {i}", {})

        context = await queue.get_context(max_messages=5)
        assert len(context) == 5
        assert "Message 19" in context[-1]["content"]

    @pytest.mark.asyncio
    async def test_get_last_sender_empty_queue(self, temp_db, logger):
        """Test get_last_sender with empty queue"""
        queue = SQLiteQueue(temp_db, logger)
        last_sender = await queue.get_last_sender()
        assert last_sender is None

    @pytest.mark.asyncio
    async def test_termination_persistence(self, temp_db, logger):
        """Test termination state persists across instances"""
        queue = SQLiteQueue(temp_db, logger)
        await queue.add_message("Agent1", "Message", {"tokens": 10})
        await queue.mark_terminated("test_reason")

        queue2 = SQLiteQueue(temp_db, logger)
        assert await queue2.is_terminated()
        assert await queue2.get_termination_reason() == "test_reason"

    @pytest.mark.asyncio
    async def test_get_termination_reason_null(self, temp_db, logger):
        """Test getting termination reason when null"""
        queue = SQLiteQueue(temp_db, logger)
        reason = await queue.get_termination_reason()
        assert reason == "unknown"

    @pytest.mark.asyncio
    async def test_initial_metadata(self, temp_db, logger):
        """Test initial metadata is set correctly"""
        queue = SQLiteQueue(temp_db, logger)
        data = await queue.load()
        meta = data["metadata"]
        assert "conversation_id" in meta
        assert "started_at" in meta
        assert meta["total_turns"] == 0
        assert meta["version"] == "5.0"

    @pytest.mark.asyncio
    async def test_metadata_updates(self, temp_db, logger):
        """Test metadata updates as conversation progresses"""
        queue = SQLiteQueue(temp_db, logger)
        await queue.add_message("Claude", "M1", {"tokens": 50})
        await queue.add_message("ChatGPT", "M2", {"tokens": 75})
        data = await queue.load()
        meta = data["metadata"]
        assert meta["total_turns"] == 2
        assert meta["claude_turns"] == 1
        assert meta["chatgpt_turns"] == 1
        assert meta["total_tokens"] == 125

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, temp_db, logger):
        """Test health check when healthy"""
        queue = SQLiteQueue(temp_db, logger)
        health = await queue.health_check()
        assert health["healthy"] is True
        assert health["checks"]["database"] == "ok"
        assert health["checks"]["lock"] == "ok"
        assert "timestamp" in health

    # --- NEW TEST 1: Lock Timeout Failure ---
    @pytest.mark.asyncio
    async def test_add_message_lock_timeout(self, temp_db, logger):
        """add_message handles FileLock Timeout and raises DatabaseError; logs lock_timeout"""
        queue = SQLiteQueue(temp_db, logger)

        # Patch the lock's acquire method to raise the Timeout exception immediately
        with patch.object(queue.lock, "acquire", side_effect=Timeout("Lock acquisition timed out")):
            # Assert that the expected DatabaseError is raised
            with pytest.raises(DatabaseError, match="Failed to acquire lock"):
                await queue.add_message("TestAgent", "Test content", {"tokens": 10})

            # Verify that a 'lock_timeout' event is logged via log_event in core.queue
            with patch('core.queue.log_event') as mock_log_event:
                with pytest.raises(DatabaseError):
                    await queue.add_message("TestAgent", "Test content", {"tokens": 10})
                mock_log_event.assert_called_with(queue.logger, "lock_timeout", {"action": "add_message"})

    # --- NEW TEST 2: Database Rollback Failure ---
    @pytest.mark.asyncio
    async def test_add_message_rollback_on_failure(self, temp_db, logger):
        """DB failure inside add_message triggers rollback and raises DatabaseError."""
        queue = SQLiteQueue(temp_db, logger)

        class MockOperationalError(sqlite3.OperationalError):
            pass

        # Patch sqlite3.connect used inside add_message
        with patch('sqlite3.connect') as mock_connect:
            mock_conn = mock_connect.return_value

            # execute(BEGIN IMMEDIATE) -> execute(INSERT) -> execute(UPDATE)
            mock_conn.execute.side_effect = [
                MagicMock(),  # BEGIN IMMEDIATE ok
                MockOperationalError("DB is full or corrupt"),  # INSERT fails
                MagicMock(),  # (would be UPDATE) not reached
            ]

            with pytest.raises(DatabaseError, match="Failed to add message"):
                await queue.add_message("TestAgent", "Test content", {"tokens": 10})

            mock_conn.rollback.assert_called_once()
            mock_conn.close.assert_called()


# ============================================================================
# REDIS QUEUE TESTS
# ============================================================================

@pytest.mark.skipif(not has_redis, reason="redis package not installed")
class TestRedisQueue:
    """Test RedisQueue implementation"""

    @pytest.mark.asyncio
    async def test_redis_init_without_package(self, logger):
        """Test Redis queue fails gracefully without redis package"""
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name.startswith("redis"):
                raise ImportError("No module named redis")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", side_effect=mock_import):
            with pytest.raises(ImportError, match="redis package required"):
                RedisQueue("redis://localhost:6379/0", logger)

    @pytest.mark.asyncio
    async def test_add_message(self, logger, mock_redis):
        """Test adding message to Redis"""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            queue = RedisQueue("redis://localhost:6379/0", logger)
            result = await queue.add_message("Agent1", "Test message", {"tokens": 50})

            assert mock_redis.xadd.called
            assert mock_redis.hincrby.called
            assert "id" in result

    @pytest.mark.asyncio
    async def test_get_context(self, logger, mock_redis):
        """Test getting context from Redis"""
        mock_redis.xrevrange.return_value = [
            (
                "1234567891-0",
                {
                    "sender": "Agent1",
                    "content": "Message 2",
                    "metadata": json.dumps({"tokens": 20}),
                },
            ),
            (
                "1234567890-0",
                {
                    "sender": "Agent2",
                    "content": "Message 1",
                    "metadata": json.dumps({"tokens": 10}),
                },
            ),
        ]

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            queue = RedisQueue("redis://localhost:6379/0", logger)
            messages = await queue.get_context(max_messages=10)

            assert len(messages) == 2
            assert messages[0]["sender"] == "Agent2"
            assert messages[1]["sender"] == "Agent1"
            assert messages[1]["metadata"]["tokens"] == 20

    @pytest.mark.asyncio
    async def test_get_last_sender(self, logger, mock_redis):
        """Test getting last sender from Redis"""
        mock_redis.xrevrange.return_value = [
            ("1234567890-0", {"sender": "Agent1", "content": "Last"})
        ]
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            queue = RedisQueue("redis://localhost:6379/0", logger)
            assert await queue.get_last_sender() == "Agent1"

    @pytest.mark.asyncio
    async def test_get_last_sender_empty(self, logger, mock_redis):
        """Test getting last sender when no messages"""
        mock_redis.xrevrange.return_value = []
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            queue = RedisQueue("redis://localhost:6379/0", logger)
            assert await queue.get_last_sender() is None

    @pytest.mark.asyncio
    async def test_is_terminated(self, logger, mock_redis):
        """Test checking if conversation terminated"""
        mock_redis.get.side_effect = ["0", "1"]
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            queue = RedisQueue("redis://localhost:6379/0", logger)
            assert not await queue.is_terminated()
            assert await queue.is_terminated()

    @pytest.mark.asyncio
    async def test_mark_terminated(self, logger, mock_redis):
        """Test marking conversation as terminated"""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            queue = RedisQueue("redis://localhost:6379/0", logger)
            await queue.mark_terminated("test_reason")

            assert mock_redis.set.call_count == 2
            mock_redis.set.assert_any_call(f"{queue.conv_id}:terminated", "1")
            mock_redis.set.assert_any_call(f"{queue.conv_id}:reason", "test_reason")
            assert mock_redis.hset.called

    @pytest.mark.asyncio
    async def test_get_termination_reason(self, logger, mock_redis):
        """Test getting termination reason"""
        mock_redis.get.side_effect = ["max_turns", None]
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            queue = RedisQueue("redis://localhost:6379/0", logger)
            assert await queue.get_termination_reason() == "max_turns"
            assert await queue.get_termination_reason() == "unknown"

    @pytest.mark.asyncio
    async def test_load(self, logger, mock_redis):
        """Test loading all data from Redis"""
        mock_redis.xrange.return_value = [("1-0", {"sender": "Agent1", "content": "M1"})]
        mock_redis.hgetall.return_value = {"total_turns": "1"}
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            queue = RedisQueue("redis://localhost:6379/0", logger)
            data = await queue.load()
            assert len(data["messages"]) == 1

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, logger, mock_redis):
        """Test health check when Redis is healthy"""
        mock_redis.ping.return_value = True
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            queue = RedisQueue("redis://localhost:6379/0", logger)
            health = await queue.health_check()
            assert health["healthy"] is True


# ============================================================================
# FACTORY FUNCTION TESTS
# ============================================================================

class TestQueueFactory:
    """Test queue factory function"""

    @pytest.mark.asyncio
    async def test_factory_creates_sqlite(self, temp_db, logger):
        """Test factory creates SQLite queue"""
        queue = create_queue(str(temp_db), logger, use_redis=False)
        assert isinstance(queue, SQLiteQueue)

    @pytest.mark.asyncio
    @pytest.mark.skipif(not has_redis, reason="redis package not installed")
    async def test_factory_creates_redis_with_flag(self, logger):
        """Test factory creates Redis queue with flag"""
        with patch("redis.asyncio.from_url", return_value=AsyncMock()):
            queue = create_queue("redis://localhost:6379/0", logger, use_redis=True)
            assert isinstance(queue, RedisQueue)

    @pytest.mark.asyncio
    @pytest.mark.skipif(not has_redis, reason="redis package not installed")
    async def test_factory_creates_redis_with_url(self, logger):
        """Test factory creates Redis queue from URL"""
        with patch("redis.asyncio.from_url", return_value=AsyncMock()):
            queue = create_queue("redis://localhost:6379/0", logger)
            assert isinstance(queue, RedisQueue)


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestErrorHandling:
    """Test error handling in queue operations"""

    @pytest.mark.asyncio
    async def test_queue_survives_errors(self, temp_db, logger):
        """Queue continues working after errors"""
        queue = SQLiteQueue(temp_db, logger)
        await queue.add_message("Agent1", "Valid", {"tokens": 10})

        with pytest.raises(ValidationError):
            await queue.add_message("Agent1", "", {"tokens": 10})

        await queue.add_message("Agent2", "Also valid", {"tokens": 10})
        data = await queue.load()
        assert data["metadata"]["total_turns"] == 2


# ============================================================================
# STRESS TESTS
# ============================================================================

class TestStressScenarios:
    """Test under stress conditions"""

    @pytest.mark.asyncio
    async def test_many_messages(self, temp_db, logger):
        """Handling many messages"""
        queue = SQLiteQueue(temp_db, logger)
        for i in range(100):
            sender = f"Agent{i % 3 + 1}"
            await queue.add_message(sender, f"Message {i}", {"tokens": 10})
        data = await queue.load()
        assert data["metadata"]["total_turns"] == 100
        assert len(data["messages"]) == 100

    @pytest.mark.asyncio
    async def test_rapid_termination_checks(self, temp_db, logger):
        """Rapid termination checking"""
        queue = SQLiteQueue(temp_db, logger)
        results = await asyncio.gather(*[queue.is_terminated() for _ in range(50)])
        assert all(not r for r in results)

        await queue.mark_terminated("test")
        results = await asyncio.gather(*[queue.is_terminated() for _ in range(50)])
        assert all(r for r in results)


# ============================================================================
# EXTRA EDGE-CASE TESTS TO LIFT COVERAGE
# ============================================================================

@pytest.mark.asyncio
async def test_sqlite_get_context_malformed_json(temp_db, logger):
    """Manually insert malformed JSON to force metadata parse fallback {}"""
    q = SQLiteQueue(temp_db, logger)
    conn = sqlite3.connect(str(temp_db))
    conn.execute(
        "INSERT INTO messages (sender, content, timestamp, hash, metadata) VALUES (?,?,?,?,?)",
        ("AgentX", "hi", "2020-01-01T00:00:00", "abc", "{not-json"),
    )
    conn.commit()
    conn.close()

    ctx = await q.get_context(1)
    assert ctx[0]["sender"] == "AgentX"
    assert ctx[0]["metadata"] == {}  # malformed json -> {}

@pytest.mark.asyncio
async def test_mark_terminated_failure_logs(temp_db, logger):
    """Force sqlite connect failure to hit 'termination_failed' logging branch"""
    q = SQLiteQueue(temp_db, logger)
    with patch("core.queue.sqlite3.connect", side_effect=Exception("boom")), \
         patch("core.queue.log_event") as mock_log:
        await q.mark_terminated("any")
        mock_log.assert_any_call(logger, "termination_failed", {"error": "boom"})

@pytest.mark.asyncio
async def test_health_check_db_error_and_lock_timeout(temp_db, logger):
    """Patch db error + lock timeout to exercise both failure branches"""
    q = SQLiteQueue(temp_db, logger)
    with patch("core.queue.sqlite3.connect", side_effect=Exception("db-bad")), \
         patch.object(q.lock, "acquire", side_effect=Timeout("nope")):
        health = await q.health_check()
        assert health["healthy"] is False
        assert health["checks"]["database"].startswith("error:")
        assert health["checks"]["lock"] == "timeout"

@pytest.mark.asyncio
async def test_sender_map_variants(temp_db, logger):
    """Ensure normalization for common agent labels"""
    q = SQLiteQueue(temp_db, logger)
    await q.add_message("simulator", "a", {})
    await q.add_message("grok", "b", {})
    await q.add_message("gemini", "c", {})
    await q.add_message("perplexity", "d", {})
    data = await q.load()
    senders = [m["sender"] for m in data["messages"]]
    assert senders == ["Simulator", "Grok", "Gemini", "Perplexity"]

@pytest.mark.asyncio
async def test_load_null_and_digit_conversion(temp_db, logger):
    """Validate 'null' → None and digit strings → ints in metadata load"""
    q = SQLiteQueue(temp_db, logger)
    data = await q.load()
    meta = data["metadata"]
    assert meta["termination_reason"] is None  # "null" normalized to None
    assert isinstance(meta["total_turns"], int)  # "0" normalized to 0 (int)

@pytest.mark.asyncio
async def test_health_check_lock_release_failure(temp_db, logger):
    """Simulate lock release failing; ensure health still reports ok for lock check."""
    q = SQLiteQueue(temp_db, logger)
    with patch.object(q.lock, "acquire", return_value=None), \
         patch.object(q.lock, "release", side_effect=Exception("Release failed")):
        health = await q.health_check()
        assert health["healthy"] is True
        assert health["checks"]["lock"] == "ok"


# ============================================================================
# RUN TESTS (if executed directly)
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=core.queue", "--cov-report=term-missing"])
