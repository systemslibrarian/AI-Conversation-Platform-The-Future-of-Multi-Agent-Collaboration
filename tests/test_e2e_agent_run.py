import pytest
import asyncio
import tempfile
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import your REAL factory and agent classes
from agents import create_agent, ChatGPTAgent, ClaudeAgent
from core.queue import create_queue

# --- Fixtures (copied from your other tests) ---

@pytest.fixture
def temp_db():
    """Create temporary database as a string path"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    
    # Yield the string path, as create_queue expects
    yield str(db_path)
    
    # Cleanup
    if db_path.exists():
        db_path.unlink()
    lock_file = Path(f"{db_path}.lock")
    if lock_file.exists():
        lock_file.unlink()

@pytest.fixture
def logger():
    """Create test logger"""
    return logging.getLogger("e2e_test")

# --- The New E2E Test ---

@pytest.mark.asyncio
async def test_real_agent_run_loop(temp_db, logger):
    """
    This test runs the *REAL* BaseAgent.run() loop by creating
    two real agents and mocking their API calls.
    """
    
    # --- 1. Setup Mocks for API Clients ---
    
    # Mock OpenAI (for ChatGPT)
    mock_openai_client = MagicMock()
    mock_openai_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="Hello from ChatGPT! [done]"))],
        usage=MagicMock(total_tokens=10),
    )
    
    # Mock Anthropic (for Claude)
    mock_anthropic_client = MagicMock()
    mock_anthropic_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="Hi from Claude!")],
        usage=MagicMock(input_tokens=5, output_tokens=6),
    )
    
    # --- 2. Apply Mocks and Create REAL Components ---
    
    with patch("openai.OpenAI", return_value=mock_openai_client) as mock_openai, \
         patch("anthropic.Anthropic", return_value=mock_anthropic_client) as mock_anthropic, \
         patch.dict("os.environ", {
             "OPENAI_API_KEY": "fake-key", 
             "ANTHROPIC_API_KEY": "fake-key"
         }):
        
        # Create the real queue
        queue = create_queue(temp_db, logger, use_redis=False)
        
        # Create the REAL agents
        agent1_claude = create_agent(
            agent_type="claude",
            queue=queue,
            logger=logger,
            topic="test"
        )
        
        agent2_chatgpt = create_agent(
            agent_type="chatgpt",
            queue=queue,
            logger=logger,
            topic="test"
        )
        
        # --- 3. Run the REAL .run() Methods ---
        
        # This will execute the code in base.py
        await asyncio.gather(
            agent1_claude.run(max_turns=5, partner_name="ChatGPT"),
            agent2_chatgpt.run(max_turns=5, partner_name="Claude")
        )

        # --- 4. Verify the Results ---
        
        # Check that the "[done]" signal was caught
        assert await queue.is_terminated()
        
        data = await queue.load()
        messages = data["messages"]

        # Verify the conversation happened
        assert len(messages) == 2  # Claude responds, then ChatGPT responds + terminates
        
        senders = {msg["sender"] for msg in messages}
        assert "Claude" in senders
        assert "ChatGPT" in senders
        
        # Check that the mocks were called
        mock_anthropic_client.messages.create.assert_called()
        mock_openai_client.chat.completions.create.assert_called()

