import asyncio
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Import your REAL factory and agent classes
from agents import create_agent, ChatGPTAgent, ClaudeAgent
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
async def test_real_agent_run_loop(temp_db, logger):
    """
    Runs the REAL BaseAgent.run() loop by creating two real agents and mocking their API calls.
    """

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

    # Adjust these patch targets if your actual files differ:
    # - agents/chatgpt.py defines and uses OpenAI
    # - agents/claude.py imports anthropic and constructs anthropic.Anthropic(...)
    with patch("agents.chatgpt.OpenAI", return_value=mock_openai_client), \
         patch("agents.claude.anthropic.Anthropic", return_value=mock_anthropic_client), \
         patch.dict(
             "os.environ",
             {"OPENAI_API_KEY": "fake-key", "ANTHROPIC_API_KEY": "fake-key"},
             clear=False,
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

        assert await queue.is_terminated(), "Conversation did not terminate as expected."

        data = await queue.load()
        messages = data["messages"]

        # Less brittle checks
        assert len(messages) >= 2
        senders = {m["sender"] for m in messages}
        assert {"Claude", "ChatGPT"} <= senders

        # The termination signal should appear somewhere
        assert any(
            TERMINATION_TOKEN in (m.get("content") or "")
            for m in messages
        ), f"Expected termination token {TERMINATION_TOKEN!r} in messages."

        # Mocks were exercised
        mock_anthropic_client.messages.create.assert_called()
        mock_openai_client.chat.completions.create.assert_called()
