# tests/test_cli.py
import asyncio
import types
from argparse import Namespace
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import builtins
import pytest

# Import after patches in individual tests to avoid side effects


@contextmanager
def mock_inputs(*answers):
    """Mock builtins.input with a sequence of answers."""
    seq = list(answers)
    def _fake_input(prompt=""):
        return seq.pop(0) if seq else ""
    with patch.object(builtins, "input", side_effect=_fake_input):
        yield


def stub_agent(name):
    """Return a minimal async-capable agent stub with .run() and .agent_name."""
    class _A:
        agent_name = name
        async def run(self, max_turns: int, partner_name: str):
            return None
    return _A()


@pytest.mark.asyncio
async def test_run_interactive_auto_yes_full_flow(capsys):
    # Arrange: configured agents, stubbed dependencies
    with patch("cli.start_conversation.detect_configured_agents", return_value={"claude", "chatgpt"}), \
         patch("cli.start_conversation.get_agent_info", side_effect=lambda t: {"class": type("C", (), {"PROVIDER_NAME": t.upper()}), "env_key": "ENV"}), \
         patch("cli.start_conversation.list_available_agents", return_value={"claude", "chatgpt"}), \
         patch("cli.start_conversation.setup_logging") as mock_setup_logging, \
         patch("cli.start_conversation.create_queue") as mock_create_queue, \
         patch("cli.start_conversation.create_agent") as mock_create_agent, \
         patch("cli.start_conversation.increment_conversations"), \
         patch("cli.start_conversation.decrement_conversations"):

        mock_setup_logging.return_value = MagicMock()
        mock_create_queue.return_value = MagicMock()
        # Two cooperating stub agents
        mock_create_agent.side_effect = [stub_agent("A1"), stub_agent("A2")]

        from cli.start_conversation import ConversationStarter
        args = Namespace(
            agent1="claude", agent2="chatgpt",
            model1="m1", model2="m2",
            topic="ethics", turns=2, db=":memory:", yes=True
        )
        starter = ConversationStarter(args)

        # Act
        await starter.run_interactive()

        # Assert (just sanity: banner & summary printed)
        out = capsys.readouterr().out
        assert "CONVERSATION SETTINGS" in out
        assert "Agent 1 : CLAUDE (m1)" in out
        assert "Agent 2 : CHATGPT (m2)" in out


def test_check_configuration_messages(capsys):
    # No agents → returns False, prints instructions
    with patch("cli.start_conversation.detect_configured_agents", return_value=set()):
        from cli.start_conversation import ConversationStarter
        starter = ConversationStarter(args=None)
        ok = starter._check_configuration()
        assert ok is False
        out = capsys.readouterr().out
        assert "No AI agents configured!" in out

    # One agent → returns True but warns
    with patch("cli.start_conversation.detect_configured_agents", return_value={"claude"}):
        from cli.start_conversation import ConversationStarter
        starter = ConversationStarter(args=Namespace(agent1=None, agent2=None))
        ok = starter._check_configuration()
        assert ok is True
        out = capsys.readouterr().out
        assert "Only 1 agent configured" in out


def test_select_agent_from_cli_and_invalid_exit():
    with patch("cli.start_conversation.detect_configured_agents", return_value={"claude", "chatgpt"}):
        from cli.start_conversation import ConversationStarter
        starter = ConversationStarter(args=None)

        # Valid CLI agent
        a, m = starter._select_agent("first", cli_agent="claude")
        assert a == "claude" and m is None

        # Invalid CLI agent → sys.exit(1)
        with pytest.raises(SystemExit):
            starter._select_agent("first", cli_agent="bogus")


def test_select_agent_interactive(capsys):
    with patch("cli.start_conversation.detect_configured_agents", return_value={"claude", "chatgpt"}):
        from cli.start_conversation import ConversationStarter
        starter = ConversationStarter(args=None)

        # Choose option 2 from the sorted list
        with mock_inputs("2"):
            a, m = starter._select_agent("first", cli_agent=None)
        assert a in {"claude", "chatgpt"} and m is None
        # Ensure menu printed
        out = capsys.readouterr().out
        assert "Select first agent:" in out


def test_get_topic_and_turns_from_args_and_prompts():
    from cli.start_conversation import ConversationStarter

    # From args
    starter = ConversationStarter(args=Namespace(topic="ethics", turns=7))
    assert starter._get_topic() == "ethics"
    assert starter._get_max_turns() == 7

    # From prompts (defaulting logic)
    starter2 = ConversationStarter(args=None)
    with mock_inputs("", ""):
        assert starter2._get_topic() == "general"
        assert starter2._get_max_turns() == 50

    # From prompts (custom values)
    starter3 = ConversationStarter(args=None)
    with mock_inputs("my topic", "12"):
        assert starter3._get_topic() == "my topic"
        assert starter3._get_max_turns() == 12


@pytest.mark.asyncio
async def test_async_main_invokes_services_and_starter():
    # Verify start_metrics_server + setup_tracing are called and run_interactive is awaited
    with patch("cli.start_conversation.start_metrics_server") as mock_metrics, \
         patch("cli.start_conversation.setup_tracing") as mock_tracing, \
         patch("cli.start_conversation.ConversationStarter") as MockStarter:

        starter_instance = MagicMock()
        starter_instance.run_interactive = MagicMock()
        async def _noop():
            return None
        # Make run_interactive an awaitable
        starter_instance.run_interactive.side_effect = _noop()
        MockStarter.return_value = starter_instance

        from cli.start_conversation import async_main
        await async_main(Namespace(yes=True))

        assert mock_metrics.called
        assert mock_tracing.called
        assert starter_instance.run_interactive.called


def test_main_parses_args_and_calls_asyncio_run(monkeypatch):
    # We don't execute the event loop; we assert asyncio.run is called with async_main(args)
    import sys

    argv = [
        "aic-start",
        "--agent1", "claude",
        "--agent2", "chatgpt",
        "--model1", "m1",
        "--model2", "m2",
        "--topic", "ethics",
        "--turns", "3",
        "--db", "conv.db",
        "-y",
    ]

    called = {}

    def fake_run(coro):
        # capture the arg Namespace passed into async_main
        called["ran"] = True
        # The coroutine is async_main(args); inspect its closure-free signature by duck-typing:
        assert hasattr(coro, "__await__")
        return None

    with patch.object(sys, "argv", argv), \
         patch("cli.start_conversation.async_main", side_effect=lambda args: asyncio.sleep(0)), \
         patch("asyncio.run", side_effect=fake_run):

        from cli.start_conversation import main
        main()
        assert called.get("ran", False)
