"""
Agent retry, rate-limit, and circuit-breaker tests
Covers: retry on timeout, 429 back-off, circuit breaker skip
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# List of all agents to test – add/remove as needed
AGENTS = ["claude", "chatgpt", "grok", "perplexity", "gemini"]


# ============================================================================
# RETRY ON TIMEOUT
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("agent_name", AGENTS)
async def test_agent_retries_on_timeout(agent_name):
    """All agents retry once on asyncio.TimeoutError"""
    module = __import__(f"agents.{agent_name}", fromlist=[""])
    AgentClass = getattr(module, f"{agent_name.capitalize()}Agent")

    mock_client = AsyncMock()
    mock_client.messages.create.side_effect = [
        asyncio.TimeoutError,
        {"content": [{"text": "success"}]},
    ]

    with patch(f"agents.{agent_name}.get_client", return_value=mock_client):
        agent = AgentClass(model="test-model")
        response = await agent.say("hello")

        assert response == "success"
        assert mock_client.messages.create.call_count == 2


# ============================================================================
# RATE LIMIT (429) WITH EXPONENTIAL BACKOFF
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("agent_name", AGENTS)
async def test_agent_backoff_on_429(agent_name):
    """All agents respect Retry-After and back off exponentially"""
    module = __import__(f"agents.{agent_name}", fromlist=[""])
    AgentClass = getattr(module, f"{agent_name.capitalize()}Agent")

    mock_client = AsyncMock()
    mock_response_429 = MagicMock()
    mock_response_429.status = 429
    mock_response_429.headers = {"Retry-After": "0.1"}  # 100ms

    mock_client.messages.create.side_effect = [
        mock_response_429,
        {"content": [{"text": "ok after backoff"}]},
    ]

    with (
        patch(f"agents.{agent_name}.get_client", return_value=mock_client),
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        agent = AgentClass(model="test-model")
        response = await agent.say("hello")

        assert response == "ok after backoff"
        assert mock_client.messages.create.call_count == 2
        mock_sleep.assert_called_once_with(0.1)  # respects Retry-After


# ============================================================================
# CIRCUIT BREAKER – SKIP CALL WHEN OPEN
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("agent_name", AGENTS)
async def test_circuit_breaker_skips_call_when_open(agent_name):
    """Circuit breaker prevents API call when open"""
    module = __import__(f"agents.{agent_name}", fromlist=[""])
    AgentClass = getattr(module, f"{agent_name.capitalize()}Agent")

    mock_client = AsyncMock()

    with (
        patch(f"agents.{agent_name}.get_client", return_value=mock_client),
        patch(f"agents.{agent_name}.circuit_breaker.is_open", return_value=True),
    ):
        agent = AgentClass(model="test-model")
        response = await agent.say("hello")

        assert response == "[Circuit breaker open - skipping]"
        mock_client.messages.create.assert_not_called()


# ============================================================================
# MALFORMED RESPONSE HANDLING (BONUS COVERAGE)
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("agent_name", AGENTS)
async def test_malformed_response_returns_fallback(agent_name):
    """Agents return fallback message on malformed JSON/response"""
    module = __import__(f"agents.{agent_name}", fromlist=[""])
    AgentClass = getattr(module, f"{agent_name.capitalize()}Agent")

    mock_client = AsyncMock()
    mock_client.messages.create.return_value = {"content": "not a list"}

    with patch(f"agents.{agent_name}.get_client", return_value=mock_client):
        agent = AgentClass(model="test-model")
        response = await agent.say("hello")

        assert response == "[Invalid response format]"
        mock_client.messages.create.assert_called_once()


# ============================================================================
# NETWORK ERROR – RETRY ON CONNECTIONERROR
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("agent_name", AGENTS)
async def test_agent_retries_on_connection_error(agent_name):
    """Agents retry on ConnectionError (e.g. DNS, network)"""
    module = __import__(f"agents.{agent_name}", fromlist=[""])
    AgentClass = getattr(module, f"{agent_name.capitalize()}Agent")

    mock_client = AsyncMock()
    mock_client.messages.create.side_effect = [
        ConnectionError("Network unreachable"),
        {"content": [{"text": "recovered"}]},
    ]

    with patch(f"agents.{agent_name}.get_client", return_value=mock_client):
        agent = AgentClass(model="test-model")
        response = await agent.say("hello")

        assert response == "recovered"
        assert mock_client.messages.create.call_count == 2
