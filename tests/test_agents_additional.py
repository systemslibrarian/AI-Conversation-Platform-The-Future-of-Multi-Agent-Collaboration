"""Additional agent tests for Gemini, Grok, and Perplexity - FIXED"""

import pytest
import logging
from unittest.mock import AsyncMock, patch
from agents.base import BaseAgent, CircuitBreaker


@pytest.fixture
def mock_queue():
    """Create a mock queue for testing"""
    q = AsyncMock()
    q.get_context.return_value = []
    q.get_last_sender.return_value = None
    q.is_terminated.return_value = False
    q.add_message.return_value = {"id": 1, "sender": "Test", "content": "Test message"}
    return q


@pytest.fixture
def logger():
    """Create test logger"""
    return logging.getLogger("test")


class DummyOpenAIClient:
    """Mock OpenAI client for Grok and Perplexity tests"""

    def __init__(self, *args, **kwargs):
        self.chat = type("Chat", (), {"completions": type("Comps", (), {})()})()

        def _create(**kwargs):
            usage = type("Usage", (), {"total_tokens": 50})()
            choice = type(
                "Choice", (), {"message": type("Msg", (), {"content": "Hi from model"})()}
            )()
            return type("Resp", (), {"choices": [choice], "usage": usage})()

        self.chat.completions.create = _create


class DummyGenAIModel:
    """Mock Google Gemini model"""

    def __init__(self, *args, **kwargs):
        pass

    def start_chat(self, history=None):
        class Chat:
            def send_message(self, last):
                return type("Resp", (), {"text": "Gemini says hi"})()

        return Chat()


class TestGrokAgent:
    """Test Grok agent"""

    @pytest.mark.asyncio
    async def test_grok_initialization(self, mock_queue, logger):
        """Test Grok agent initialization"""
        from agents import GrokAgent

        with patch.dict("os.environ", {"XAI_API_KEY": "test-key"}):
            # Patch at source: openai.OpenAI
            with patch("openai.OpenAI", DummyOpenAIClient):
                agent = GrokAgent(
                    api_key="test-key",
                    queue=mock_queue,
                    logger=logger,
                    model="grok-beta",
                    topic="test",
                    timeout_minutes=30,
                )

                assert agent.PROVIDER_NAME == "Grok"
                assert agent.model == "grok-beta"
                assert agent.topic == "test"

    @pytest.mark.asyncio
    async def test_grok_api_call(self, mock_queue, logger):
        """Test Grok API call"""
        from agents import GrokAgent

        with patch.dict("os.environ", {"XAI_API_KEY": "test-key"}):
            # Patch at source: openai.OpenAI
            with patch("openai.OpenAI", DummyOpenAIClient):
                agent = GrokAgent(
                    api_key="test-key",
                    queue=mock_queue,
                    logger=logger,
                    model="grok-beta",
                    topic="test",
                    timeout_minutes=30,
                )
                content, tokens = await agent._call_api([{"role": "user", "content": "hi"}])
                assert content != ""
                assert tokens > 0


class TestPerplexityAgent:
    """Test Perplexity agent"""

    @pytest.mark.asyncio
    async def test_perplexity_initialization(self, mock_queue, logger):
        """Test Perplexity agent initialization"""
        from agents import PerplexityAgent

        with patch.dict("os.environ", {"PERPLEXITY_API_KEY": "test-key"}):
            # Patch at source: openai.OpenAI
            with patch("openai.OpenAI", DummyOpenAIClient):
                agent = PerplexityAgent(
                    api_key="test-key",
                    queue=mock_queue,
                    logger=logger,
                    model="llama-3.1-sonar-large-128k-online",
                    topic="test",
                    timeout_minutes=30,
                )

                assert agent.PROVIDER_NAME == "Perplexity"
                assert agent.model == "llama-3.1-sonar-large-128k-online"
                assert agent.topic == "test"

    @pytest.mark.asyncio
    async def test_perplexity_api_call(self, mock_queue, logger):
        """Test Perplexity API call"""
        from agents import PerplexityAgent

        with patch.dict("os.environ", {"PERPLEXITY_API_KEY": "test-key"}):
            # Patch at source: openai.OpenAI
            with patch("openai.OpenAI", DummyOpenAIClient):
                agent = PerplexityAgent(
                    api_key="test-key",
                    queue=mock_queue,
                    logger=logger,
                    model="llama-3.1-sonar-large-128k-online",
                    topic="test",
                    timeout_minutes=30,
                )
                content, tokens = await agent._call_api([{"role": "user", "content": "hi"}])
                assert content != ""
                assert tokens > 0


class TestGeminiAgent:
    """Test Gemini agent"""

    @pytest.mark.asyncio
    async def test_gemini_initialization(self, mock_queue, logger):
        """Test Gemini agent initialization"""
        from agents import GeminiAgent

        with patch.dict("os.environ", {"GOOGLE_API_KEY": "test-key"}):
            # Patch at source: google.generativeai module
            with patch("google.generativeai.configure"):
                with patch("google.generativeai.GenerativeModel", DummyGenAIModel):
                    agent = GeminiAgent(
                        api_key="test-key",
                        queue=mock_queue,
                        logger=logger,
                        model="gemini-1.5-pro",
                        topic="test",
                        timeout_minutes=30,
                    )

                    assert agent.PROVIDER_NAME == "Gemini"
                    assert agent.model == "gemini-1.5-pro"
                    assert agent.topic == "test"

    @pytest.mark.asyncio
    async def test_gemini_api_call(self, mock_queue, logger):
        """Test Gemini API call"""
        from agents import GeminiAgent

        with patch.dict("os.environ", {"GOOGLE_API_KEY": "test-key"}):
            # Patch at source: google.generativeai module
            with patch("google.generativeai.configure"):
                with patch("google.generativeai.GenerativeModel", DummyGenAIModel):
                    agent = GeminiAgent(
                        api_key="test-key",
                        queue=mock_queue,
                        logger=logger,
                        model="gemini-1.5-pro",
                        topic="test",
                        timeout_minutes=30,
                    )
                    content, tokens = await agent._call_api([{"role": "user", "content": "hi"}])
                    assert "gemini" in content.lower()
                    assert tokens >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


# Additional comprehensive tests for base agent coverage


class MockQueue:
    async def add_message(self, *a, **k):
        return {"id": 1}

    async def get_context(self, *a, **k):
        return []

    async def get_last_sender(self):
        return "other"

    async def is_terminated(self):
        return False

    async def mark_terminated(self, *a, **k):
        pass

    async def get_termination_reason(self):
        return ""

    async def load(self):
        return {"messages": [], "metadata": {}}


class TestAgentExtended(BaseAgent):
    PROVIDER_NAME = "test"
    DEFAULT_MODEL = "test-model"

    def __init__(self, **kwargs):
        super().__init__(
            queue=kwargs.get("queue", MockQueue()),
            logger=kwargs.get("logger", logging.getLogger("test")),
            model=kwargs.get("model", "test-model"),
            topic=kwargs.get("topic", "test"),
            timeout_minutes=kwargs.get("timeout_minutes", 5),
            agent_name=kwargs.get("agent_name"),
        )

    async def _call_api(self, prompt: str) -> tuple:
        return "test response", 10


def test_circuit_breaker_timeout():
    log = logging.getLogger("test")
    cb = CircuitBreaker(log, "test", failure_threshold=3, timeout_seconds=1)

    for _ in range(3):
        cb.record_failure()

    assert cb.is_open()
    assert cb.state == "OPEN"


def test_circuit_breaker_recovery():
    log = logging.getLogger("test")
    cb = CircuitBreaker(log, "test", failure_threshold=2)

    cb.record_failure()
    cb.record_failure()
    assert cb.state == "OPEN"

    cb.state = "HALF_OPEN"
    cb.record_success()
    assert cb.state == "CLOSED"


@pytest.mark.asyncio
async def test_agent_in_executor_with_args():
    agent = TestAgentExtended()

    def add(a, b):
        return a + b

    result = await agent._in_executor(add, 2, 3)
    assert result == 5
