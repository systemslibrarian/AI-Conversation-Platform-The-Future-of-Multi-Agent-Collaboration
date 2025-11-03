
import pytest
import logging
from unittest.mock import MagicMock, patch
from agents import GeminiAgent, GrokAgent, PerplexityAgent

@pytest.fixture
def mock_queue(asyncio):
    from unittest.mock import AsyncMock
    q = AsyncMock()
    q.get_context.return_value = []
    q.get_last_sender.return_value = None
    q.is_terminated.return_value = False
    q.add_message.return_value = {"id": 1, "sender": "Test", "content": "Test message"}
    return q

@pytest.fixture
def logger():
    return logging.getLogger("test")

class DummyOpenAIClient:
    def __init__(self, *args, **kwargs):
        self.chat = type("Chat", (), {"completions": type("Comps", (), {})()})()
        def _create(**kwargs):
            usage = type("Usage", (), {"total_tokens": 50})()
            choice = type("Choice", (), {"message": type("Msg", (), {"content": "Hi from model"})()})()
            return type("Resp", (), {"choices": [choice], "usage": usage})()
        self.chat.completions.create = _create

class DummyGenAIModel:
    def __init__(self, *args, **kwargs):
        pass
    def start_chat(self, history=None):
        class Chat:
            def send_message(self, last):
                return type("Resp", (), {"text": "Gemini says hi"})()
        return Chat()

@pytest.mark.asyncio
async def test_grok_call(mock_queue, logger, monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "test-key")
    with patch("agents.grok.OpenAI", DummyOpenAIClient):
        agent = GrokAgent(api_key="dummy", queue=mock_queue, logger=logger, model="grok-beta", topic="x", timeout_minutes=1)
        content, tokens = await agent._call_api([{"role": "user", "content": "hi"}])
        assert "hi" in content.lower() or content != ""
        assert tokens > 0

@pytest.mark.asyncio
async def test_perplexity_call(mock_queue, logger, monkeypatch):
    monkeypatch.setenv("PERPLEXITY_API_KEY", "test-key")
    with patch("agents.perplexity.OpenAI", DummyOpenAIClient):
        agent = PerplexityAgent(api_key="dummy", queue=mock_queue, logger=logger, model="llama-3.1-sonar-large-128k-online", topic="x", timeout_minutes=1)
        content, tokens = await agent._call_api([{"role": "user", "content": "hi"}])
        assert content != ""
        assert tokens > 0

@pytest.mark.asyncio
async def test_gemini_call(mock_queue, logger, monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    # Patch google.generativeai.GenerativeModel
    with patch("agents.gemini.genai.GenerativeModel", DummyGenAIModel):
        agent = GeminiAgent(api_key="dummy", queue=mock_queue, logger=logger, model="gemini-1.5-pro", topic="x", timeout_minutes=1)
        content, tokens = await agent._call_api([{"role": "user", "content": "hi"}])
        assert "gemini" in content.lower()
        assert tokens >= 0
