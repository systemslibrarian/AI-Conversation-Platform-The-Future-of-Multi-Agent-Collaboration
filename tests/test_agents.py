"""Comprehensive agent tests for AI Conversation Platform v5.0 - FIXED"""

import pytest
import logging
from unittest.mock import AsyncMock, MagicMock, patch
import importlib.util

# We patch 'agents.base.config' so we must import from agents.base
from agents import ClaudeAgent, ChatGPTAgent
from agents.base import CircuitBreaker


@pytest.fixture
def mock_queue():
    """Create a mock queue for testing"""
    queue = AsyncMock()
    queue.get_context.return_value = []
    queue.get_last_sender.return_value = None
    queue.is_terminated.return_value = False
    queue.add_message.return_value = {"id": 1, "sender": "Test", "content": "Test message"}
    return queue


@pytest.fixture
def logger():
    """Create test logger"""
    return logging.getLogger("test")


class TestCircuitBreaker:
    """Test circuit breaker functionality"""

    # --- THIS IS THE FIX ---
    # We now pass the 'logger' fixture and a test provider name
    # to the CircuitBreaker constructor in all tests.

    def test_circuit_breaker_initial_state(self, logger):  # Added logger
        """Test circuit breaker starts in CLOSED state"""
        cb = CircuitBreaker(logger=logger, provider_name="TestProvider")  # Updated
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0
        assert not cb.is_open()

    def test_circuit_breaker_opens_after_failures(self, logger):  # Added logger
        """Test circuit breaker opens after threshold failures"""
        cb = CircuitBreaker(
            logger=logger, provider_name="TestProvider", failure_threshold=3
        )  # Updated

        for _ in range(3):
            cb.record_failure()

        assert cb.state == "OPEN"
        assert cb.is_open()

    def test_circuit_breaker_half_open_transition(self, logger):  # Added logger
        """Test circuit breaker transitions to HALF_OPEN after timeout"""
        cb = CircuitBreaker(
            logger=logger,
            provider_name="TestProvider",
            failure_threshold=2,
            timeout_seconds=0,
        )  # Updated

        cb.record_failure()
        cb.record_failure()
        assert cb.state == "OPEN"

        # After timeout, should transition to HALF_OPEN when queried
        assert not cb.is_open()  # This triggers the transition logic

    def test_circuit_breaker_success_resets(self, logger):  # Added logger
        """Test successful call resets circuit breaker"""
        cb = CircuitBreaker(logger=logger, provider_name="TestProvider")  # Updated

        cb.record_failure()
        cb.record_failure()
        assert cb.failure_count == 2

        cb.record_success()
        assert cb.failure_count == 0
    
    # --- END OF FIX ---


class TestChatGPTAgent:
    """Test ChatGPT agent"""

    @pytest.mark.asyncio
    async def test_chatgpt_initialization(self, mock_queue, logger):
        """Test ChatGPT agent initialization"""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            # CRITICAL: Patch at the SOURCE of the import (openai.OpenAI)
            # NOT where it's used (agents.chatgpt.OpenAI doesn't exist)
            with patch("openai.OpenAI"):
                agent = ChatGPTAgent(
                    api_key="test-key",
                    queue=mock_queue,
                    logger=logger,
                    model="gpt-4o",
                    topic="test",
                    timeout_minutes=30,
                )

                assert agent.PROVIDER_NAME == "ChatGPT"
                assert agent.model == "gpt-4o"
                assert agent.topic == "test"

    @pytest.mark.asyncio
    async def test_chatgpt_api_call(self, mock_queue, logger):
        """Test ChatGPT API call"""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            # CRITICAL: Patch at the SOURCE of the import (openai.OpenAI)
            with patch("openai.OpenAI") as mock_openai:
                # Create a mock client
                mock_client = MagicMock()
                mock_client.chat.completions.create.return_value = MagicMock(
                    choices=[MagicMock(message=MagicMock(content="Hello"))],
                    usage=MagicMock(total_tokens=10),
                )
                mock_openai.return_value = mock_client

                agent = ChatGPTAgent(
                    api_key="test-key",
                    queue=mock_queue,
                    logger=logger,
                    model="gpt-4o",
                    topic="test",
                    timeout_minutes=30,
                )
                content, tokens = await agent._call_api(
                    [{"role": "user", "content": "hi"}]
                )
                assert content == "Hello"
                assert tokens == 10


class TestClaudeAgent:
    """Test Claude agent"""

    @pytest.mark.asyncio
    async def test_claude_initialization(self, mock_queue, logger):
        """Test Claude agent initialization"""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            # CRITICAL: Patch at the SOURCE of the import (anthropic.Anthropic)
            with patch("anthropic.Anthropic"):
                agent = ClaudeAgent(
                    api_key="test-key",
                    queue=mock_queue,
                    logger=logger,
                    model="claude-3-opus-20240229",
                    topic="test",
                    timeout_minutes=30,
                )

                assert agent.PROVIDER_NAME == "Claude"
                assert agent.model == "claude-3-opus-20240229"
                assert agent.topic == "test"

    @pytest.mark.asyncio
    async def test_claude_api_call(self, mock_queue, logger):
        """Test Claude API call"""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            # CRITICAL: Patch at the SOURCE of the import (anthropic.Anthropic)
            with patch("anthropic.Anthropic") as mock_anthropic:
                # Create a mock client
                mock_client = MagicMock()
                mock_client.messages.create.return_value = MagicMock(
                    content=[MagicMock(text="Hi from Claude")],
                    usage=MagicMock(input_tokens=5, output_tokens=6),
                )
                mock_anthropic.return_value = mock_client

                agent = ClaudeAgent(
                    api_key="test-key",
                    queue=mock_queue,
                    logger=logger,
                    model="claude-3-opus-20240229",
                    topic="test",
                    timeout_minutes=30,
                )
                content, tokens = await agent._call_api(
                    [{"role": "user", "content": "hi"}]
                )
                assert content == "Hi from Claude"
                assert tokens == 11


class TestSimilarity:
    """Test similarity detection logic"""

    @pytest.mark.asyncio
    async def test_similarity_detection(self, mock_queue, logger):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            with patch("openai.OpenAI"):
                agent = ChatGPTAgent(
                    api_key="test-key",
                    queue=mock_queue,
                    logger=logger,
                    model="gpt-4o",
                    topic="test",
                    timeout_minutes=30,
                )
            test_message = "I am a repetitive message."
            diff_message = "Something completely different."

            # `recent_responses` is empty, so check returns False and counter is 0
            assert agent._check_similarity(test_message) is False
            assert agent.consecutive_similar == 0
            agent.recent_responses.append(test_message)  # Manually add first message

            # First similar message (compares to 1st)
            # counter becomes 1 (which is < 2), so returns False
            assert agent._check_similarity(test_message) is False
            assert agent.consecutive_similar == 1
            agent.recent_responses.append(test_message)  # Manually add second message

            # Second similar message (compares to 2nd) → triggers threshold
            # counter becomes 2 (which is >= 2), so returns True
            assert agent._check_similarity(test_message) is True
            assert agent.consecutive_similar == 2

            # Different message resets
            assert agent._check_similarity(diff_message) is False
            assert agent.consecutive_similar == 0


class TestShouldRespond:
    """Test should_respond logic"""

    @pytest.mark.asyncio
    async def test_should_respond(self, mock_queue, logger):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            with patch("openai.OpenAI"):
                agent = ChatGPTAgent(
                    api_key="test-key",
                    queue=mock_queue,
                    logger=logger,
                    model="gpt-4o",
                    topic="test",
                    timeout_minutes=30,
                )

            mock_queue.get_last_sender.return_value = None
            assert await agent.should_respond("OtherAgent") is True

            mock_queue.get_last_sender.return_value = "OtherAgent"
            assert await agent.should_respond("OtherAgent") is True

            mock_queue.get_last_sender.return_value = "ChatGPT"
            assert await agent.should_respond("OtherAgent") is False


class TestAgentSecurity:
    """Test agent security features"""

    @pytest.mark.asyncio
    async def test_llm_guard_integration(self, mock_queue, logger):
        """Test LLM Guard integration (if available)"""
        with patch.dict(
            "os.environ", {"OPENAI_API_KEY": "test-key", "ENABLE_LLM_GUARD": "true"}
        ):
            if importlib.util.find_spec("llm_guard") is None:
                pytest.skip("llm-guard not installed")

            with patch("openai.OpenAI"):
                agent = ChatGPTAgent(
                    api_key="test-key",
                    queue=mock_queue,
                    logger=logger,
                    model="gpt-4o",
                    topic="test",
                    timeout_minutes=30,
                )

            if getattr(agent, "llm_guard_enabled", False):
                result = agent._scan_input("Normal text")
                if isinstance(result, tuple):
                    _, valid = result
                    assert valid is True
                else:
                    assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=agents"])
