# Minimal tests to increase coverage for agents/base.py
import logging
from unittest.mock import patch, MagicMock
from agents import base


class DummyQueue:
    async def add_message(self, *a, **k):
        pass

    async def get_context(self, *a, **k):
        return []

    async def get_last_sender(self):
        return None

    async def is_terminated(self):
        return False

    async def mark_terminated(self, *a, **k):
        pass

    async def get_termination_reason(self):
        return ""

    async def load(self):
        return {}


class DummyAgent(base.BaseAgent):
    PROVIDER_NAME = "dummy"

    def __init__(self):
        super().__init__(
            queue=DummyQueue(),
            logger=logging.getLogger("test"),
            model="dummy-model",
            topic="test-topic",
            timeout_minutes=5,
            agent_name="dummy",
        )

    async def respond(self, *a, **k):
        return "ok"


def test_agent_str_repr():
    agent = DummyAgent()
    assert "dummy" in str(agent).lower()
    assert "dummy" in repr(agent).lower()


def test_agent_circuit_breaker():
    agent = DummyAgent()
    assert agent.circuit_breaker.state == "CLOSED"
    agent.circuit_breaker.record_failure()
    agent.circuit_breaker.record_success()
    assert agent.circuit_breaker.failure_count == 0


def test_agent_circuit_breaker_opens():
    agent = DummyAgent()
    # Record multiple failures to open circuit
    for _ in range(6):
        agent.circuit_breaker.record_failure()
    assert agent.circuit_breaker.is_open()


def test_agent_turn_tracking():
    agent = DummyAgent()
    assert agent.turn_count == 0
    agent.turn_count += 1
    assert agent.turn_count == 1


def test_agent_consecutive_errors():
    agent = DummyAgent()
    assert agent.consecutive_errors == 0
    agent.consecutive_errors += 1
    assert agent.consecutive_errors == 1


def test_agent_recent_responses():
    agent = DummyAgent()
    agent.recent_responses.append("response1")
    agent.recent_responses.append("response2")
    assert len(agent.recent_responses) == 2


def test_agent_circuit_breaker_half_open():
    agent = DummyAgent()
    # Open circuit
    for _ in range(6):
        agent.circuit_breaker.record_failure()
    # Manually set to HALF_OPEN
    agent.circuit_breaker.state = "HALF_OPEN"
    assert not agent.circuit_breaker.is_open()


def test_agent_scan_input_disabled():
    agent = DummyAgent()
    text, valid = agent._scan_input("test input")
    assert text == "test input"
    assert valid is True


def test_agent_scan_output_disabled():
    agent = DummyAgent()
    result = agent._scan_output("test output")
    assert result == "test output"


def test_agent_llm_guard_enabled_import_error():
    """Test LLM Guard ImportError path (lines 128-133)"""
    with patch("agents.base.config.ENABLE_LLM_GUARD", True):
        # The import will fail and agent should disable llm_guard
        agent = DummyAgent()
        assert not agent.llm_guard_enabled


def test_agent_scan_input_with_llm_guard():
    """Test _scan_input with LLM Guard enabled (lines 160-162)"""
    agent = DummyAgent()
    agent.llm_guard_enabled = True
    agent.input_scanner = MagicMock()
    # Simulate invalid input detection
    agent.input_scanner.scan = MagicMock(return_value=("sanitized", False, 0.8))
    
    text, valid = agent._scan_input("malicious input")
    assert text == "sanitized"
    assert valid is False


def test_agent_scan_output_with_llm_guard():
    """Test _scan_output with LLM Guard enabled (lines 173-175)"""
    agent = DummyAgent()
    agent.llm_guard_enabled = True
    agent.output_scanner = MagicMock()
    # Simulate output scanning issue
    agent.output_scanner.scan = MagicMock(return_value=("sanitized output", False, 0.7))
    
    result = agent._scan_output("problematic output")
    assert result == "sanitized output"
