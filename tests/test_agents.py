import pytest
import logging
from unittest.mock import patch
from agents import create_agent, ChatGPTAgent, ClaudeAgent


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


class DummyChoice:
    def __init__(self, text):
        self.message = type("Msg", (), {"content": text})


class DummyUsage:
    def __init__(self, total_tokens):
        self.total_tokens = total_tokens


class DummyOpenAIClient:
    def __init__(self, *args, **kwargs):
        self.chat = type("Chat", (), {"completions": type("Comps", (), {})()})()

        def _create(**kwargs):
            return type(
                "Resp", (), {"choices": [DummyChoice("Hello, world!")], "usage": DummyUsage(20)}
            )()

        self.chat.completions.create = _create


class DummyAnthropicClient:
    def __init__(self, *args, **kwargs):
        def _create(**kwargs):
            content = [type("Block", (), {"text": "Hello from Claude!"})()]
            usage = type("Usage", (), {"input_tokens": 10, "output_tokens": 15})()
            return type("Resp", (), {"content": content, "usage": usage})()

        self.messages = type("Msgs", (), {"create": _create})()


@pytest.mark.asyncio
async def test_chatgpt_api_call(mock_queue, logger, monkeypatch):
    # Patch OpenAI in agents.chatgpt before instantiation
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    with patch("agents.chatgpt.OpenAI", DummyOpenAIClient):
        agent = ChatGPTAgent(
            api_key="dummy",
            queue=mock_queue,
            logger=logger,
            model="gpt-4o",
            topic="x",
            timeout_minutes=1,
        )
        content, tokens = await agent._call_api([{"role": "user", "content": "Hi"}])
        assert content == "Hello, world!"
        assert tokens == 20


@pytest.mark.asyncio
async def test_claude_api_call(mock_queue, logger, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    with patch("agents.claude.anthropic.Anthropic", DummyAnthropicClient):
        agent = ClaudeAgent(
            api_key="dummy",
            queue=mock_queue,
            logger=logger,
            model="claude-sonnet-4-5-20250929",
            topic="x",
            timeout_minutes=1,
        )
        content, tokens = await agent._call_api([{"role": "user", "content": "Hi"}])
        assert content == "Hello from Claude!"
        assert tokens == 25


def test_agent_factory_create(mock_queue, logger, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    with patch("agents.chatgpt.OpenAI", DummyOpenAIClient):
        agent = create_agent(agent_type="chatgpt", queue=mock_queue, logger=logger, api_key="dummy")
        assert isinstance(agent, ChatGPTAgent)
