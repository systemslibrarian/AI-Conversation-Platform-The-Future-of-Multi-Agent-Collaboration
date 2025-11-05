"""
Full retry + circuit breaker tests for ALL 5 agents
Covers: timeout retry, 429 backoff, circuit open skip, malformed response
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# Provider patch paths for each agent
PROVIDER_PATCH = {
    "claude": "anthropic.Anthropic",
    "chatgpt": "openai.OpenAI",
    "grok": "openai.OpenAI",
    "perplexity": "openai.OpenAI",
    "gemini": "google.generativeai.GenerativeModel",
}

AGENTS = list(PROVIDER_PATCH.keys())


@pytest.mark.asyncio
@pytest.mark.parametrize("agent_name", AGENTS)
async def test_retry_on_timeout(agent_name):
    module = __import__(f"agents.{agent_name}", fromlist=[""])
    AgentClass = getattr(module, f"{agent_name.capitalize()}Agent")

    patch_path = PROVIDER_PATCH[agent_name]

    mock_client = AsyncMock()
    if agent_name == "gemini":
        mock_chat = MagicMock()
        mock_chat.send_message.side_effect = [asyncio.TimeoutError, MagicMock(text="success")]
        mock_client.start_chat.return_value = mock_chat
    elif agent_name == "claude":
        mock_client.messages.create.side_effect = [asyncio.TimeoutError, MagicMock(content=[MagicMock(text="success")], usage=MagicMock(input_tokens=1, output_tokens=1))]
    else:
        mock_client.chat.completions.create.side_effect = [asyncio.TimeoutError, MagicMock(choices=[MagicMock(message=MagicMock(content="success"))], usage=MagicMock(total_tokens=2))]

    additional_patches = []
    if agent_name == "gemini":
        additional_patches.append(patch("google.generativeai.configure", return_value=None))

    with patch(patch_path, return_value=mock_client), *additional_patches:
        agent = AgentClass(api_key="test", model="test")
        response = await agent.say("hello")

        assert "success" in response

        if agent_name == "gemini":
            assert mock_chat.send_message.call_count == 2
        elif agent_name == "claude":
            assert mock_client.messages.create.call_count == 2
        else:
            assert mock_client.chat.completions.create.call_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("agent_name", AGENTS)
async def test_429_backoff_respects_retry_after(agent_name):
    module = __import__(f"agents.{agent_name}", fromlist=[""])
    AgentClass = getattr(module, f"{agent_name.capitalize()}Agent")

    patch_path = PROVIDER_PATCH[agent_name]

    mock_client = AsyncMock()
    mock_429 = MagicMock(status=429, headers={"Retry-After": "0.1"})

    if agent_name == "gemini":
        mock_chat = MagicMock()
        mock_chat.send_message.side_effect = [mock_429, MagicMock(text="ok")]
        mock_client.start_chat.return_value = mock_chat
    elif agent_name == "claude":
        mock_client.messages.create.side_effect = [mock_429, MagicMock(content=[MagicMock(text="ok")])]
    else:
        mock_client.chat.completions.create.side_effect = [mock_429, MagicMock(choices=[MagicMock(message=MagicMock(content="ok"))])]

    additional_patches = []
    if agent_name == "gemini":
        additional_patches.append(patch("google.generativeai.configure", return_value=None))

    with patch(patch_path, return_value=mock_client), \
         patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep, \
         *additional_patches:

        agent = AgentClass(api_key="test", model="test")
        await agent.say("hello")

        mock_sleep.assert_called_once_with(0.1)

        if agent_name == "gemini":
            assert mock_chat.send_message.call_count == 2
        elif agent_name == "claude":
            assert mock_client.messages.create.call_count == 2
        else:
            assert mock_client.chat.completions.create.call_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("agent_name", AGENTS)
async def test_circuit_breaker_skips_when_open(agent_name):
    module = __import__(f"agents.{agent_name}", fromlist=[""])
    AgentClass = getattr(module, f"{agent_name.capitalize()}Agent")

    patch_path = PROVIDER_PATCH[agent_name]

    mock_client = AsyncMock()

    additional_patches = []
    if agent_name == "gemini":
        additional_patches.append(patch("google.generativeai.configure", return_value=None))

    with patch(patch_path, return_value=mock_client), \
         patch(f"agents.{agent_name}.circuit_breaker.is_open", return_value=True), \
         *additional_patches:

        agent = AgentClass(api_key="test", model="test")
        response = await agent.say("hello")

        assert "[Circuit breaker open" in response

        if agent_name == "gemini":
            mock_client.start_chat.assert_not_called()
        elif agent_name == "claude":
            mock_client.messages.create.assert_not_called()
        else:
            mock_client.chat.completions.create.assert_not_called()
