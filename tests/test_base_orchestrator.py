# tests/test_base_orchestrator.py

"""
Tests for BaseAgent orchestrator logic:
- run(): timeouts, max turns, interrupts, fatal errors
- respond(): retry loop, consecutive errors, repetition detection
- LLM-Guard import/scan failures
- Agent factory error paths & model selection
"""

import sys
import logging
import importlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.base import BaseAgent
from agents import create_agent
from core.config import config


# ---------- Fixtures ----------


@pytest.fixture
def mock_queue():
    """Fresh AsyncMock for QueueInterface-like surface."""
    q = AsyncMock()
    q.is_terminated.return_value = False
    q.get_last_sender.return_value = "Partner"
    return q


@pytest.fixture
def mock_logger():
    """MagicMock for logger."""
    return MagicMock(spec=logging.Logger)


@pytest.fixture
def test_agent(mock_queue, mock_logger):
    """
    Concrete BaseAgent with abstract API patched.
    Also patches key methods used by run()/respond().
    """
    with patch.object(
        BaseAgent, "_call_api", new_callable=AsyncMock, return_value=("Test response", 10)
    ):
        agent = BaseAgent(
            queue=mock_queue,
            logger=mock_logger,
            model="test-model",
            topic="test-topic",
            timeout_minutes=1,
            agent_name="TestAgent",
        )
        agent.generate_response = AsyncMock(return_value=("Test response", 10, 0.1))
        agent.should_respond = AsyncMock(return_value=True)
        agent._is_timeout = AsyncMock(return_value=False)
        yield agent


# ---------- run() tests ----------


@pytest.mark.asyncio
class TestAgentRunLoop:
    async def test_run_terminates_on_timeout(self, test_agent, mock_queue):
        test_agent._is_timeout.return_value = True

        # Spy on respond so we can assert it wasn't called
        with patch.object(test_agent, "respond", new_callable=AsyncMock) as mock_respond:
            await test_agent.run(max_turns=10, partner_name="Partner")

            mock_queue.mark_terminated.assert_called_with("timeout")
            mock_respond.assert_not_called()

    async def test_run_terminates_on_max_turns(self, test_agent, mock_queue):
        test_agent.should_respond.return_value = True

        async def respond_and_increment():
            test_agent.turn_count += 1

        # Patch respond to control call count
        with patch.object(test_agent, "respond", new_callable=AsyncMock) as mock_respond:
            mock_respond.side_effect = respond_and_increment

            await test_agent.run(max_turns=3, partner_name="Partner")

            assert mock_respond.call_count == 3
            mock_queue.mark_terminated.assert_called_with("max_turns_reached")

    async def test_run_terminates_on_keyboard_interrupt(self, test_agent, mock_queue):
        test_agent.should_respond.side_effect = KeyboardInterrupt

        await test_agent.run(max_turns=10, partner_name="Partner")

        mock_queue.mark_terminated.assert_called_with("user_interrupt")

    async def test_run_logs_and_raises_fatal_error(self, test_agent, mock_logger):
        err = RuntimeError("Fatal test error")
        test_agent.should_respond.side_effect = err

        with pytest.raises(RuntimeError, match="Fatal test error"):
            await test_agent.run(max_turns=10, partner_name="Partner")

        assert mock_logger.error.called
        msg, payload = mock_logger.error.call_args.args
        assert msg == "agent_error"
        assert payload.get("agent") == "TestAgent"
        assert "Fatal test error" in payload.get("error", "")


# ---------- respond() tests ----------


@pytest.mark.asyncio
class TestAgentRespondLoop:
    async def test_respond_terminates_on_consecutive_errors(self, test_agent, mock_queue):
        test_agent.generate_response.side_effect = Exception("Generic API error")
        test_agent.max_consecutive_errors = 3
        test_agent.max_retries = 1  # keep each attempt fast

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await test_agent.respond()
        assert test_agent.consecutive_errors == 1
        mock_queue.mark_terminated.assert_not_called()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await test_agent.respond()
        assert test_agent.consecutive_errors == 2
        mock_queue.mark_terminated.assert_not_called()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(Exception, match="Generic API error"):
                await test_agent.respond()
        assert test_agent.consecutive_errors == 3
        mock_queue.mark_terminated.assert_called_with("consecutive_errors")

    async def test_respond_terminates_on_too_many_retries(self, test_agent, mock_queue):
        test_agent.generate_response.side_effect = TimeoutError("API timeout")
        test_agent.max_retries = 5

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await test_agent.respond()

        assert test_agent.generate_response.call_count == 5
        mock_queue.mark_terminated.assert_called_with("too_many_retries")

    async def test_respond_terminates_on_repetition(self, test_agent, mock_queue, monkeypatch):
        test_agent.generate_response.return_value = ("I am a robot", 10, 0.1)
        monkeypatch.setattr(config, "MAX_CONSECUTIVE_SIMILAR", 2, raising=False)

        await test_agent.respond()
        assert test_agent.consecutive_similar == 0
        mock_queue.mark_terminated.assert_not_called()

        await test_agent.respond()
        assert test_agent.consecutive_similar == 1
        mock_queue.mark_terminated.assert_not_called()

        await test_agent.respond()
        mock_queue.mark_terminated.assert_called_with("repetition_detected")


# ---------- LLM-Guard & scanning tests ----------


class TestSecurityAndImports:
    def test_base_agent_init_without_llm_guard(self, mock_queue, mock_logger):
        import agents.base as agents_base_module

        prior_llm_guard = sys.modules.pop("llm_guard", None)
        prior_input = sys.modules.pop("llm_guard.input_scanners", None)
        prior_output = sys.modules.pop("llm_guard.output_scanners", None)

        try:
            importlib.reload(agents_base_module)
            with patch.object(
                agents_base_module.BaseAgent,
                "_call_api",
                new_callable=AsyncMock,
                return_value=("x", 1),
            ):
                agent = agents_base_module.BaseAgent(
                    queue=mock_queue,
                    logger=mock_logger,
                    model="m",
                    topic="t",
                    timeout_minutes=1,
                )
            assert agent.llm_guard_enabled is False
            assert mock_logger.warning.called
            assert "llm-guard" in (mock_logger.warning.call_args.args[0] or "").lower()
        finally:
            if prior_llm_guard:
                sys.modules["llm_guard"] = prior_llm_guard
            if prior_input:
                sys.modules["llm_guard.input_scanners"] = prior_input
            if prior_output:
                sys.modules["llm_guard.output_scanners"] = prior_output
            importlib.reload(agents_base_module)

    def test_scan_input_handles_exception(self, test_agent, mock_logger):
        test_agent.llm_guard_enabled = True
        test_agent.input_scanner = MagicMock()
        test_agent.input_scanner.scan.side_effect = Exception("Scan failed!")

        text, is_valid = test_agent._scan_input("original text")

        assert text == "original text"
        assert is_valid is True
        mock_logger.error.assert_called()
        assert "Input scanning failed" in mock_logger.error.call_args.args[0]

    def test_scan_output_handles_exception(self, test_agent, mock_logger):
        test_agent.llm_guard_enabled = True
        test_agent.output_scanner = MagicMock()
        test_agent.output_scanner.scan.side_effect = Exception("Scan failed!")

        text = test_agent._scan_output("original text")

        assert text == "original text"
        mock_logger.error.assert_called()
        assert "Output scanning failed" in mock_logger.error.call_args.args[0]


# ---------- Agent factory tests ----------


class TestAgentFactoryFailures:
    def test_factory_raises_unknown_agent(self, mock_queue, mock_logger):
        with pytest.raises(ValueError, match="Unknown agent type: 'foobar'"):
            create_agent(agent_type="foobar", queue=mock_queue, logger=mock_logger)

    def test_factory_raises_missing_api_key(self, mock_queue, mock_logger):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="Missing API key for 'chatgpt'"):
                create_agent(
                    agent_type="chatgpt",
                    queue=mock_queue,
                    logger=mock_logger,
                )

    def test_factory_loads_default_model(self, mock_queue, mock_logger):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "fake-key"}):
            with patch("openai.OpenAI"):
                from agents.chatgpt import ChatGPTAgent

                agent = create_agent(
                    agent_type="chatgpt",
                    queue=mock_queue,
                    logger=mock_logger,
                )
                assert agent.model == ChatGPTAgent.DEFAULT_MODEL

    def test_factory_loads_model_override(self, mock_queue, mock_logger):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "fake-key"}):
            with patch("openai.OpenAI"):
                agent = create_agent(
                    agent_type="chatgpt",
                    queue=mock_queue,
                    logger=mock_logger,
                    model="my-custom-model-123",
                )
                assert agent.model == "my-custom-model-123"
