"""
Comprehensive Agent Tests - Merged Edition
Combines comprehensive BaseAgent testing with specific agent implementation tests
Coverage target: 90%+ for agents/base.py and agent implementations
"""

import pytest
import asyncio
import logging
import time
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta

from agents import (
    create_agent,
    ChatGPTAgent,
    ClaudeAgent,
    GeminiAgent,
    GrokAgent,
    PerplexityAgent,
)
from agents.base import BaseAgent, CircuitBreaker
from core.config import config


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_queue():
    """Create a comprehensive mock queue"""
    queue = AsyncMock()
    queue.get_context.return_value = []
    queue.get_last_sender.return_value = None
    queue.is_terminated.return_value = False
    queue.get_termination_reason.return_value = "unknown"
    queue.add_message.return_value = {"id": 1, "sender": "Test", "content": "Test message"}
    queue.load.return_value = {
        "messages": [],
        "metadata": {
            "total_turns": 0,
            "testagent_turns": 0,
            "total_tokens": 0,
            "termination_reason": None,
        },
    }
    return queue


@pytest.fixture
def logger():
    """Create test logger"""
    return logging.getLogger("test")


# ============================================================================
# MOCK API CLIENTS
# ============================================================================


class DummyOpenAIClient:
    """Mock OpenAI client for testing"""

    def __init__(self, *args, **kwargs):
        self.chat = type("Chat", (), {"completions": type("Comps", (), {})()})()

        def _create(**kwargs):
            choice = type(
                "Choice", (), {"message": type("Msg", (), {"content": "Hello, world!"})()}
            )()
            usage = type("Usage", (), {"total_tokens": 20})()
            return type("Resp", (), {"choices": [choice], "usage": usage})()

        self.chat.completions.create = _create


class DummyAnthropicClient:
    """Mock Anthropic client for testing"""

    def __init__(self, *args, **kwargs):
        def _create(**kwargs):
            content = [type("Block", (), {"text": "Hello from Claude!"})()]
            usage = type("Usage", (), {"input_tokens": 10, "output_tokens": 15})()
            return type("Resp", (), {"content": content, "usage": usage})()

        self.messages = type("Msgs", (), {"create": _create})()


class DummyGeminiModel:
    """Mock Gemini model for testing"""

    def __init__(self, *args, **kwargs):
        pass

    def start_chat(self, history=None):
        class Chat:
            def send_message(self, last):
                return type("Resp", (), {"text": "Gemini says hi"})()

        return Chat()


# ============================================================================
# TESTABLE AGENT (for BaseAgent testing)
# ============================================================================


class TestableAgent(BaseAgent):
    """Concrete implementation for testing BaseAgent"""

    PROVIDER_NAME = "TestAgent"
    DEFAULT_MODEL = "test-model"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_call_count = 0
        self.should_fail = False
        self.fail_count = 0

    async def _call_api(self, messages):
        """Mock API call"""
        self.api_call_count += 1
        await asyncio.sleep(0.01)  # Simulate network delay

        if self.should_fail and self.api_call_count <= self.fail_count:
            raise Exception("API Error for testing")

        return f"Response {self.api_call_count}", 100


@pytest.fixture
def agent(mock_queue, logger):
    """Create a test agent"""
    return TestableAgent(
        queue=mock_queue,
        logger=logger,
        model="test-model",
        topic="testing",
        timeout_minutes=1,
    )


# ============================================================================
# CIRCUIT BREAKER TESTS
# ============================================================================


class TestCircuitBreaker:
    """Comprehensive circuit breaker tests"""

    def test_initial_state(self):
        """Test circuit breaker starts in CLOSED state"""
        cb = CircuitBreaker()
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0
        assert cb.last_failure_time is None
        assert not cb.is_open()

    def test_open_after_threshold(self):
        """Test circuit opens after failure threshold"""
        cb = CircuitBreaker(failure_threshold=3, timeout_seconds=60)

        assert cb.state == "CLOSED"
        cb.record_failure()
        assert cb.state == "CLOSED"
        assert cb.failure_count == 1

        cb.record_failure()
        assert cb.state == "CLOSED"
        assert cb.failure_count == 2

        cb.record_failure()
        assert cb.state == "OPEN"
        assert cb.failure_count == 3
        assert cb.is_open()

    def test_half_open_after_timeout(self):
        """Test transition to HALF_OPEN after timeout"""
        # --- THIS IS THE FIX ---
        # Changed 0.1 (float) to 0 (int) to match mypy's expectation
        cb = CircuitBreaker(failure_threshold=2, timeout_seconds=0)

        # Open the circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "OPEN"

        # Wait for timeout (no-op, since timeout=0)
        # time.sleep(0.2) # No longer necessary

        # With timeout=0, the *first call* to is_open() will detect the
        # timeout, transition to HALF_OPEN, and return False.
        assert not cb.is_open()
        assert cb.state == "HALF_OPEN"

    def test_success_resets_closed(self):
        """Test success resets failure count in CLOSED state"""
        cb = CircuitBreaker()

        cb.record_failure()
        cb.record_failure()
        assert cb.failure_count == 2

        cb.record_success()
        assert cb.failure_count == 0
        assert cb.state == "CLOSED"

    def test_success_closes_half_open(self):
        """Test success transitions HALF_OPEN to CLOSED"""
        cb = CircuitBreaker(failure_threshold=2, timeout_seconds=0)

        # Open circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "OPEN"

        # Transition to HALF_OPEN
        cb.is_open()  # Triggers transition due to timeout
        assert cb.state == "HALF_OPEN"

        # Success should close circuit
        cb.record_success()
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0

    def test_multiple_failures_stay_open(self):
        """Test multiple failures keep circuit OPEN"""
        cb = CircuitBreaker(failure_threshold=2, timeout_seconds=60)

        cb.record_failure()
        cb.record_failure()
        assert cb.state == "OPEN"

        # Additional failures while open
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "OPEN"
        assert cb.failure_count == 4


# ============================================================================
# BASE AGENT INITIALIZATION
# ============================================================================


class TestBaseAgentInitialization:
    """Test agent initialization"""

    @pytest.mark.asyncio
    async def test_basic_initialization(self, mock_queue, logger):
        """Test basic agent initialization"""
        agent = TestableAgent(
            queue=mock_queue,
            logger=logger,
            model="test-model",
            topic="test-topic",
            timeout_minutes=30,
        )

        assert agent.agent_name == "TestAgent"
        assert agent.model == "test-model"
        assert agent.topic == "test-topic"
        assert agent.timeout_minutes == 30
        assert agent.turn_count == 0
        assert agent.consecutive_similar == 0
        assert agent.consecutive_errors == 0
        assert len(agent.recent_responses) == 0

    @pytest.mark.asyncio
    async def test_custom_agent_name(self, mock_queue, logger):
        """Test custom agent name"""
        agent = TestableAgent(
            queue=mock_queue,
            logger=logger,
            model="test-model",
            topic="test",
            timeout_minutes=1,
            agent_name="CustomName",
        )

        assert agent.agent_name == "CustomName"

    @pytest.mark.asyncio
    async def test_llm_guard_disabled_by_default(self, mock_queue, logger):
        """Test LLM Guard is handled when disabled"""
        with patch.object(config, "ENABLE_LLM_GUARD", False):
            agent = TestableAgent(
                queue=mock_queue,
                logger=logger,
                model="test",
                topic="test",
                timeout_minutes=1,
            )
            assert not agent.llm_guard_enabled

    @pytest.mark.asyncio
    async def test_default_model_fallback(self, mock_queue, logger):
        """Test fallback to DEFAULT_MODEL when model not specified"""
        agent = TestableAgent(
            queue=mock_queue,
            logger=logger,
            model="",
            topic="test",
            timeout_minutes=1,
        )
        assert agent.model == "test-model"  # Falls back to DEFAULT_MODEL


# ============================================================================
# TERMINATION SIGNALS
# ============================================================================


class TestTerminationSignals:
    """Test termination signal detection"""

    @pytest.mark.asyncio
    async def test_detect_done_signal(self, agent):
        """Test detection of [done] signal"""
        result = agent._check_termination_signals("This conversation is [done]")
        assert result is not None
        assert "sentinel_phrase" in result
        assert "[done]" in result

    @pytest.mark.asyncio
    async def test_detect_cant_continue(self, agent):
        """Test detection of 'can't continue' signal"""
        result = agent._check_termination_signals("I can't continue this discussion")
        assert result is not None
        assert "can't continue" in result.lower()

    @pytest.mark.asyncio
    async def test_detect_off_topic(self, agent):
        """Test detection of off topic signal"""
        result = agent._check_termination_signals("This seems off topic")
        assert result is not None
        assert "off topic" in result.lower()

    @pytest.mark.asyncio
    async def test_no_termination_signal(self, agent):
        """Test normal message without termination signal"""
        result = agent._check_termination_signals("This is a normal message")
        assert result is None

    @pytest.mark.asyncio
    async def test_case_insensitive_detection(self, agent):
        """Test case-insensitive termination detection"""
        result = agent._check_termination_signals("I CAN'T CONTINUE")
        assert result is not None


# ============================================================================
# SIMILARITY DETECTION
# ============================================================================


class TestSimilarityDetection:
    """Test similarity detection"""

    @pytest.mark.asyncio
    async def test_empty_history(self, agent):
        """Test similarity with empty history"""
        result = agent._check_similarity("New message")
        assert result is False
        assert agent.consecutive_similar == 0

    @pytest.mark.asyncio
    async def test_similar_messages(self, agent):
        """Test detection of similar messages"""
        agent.recent_responses.append("Hello world this is a test")

        # First similar message
        result = agent._check_similarity("Hello world this is a test message")
        assert agent.consecutive_similar == 1
        assert result is False

        # Second similar message
        result = agent._check_similarity("Hello world this is a test again")
        assert agent.consecutive_similar == 2

        # Depends on MAX_CONSECUTIVE_SIMILAR threshold
        if agent.consecutive_similar >= config.MAX_CONSECUTIVE_SIMILAR:
            assert result is True

    @pytest.mark.asyncio
    async def test_dissimilar_resets_counter(self, agent):
        """Test dissimilar message resets counter"""
        agent.recent_responses.append("Hello world")
        agent.consecutive_similar = 2

        result = agent._check_similarity("Completely different content here")
        assert result is False
        assert agent.consecutive_similar == 0

    @pytest.mark.asyncio
    async def test_threshold_triggering(self, agent):
        """Test similarity threshold triggering"""
        with patch.object(config, "SIMILARITY_THRESHOLD", 0.8):
            with patch.object(config, "MAX_CONSECUTIVE_SIMILAR", 2):
                test_msg = "This is a test message for similarity"
                agent.recent_responses.append(test_msg)

                # Add similar messages
                agent._check_similarity(test_msg)
                assert agent.consecutive_similar == 1

                result = agent._check_similarity(test_msg)
                # Should trigger after 2 consecutive similar
                assert result is True
                assert agent.consecutive_similar == 2


# ============================================================================
# TIMEOUT TESTS
# ============================================================================


class TestTimeout:
    """Test timeout functionality"""

    @pytest.mark.asyncio
    async def test_no_timeout_when_not_started(self, agent):
        """Test no timeout when start_time not set"""
        agent.start_time = None
        result = await agent._is_timeout()
        assert result is False

    @pytest.mark.asyncio
    async def test_timeout_not_exceeded(self, agent):
        """Test timeout not exceeded"""
        agent.start_time = datetime.now()
        agent.timeout_minutes = 60
        result = await agent._is_timeout()
        assert result is False

    @pytest.mark.asyncio
    async def test_timeout_exceeded(self, agent):
        """Test timeout exceeded"""
        agent.start_time = datetime.now() - timedelta(minutes=61)
        agent.timeout_minutes = 60
        result = await agent._is_timeout()
        assert result is True


# ============================================================================
# SHOULD RESPOND LOGIC
# ============================================================================


class TestShouldRespond:
    """Test should_respond logic"""

    @pytest.mark.asyncio
    async def test_respond_when_no_last_sender(self, agent, mock_queue):
        """Test should respond when no last sender"""
        mock_queue.get_last_sender.return_value = None
        result = await agent.should_respond("Partner")
        assert result is True

    @pytest.mark.asyncio
    async def test_respond_when_partner_sent_last(self, agent, mock_queue):
        """Test should respond when partner sent last message"""
        mock_queue.get_last_sender.return_value = "Partner"
        result = await agent.should_respond("Partner")
        assert result is True

    @pytest.mark.asyncio
    async def test_no_respond_when_self_sent_last(self, agent, mock_queue):
        """Test should not respond when self sent last message"""
        mock_queue.get_last_sender.return_value = "TestAgent"
        result = await agent.should_respond("Partner")
        assert result is False

    @pytest.mark.asyncio
    async def test_no_respond_when_timeout(self, agent, mock_queue):
        """Test should not respond when timeout"""
        agent.start_time = datetime.now() - timedelta(minutes=61)
        agent.timeout_minutes = 60
        result = await agent.should_respond("Partner")
        assert result is False

    @pytest.mark.asyncio
    async def test_no_respond_when_terminated(self, agent, mock_queue):
        """Test should not respond when conversation terminated"""
        mock_queue.is_terminated.return_value = True
        result = await agent.should_respond("Partner")
        assert result is False


# ============================================================================
# RESPONSE GENERATION
# ============================================================================


class TestGenerateResponse:
    """Test generate_response method"""

    @pytest.mark.asyncio
    async def test_successful_generation(self, agent, mock_queue):
        """Test successful response generation"""
        mock_queue.get_context.return_value = [{"sender": "Partner", "content": "Hello"}]

        content, tokens, response_time = await agent.generate_response()

        assert content == "Response 1"
        assert tokens == 100
        assert response_time > 0
        assert agent.consecutive_errors == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_open(self, agent):
        """Test generation fails when circuit breaker open"""
        agent.circuit_breaker.state = "OPEN"
        agent.circuit_breaker.last_failure_time = time.time()

        with pytest.raises(Exception, match="Circuit breaker OPEN"):
            await agent.generate_response()

    @pytest.mark.asyncio
    async def test_api_error_handling(self, agent, mock_queue):
        """Test API error handling"""
        agent.should_fail = True
        agent.fail_count = 1

        with pytest.raises(Exception, match="API Error"):
            await agent.generate_response()

        assert agent.consecutive_errors == 1
        assert agent.circuit_breaker.failure_count == 1

    @pytest.mark.asyncio
    async def test_rate_limit_detection(self, agent):
        """Test rate limit error detection"""

        async def failing_api(messages):
            raise Exception("Rate limit exceeded (429)")

        agent._call_api = failing_api

        with pytest.raises(Exception, match="Rate limit"):
            await agent.generate_response()


# ============================================================================
# MESSAGE BUILDING
# ============================================================================


class TestBuildMessages:
    """Test message building"""

    @pytest.mark.asyncio
    async def test_build_empty_context(self, agent, mock_queue):
        """Test building messages with empty context"""
        mock_queue.get_context.return_value = []

        messages = await agent._build_messages()

        assert messages == []

    @pytest.mark.asyncio
    async def test_build_with_context(self, agent, mock_queue):
        """Test building messages with context"""
        mock_queue.get_context.return_value = [
            {"sender": "Partner", "content": "Hello"},
            {"sender": "TestAgent", "content": "Hi there"},
        ]

        messages = await agent._build_messages()

        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "Hi there"


# ============================================================================
# SYSTEM PROMPT
# ============================================================================


class TestSystemPrompt:
    """Test system prompt building"""

    @pytest.mark.asyncio
    async def test_system_prompt_with_topic(self, agent):
        """Test system prompt includes topic"""
        agent.topic = "AI Ethics"
        prompt = agent._build_system_prompt()

        assert "TestAgent" in prompt
        assert "AI Ethics" in prompt

    @pytest.mark.asyncio
    async def test_system_prompt_without_topic(self, mock_queue, logger):
        """Test system prompt with no topic"""
        agent = TestableAgent(
            queue=mock_queue,
            logger=logger,
            model="test",
            topic=None,
            timeout_minutes=1,
        )

        prompt = agent._build_system_prompt()

        assert "TestAgent" in prompt
        assert "general" in prompt


# ============================================================================
# SPECIFIC AGENT TESTS - ChatGPT
# ============================================================================


class TestChatGPTAgent:
    """Test ChatGPT agent implementation"""

    @pytest.mark.asyncio
    async def test_chatgpt_initialization(self, mock_queue, logger):
        """Test ChatGPT agent initialization"""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            with patch("agents.chatgpt.OpenAI", DummyOpenAIClient):
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
            with patch("agents.chatgpt.OpenAI", DummyOpenAIClient):
                agent = ChatGPTAgent(
                    api_key="test-key",
                    queue=mock_queue,
                    logger=logger,
                    model="gpt-4o",
                    topic="test",
                    timeout_minutes=30,
                )

                content, tokens = await agent._call_api([{"role": "user", "content": "Hi"}])

                assert content == "Hello, world!"
                assert tokens == 20


# ============================================================================
# SPECIFIC AGENT TESTS - Claude
# ============================================================================


class TestClaudeAgent:
    """Test Claude agent implementation"""

    @pytest.mark.asyncio
    async def test_claude_initialization(self, mock_queue, logger):
        """Test Claude agent initialization"""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("agents.claude.anthropic.Anthropic", DummyAnthropicClient):
                agent = ClaudeAgent(
                    api_key="test-key",
                    queue=mock_queue,
                    logger=logger,
                    model="claude-sonnet-4-5-20250929",
                    topic="test",
                    timeout_minutes=30,
                )

                assert agent.PROVIDER_NAME == "Claude"
                assert agent.model == "claude-sonnet-4-5-20250929"

    @pytest.mark.asyncio
    async def test_claude_api_call(self, mock_queue, logger):
        """Test Claude API call"""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("agents.claude.anthropic.Anthropic", DummyAnthropicClient):
                agent = ClaudeAgent(
                    api_key="test-key",
                    queue=mock_queue,
                    logger=logger,
                    model="claude-sonnet-4-5-20250929",
                    topic="test",
                    timeout_minutes=30,
                )

                content, tokens = await agent._call_api([{"role": "user", "content": "Hi"}])

                assert content == "Hello from Claude!"
                assert tokens == 25


# ============================================================================
# SPECIFIC AGENT TESTS - Gemini
# ============================================================================


class TestGeminiAgent:
    """Test Gemini agent implementation"""

    @pytest.mark.asyncio
    async def test_gemini_api_call(self, mock_queue, logger):
        """Test Gemini API call"""
        with patch.dict("os.environ", {"GOOGLE_API_KEY": "test-key"}):
            with patch("agents.gemini.genai.GenerativeModel", DummyGeminiModel):
                agent = GeminiAgent(
                    api_key="test-key",
                    queue=mock_queue,
                    logger=logger,
                    model="gemini-1.5-pro",
                    topic="test",
                    timeout_minutes=30,
                )

                content, tokens = await agent._call_api([{"role": "user", "content": "Hi"}])

                assert "gemini" in content.lower()
                assert tokens >= 0


# ============================================================================
# SPECIFIC AGENT TESTS - Grok
# ============================================================================


class TestGrokAgent:
    """Test Grok agent implementation"""

    @pytest.mark.asyncio
    async def test_grok_api_call(self, mock_queue, logger, monkeypatch):
        """Test Grok API call"""
        monkeypatch.setenv("XAI_API_KEY", "test-key")
        with patch("agents.grok.OpenAI", DummyOpenAIClient):
            agent = GrokAgent(
                api_key="dummy",
                queue=mock_queue,
                logger=logger,
                model="grok-beta",
                topic="x",
                timeout_minutes=1,
            )
            content, tokens = await agent._call_api([{"role": "user", "content": "hi"}])
            assert content == "Hello, world!"
            assert tokens == 20


# ============================================================================
# SPECIFIC AGENT TESTS - Perplexity
# ============================================================================


class TestPerplexityAgent:
    """Test Perplexity agent implementation"""

    @pytest.mark.asyncio
    async def test_perplexity_api_call(self, mock_queue, logger, monkeypatch):
        """Test Perplexity API call"""
        monkeypatch.setenv("PERPLEXITY_API_KEY", "test-key")
        with patch("agents.perplexity.OpenAI", DummyOpenAIClient):
            agent = PerplexityAgent(
                api_key="dummy",
                queue=mock_queue,
                logger=logger,
                model="llama-3.1-sonar-large-128k-online",
                topic="x",
                timeout_minutes=1,
            )
            content, tokens = await agent._call_api([{"role": "user", "content": "hi"}])
            assert content == "Hello, world!"
            assert tokens == 20


# ============================================================================
# AGENT FACTORY
# ============================================================================


class TestAgentFactory:
    """Test agent factory function"""

    def test_create_chatgpt_agent(self, mock_queue, logger):
        """Test creating ChatGPT agent via factory"""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            with patch("agents.chatgpt.OpenAI", DummyOpenAIClient):
                agent = create_agent(
                    agent_type="chatgpt",
                    queue=mock_queue,
                    logger=logger,
                    api_key="test-key",
                )

                assert isinstance(agent, ChatGPTAgent)

    def test_create_claude_agent(self, mock_queue, logger):
        """Test creating Claude agent via factory"""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("agents.claude.anthropic.Anthropic", DummyAnthropicClient):
                agent = create_agent(
                    agent_type="claude",
                    queue=mock_queue,
                    logger=logger,
                    api_key="test-key",
                )

                assert isinstance(agent, ClaudeAgent)

    def test_create_grok_agent(self, mock_queue, logger):
        """Test creating Grok agent via factory"""
        with patch.dict("os.environ", {"XAI_API_KEY": "test-key"}):
            with patch("agents.grok.OpenAI", DummyOpenAIClient):
                agent = create_agent(
                    agent_type="grok",
                    queue=mock_queue,
                    logger=logger,
                    api_key="test-key",
                )

                assert isinstance(agent, GrokAgent)

    def test_create_perplexity_agent(self, mock_queue, logger):
        """Test creating Perplexity agent via factory"""
        with patch.dict("os.environ", {"PERPLEXITY_API_KEY": "test-key"}):
            with patch("agents.perplexity.OpenAI", DummyOpenAIClient):
                agent = create_agent(
                    agent_type="perplexity",
                    queue=mock_queue,
                    logger=logger,
                    api_key="test-key",
                )

                assert isinstance(agent, PerplexityAgent)

    def test_create_invalid_agent(self, mock_queue, logger):
        """Test creating invalid agent type"""
        with pytest.raises(ValueError, match="Unknown agent type"):
            create_agent(agent_type="invalid", queue=mock_queue, logger=logger)

    def test_create_agent_with_model_override(self, mock_queue, logger):
        """Test agent creation with model override"""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            with patch("agents.chatgpt.OpenAI", DummyOpenAIClient):
                agent = create_agent(
                    agent_type="chatgpt",
                    queue=mock_queue,
                    logger=logger,
                    model="gpt-4o-mini",
                    api_key="test-key",
                )

                assert agent.model == "gpt-4o-mini"


# ============================================================================
# RUN TESTS (if executed directly)
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=agents", "--cov-report=term-missing"])
