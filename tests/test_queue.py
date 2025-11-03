import pytest
import asyncio
import tempfile
from pathlib import Path
import logging
from core.queue import SQLiteQueue, create_queue


@pytest.fixture
def temp_db():
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
    return logging.getLogger("test")


@pytest.mark.asyncio
async def test_queue_initialization(temp_db, logger):
    queue = SQLiteQueue(temp_db, logger)
    data = await queue.load()
    assert "messages" in data and "metadata" in data
    assert data["metadata"]["version"] == "5.0"


@pytest.mark.asyncio
async def test_add_and_context(temp_db, logger):
    queue = SQLiteQueue(temp_db, logger)
    await queue.add_message("Claude", "Hello, world!", {"tokens": 10})
    await queue.add_message("ChatGPT", "Second", {"tokens": 5})
    ctx = await queue.get_context(2)
    assert len(ctx) == 2
    assert ctx[0]["sender"] == "Claude"
    assert ctx[1]["sender"] == "ChatGPT"
    last = await queue.get_last_sender()
    assert last == "ChatGPT"


@pytest.mark.asyncio
async def test_termination(temp_db, logger):
    queue = SQLiteQueue(temp_db, logger)
    assert not await queue.is_terminated()
    await queue.mark_terminated("done")
    assert await queue.is_terminated()
    assert (await queue.get_termination_reason()) == "done"


@pytest.mark.asyncio
async def test_concurrent_writes(temp_db, logger):
    queue = SQLiteQueue(temp_db, logger)

    async def add(sender):
        for i in range(10):
            await queue.add_message(sender, f"m{i}", {"tokens": 1})

    await asyncio.gather(add("Claude"), add("ChatGPT"))
    data = await queue.load()
    assert len(data["messages"]) == 20
    assert data["metadata"]["total_turns"] == 20


@pytest.mark.asyncio
async def test_factory(temp_db, logger):
    q = create_queue(str(temp_db), logger, use_redis=False)
    assert isinstance(q, SQLiteQueue)
