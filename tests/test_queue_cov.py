# Minimal tests to increase coverage for core/queue.py
import logging
import tempfile
from pathlib import Path

import pytest

from core.queue import SQLiteQueue


@pytest.mark.asyncio
async def test_queue_init_and_basic_ops():
    logger = logging.getLogger("test")
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        q = SQLiteQueue(filepath=tmp_path, logger=logger)
        await q.add_message("agent1", "hello")
        ctx = await q.get_context(max_messages=10)
        assert len(ctx) >= 1
    finally:
        tmp_path.unlink(missing_ok=True)
        Path(f"{tmp_path}.lock").unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_queue_termination_flags():
    logger = logging.getLogger("test")
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        q = SQLiteQueue(filepath=tmp_path, logger=logger)
        await q.mark_terminated("done")
        assert await q.is_terminated()
        reason = await q.get_termination_reason()
        assert reason == "done"
    finally:
        tmp_path.unlink(missing_ok=True)
        Path(f"{tmp_path}.lock").unlink(missing_ok=True)
