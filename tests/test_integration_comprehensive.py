"""
Integration tests for AI Conversation Platform
Tests end-to-end scenarios to ensure all components work together
"""

import pytest
import asyncio
import tempfile
import logging
from pathlib import Path
from unittest.mock import patch

from agents import create_agent, ChatGPTAgent, ClaudeAgent
from core.queue import SQLiteQueue, create_queue
from core.config import config


@pytest.fixture
def temp_db():
    """Create temporary database"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    if db_path.exists():
        db_path.unlink()
    lock_file = Path(f"{db_path}.lock")
    if lock_file.exists():
        lock_file.unlink()


@pytest.fixture
def logger():
    """Create test logger"""
    return logging.getLogger("integration_test")


class MockAPIClient:
    """Mock API client for testing"""

    def __init__(self, agent_name, responses=None):
        self.agent_name = agent_name
        self.call_count = 0
        self.responses = responses or []

    def get_response(self, turn):
        """Get response for turn"""
        if turn < len(self.responses):
            return self.responses[turn]
        return f"{self.agent_name} response {turn + 1}"


class IntegrationTestAgent:
    """Test agent for integration tests"""

    def __init__(self, name, queue, logger, model="test", topic="test", responses=None):
        self.name = name
        self.queue = queue
        self.logger = logger
        self.model = model
        self.topic = topic
        self.turn_count = 0
        self.responses = responses or []

    async def run(self, max_turns, partner_name):
        """Simplified run loop for testing"""
        for turn in range(max_turns):
            # Wait for turn
            await asyncio.sleep(0.01)

            last_sender = await self.queue.get_last_sender()

            # Check if it's our turn
            if last_sender is None or last_sender == partner_name:
                # Generate response
                if turn < len(self.responses):
                    content = self.responses[turn]
                else:
                    content = f"{self.name} message {turn + 1}"

                # Add to queue
                await self.queue.add_message(
                    self.name,
                    content,
                    {"turn": turn + 1, "tokens": 50, "response_time": 0.1},
                )
                self.turn_count += 1

                # Check termination
                if await self.queue.is_terminated():
                    break

            # Check if partner terminated
            if await self.queue.is_terminated():
                break

        # Mark complete if we reached max turns
        if self.turn_count >= max_turns:
            await self.queue.mark_terminated("max_turns_reached")


class TestFullConversationFlow:
    """Test complete conversation flows"""

    @pytest.mark.asyncio
    async def test_two_agent_conversation(self, temp_db, logger):
        """Test two agents having a conversation"""
        queue = SQLiteQueue(temp_db, logger)

        # Create two test agents
        agent1 = IntegrationTestAgent(
            "Agent1",
            queue,
            logger,
            responses=["Hello Agent2", "How are you?", "Goodbye"],
        )
        agent2 = IntegrationTestAgent(
            "Agent2",
            queue,
            logger,
            responses=["Hi Agent1", "I'm good, you?", "See you later"],
        )

        # Run both agents concurrently
        await asyncio.gather(
            agent1.run(max_turns=3, partner_name="Agent2"),
            agent2.run(max_turns=3, partner_name="Agent1"),
        )

        # Verify conversation
        data = await queue.load()
        messages = data["messages"]

        assert len(messages) >= 3  # At least 3 messages
        assert data["metadata"]["total_turns"] >= 3

        # Verify alternating pattern
        senders = [msg["sender"] for msg in messages]
        assert "Agent1" in senders
        assert "Agent2" in senders

    @pytest.mark.asyncio
    async def test_conversation_with_termination(self, temp_db, logger):
        """Test conversation that terminates mid-way"""
        queue = SQLiteQueue(temp_db, logger)

        agent1 = IntegrationTestAgent(
            "Agent1",
            queue,
            logger,
            responses=["Hello", "[done]"],  # Terminate after 2nd message
        )
        agent2 = IntegrationTestAgent(
            "Agent2",
            queue,
            logger,
            responses=["Hi", "Okay"],
        )

        # Run both agents
        await asyncio.gather(
            agent1.run(max_turns=10, partner_name="Agent2"),
            agent2.run(max_turns=10, partner_name="Agent1"),
        )

        # Verify terminated
        assert await queue.is_terminated()

        data = await queue.load()
        # Should have stopped early
        assert data["metadata"]["total_turns"] < 10

    @pytest.mark.asyncio
    async def test_concurrent_message_adding(self, temp_db, logger):
        """Test concurrent message adding doesn't cause race conditions"""
        queue = SQLiteQueue(temp_db, logger)

        async def add_messages(sender, count):
            for i in range(count):
                await queue.add_message(sender, f"Message {i}", {"tokens": 10})
                await asyncio.sleep(0.001)  # Small delay

        # Add messages concurrently from two senders
        await asyncio.gather(add_messages("Agent1", 20), add_messages("Agent2", 20))

        # Verify all messages were added
        data = await queue.load()
        assert data["metadata"]["total_turns"] == 40
        assert len(data["messages"]) == 40

    @pytest.mark.asyncio
    async def test_context_retrieval(self, temp_db, logger):
        """Test context retrieval with multiple messages"""
        queue = SQLiteQueue(temp_db, logger)

        # Add several messages
        for i in range(15):
            sender = "Agent1" if i % 2 == 0 else "Agent2"
            await queue.add_message(sender, f"Message {i}", {"turn": i})

        # Get context
        context = await queue.get_context(max_messages=10)

        assert len(context) == 10
        # Should get most recent messages
        assert "Message 14" in context[-1]["content"]

    @pytest.mark.asyncio
    async def test_token_accumulation(self, temp_db, logger):
        """Test token counts accumulate correctly"""
        queue = SQLiteQueue(temp_db, logger)

        # Add messages with varying token counts
        await queue.add_message("Agent1", "Message 1", {"tokens": 50})
        await queue.add_message("Agent2", "Message 2", {"tokens": 75})
        await queue.add_message("Agent1", "Message 3", {"tokens": 100})

        data = await queue.load()
        assert data["metadata"]["total_tokens"] == 225

    @pytest.mark.asyncio
    async def test_agent_turn_counting(self, temp_db, logger):
        """Test individual agent turn counting"""
        queue = SQLiteQueue(temp_db, logger)

        # Agent1 sends 3, Agent2 sends 2
        await queue.add_message("Agent1", "M1", {"tokens": 10})
        await queue.add_message("Agent2", "M2", {"tokens": 10})
        await queue.add_message("Agent1", "M3", {"tokens": 10})
        await queue.add_message("Agent1", "M4", {"tokens": 10})
        await queue.add_message("Agent2", "M5", {"tokens": 10})

        data = await queue.load()
        assert data["metadata"]["agent1_turns"] == 3
        assert data["metadata"]["agent2_turns"] == 2
        assert data["metadata"]["total_turns"] == 5


class TestErrorRecovery:
    """Test error recovery scenarios"""

    @pytest.mark.asyncio
    async def test_queue_survives_errors(self, temp_db, logger):
        """Test queue continues working after errors"""
        queue = SQLiteQueue(temp_db, logger)

        # Add a valid message
        await queue.add_message("Agent1", "Valid", {"tokens": 10})

        # Try to add invalid message (empty content)
        with pytest.raises(Exception):
            await queue.add_message("Agent1", "", {"tokens": 10})

        # Queue should still work
        await queue.add_message("Agent2", "Also valid", {"tokens": 10})

        data = await queue.load()
        assert data["metadata"]["total_turns"] == 2

    @pytest.mark.asyncio
    async def test_termination_persistence(self, temp_db, logger):
        """Test termination state persists"""
        queue = SQLiteQueue(temp_db, logger)

        # Add messages and terminate
        await queue.add_message("Agent1", "Message", {"tokens": 10})
        await queue.mark_terminated("test_reason")

        # Verify terminated
        assert await queue.is_terminated()
        reason = await queue.get_termination_reason()
        assert reason == "test_reason"

        # Create new queue instance with same db
        queue2 = SQLiteQueue(temp_db, logger)

        # Termination should persist
        assert await queue2.is_terminated()
        assert await queue2.get_termination_reason() == "test_reason"


class TestFactoryAndAgentCreation:
    """Test agent factory and creation"""

    @pytest.mark.asyncio
    async def test_create_queue_factory_sqlite(self, temp_db, logger):
        """Test queue factory creates SQLite queue"""
        queue = create_queue(str(temp_db), logger, use_redis=False)
        assert isinstance(queue, SQLiteQueue)

        # Test it works
        await queue.add_message("Test", "Message", {})
        data = await queue.load()
        assert len(data["messages"]) == 1

    @pytest.mark.asyncio
    async def test_create_chatgpt_agent(self, temp_db, logger):
        """Test ChatGPT agent creation"""
        queue = SQLiteQueue(temp_db, logger)

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            with patch("agents.chatgpt.OpenAI"):
                agent = create_agent(
                    agent_type="chatgpt",
                    queue=queue,
                    logger=logger,
                    api_key="test-key",
                )

                assert isinstance(agent, ChatGPTAgent)
                assert agent.PROVIDER_NAME == "ChatGPT"

    @pytest.mark.asyncio
    async def test_create_claude_agent(self, temp_db, logger):
        """Test Claude agent creation"""
        queue = SQLiteQueue(temp_db, logger)

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("agents.claude.anthropic.Anthropic"):
                agent = create_agent(
                    agent_type="claude",
                    queue=queue,
                    logger=logger,
                    api_key="test-key",
                )

                assert isinstance(agent, ClaudeAgent)
                assert agent.PROVIDER_NAME == "Claude"

    @pytest.mark.asyncio
    async def test_create_agent_with_model_override(self, temp_db, logger):
        """Test agent creation with model override"""
        queue = SQLiteQueue(temp_db, logger)

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            with patch("agents.chatgpt.OpenAI"):
                agent = create_agent(
                    agent_type="chatgpt",
                    queue=queue,
                    logger=logger,
                    model="gpt-4o-mini",
                    api_key="test-key",
                )

                assert agent.model == "gpt-4o-mini"


class TestHealthChecks:
    """Test health check functionality"""

    @pytest.mark.asyncio
    async def test_sqlite_health_check_healthy(self, temp_db, logger):
        """Test SQLite queue health check when healthy"""
        queue = SQLiteQueue(temp_db, logger)

        health = await queue.health_check()

        assert health["healthy"] is True
        assert health["checks"]["database"] == "ok"
        assert health["checks"]["lock"] == "ok"
        assert "timestamp" in health

    @pytest.mark.asyncio
    async def test_health_check_with_invalid_db(self, logger):
        """Test health check with invalid database"""
        # Create queue with invalid path
        invalid_path = Path("/invalid/path/db.db")

        # This will fail during init, so we can't test health check
        # But we can test validation
        with pytest.raises(Exception):
            SQLiteQueue(invalid_path, logger)


class TestMessageValidation:
    """Test message validation"""

    @pytest.mark.asyncio
    async def test_empty_content_rejected(self, temp_db, logger):
        """Test empty content is rejected"""
        queue = SQLiteQueue(temp_db, logger)

        with pytest.raises(Exception):
            await queue.add_message("Agent1", "", {})

        with pytest.raises(Exception):
            await queue.add_message("Agent1", "   ", {})

    @pytest.mark.asyncio
    async def test_sender_normalization(self, temp_db, logger):
        """Test sender names are normalized"""
        queue = SQLiteQueue(temp_db, logger)

        # Test various formats
        await queue.add_message("claude", "Message 1", {})
        await queue.add_message("CLAUDE", "Message 2", {})
        await queue.add_message("Claude", "Message 3", {})

        data = await queue.load()
        messages = data["messages"]

        # All should be normalized to "Claude"
        assert all(msg["sender"] == "Claude" for msg in messages)

    @pytest.mark.asyncio
    async def test_message_too_long_rejected(self, temp_db, logger):
        """Test messages exceeding max length are rejected"""
        queue = SQLiteQueue(temp_db, logger)

        # Create message longer than MAX_MESSAGE_LENGTH
        long_message = "x" * (config.MAX_MESSAGE_LENGTH + 1)

        with pytest.raises(Exception):
            await queue.add_message("Agent1", long_message, {})


class TestConversationMetadata:
    """Test conversation metadata management"""

    @pytest.mark.asyncio
    async def test_initial_metadata(self, temp_db, logger):
        """Test initial metadata is set correctly"""
        queue = SQLiteQueue(temp_db, logger)

        data = await queue.load()
        meta = data["metadata"]

        assert "conversation_id" in meta
        assert "started_at" in meta
        assert meta["total_turns"] == 0
        assert meta["version"] == "5.0"

    @pytest.mark.asyncio
    async def test_metadata_updates(self, temp_db, logger):
        """Test metadata updates as conversation progresses"""
        queue = SQLiteQueue(temp_db, logger)

        # Add messages
        await queue.add_message("Claude", "M1", {"tokens": 50})
        await queue.add_message("ChatGPT", "M2", {"tokens": 75})

        data = await queue.load()
        meta = data["metadata"]

        assert meta["total_turns"] == 2
        assert meta["claude_turns"] == 1
        assert meta["chatgpt_turns"] == 1
        assert meta["total_tokens"] == 125

    @pytest.mark.asyncio
    async def test_termination_metadata(self, temp_db, logger):
        """Test termination adds metadata"""
        queue = SQLiteQueue(temp_db, logger)

        await queue.mark_terminated("test_complete")

        data = await queue.load()
        meta = data["metadata"]

        assert meta["terminated"] == 1
        assert meta["termination_reason"] == "test_complete"
        assert "ended_at" in meta


class TestConcurrentAgents:
    """Test concurrent agent operations"""

    @pytest.mark.asyncio
    async def test_agents_alternate_correctly(self, temp_db, logger):
        """Test agents properly alternate turns"""
        queue = SQLiteQueue(temp_db, logger)

        async def agent1_run():
            for i in range(5):
                while True:
                    last = await queue.get_last_sender()
                    if last is None or last == "Agent2":
                        await queue.add_message("Agent1", f"A1-{i}", {"tokens": 10})
                        break
                    await asyncio.sleep(0.01)

        async def agent2_run():
            for i in range(5):
                while True:
                    last = await queue.get_last_sender()
                    if last == "Agent1":
                        await queue.add_message("Agent2", f"A2-{i}", {"tokens": 10})
                        break
                    await asyncio.sleep(0.01)

        await asyncio.gather(agent1_run(), agent2_run())

        data = await queue.load()
        messages = data["messages"]

        # Should have 10 messages alternating
        assert len(messages) == 10

        # Check alternation (allowing for first message)
        for i in range(1, len(messages)):
            assert messages[i]["sender"] != messages[i - 1]["sender"]


class TestStressScenarios:
    """Test under stress conditions"""

    @pytest.mark.asyncio
    async def test_many_messages(self, temp_db, logger):
        """Test handling many messages"""
        queue = SQLiteQueue(temp_db, logger)

        # Add 100 messages
        for i in range(100):
            sender = f"Agent{i % 3 + 1}"
            await queue.add_message(sender, f"Message {i}", {"tokens": 10})

        data = await queue.load()
        assert data["metadata"]["total_turns"] == 100
        assert len(data["messages"]) == 100

    @pytest.mark.asyncio
    async def test_rapid_termination_checks(self, temp_db, logger):
        """Test rapid termination checking"""
        queue = SQLiteQueue(temp_db, logger)

        # Check termination many times rapidly
        results = await asyncio.gather(*[queue.is_terminated() for _ in range(50)])

        assert all(result is False for result in results)

        # Now terminate and check again
        await queue.mark_terminated("test")

        results = await asyncio.gather(*[queue.is_terminated() for _ in range(50)])

        assert all(result is True for result in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=agents", "--cov=core", "--cov-report=term-missing"])
