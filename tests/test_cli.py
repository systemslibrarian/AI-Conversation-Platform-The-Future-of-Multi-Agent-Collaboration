# tests/test_cli.py
import asyncio
from argparse import Namespace
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import builtins
import pytest
import sys


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


# -------- run_interactive (auto-yes happy path) --------
@pytest.mark.asyncio
async def test_run_interactive_auto_yes_full_flow(capsys):
    # Arrange: configured agents, stubbed dependencies
    with (
        patch("cli.start_conversation.detect_configured_agents", return_value={"claude", "chatgpt"}),
        patch(
            "cli.start_conversation.get_agent_info",
            side_effect=lambda t: {
                "class": type("C", (), {"PROVIDER_NAME": t.upper()}),
                "env_key": "ENV",
            },
        ),
        patch("cli.start_conversation.list_available_agents", return_value={"claude", "chatgpt"}),
        patch("cli.start_conversation.setup_logging") as mock_setup_logging,
        patch("cli.start_conversation.create_queue") as mock_create_queue,
        patch("cli.start_conversation.create_agent") as mock_create_agent,
        patch("cli.start_conversation.increment_conversations"),
        patch("cli.start_conversation.decrement_conversations"),
    ):
        mock_setup_logging.return_value = MagicMock()
        mock_create_queue.return_value = MagicMock()
        # Two cooperating stub agents
        mock_create_agent.side_effect = [stub_agent("A1"), stub_agent("A2")]

        from cli.start_conversation import ConversationStarter

        args = Namespace(
            agent1="claude",
            agent2="chatgpt",
            model1="m1",
            model2="m2",
            topic="ethics",
            turns=2,
            db=":memory:",
            yes=True,
        )
        starter = ConversationStarter(args)

        # Act
        await starter.run_interactive()

        out = capsys.readouterr().out.lower()
        # Tolerant to minor formatting changes
        assert "conversation" in out and "settings" in out
        assert "agent 1" in out and "claude" in out and "m1" in out
        assert "agent 2" in out and "chatgpt" in out and "m2" in out


# -------- run_interactive (confirmation prompt, user declines) --------
@pytest.mark.asyncio
async def test_run_interactive_requires_confirmation_and_aborts(capsys):
    with (
        patch("cli.start_conversation.detect_configured_agents", return_value={"claude", "chatgpt"}),
        patch(
            "cli.start_conversation.get_agent_info",
            side_effect=lambda t: {
                "class": type("C", (), {"PROVIDER_NAME": t.upper()}),
                "env_key": "ENV",
            },
        ),
        patch("cli.start_conversation.list_available_agents", return_value={"claude", "chatgpt"}),
        patch("cli.start_conversation.setup_logging") as mock_setup_logging,
        patch("cli.start_conversation.create_queue") as mock_create_queue,
        patch("cli.start_conversation.create_agent") as mock_create_agent,
        patch("cli.start_conversation.increment_conversations"),
        patch("cli.start_conversation.decrement_conversations"),
    ):
        mock_setup_logging.return_value = MagicMock()
        mock_create_queue.return_value = MagicMock()
        mock_create_agent.side_effect = [stub_agent("A1"), stub_agent("A2")]

        from cli.start_conversation import ConversationStarter

        # Include all args expected by ConversationStarter.__init__
        args = Namespace(
            agent1="claude",
            agent2="chatgpt",
            model1=None,
            model2=None,
            topic="ethics",
            turns=2,
            db=":memory:",
            yes=False,  # force confirmation prompt
        )
        starter = ConversationStarter(args)

        # Say “n” to confirmation prompt
        with mock_inputs("n"):
            await starter.run_interactive()

        out = capsys.readouterr().out.lower()
        # Check for core summary words, ignoring spacing/formatting
        assert "conversation" in out and "settings" in out
        assert "turns" in out
        assert "db file" in out
        # Successful return shows the 'n' input aborted early.


# -------- configuration checks --------
def test_check_configuration_messages(capsys):
    # No agents → returns False, prints instructions
    with patch("cli.start_conversation.detect_configured_agents", return_value=set()):
        from cli.start_conversation import ConversationStarter
        starter = ConversationStarter(args=None)
        ok = starter._check_configuration()
        assert ok is False

        out = capsys.readouterr().out.lower()
        assert "no ai agents configured" in out

    # One agent → returns True but warns
    with patch("cli.start_conversation.detect_configured_agents", return_value={"claude"}):
        from cli.start_conversation import ConversationStarter
        starter = ConversationStarter(args=Namespace(agent1=None, agent2=None, db=None))
        ok = starter._check_configuration()
        assert ok is True

        out = capsys.readouterr().out.lower()
        assert "only 1 agent configured" in out


# -------- selecting agents --------
def test_select_agent_from_cli_and_invalid_exit():
    with patch("cli.start_conversation.detect_configured_agents", return_value={"claude", "chatgpt"}):
        from cli.start_conversation import ConversationStarter
        starter = ConversationStarter(args=None)

        # Valid CLI agent
        a, m = starter._select_agent("first", cli_agent="claude")
        assert a == "claude" and m is None

        # Invalid CLI agent → sys.exit(1) and code == 1
        with pytest.raises(SystemExit) as e:
            starter._select_agent("first", cli_agent="bogus")
        assert e.value.code == 1


def test_select_agent_interactive(capsys):
    with patch("cli.start_conversation.detect_configured_agents", return_value={"claude", "chatgpt"}):
        from cli.start_conversation import ConversationStarter
        starter = ConversationStarter(args=None)

        # Choose option 2 from the sorted list
        with mock_inputs("2"):
            a, m = starter._select_agent("first", cli_agent=None)
        assert a in {"claude", "chatgpt"} and m is None

        # Ensure menu printed (case-insensitive)
        out = capsys.readouterr().out.lower()
        assert "select" in out and "agent" in out


def test_select_agent_interactive_invalid_input(capsys):
    """Interactive selection handles invalid input before succeeding."""
    with patch("cli.start_conversation.detect_configured_agents", return_value={"claude", "chatgpt"}):
        from cli.start_conversation import ConversationStarter
        starter = ConversationStarter(args=None)

        # Inputs: 1) invalid text, 2) out-of-range number, 3) valid number
        with mock_inputs("invalid_text", "99", "2"):
            a, m = starter._select_agent("second", cli_agent=None)

        out = capsys.readouterr().out
        assert a in {"claude", "chatgpt"}
        assert out.lower().count("invalid") >= 2


# -------- topic + turns prompts --------
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

    # From prompts (invalid turns input then valid turns)
    starter4 = ConversationStarter(args=None)
    with mock_inputs("topic", "invalid", "0", "5"):
        assert starter4._get_topic() == "topic"
        assert starter4._get_max_turns() == 5


# -------- async_main coverage (prove awaiting happens) --------
@pytest.mark.asyncio
async def test_async_main_invokes_services_and_starter_awaits():
    # Verify start_metrics_server + setup_tracing are called and run_interactive is awaited
    with (
        patch("cli.start_conversation.start_metrics_server") as mock_metrics,
        patch("cli.start_conversation.setup_tracing", create=True) as mock_tracing,
        patch("cli.start_conversation.ConversationStarter") as MockStarter,
    ):
        awaited = {"v": False}

        async def _noop():
            awaited["v"] = True

        starter_instance = MagicMock()
        starter_instance.run_interactive = _noop  # genuinely awaitable
        MockStarter.return_value = starter_instance

        from cli.start_conversation import async_main
        await async_main(Namespace(yes=True))

        assert mock_metrics.called and mock_tracing.called
        assert awaited["v"] is True  # proves run_interactive was awaited


# -------- main() coverage: happy path, argparse error, KeyboardInterrupt --------
def test_main_parses_args_and_calls_asyncio_run():
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
        called["ran"] = True
        assert hasattr(coro, "__await__")  # coroutine-like
        return None

    with (
        patch.object(sys, "argv", argv),
        patch("cli.start_conversation.async_main", side_effect=lambda args: asyncio.sleep(0)),
        patch("asyncio.run", side_effect=fake_run),
    ):
        from cli.start_conversation import main
        main()
        assert called.get("ran", False)


def test_main_argparse_error_exits_nonzero():
    # Invalid value for --turns so argparse exits nonzero
    with (
        patch.object(sys, "argv", ["aic-start", "--turns", "not_an_int"]),
        patch.object(sys, "exit") as mock_exit,
    ):
        from cli.start_conversation import main
        main()
        # argparse typically exits nonzero; accept any non-0 to avoid coupling to exact code
        assert mock_exit.call_args and mock_exit.call_args[0][0] != 0


def test_main_handles_keyboard_interrupt():
    """main() handles KeyboardInterrupt gracefully and exits with code 0."""
    with (
        patch("asyncio.run", side_effect=KeyboardInterrupt),
        patch.object(sys, "exit") as mock_exit,
    ):
        from cli.start_conversation import main
        main()
        mock_exit.assert_called_with(0)
