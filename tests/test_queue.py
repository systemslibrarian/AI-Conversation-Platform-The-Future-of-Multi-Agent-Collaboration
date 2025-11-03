"""Test suite for queue module"""

import pytest
import asyncio
import tempfile
from pathlib import Path
import logging

from core.queue import SQLiteQueue, create_queue


@pytest.fixture
def temp_db():
    """Create temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    # Cleanup
    if db_path.exists():
        db_path.unlink()
    lock_file = Path(f"{db_path}.lock")
    if lock_file.exists():
        lock_file.unlink()


@pytest.fixture
def logger():
    """Create test logger"""
    return logging.getLogger("test")


@pytest.mark.asyncio
async def test_queue_initialization(temp_db, logger):
    """Test queue initialization"""
    queue = SQLiteQueue(temp_db, logger)

    data = await queue.load()
    assert "messages" in data
    assert "metadata" in data
    assert data["metadata"]["version"] == "5.0"


@pytest.mark.asyncio
async def test_add_message(temp_db, logger):
    """Test adding a message"""
    queue = SQLiteQueue(temp_db, logger)

    msg = await queue.add_message("Claude", "Hello, world!", {"tokens": 10})

    assert msg["sender"] == "Claude"
    assert msg["content"] == "Hello, world!"
    assert "id" in msg

    # Verify in database
    data = await queue.load()
    assert len(data["messages"]) == 1
    assert data["metadata"]["total_turns"] == 1
    assert data["metadata"]["claude_turns"] == 1
    assert data["metadata"]["total_tokens"] == 10


@pytest.mark.asyncio
async def test_get_context(temp_db, logger):
    """Test getting conversation context"""
    queue = SQLiteQueue(temp_db, logger)

    # Add multiple messages
    await queue.add_message("Claude", "Message 1", {"tokens": 5})
    await queue.add_message("ChatGPT", "Message 2", {"tokens": 6})
    await queue.add_message("Claude", "Message 3", {"tokens": 7})

    # Get context
    context = await queue.get_context(max_messages=2)

    assert len(context) == 2
    assert context[0]["sender"] == "ChatGPT"
    assert context[1]["sender"] == "Claude"


@pytest.mark.asyncio
async def test_termination(temp_db, logger):
    """Test conversation termination"""
    queue = SQLiteQueue(temp_db, logger)

    # Initially not terminated
    assert not await queue.is_terminated()

    # Mark as terminated
    await queue.mark_terminated("test_reason")

    # Should be terminated now
    assert await queue.is_terminated()
    reason = await queue.get_termination_reason()
    assert reason == "test_reason"


@pytest.mark.asyncio
async def test_get_last_sender(temp_db, logger):
    """Test getting last sender"""
    queue = SQLiteQueue(temp_db, logger)

    # No messages yet
    assert await queue.get_last_sender() is None

    # Add messages
    await queue.add_message("Claude", "First", {})
    assert await queue.get_last_sender() == "Claude"

    await queue.add_message("ChatGPT", "Second", {})
    assert await queue.get_last_sender() == "ChatGPT"


@pytest.mark.asyncio
async def test_concurrent_writes(temp_db, logger):
    """Test concurrent writes (race condition test)"""
    queue = SQLiteQueue(temp_db, logger)

    async def add_messages(sender, count):
        for i in range(count):
            await queue.add_message(sender, f"Message {i}", {"tokens": 1})

    # Run concurrent writes
    await asyncio.gather(add_messages("Claude", 10), add_messages("ChatGPT", 10))

    # Verify all messages were added
    data = await queue.load()
    assert len(data["messages"]) == 20
    assert data["metadata"]["total_turns"] == 20
    assert data["metadata"]["claude_turns"] == 10
    assert data["metadata"]["chatgpt_turns"] == 10


@pytest.mark.asyncio
async def test_health_check(temp_db, logger):
    """Test health check"""
    queue = SQLiteQueue(temp_db, logger)

    health = await queue.health_check()

    assert health["healthy"] is True
    assert health["checks"]["database"] == "ok"
    assert health["checks"]["lock"] == "ok"


@pytest.mark.asyncio
async def test_queue_factory(temp_db, logger):
    """Test queue factory function"""
    queue = create_queue(str(temp_db), logger, use_redis=False)

    assert isinstance(queue, SQLiteQueue)

    # Test adding message
    msg = await queue.add_message("Claude", "Test", {})
    assert msg["sender"] == "Claude"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
