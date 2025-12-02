# Tests for provider initialization to cover lines 27-30
import pytest
import logging
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.fixture
def mock_queue():
    q = AsyncMock()
    q.get_context.return_value = []
    q.is_terminated.return_value = False
    q.add_message.return_value = {"id": 1}
    return q


@pytest.mark.asyncio
async def test_chatgpt_with_valid_key(mock_queue):
    """Test ChatGPT initialization with valid key"""
    from agents.chatgpt import ChatGPTAgent
    
    with patch("openai.OpenAI"):
        agent = ChatGPTAgent(
            api_key="test-key",
            queue=mock_queue,
            logger=logging.getLogger("test"),
            model="gpt-4",
            topic="test",
            timeout_minutes=5
        )
        assert agent.client is not None


@pytest.mark.asyncio
async def test_claude_with_valid_key(mock_queue):
    """Test Claude initialization with valid key"""
    from agents.claude import ClaudeAgent
    
    with patch("anthropic.Anthropic"):
        agent = ClaudeAgent(
            api_key="test-key",
            queue=mock_queue,
            logger=logging.getLogger("test"),
            model="claude-3-opus-20240229",
            topic="test",
            timeout_minutes=5
        )
        assert agent.client is not None


@pytest.mark.asyncio
async def test_gemini_with_valid_key(mock_queue):
    """Test Gemini initialization"""
    from agents.gemini import GeminiAgent
    
    with patch("google.generativeai.configure"):
        with patch("google.generativeai.GenerativeModel") as mock_model:
            mock_model.return_value = MagicMock()
            agent = GeminiAgent(
                api_key="test-key",
                queue=mock_queue,
                logger=logging.getLogger("test"),
                model="gemini-pro",
                topic="test",
                timeout_minutes=5
            )
            assert agent.model is not None


@pytest.mark.asyncio
async def test_grok_with_valid_key(mock_queue):
    """Test Grok initialization with valid key"""
    from agents.grok import GrokAgent
    
    with patch("openai.OpenAI"):
        agent = GrokAgent(
            api_key="test-key",
            queue=mock_queue,
            logger=logging.getLogger("test"),
            model="grok-beta",
            topic="test",
            timeout_minutes=5
        )
        assert agent.client is not None


@pytest.mark.asyncio
async def test_perplexity_with_valid_key(mock_queue):
    """Test Perplexity initialization with valid key"""
    from agents.perplexity import PerplexityAgent
    
    with patch("openai.OpenAI"):
        agent = PerplexityAgent(
            api_key="test-key",
            queue=mock_queue,
            logger=logging.getLogger("test"),
            model="llama-3.1-sonar-large-128k-online",
            topic="test",
            timeout_minutes=5
        )
        assert agent.client is not None
