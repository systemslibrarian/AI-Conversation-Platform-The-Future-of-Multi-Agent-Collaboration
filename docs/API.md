# 📘 API Reference

**AI Conversation Platform v5.0 - Complete API Documentation**

---

## Table of Contents

1. [Overview](#overview)
2. [Agent API](#agent-api)
3. [Queue API](#queue-api)
4. [Metrics API](#metrics-api)
5. [Configuration API](#configuration-api)
6. [Utility Functions](#utility-functions)
7. [Type Definitions](#type-definitions)
8. [Error Handling](#error-handling)
9. [Examples](#examples)

---

## Overview

This document provides complete API reference for the AI Conversation Platform. All APIs are **async-first** and designed for production use.

### Installation

```python
# Import core modules
from agents import create_agent, BaseAgent, ClaudeAgent, ChatGPTAgent
from core.queue import create_queue, QueueInterface
from core.config import config
from core.metrics import record_call, record_latency
from core.common import setup_logging
```

---

## Agent API

### Factory Function

#### `create_agent()`

Create an agent instance from the registry.

**Signature:**
```python
def create_agent(
    agent_type: str,
    queue: QueueInterface,
    logger: logging.Logger,
    *,
    model: str | None = None,
    topic: str = "general",
    timeout: int = 30,
    api_key: str | None = None,
) -> BaseAgent
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_type` | `str` | Yes | Provider name: `"claude"`, `"chatgpt"`, `"gemini"`, `"grok"`, `"perplexity"` |
| `queue` | `QueueInterface` | Yes | Message queue instance |
| `logger` | `logging.Logger` | Yes | Logger for the agent |
| `model` | `str \| None` | No | Model name (defaults to provider's DEFAULT_MODEL) |
| `topic` | `str` | No | Conversation topic (default: `"general"`) |
| `timeout` | `int` | No | Timeout in minutes (default: `30`) |
| `api_key` | `str \| None` | No | API key (defaults to environment variable) |

**Returns:** `BaseAgent` instance

**Raises:**
- `ValueError`: If agent_type is unknown or API key is missing

**Example:**
```python
import logging
from agents import create_agent
from core.queue import create_queue

logger = logging.getLogger("my_agent")
queue = create_queue("conversation.db", logger, use_redis=False)

agent = create_agent(
    agent_type="claude",
    queue=queue,
    logger=logger,
    model="claude-sonnet-4-5-20250929",
    topic="AI ethics",
    timeout=30
)
```

---

### Agent Registry Functions

#### `list_available_agents()`

Get all registered agent types.

**Signature:**
```python
def list_available_agents() -> List[str]
```

**Returns:** List of agent type names

**Example:**
```python
from agents import list_available_agents

agents = list_available_agents()
print(agents)  # ['chatgpt', 'claude', 'gemini', 'grok', 'perplexity']
```

#### `detect_configured_agents()`

Get agents with API keys present in environment.

**Signature:**
```python
def detect_configured_agents() -> List[str]
```

**Returns:** List of configured agent type names

**Example:**
```python
from agents import detect_configured_agents

configured = detect_configured_agents()
print(configured)  # ['claude', 'chatgpt'] (if only these have API keys)
```

#### `get_agent_info()`

Get registry information for an agent type.

**Signature:**
```python
def get_agent_info(agent_type: str) -> Dict[str, object]
```

**Parameters:**
- `agent_type`: Agent type name (case-insensitive)

**Returns:** Dictionary with agent metadata:
```python
{
    "class": AgentClass,
    "env_key": "ANTHROPIC_API_KEY",
    "default_model": "claude-sonnet-4-5-20250929",
    "models": ["claude-sonnet-4-5-20250929", ...]
}
```

**Raises:**
- `ValueError`: If agent_type is unknown

**Example:**
```python
from agents import get_agent_info

info = get_agent_info("claude")
print(info["default_model"])  # claude-sonnet-4-5-20250929
print(info["env_key"])  # ANTHROPIC_API_KEY
```

---

### BaseAgent Class

Abstract base class for all agents.

#### Constructor

```python
def __init__(
    self,
    api_key: str,
    queue: QueueInterface,
    logger: logging.Logger,
    model: str,
    topic: str = "general",
    timeout_minutes: int = 30,
)
```

#### Instance Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `api_key` | `str` | API key for the provider |
| `queue` | `QueueInterface` | Message queue |
| `logger` | `logging.Logger` | Logger instance |
| `model` | `str` | Model name |
| `topic` | `str` | Conversation topic |
| `timeout_minutes` | `int` | Timeout duration |
| `circuit_breaker` | `CircuitBreaker` | Circuit breaker instance |
| `consecutive_similar` | `int` | Similar response counter |
| `recent_responses` | `List[str]` | Recent response history |

#### Class Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `PROVIDER_NAME` | `str` | Display name (e.g., "Claude") |
| `DEFAULT_MODEL` | `str` | Default model name |

#### Methods

##### `run()`

Main agent loop - runs until termination.

**Signature:**
```python
async def run(self, max_turns: int, partner_name: str) -> None
```

**Parameters:**
- `max_turns`: Maximum conversation turns
- `partner_name`: Partner agent's display name

**Example:**
```python
await agent.run(max_turns=50, partner_name="ChatGPT")
```

##### `should_respond()`

Check if agent should respond this turn.

**Signature:**
```python
async def should_respond(self, partner_name: str) -> bool
```

**Parameters:**
- `partner_name`: Partner agent's display name

**Returns:** `True` if should respond, `False` otherwise

**Example:**
```python
if await agent.should_respond("ChatGPT"):
    response = await agent.generate_response(context, turn)
```

##### `generate_response()`

Generate a response given conversation context.

**Signature:**
```python
async def generate_response(
    self,
    context: List[Dict[str, Any]],
    turn_number: int
) -> str
```

**Parameters:**
- `context`: List of previous messages
- `turn_number`: Current turn number

**Returns:** Generated response text

**Raises:**
- `Exception`: Various API errors

**Example:**
```python
context = await queue.get_context(max_messages=10)
response = await agent.generate_response(context, turn_number=5)
```

##### `_call_api()` (Abstract)

**Must be implemented by subclasses**

Call the provider's API.

**Signature:**
```python
async def _call_api(self, messages: List[Dict]) -> Tuple[str, int]
```

**Parameters:**
- `messages`: List of message dicts with `role` and `content`

**Returns:** Tuple of (response_content, token_count)

**Example Implementation:**
```python
async def _call_api(self, messages: List[Dict]) -> Tuple[str, int]:
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: self.client.messages.create(
            model=self.model,
            messages=messages,
            max_tokens=1024
        )
    )
    return response.content[0].text, response.usage.total_tokens
```

---

### Provider-Specific Agents

#### ClaudeAgent

**Model:** Anthropic Claude

**Default Model:** `claude-sonnet-4-5-20250929`

**Environment Variable:** `ANTHROPIC_API_KEY`

**Example:**
```python
from agents import ClaudeAgent

agent = ClaudeAgent(
    api_key="sk-ant-xxxxx",
    queue=queue,
    logger=logger,
    model="claude-sonnet-4-5-20250929",
    topic="AI safety",
    timeout_minutes=30
)
```

#### ChatGPTAgent

**Provider:** OpenAI

**Default Model:** `gpt-4o`

**Environment Variable:** `OPENAI_API_KEY`

**Example:**
```python
from agents import ChatGPTAgent

agent = ChatGPTAgent(
    api_key="sk-xxxxx",
    queue=queue,
    logger=logger,
    model="gpt-4o",
    topic="Machine learning",
    timeout_minutes=30
)
```

#### GeminiAgent

**Provider:** Google

**Default Model:** `gemini-1.5-pro`

**Environment Variable:** `GOOGLE_API_KEY`

**Example:**
```python
from agents import GeminiAgent

agent = GeminiAgent(
    api_key="xxxxx",
    queue=queue,
    logger=logger,
    model="gemini-1.5-pro",
    topic="Quantum computing",
    timeout_minutes=30
)
```

#### GrokAgent

**Provider:** X.AI

**Default Model:** `grok-beta`

**Environment Variable:** `XAI_API_KEY`

**Example:**
```python
from agents import GrokAgent

agent = GrokAgent(
    api_key="xxxxx",
    queue=queue,
    logger=logger,
    model="grok-beta",
    topic="Space exploration",
    timeout_minutes=30
)
```

#### PerplexityAgent

**Provider:** Perplexity AI

**Default Model:** `llama-3.1-sonar-large-128k-online`

**Environment Variable:** `PERPLEXITY_API_KEY`

**Example:**
```python
from agents import PerplexityAgent

agent = PerplexityAgent(
    api_key="pplx-xxxxx",
    queue=queue,
    logger=logger,
    model="llama-3.1-sonar-large-128k-online",
    topic="Current events",
    timeout_minutes=30
)
```

---

## Queue API

### Factory Function

#### `create_queue()`

Create a queue instance (SQLite or Redis).

**Signature:**
```python
def create_queue(
    path: str,
    logger: logging.Logger,
    use_redis: bool = False
) -> QueueInterface
```

**Parameters:**
- `path`: Database path (SQLite) or Redis URL
- `logger`: Logger instance
- `use_redis`: `True` for Redis, `False` for SQLite

**Returns:** `QueueInterface` implementation

**Example:**
```python
from core.queue import create_queue
import logging

logger = logging.getLogger("queue")

# SQLite
queue = create_queue("conversation.db", logger, use_redis=False)

# Redis
queue = create_queue("redis://localhost:6379/0", logger, use_redis=True)
```

---

### QueueInterface (Abstract)

Interface for message queues.

#### Methods

##### `add_message()`

Add a message to the conversation.

**Signature:**
```python
async def add_message(
    self,
    sender: str,
    content: str,
    metadata: Dict[str, Any]
) -> Dict[str, Any]
```

**Parameters:**
- `sender`: Agent name (e.g., "Claude")
- `content`: Message content
- `metadata`: Additional data (tokens, model, etc.)

**Returns:** Message dictionary with `id` added

**Example:**
```python
message = await queue.add_message(
    sender="Claude",
    content="Hello, world!",
    metadata={"tokens": 10, "model": "claude-sonnet-4-5-20250929"}
)
print(message["id"])  # 1
```

##### `get_context()`

Get recent conversation history.

**Signature:**
```python
async def get_context(self, max_messages: int = 10) -> List[Dict[str, Any]]
```

**Parameters:**
- `max_messages`: Maximum messages to retrieve (default: 10)

**Returns:** List of message dictionaries (most recent first)

**Example:**
```python
context = await queue.get_context(max_messages=5)
for msg in context:
    print(f"{msg['sender']}: {msg['content']}")
```

##### `get_last_sender()`

Get the name of the last message sender.

**Signature:**
```python
async def get_last_sender(self) -> Optional[str]
```

**Returns:** Sender name or `None` if no messages

**Example:**
```python
last_sender = await queue.get_last_sender()
if last_sender == "Claude":
    print("Claude sent the last message")
```

##### `mark_terminated()`

Mark conversation as terminated.

**Signature:**
```python
async def mark_terminated(self, reason: str) -> None
```

**Parameters:**
- `reason`: Termination reason (e.g., "max_turns_reached")

**Example:**
```python
await queue.mark_terminated("max_turns_reached")
```

##### `is_terminated()`

Check if conversation is terminated.

**Signature:**
```python
async def is_terminated(self) -> bool
```

**Returns:** `True` if terminated, `False` otherwise

**Example:**
```python
if await queue.is_terminated():
    print("Conversation has ended")
```

##### `get_termination_reason()`

Get termination reason if terminated.

**Signature:**
```python
async def get_termination_reason(self) -> Optional[str]
```

**Returns:** Reason string or `None`

**Example:**
```python
reason = await queue.get_termination_reason()
print(f"Ended because: {reason}")
```

##### `health_check()`

Check queue health status.

**Signature:**
```python
async def health_check(self) -> Dict[str, Any]
```

**Returns:** Health status dictionary
```python
{
    "healthy": bool,
    "checks": {
        "database": "ok" | "error",
        "lock": "ok" | "error"
    }
}
```

**Example:**
```python
health = await queue.health_check()
if health["healthy"]:
    print("Queue is healthy")
```

---

## Metrics API

### Functions

#### `record_call()`

Record an API call.

**Signature:**
```python
def record_call(provider: str, model: str, status: str = "success") -> None
```

**Parameters:**
- `provider`: Provider name (e.g., "Claude")
- `model`: Model name
- `status`: Call status ("success" or "error")

**Example:**
```python
from core.metrics import record_call

record_call("Claude", "claude-sonnet-4-5-20250929", "success")
```

#### `record_latency()`

Record response latency.

**Signature:**
```python
def record_latency(provider: str, model: str, seconds: float) -> None
```

**Parameters:**
- `provider`: Provider name
- `model`: Model name
- `seconds`: Latency in seconds

**Example:**
```python
from core.metrics import record_latency
import time

start = time.time()
# ... API call ...
latency = time.time() - start

record_latency("ChatGPT", "gpt-4o", latency)
```

#### `record_tokens()`

Record token usage.

**Signature:**
```python
def record_tokens(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int
) -> None
```

**Parameters:**
- `provider`: Provider name
- `model`: Model name
- `input_tokens`: Input token count
- `output_tokens`: Output token count

**Example:**
```python
from core.metrics import record_tokens

record_tokens("Gemini", "gemini-1.5-pro", input_tokens=100, output_tokens=150)
```

#### `record_error()`

Record an error.

**Signature:**
```python
def record_error(provider: str, error_type: str) -> None
```

**Parameters:**
- `provider`: Provider name
- `error_type`: Error type (e.g., "rate_limit", "timeout", "api_error")

**Example:**
```python
from core.metrics import record_error

try:
    response = await api_call()
except RateLimitError:
    record_error("Grok", "rate_limit")
```

#### `increment_conversations()`

Increment active conversation counter.

**Signature:**
```python
def increment_conversations() -> None
```

**Example:**
```python
from core.metrics import increment_conversations

increment_conversations()
# ... run conversation ...
```

#### `decrement_conversations()`

Decrement active conversation counter.

**Signature:**
```python
def decrement_conversations() -> None
```

**Example:**
```python
from core.metrics import decrement_conversations

try:
    # ... run conversation ...
finally:
    decrement_conversations()
```

#### `start_metrics_server()`

Start Prometheus HTTP server.

**Signature:**
```python
def start_metrics_server(port: Optional[int] = None) -> None
```

**Parameters:**
- `port`: HTTP port (default: from `PROMETHEUS_PORT` env or 8000)

**Example:**
```python
from core.metrics import start_metrics_server

start_metrics_server(port=8000)
# Metrics available at http://localhost:8000/metrics
```

---

## Configuration API

### Config Class

Centralized configuration management.

#### Usage

```python
from core.config import config

# Access configuration
max_turns = config.DEFAULT_MAX_TURNS
temperature = config.TEMPERATURE
max_tokens = config.MAX_TOKENS

# Validate configuration
config.validate()
```

#### Configuration Options

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `DEFAULT_MAX_TURNS` | `int` | 50 | Maximum conversation turns |
| `DEFAULT_TIMEOUT_MINUTES` | `int` | 30 | Agent timeout |
| `TEMPERATURE` | `float` | 0.7 | LLM sampling temperature |
| `MAX_TOKENS` | `int` | 1024 | Maximum tokens per response |
| `MAX_CONTEXT_MSGS` | `int` | 10 | Context messages to include |
| `SIMILARITY_THRESHOLD` | `float` | 0.85 | Loop detection threshold |
| `MAX_CONSECUTIVE_SIMILAR` | `int` | 2 | Similar responses before termination |
| `USE_REDIS` | `bool` | False | Use Redis instead of SQLite |
| `REDIS_URL` | `str` | "" | Redis connection URL |
| `PROMETHEUS_PORT` | `int` | 8000 | Metrics server port |
| `ENABLE_LLM_GUARD` | `bool` | True | Enable security scanning |
| `MAX_MESSAGE_LENGTH` | `int` | 100000 | Maximum message length |

#### Model Defaults

| Provider | Default Model |
|----------|---------------|
| Claude | `claude-sonnet-4-5-20250929` |
| ChatGPT | `gpt-4o` |
| Gemini | `gemini-1.5-pro` |
| Grok | `grok-beta` |
| Perplexity | `llama-3.1-sonar-large-128k-online` |

#### Methods

##### `get_api_key()`

Get API key from environment.

**Signature:**
```python
@classmethod
def get_api_key(cls, env_var: str) -> str
```

**Parameters:**
- `env_var`: Environment variable name

**Returns:** API key string

**Raises:**
- `ValueError`: If key is not set

**Example:**
```python
from core.config import config

api_key = config.get_api_key("ANTHROPIC_API_KEY")
```

##### `validate()`

Validate configuration using Pydantic.

**Signature:**
```python
@classmethod
def validate(cls) -> None
```

**Raises:**
- `ValueError`: If configuration is invalid

**Example:**
```python
from core.config import config

config.validate()  # Raises ValueError if invalid
```

---

## Utility Functions

### Logging

#### `setup_logging()`

Setup structured JSON logging.

**Signature:**
```python
def setup_logging(agent_name: str, log_dir: str = "logs") -> logging.Logger
```

**Parameters:**
- `agent_name`: Logger name
- `log_dir`: Log directory path

**Returns:** Configured logger

**Example:**
```python
from core.common import setup_logging

logger = setup_logging("my_agent", "logs")
logger.info("Agent started")
```

#### `log_event()`

Log a structured event.

**Signature:**
```python
def log_event(logger: logging.Logger, event_type: str, data: Dict[str, Any]) -> None
```

**Parameters:**
- `logger`: Logger instance
- `event_type`: Event type name
- `data`: Event data dictionary

**Example:**
```python
from core.common import log_event

log_event(logger, "api_call", {
    "provider": "Claude",
    "model": "claude-sonnet-4-5-20250929",
    "tokens": 150,
    "latency": 1.23
})
```

### Text Processing

#### `simple_similarity()`

Calculate similarity using word n-grams.

**Signature:**
```python
def simple_similarity(text1: str, text2: str) -> float
```

**Parameters:**
- `text1`: First text
- `text2`: Second text

**Returns:** Similarity score (0.0 to 1.0)

**Example:**
```python
from core.common import simple_similarity

score = simple_similarity("Hello world", "Hello there")
print(score)  # 0.5
```

#### `hash_message()`

Generate hash of message content.

**Signature:**
```python
def hash_message(content: str) -> str
```

**Parameters:**
- `content`: Message content

**Returns:** 8-character hash

**Example:**
```python
from core.common import hash_message

hash_val = hash_message("Hello, world!")
print(hash_val)  # e.g., "a3b2c1d0"
```

### Utilities

#### `add_jitter()`

Add random jitter for backoff.

**Signature:**
```python
def add_jitter(value: float, jitter_range: float = 0.2) -> float
```

**Parameters:**
- `value`: Base value
- `jitter_range`: Jitter range (default: 0.2 = ±20%)

**Returns:** Value with jitter applied

**Example:**
```python
from core.common import add_jitter

backoff = 2.0
backoff_with_jitter = add_jitter(backoff)
print(backoff_with_jitter)  # e.g., 2.15
```

#### `mask_api_key()`

Mask API keys in text.

**Signature:**
```python
def mask_api_key(text: str) -> str
```

**Parameters:**
- `text`: Text containing API keys

**Returns:** Text with keys masked

**Example:**
```python
from core.common import mask_api_key

text = "API key: sk-ant-abc123xyz"
masked = mask_api_key(text)
print(masked)  # "API key: [ANTHROPIC_KEY]"
```

---

## Type Definitions

### Message Dictionary

```python
MessageDict = {
    "id": int,  # Message ID
    "sender": str,  # Agent name
    "content": str,  # Message content
    "timestamp": str,  # ISO format
    "metadata": {  # Optional metadata
        "tokens": int,
        "model": str,
        "turn": int,
        "response_time": float
    }
}
```

### Context List

```python
ContextList = List[MessageDict]
```

### Health Status

```python
HealthStatus = {
    "healthy": bool,
    "checks": {
        "database": str,  # "ok" or "error"
        "lock": str  # "ok" or "error"
    }
}
```

---

## Error Handling

### Exception Types

```python
# Configuration errors
ValueError  # Invalid configuration or parameters

# API errors
Exception  # Generic API errors (provider-specific)

# Queue errors
sqlite3.OperationalError  # SQLite errors
redis.RedisError  # Redis errors
```

### Error Handling Pattern

```python
from core.metrics import record_error

try:
    response = await agent.generate_response(context, turn)
except RateLimitError as e:
    record_error(agent.PROVIDER_NAME, "rate_limit")
    logger.error(f"Rate limit exceeded: {e}")
    await asyncio.sleep(backoff)
except APIError as e:
    record_error(agent.PROVIDER_NAME, "api_error")
    logger.error(f"API error: {e}")
    agent.circuit_breaker.record_failure()
except Exception as e:
    record_error(agent.PROVIDER_NAME, "unknown")
    logger.error(f"Unexpected error: {e}")
    raise
```

---

## Examples

### Complete Conversation Example

```python
import asyncio
import logging
from agents import create_agent
from core.queue import create_queue
from core.metrics import start_metrics_server, increment_conversations, decrement_conversations
from core.common import setup_logging
from core.config import config

async def run_conversation():
    # Setup
    logger = setup_logging("conversation", "logs")
    queue = create_queue("conversation.db", logger, use_redis=False)
    
    # Start metrics
    start_metrics_server(8000)
    increment_conversations()
    
    try:
        # Create agents
        agent1 = create_agent(
            "claude",
            queue=queue,
            logger=logger,
            model="claude-sonnet-4-5-20250929",
            topic="AI ethics",
            timeout=30
        )
        
        agent2 = create_agent(
            "chatgpt",
            queue=queue,
            logger=logger,
            model="gpt-4o",
            topic="AI ethics",
            timeout=30
        )
        
        # Run conversation
        await asyncio.gather(
            agent1.run(max_turns=10, partner_name="ChatGPT"),
            agent2.run(max_turns=10, partner_name="Claude")
        )
        
        print("Conversation completed!")
        
    finally:
        decrement_conversations()

if __name__ == "__main__":
    asyncio.run(run_conversation())
```

### Custom Agent Example

```python
from agents.base import BaseAgent
from typing import List, Dict, Tuple
import asyncio

class CustomAgent(BaseAgent):
    """Custom AI agent implementation"""
    
    PROVIDER_NAME = "CustomAI"
    DEFAULT_MODEL = "custom-model-v1"
    
    def __init__(self, api_key: str, *args, **kwargs):
        kwargs["api_key"] = api_key
        super().__init__(*args, **kwargs)
        
        # Initialize your custom client
        self.client = YourCustomClient(api_key=api_key)
    
    async def _call_api(self, messages: List[Dict]) -> Tuple[str, int]:
        """Implement your custom API call"""
        loop = asyncio.get_event_loop()
        
        # Run blocking call in executor
        response = await loop.run_in_executor(
            None,
            lambda: self.client.generate(
                messages=messages,
                model=self.model,
                max_tokens=1024
            )
        )
        
        return response.text, response.token_count

# Register in agent registry
from agents import _AGENT_REGISTRY
_AGENT_REGISTRY["custom"] = {
    "class": CustomAgent,
    "env_key": "CUSTOM_API_KEY",
    "default_model": "custom-model-v1",
    "models": ["custom-model-v1", "custom-model-v2"]
}

# Use it
agent = create_agent("custom", queue, logger)
```

### Queue Inspection Example

```python
async def inspect_conversation(db_path: str):
    """Inspect conversation state"""
    logger = logging.getLogger("inspector")
    queue = create_queue(db_path, logger, use_redis=False)
    
    # Get metadata
    data = await queue.load()
    metadata = data["metadata"]
    
    print(f"Total turns: {metadata.get('total_turns', 0)}")
    print(f"Total tokens: {metadata.get('total_tokens', 0)}")
    print(f"Terminated: {metadata.get('terminated', False)}")
    
    # Get recent messages
    context = await queue.get_context(max_messages=5)
    
    print("\nRecent messages:")
    for msg in context:
        print(f"{msg['sender']}: {msg['content'][:100]}...")
    
    # Check health
    health = await queue.health_check()
    print(f"\nQueue health: {health['healthy']}")

asyncio.run(inspect_conversation("conversation.db"))
```

---

**Document Version**: 5.0.0  
**Last Updated**: 2025-11-03  
**Maintained by**: Paul Clark (@systemslibrarian)

---

[⬆ Back to Documentation Index](README.md)
