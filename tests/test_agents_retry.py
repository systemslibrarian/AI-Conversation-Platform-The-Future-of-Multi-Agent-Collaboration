"""
Full retry + circuit breaker tests for ALL 5 agents
Covers: timeout retry, 429 backoff, circuit open skip, malformed response
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# === ALL AGENTS ===
AGENTS = ["claude", "chatgpt", "grok", "perplexity", "gemini"]


# ============================================================================
# RETRY ON TIMEOUT
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("agent_name", AGENTS)
async def test_retry_on_timeout(agent_name):
    """All agents retry once on asyncio.TimeoutError"""
    module = __import__(f"agents.{agent_name}", fromlist=[""])
    AgentClass = getattr(module, f"{agent_name.capitalize()}Agent")

    mock_client = AsyncMock()
    mock_client.messages.create.side_effect = [
        asyncio.TimeoutError,
        MagicMock(
            content=[MagicMock(text="success")], usage=MagicMock(input_tokens=1, output_tokens=1)
        ),
    ]

    with patch(f"agents.{agent_name}.get_client", return_value=mock_client):
        agent = AgentClass(model="test")
        response = await agent.say("hello")

        assert response == "success"
        assert mock_client.messages.create.call_count == 2


# ============================================================================
# 429 + EXPONENTIAL BACKOFF
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("agent_name", AGENTS)
async def test_429_backoff_respects_retry_after(agent_name):
    """All agents back off using Retry-After header"""
    module = __import__(f"agents.{agent_name}", fromlist=[""])
    AgentClass = getattr(module, f"{agent_name.capitalize()}Agent")

    mock_client = AsyncMock()
    mock_429 = MagicMock()
    mock_429.status = 429
    mock_429.headers = {"Retry-After": "0.1"}

    mock_client.messages.create.side_effect = [mock_429, MagicMock(content=[MagicMock(text="ok")])]

    with (
        patch(f"agents.{agent_name}.get_client", return_value=mock_client),
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        agent = AgentClass(model="test")
        await agent.say("hello")

        mock_sleep.assert_called_once_with(0.1)
        assert mock_client.messages.create.call_count == 2


# ============================================================================
# CIRCUIT BREAKER SKIP
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("agent_name", AGENTS)
async def test_circuit_breaker_skips_when_open(agent_name):
    """No API call when circuit is open"""
    module = __import__(f"agents.{agent_name}", fromlist=[""])
    AgentClass = getattr(module, f"{agent_name.capitalize()}Agent")

    mock_client = AsyncMock()

    with (
        patch(f"agents.{agent_name}.get_client", return_value=mock_client),
        patch(f"agents.{agent_name}.circuit_breaker.is_open", return_value=True),
    ):
        agent = AgentClass(model="test")
        response = await agent.say("hello")

        assert "[Circuit breaker open" in response
        mock_client.messages.create.assert_not_called()


# ============================================================================
# MALFORMED RESPONSE FALLBACK
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("agent_name", AGENTS)
async def test_malformed_response_returns_fallback(agent_name):
    """Agents return fallback on bad JSON/response"""
    module = __import__(f"agents.{agent_name}", fromlist=[""])
    AgentClass = getattr(module, f"{agent_name.capitalize()}Agent")

    mock_client = AsyncMock()
    mock_client.messages.create.return_value = {"content": "not a list"}

    with patch(f"agents.{agent_name}.get_client", return_value=mock_client):
        agent = AgentClass(model="test")
        response = await agent.say("hello")

        assert "[Invalid response" in response or "error" in response.lower()
        mock_client.messages.create.assert_called_once()


# ============================================================================
# CONNECTION ERROR RETRY
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("agent_name", AGENTS)
async def test_retry_on_connection_error(agent_name):
    """Retry on network/DNS failure"""
    module = __import__(f"agents.{agent_name}", fromlist=[""])
    AgentClass = getattr(module, f"{agent_name.capitalize()}Agent")

    mock_client = AsyncMock()
    mock_client.messages.create.side_effect = [
        ConnectionError("Network down"),
        MagicMock(content=[MagicMock(text="recovered")]),
    ]

    with patch(f"agents.{agent_name}.get_client", return_value=mock_client):
        agent = AgentClass(model="test")
        response = await agent.say("hello")

        assert response == "recovered"
        assert mock_client.messages.create.call_count == 2
