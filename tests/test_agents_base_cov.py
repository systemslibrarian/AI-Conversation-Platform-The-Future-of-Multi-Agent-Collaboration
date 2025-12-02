# Minimal tests to increase coverage for agents/base.py
import logging
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
