import sys
import asyncio
import logging
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Ensure a compatible event loop policy on Windows CI (prevents occasional hangs)
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        # Safe fallback; some Python builds may not expose WindowsSelectorEventLoopPolicy
        pass

# Import your REAL factory and agent classes
# (We only need create_agent, which avoids F401.)
from agents import create_agent
from core.queue import create_queue

# If you have this constant in code, prefer importing it:
# from core.constants import TERMINATION_TOKEN
TERMINATION_TOKEN = "[done]"


# --- Fixtures ---

@pytest.fixture
def temp_db(tmp_path):
    """Provide a temporary DB path as a string (what create_queue expects)."""
    db_path = tmp_path / "test.db"
    yield str(db_path)
    # Clean up any lock file left by the queue
    lock = Path(str(db_path) + ".lock")
    if lock.exists():
        lock.unlink()


@pytest.fixture
def logger():
    """Create a visible, quiet logger for debugging test failures."""
    lg = logging.getLogger("e2e_test")
    lg.setLevel(logging.DEBUG)
    if not lg.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
        lg.addHandler(h)
    return lg


# --- The E2E Test ---

@pytest.mark.asyncio
async def test_real_agent_run_loop(temp_db, logger, caplog):
    """
    Runs the REAL BaseAgent.run() loop by creating two real agents and mocking their API calls.
    """

    # Capture logs at INFO+ for easier debugging (optional; not asserting on content)
    caplog.set_level(logging.INFO)

    # --- 1) Setup Mocks for API Clients ---

    # OpenAI (Chat Completions style)
    mock_openai_client = MagicMock()
    mock_openai_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=f"Hello from ChatGPT! {TERMINATION_TOKEN}"))],
        usage=MagicMock(total_tokens=10),
    )

    # Anthropic (Messages API shape)
    mock_anthropic_client = MagicMock()
    mock_anthropic_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="Hi from Claude!")],
        usage=MagicMock(input_tokens=5, output_tokens=6),
    )

    # --- 2) Patch where the symbols are LOOKED UP in your code ---
    #
    # THIS IS THE FIX:
    # Both agents import their clients *locally* inside their __init__ methods.
    # Therefore, we must patch both at their original source.
    #
    with patch("openai.OpenAI", return_value=mock_openai_client), \
         patch("anthropic.Anthropic", return_value=mock_anthropic_client), \
         patch.dict(
             os.environ,
             {"OPENAI_API_KEY": "fake-key", "ANTHROPIC_API_KEY": "fake-key"},
             clear=True,  # fully isolate env to only the fake keys
         ):

        queue = create_queue(temp_db, logger, use_redis=False)

        # Real agents
        claude = create_agent(agent_type="claude", queue=queue, logger=logger, topic="test")
        chatgpt = create_agent(agent_type="chatgpt", queue=queue, logger=logger, topic="test")

        # --- 3) Run the REAL .run() Methods with a timeout guard ---
        await asyncio.wait_for(
            asyncio.gather(
                claude.run(max_turns=5, partner_name="ChatGPT"),
                chatgpt.run(max_turns=5, partner_name="Claude"),
            ),
            timeout=10,
        )

        # --- 4) Verify Results ---

        # Termination must have been reached
        assert await queue.is_terminated(), "Conversation did not terminate as expected."

        data = await queue.load()
        messages = data["messages"]

        # Less brittle checks
        assert len(messages) >= 2
        senders = {m["sender"] for m in messages}
        assert {"Claude", "ChatGPT"} <= senders

        # Strong assertion: the termination signal should be present
        assert any(
            TERMINATION_TOKEN in (m.get("content") or "")
            for m in messages
        ), f"Expected termination token {TERMINATION_TOKEN!r} in messages."

        # Even stronger: ensure the terminator came from ChatGPT specifically
        assert any(
            m["sender"] == "ChatGPT" and TERMINATION_TOKEN in (m.get("content") or "")
            for m in messages
        ), f"Expected ChatGPT to emit the termination token {TERMINATION_TOKEN!r}."

        # Mocks were exercised (at least once)
        mock_anthropic_client.messages.create.assert_called()
        mock_openai_client.chat.completions.create.assert_called()
