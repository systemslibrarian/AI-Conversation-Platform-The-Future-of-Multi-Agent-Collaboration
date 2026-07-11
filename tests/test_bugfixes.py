"""Regression tests for bug fixes (in-memory queue, first-turn handling, etc.)."""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.base import BaseAgent
from core.config import config
from core.queue import SQLiteQueue


@pytest.fixture
def logger():
    return logging.getLogger("test_bugfixes")


@pytest.fixture
def mock_queue():
    queue = AsyncMock()
    queue.get_context.return_value = []
    queue.get_last_sender.return_value = None
    queue.is_terminated.return_value = False
    return queue


def make_agent(queue, logger, **kwargs):
    defaults = dict(model="test-model", topic="testing", timeout_minutes=5)
    defaults.update(kwargs)
    return BaseAgent(queue=queue, logger=logger, **defaults)


# ---------------------------------------------------------------------------
# SQLiteQueue ":memory:" support
# ---------------------------------------------------------------------------
class TestInMemoryQueue:
    @pytest.mark.asyncio
    async def test_memory_queue_persists_across_operations(self, logger, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)  # any stray lock file would land here
        queue = SQLiteQueue(":memory:", logger)

        await queue.add_message("claude", "hello there", {"tokens": 5})
        await queue.add_message("chatgpt", "hi back", {"tokens": 3})

        context = await queue.get_context()
        assert [m["content"] for m in context] == ["hello there", "hi back"]
        assert await queue.get_last_sender() == "ChatGPT"

        data = await queue.load()
        assert data["metadata"]["total_turns"] == 2
        assert data["metadata"]["total_tokens"] == 8

        await queue.mark_terminated("test_reason")
        assert await queue.is_terminated() is True
        assert await queue.get_termination_reason() == "test_reason"

        # No junk lock file created anywhere
        assert not list(tmp_path.iterdir()), "in-memory queue must not create files"

    @pytest.mark.asyncio
    async def test_memory_queues_are_isolated(self, logger):
        q1 = SQLiteQueue(":memory:", logger)
        q2 = SQLiteQueue(":memory:", logger)
        await q1.add_message("claude", "only in q1")
        assert await q2.get_last_sender() is None

    @pytest.mark.asyncio
    async def test_memory_queue_health_check(self, logger):
        queue = SQLiteQueue(":memory:", logger)
        health = await queue.health_check()
        assert health["healthy"] is True
        assert health["checks"]["database"] == "ok"
        assert health["checks"]["lock"] == "ok"

    @pytest.mark.asyncio
    async def test_unknown_sender_turns_are_counted(self, logger):
        queue = SQLiteQueue(":memory:", logger)
        await queue.add_message("CustomBot", "hello")
        data = await queue.load()
        assert data["metadata"]["custombot_turns"] == 1


# ---------------------------------------------------------------------------
# First-turn message building
# ---------------------------------------------------------------------------
class TestFirstTurnMessages:
    @pytest.mark.asyncio
    async def test_empty_context_seeds_user_kickoff(self, mock_queue, logger):
        agent = make_agent(mock_queue, logger, topic="AI ethics")
        messages = await agent._build_messages()
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert "AI ethics" in messages[0]["content"]

    @pytest.mark.asyncio
    async def test_partner_message_gets_topic_anchor(self, mock_queue, logger):
        """Each turn re-anchors the topic so the model doesn't chase tangents."""
        mock_queue.get_context.return_value = [{"sender": "Other", "content": "hi"}]
        agent = make_agent(mock_queue, logger, topic="AI safety")
        messages = await agent._build_messages()
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"].startswith("hi")
        assert "Moderator note" in messages[0]["content"]
        assert "AI safety" in messages[0]["content"]

    @pytest.mark.asyncio
    async def test_own_last_message_gets_no_anchor(self, mock_queue, logger):
        """The anchor is only appended to partner (user-role) messages."""
        mock_queue.get_context.return_value = [{"sender": "Base", "content": "my own words"}]
        agent = make_agent(mock_queue, logger)
        messages = await agent._build_messages()
        assert messages == [{"role": "assistant", "content": "my own words"}]


class TestClaudeMessageNormalization:
    def _claude_agent(self, mock_queue, logger):
        with patch("anthropic.Anthropic", return_value=MagicMock()):
            from agents.claude import ClaudeAgent

            return ClaudeAgent(
                api_key="k",
                queue=mock_queue,
                logger=logger,
                model="m",
                topic="t",
                timeout_minutes=1,
            )

    def test_assistant_first_gets_user_prefix(self, mock_queue, logger):
        agent = self._claude_agent(mock_queue, logger)
        result = agent._normalize_messages([{"role": "assistant", "content": "I went first"}])
        assert result[0]["role"] == "user"
        assert result[1] == {"role": "assistant", "content": "I went first"}

    def test_consecutive_same_role_merged(self, mock_queue, logger):
        agent = self._claude_agent(mock_queue, logger)
        result = agent._normalize_messages(
            [
                {"role": "user", "content": "a"},
                {"role": "user", "content": "b"},
                {"role": "assistant", "content": "c"},
            ]
        )
        assert result == [
            {"role": "user", "content": "a\n\nb"},
            {"role": "assistant", "content": "c"},
        ]

    def test_empty_messages_get_kickoff(self, mock_queue, logger):
        agent = self._claude_agent(mock_queue, logger)
        result = agent._normalize_messages([])
        assert len(result) == 1
        assert result[0]["role"] == "user"


# ---------------------------------------------------------------------------
# Conversation-opening race (is_initiator)
# ---------------------------------------------------------------------------
class TestInitiator:
    @pytest.mark.asyncio
    async def test_initiator_responds_to_empty_queue(self, mock_queue, logger):
        agent = make_agent(mock_queue, logger)
        assert await agent.should_respond("Partner") is True

    @pytest.mark.asyncio
    async def test_non_initiator_waits_on_empty_queue(self, mock_queue, logger):
        agent = make_agent(mock_queue, logger)
        agent.is_initiator = False
        assert await agent.should_respond("Partner") is False

    @pytest.mark.asyncio
    async def test_non_initiator_responds_after_partner(self, mock_queue, logger):
        mock_queue.get_last_sender.return_value = "Partner"
        agent = make_agent(mock_queue, logger)
        agent.is_initiator = False
        assert await agent.should_respond("Partner") is True


# ---------------------------------------------------------------------------
# Termination signals
# ---------------------------------------------------------------------------
class TestTerminationSignals:
    def test_termination_token_defined_in_config(self):
        assert config.TERMINATION_TOKEN == "[done]"

    def test_off_topic_marker_detected(self, mock_queue, logger):
        agent = make_agent(mock_queue, logger)
        reason = agent._check_termination_signals("This drifted. [off_topic]")
        assert reason is not None and "[off_topic]" in reason


# ---------------------------------------------------------------------------
# Retry-After header extraction (httpx.Headers-like, not a plain dict)
# ---------------------------------------------------------------------------
class TestRetryAfterHeaders:
    @pytest.mark.asyncio
    async def test_dict_like_headers_are_honored(self, mock_queue, logger):
        class Headers:  # mimics httpx.Headers: has .get but is not a dict
            def get(self, key, default=None):
                return "0.3" if key.lower() == "retry-after" else default

        class RateLimited(Exception):
            status = 429
            headers = Headers()

        agent = make_agent(mock_queue, logger)
        calls = iter([RateLimited("429 rate_limit"), ("ok", 1, 0.1)])

        async def fake_generate():
            item = next(calls)
            if isinstance(item, Exception):
                raise item
            return item

        sleeps = []

        async def fake_sleep(t):
            sleeps.append(t)

        with (
            patch.object(agent, "generate_response", side_effect=fake_generate),
            patch("agents.base.add_jitter", lambda x: x),
            patch("asyncio.sleep", fake_sleep),
        ):
            await agent.respond()

        assert sleeps == [pytest.approx(0.3)]
        mock_queue.add_message.assert_awaited()
