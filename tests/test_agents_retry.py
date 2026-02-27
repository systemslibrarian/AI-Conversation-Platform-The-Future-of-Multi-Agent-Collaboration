# tests/test_agents_retry.py
from contextlib import ExitStack
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

# Provider patch targets used by your concrete agents
PROVIDER_PATCH = {
    "claude": "anthropic.Anthropic",
    "chatgpt": "openai.OpenAI",
    "grok": "openai.OpenAI",  # xAI Grok via OpenAI-compatible client
    "perplexity": "openai.OpenAI",  # Perplexity via OpenAI-compatible client
    "gemini": "google.generativeai.GenerativeModel",
}

# Explicit agent class names (avoid .capitalize() issues like "ChatgptAgent")
AGENT_CLASSES = {
    "claude": "ClaudeAgent",
    "chatgpt": "ChatGPTAgent",
    "grok": "GrokAgent",
    "perplexity": "PerplexityAgent",
    "gemini": "GeminiAgent",
}

AGENTS = list(PROVIDER_PATCH.keys())


class RateLimitError(Exception):
    """Test helper that looks like a 429 from an HTTP client."""

    def __init__(self, retry_after: float):
        self.status = 429
        self.headers = {"Retry-After": str(retry_after)}
        super().__init__("429 Too Many Requests")


def success_for(agent_name: str, text: str = "ok"):
    """Return a provider-shaped success object for each SDK."""
    if agent_name == "gemini":
        return MagicMock(text=text)
    elif agent_name == "claude":
        # Anthropic messages.create result shape
        return MagicMock(
            content=[MagicMock(text=text)],
            usage=MagicMock(input_tokens=1, output_tokens=1),
        )
    else:
        # OpenAI chat.completions.create result shape
        return MagicMock(
            choices=[MagicMock(message=MagicMock(content=text))],
            usage=MagicMock(total_tokens=2),
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("agent_name", AGENTS)
async def test_retry_on_timeout(agent_name):
    """Confirms retry on asyncio.TimeoutError then success enqueued."""
    module = __import__(f"agents.{agent_name}", fromlist=[""])
    AgentClass = getattr(module, AGENT_CLASSES[agent_name])
    patch_path = PROVIDER_PATCH[agent_name]

    mock_client = MagicMock()

    # --- THIS IS THE FIX ---
    # Raise a standard TimeoutError. Our base.py logic will catch
    # the "timeout" in the class name and error string.
    timeout_exc = TimeoutError("API call timed out")
    # --- END FIX ---

    if agent_name == "gemini":
        mock_chat = MagicMock()
        mock_chat.send_message.side_effect = [timeout_exc, success_for(agent_name, "success")]
        mock_client.start_chat.return_value = mock_chat
    elif agent_name == "claude":
        mock_client.messages.create.side_effect = [timeout_exc, success_for(agent_name, "success")]
    else:
        mock_client.chat.completions.create.side_effect = [
            timeout_exc,
            success_for(agent_name, "success"),
        ]

    patches_to_apply = [patch(patch_path, return_value=mock_client)]
    if agent_name == "gemini":
        patches_to_apply.append(patch("google.generativeai.configure", return_value=None))

    with ExitStack() as stack:
        for p in patches_to_apply:
            stack.enter_context(p)

        queue = AsyncMock()
        # Ensure awaited assertion works on this method explicitly
        queue.add_message = AsyncMock()
        logger = MagicMock()
        agent = AgentClass(
            api_key="test", model="test", queue=queue, logger=logger, topic="t", timeout_minutes=1
        )

        # BaseAgent._build_messages is async in your code → patch with AsyncMock
        with patch.object(
            agent,
            "_build_messages",
            new_callable=AsyncMock,
            return_value=[{"role": "user", "content": "hello"}],
        ):
            await agent.respond()

        # Assert we retried after timeout and then succeeded
        if agent_name == "gemini":
            assert mock_chat.send_message.call_count == 2
        elif agent_name == "claude":
            assert mock_client.messages.create.call_count == 2
        else:
            assert mock_client.chat.completions.create.call_count == 2

        queue.add_message.assert_awaited_with(agent.agent_name, "success", ANY)


@pytest.mark.asyncio
@pytest.mark.parametrize("agent_name", AGENTS)
async def test_429_backoff_respects_retry_after(agent_name):
    """Confirms 429 uses Retry-After (deterministic via patched add_jitter)."""
    module = __import__(f"agents.{agent_name}", fromlist=[""])
    AgentClass = getattr(module, AGENT_CLASSES[agent_name])
    patch_path = PROVIDER_PATCH[agent_name]

    mock_client = MagicMock()
    if agent_name == "gemini":
        mock_chat = MagicMock()
        mock_chat.send_message.side_effect = [RateLimitError(0.1), success_for(agent_name, "ok")]
        mock_client.start_chat.return_value = mock_chat
    elif agent_name == "claude":
        mock_client.messages.create.side_effect = [
            RateLimitError(0.1),
            success_for(agent_name, "ok"),
        ]
    else:
        mock_client.chat.completions.create.side_effect = [
            RateLimitError(0.1),
            success_for(agent_name, "ok"),
        ]

    patches_to_apply = [patch(patch_path, return_value=mock_client)]
    if agent_name == "gemini":
        patches_to_apply.append(patch("google.generativeai.configure", return_value=None))

    with ExitStack() as stack:
        for p in patches_to_apply:
            stack.enter_context(p)

        mock_sleep = stack.enter_context(patch("asyncio.sleep", new_callable=AsyncMock))
        # Make jitter deterministic (identity)
        stack.enter_context(patch("agents.base.add_jitter", lambda x: x))

        queue = AsyncMock()
        queue.add_message = AsyncMock()
        logger = MagicMock()
        agent = AgentClass(
            api_key="test", model="test", queue=queue, logger=logger, topic="t", timeout_minutes=1
        )

        with patch.object(
            agent,
            "_build_messages",
            new_callable=AsyncMock,
            return_value=[{"role": "user", "content": "hello"}],
        ):
            await agent.respond()

        mock_sleep.assert_awaited_once_with(0.1)
        queue.add_message.assert_awaited_with(agent.agent_name, "ok", ANY)

        if agent_name == "gemini":
            assert mock_chat.send_message.call_count == 2
        elif agent_name == "claude":
            assert mock_client.messages.create.call_count == 2
        else:
            assert mock_client.chat.completions.create.call_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("agent_name", AGENTS)
async def test_circuit_breaker_skips_when_open(agent_name):
    """Confirms circuit breaker skip: no provider call, no enqueue."""
    module = __import__(f"agents.{agent_name}", fromlist=[""])
    AgentClass = getattr(module, AGENT_CLASSES[agent_name])
    patch_path = PROVIDER_PATCH[agent_name]

    mock_client = MagicMock()
    patches_to_apply = [
        patch(patch_path, return_value=mock_client),
        patch("agents.base.CircuitBreaker.is_open", return_value=True),
    ]
    if agent_name == "gemini":
        patches_to_apply.append(patch("google.generativeai.configure", return_value=None))

    with ExitStack() as stack:
        for p in patches_to_apply:
            stack.enter_context(p)

        queue = AsyncMock()
        queue.add_message = AsyncMock()
        logger = MagicMock()
        agent = AgentClass(
            api_key="test", model="test", queue=queue, logger=logger, topic="t", timeout_minutes=1
        )

        with patch.object(
            agent,
            "_build_messages",
            new_callable=AsyncMock,
            return_value=[{"role": "user", "content": "hello"}],
        ):
            await agent.respond()

        # Provider never called
        if agent_name == "gemini":
            mock_client.start_chat.assert_not_called()
        elif agent_name == "claude":
            mock_client.messages.create.assert_not_called()
        else:
            mock_client.chat.completions.create.assert_not_called()

        # And nothing enqueued
        queue.add_message.assert_not_awaited()
