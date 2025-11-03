"""Comprehensive agent tests for AI Conversation Platform v5.0"""

import pytest
import logging
from unittest.mock import AsyncMock, MagicMock, patch
import importlib.util

from agents import create_agent, ClaudeAgent, ChatGPTAgent
from agents.base import CircuitBreaker


@pytest.fixture
def mock_queue():
    """Create a mock queue for testing"""
    queue = AsyncMock()
    queue.get_context.return_value = []
    queue.get_last_sender.return_value = None
    queue.is_terminated.return_value = False
    queue.add_message.return_value = {"id": 1, "sender": "Test", "content": "Test message"}
    return queue


@pytest.fixture
def logger():
    """Create test logger"""
    return logging.getLogger("test")


class TestCircuitBreaker:
    """Test circuit breaker functionality"""
    
    def test_circuit_breaker_initial_state(self):
        """Test circuit breaker starts in CLOSED state"""
        cb = CircuitBreaker()
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0
        assert not cb.is_open()
    
    def test_circuit_breaker_opens_after_failures(self):
        """Test circuit breaker opens after threshold failures"""
        cb = CircuitBreaker(failure_threshold=3)
        
        for _ in range(3):
            cb.record_failure()
        
        assert cb.state == "OPEN"
        assert cb.is_open()
    
    def test_circuit_breaker_half_open_transition(self):
        """Test circuit breaker transitions to HALF_OPEN after timeout"""
        cb = CircuitBreaker(failure_threshold=2, timeout_seconds=0)
        
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "OPEN"
        
        # After timeout, should transition to HALF_OPEN when queried
        assert not cb.is_open()  # This triggers the transition logic
    
    def test_circuit_breaker_success_resets(self):
        """Test successful call resets circuit breaker"""
        cb = CircuitBreaker()
        
        cb.record_failure()
        cb.record_failure()
        assert cb.failure_count == 2
        
        cb.record_success()
        assert cb.failure_count == 0


class TestChatGPTAgent:
    """Test ChatGPT agent"""
    
    @pytest.mark.asyncio
    async def test_chatgpt_initialization(self, mock_queue, logger):
        """Test ChatGPT agent initialization"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            agent = ChatGPTAgent(
                api_key='test-key',
                queue=mock_queue,
                logger=logger,
                model='gpt-4o',
                topic='test',
                timeout_minutes=30
            )
            
            assert agent.PROVIDER_NAME == "ChatGPT"
            assert agent.model == "gpt-4o"
            assert agent.topic == "test"
    
    @pytest.mark.asyncio
    async def test_chatgpt_api_call(self, mock_queue, logger):
        """Test ChatGPT API call"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            agent = ChatGPTAgent(
                api_key='test-key',
                queue=mock_queue,
                logger=logger,
                model='gpt-4o',
                topic='test',
                timeout_minutes=30
            )
            
            # Mock the API response
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Hello, world!"
            mock_response.usage.total_tokens = 20
            
            with patch.object(agent.client.chat.completions, 'create', return_value=mock_response):
                content, tokens = await agent._call_api([{"role": "user", "content": "Hi"}])
                
                assert content == "Hello, world!"
                assert tokens == 20


class TestClaudeAgent:
    """Test Claude agent"""
    
    @pytest.mark.asyncio
    async def test_claude_initialization(self, mock_queue, logger):
        """Test Claude agent initialization"""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            agent = ClaudeAgent(
                api_key='test-key',
                queue=mock_queue,
                logger=logger,
                model='claude-sonnet-4-5-20250929',
                topic='test',
                timeout_minutes=30
            )
            
            assert agent.PROVIDER_NAME == "Claude"
            assert agent.model == 'claude-sonnet-4-5-20250929'
    
    @pytest.mark.asyncio
    async def test_claude_api_call(self, mock_queue, logger):
        """Test Claude API call"""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            agent = ClaudeAgent(
                api_key='test-key',
                queue=mock_queue,
                logger=logger,
                model='claude-sonnet-4-5-20250929',
                topic='test',
                timeout_minutes=30
            )
            
            # Mock the API response
            mock_response = MagicMock()
            mock_response.content = [MagicMock()]
            mock_response.content[0].text = "Hello from Claude!"
            mock_response.usage.input_tokens = 10
            mock_response.usage.output_tokens = 15
            
            with patch.object(agent.client.messages, 'create', return_value=mock_response):
                content, tokens = await agent._call_api([{"role": "user", "content": "Hi"}])
                
                assert content == "Hello from Claude!"
                assert tokens == 25


class TestAgentFactory:
    """Test agent factory function"""
    
    def test_create_chatgpt_agent(self, mock_queue, logger):
        """Test creating ChatGPT agent via factory"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            agent = create_agent(
                agent_type='chatgpt',
                queue=mock_queue,
                logger=logger,
                api_key='test-key'
            )
            
            assert isinstance(agent, ChatGPTAgent)
    
    def test_create_claude_agent(self, mock_queue, logger):
        """Test creating Claude agent via factory"""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            agent = create_agent(
                agent_type='claude',
                queue=mock_queue,
                logger=logger,
                api_key='test-key'
            )
            
            assert isinstance(agent, ClaudeAgent)
    
    def test_create_invalid_agent(self, mock_queue, logger):
        """Test creating invalid agent type"""
        with pytest.raises(ValueError, match="Unknown agent type"):
            create_agent(
                agent_type='invalid',
                queue=mock_queue,
                logger=logger
            )


class TestAgentBehavior:
    """Test agent behavior and logic"""
    
    @pytest.mark.asyncio
    async def test_check_termination_signals(self, mock_queue, logger):
        """Test termination signal detection"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            agent = ChatGPTAgent(
                api_key='test-key',
                queue=mock_queue,
                logger=logger,
                model='gpt-4o',
                topic='test',
                timeout_minutes=30
            )
            
            # Test termination signal detection
            result = agent._check_termination_signals("I can't continue this conversation")
            assert result is not None
            assert "sentinel_phrase" in result
            
            # Test normal message
            result = agent._check_termination_signals("This is a normal message")
            assert result is None
    
    @pytest.mark.asyncio
    async def test_similarity_detection(self, mock_queue, logger):
        """Test similarity detection"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            agent = ChatGPTAgent(
                api_key='test-key',
                queue=mock_queue,
                logger=logger,
                model='gpt-4o',
                topic='test',
                timeout_minutes=30
            )
            
            # Add a response
            agent.recent_responses.append("This is a test message")
            
            # Test high similarity (assert return value directly)
            assert agent._check_similarity("This is a test message") is True
            assert agent.consecutive_similar > 0
            
            # Test low similarity
            assert agent._check_similarity("Completely different content here") is False
            assert agent.consecutive_similar == 0
    
    @pytest.mark.asyncio
    async def test_should_respond(self, mock_queue, logger):
        """Test should_respond logic"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            agent = ChatGPTAgent(
                api_key='test-key',
                queue=mock_queue,
                logger=logger,
                model='gpt-4o',
                topic='test',
                timeout_minutes=30
            )
            
            # Test when no last sender (should respond)
            mock_queue.get_last_sender.return_value = None
            should = await agent.should_respond("OtherAgent")
            assert should is True
            
            # Test when partner sent last message (should respond)
            mock_queue.get_last_sender.return_value = "OtherAgent"
            should = await agent.should_respond("OtherAgent")
            assert should is True
            
            # Test when this agent sent last message (should not respond)
            mock_queue.get_last_sender.return_value = "ChatGPT"
            should = await agent.should_respond("OtherAgent")
            assert should is False


class TestAgentSecurity:
    """Test agent security features"""
    
    @pytest.mark.asyncio
    async def test_llm_guard_integration(self, mock_queue, logger):
        """Test LLM Guard integration (if available)"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key', 'ENABLE_LLM_GUARD': 'true'}):
            # Use importlib.util.find_spec to check presence without importing unused names
            if importlib.util.find_spec("llm_guard.input_scanners") is None:
                pytest.skip("llm-guard not installed")
            
            agent = ChatGPTAgent(
                api_key='test-key',
                queue=mock_queue,
                logger=logger,
                model='gpt-4o',
                topic='test',
                timeout_minutes=30
            )
            
            # If llm-guard is available and the agent has scanning enabled, exercise the scan
            if getattr(agent, "llm_guard_enabled", False):
                scan_result = agent._scan_input("Normal text")
                # _scan_input may return tuple (text, bool) or bool depending on implementation; handle both.
                if isinstance(scan_result, tuple):
                    _, valid_flag = scan_result
                    assert valid_flag is True
                else:
                    assert scan_result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=agents"])
