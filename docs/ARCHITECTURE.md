# 🏗️ System Architecture

**AI Conversation Platform v5.0 - Technical Design Document**

---

## Table of Contents

1. [Overview](#overview)
2. [High-Level Architecture](#high-level-architecture)
3. [Component Design](#component-design)
4. [Data Flow](#data-flow)
5. [Concurrency Model](#concurrency-model)
6. [Storage Architecture](#storage-architecture)
7. [Observability Design](#observability-design)
8. [Security Architecture](#security-architecture)
9. [Design Patterns](#design-patterns)
10. [Performance Characteristics](#performance-characteristics)
11. [Scalability Considerations](#scalability-considerations)
12. [Future Enhancements](#future-enhancements)

---

## Overview

The AI Conversation Platform is an **async-first, event-driven system** designed to facilitate autonomous conversations between multiple AI agents. The architecture emphasizes:

- **Reliability**: Circuit breakers, retry logic, graceful degradation
- **Observability**: Comprehensive metrics, tracing, and logging
- **Security**: Input validation, output sanitization, credential management
- **Scalability**: Horizontal scaling via Redis, stateless agents
- **Maintainability**: Clean separation of concerns, dependency injection

### Key Architectural Principles

1. **Async Everything**: All I/O operations are non-blocking
2. **Fail Fast**: Circuit breakers prevent cascading failures
3. **Idempotency**: Operations can be safely retried
4. **Observability First**: Metrics and logs are first-class citizens
5. **Pluggable Components**: Easy to swap implementations

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Presentation Layer                        │
│  ┌──────────────────────┐       ┌─────────────────────────┐    │
│  │   CLI Interface      │       │   Web Interface         │    │
│  │  (Click/Argparse)    │       │   (Streamlit)           │    │
│  │  - Interactive Mode  │       │  - Real-time Updates    │    │
│  │  - Non-interactive   │       │  - Search & Filter      │    │
│  └──────────┬───────────┘       └───────────┬─────────────┘    │
└─────────────┼─────────────────────────────────┼─────────────────┘
              │                                 │
              └────────────┬────────────────────┘
                           │
┌──────────────────────────▼────────────────────────────────────┐
│                   Application Layer                            │
│  ┌───────────────────────────────────────────────────────┐   │
│  │           Conversation Manager                         │   │
│  │  - Async orchestration (asyncio.gather)               │   │
│  │  - Turn management (deterministic first speaker)      │   │
│  │  - Termination detection (signals, max turns)         │   │
│  │  - Error handling & recovery                          │   │
│  └───────────────────────────────────────────────────────┘   │
└─────────────┬──────────────────────────────┬──────────────────┘
              │                              │
┌─────────────▼──────────┐      ┌───────────▼─────────────┐
│      Agent System      │      │   Queue System          │
│  ┌──────────────────┐  │      │  ┌──────────────────┐  │
│  │  Base Agent      │  │      │  │ Queue Interface  │  │
│  │  - Circuit Breaker│ │      │  │ (Abstract)       │  │
│  │  - Rate Limiting  │ │      │  └────┬────────┬────┘  │
│  │  - Similarity Det │ │      │       │        │        │
│  │  - Metrics        │ │      │  ┌────▼────┐ ┌▼─────┐ │
│  └────────┬─────────┘  │      │  │ SQLite  │ │Redis │ │
│           │            │      │  │ Queue   │ │Queue │ │
│  ┌────────▼─────────┐  │      │  └─────────┘ └──────┘ │
│  │ Provider Agents  │  │      └─────────────────────────┘
│  │ - Claude         │  │
│  │ - ChatGPT        │  │
│  │ - Gemini         │  │
│  │ - Grok           │  │
│  │ - Perplexity     │  │
│  └──────────────────┘  │
└────────────┬────────────┘
             │
┌────────────▼──────────────────────────────────────────────┐
│                   Infrastructure Layer                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │Prometheus│  │ Grafana  │  │OpenTelem │  │  Logging │ │
│  │(Metrics) │  │(Dashbrd) │  │(Tracing) │  │  (JSON)  │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │
└───────────────────────────────────────────────────────────┘
```

---

## Component Design

### 1. Agent System

#### Base Agent (`agents/base.py`)

**Responsibilities:**
- Conversation lifecycle management
- Circuit breaker pattern implementation
- Rate limiting with exponential backoff
- Similarity detection for loop prevention
- Metrics collection and reporting

**Key Methods:**
```python
class BaseAgent:
    async def run(max_turns: int, partner_name: str) -> None
    async def should_respond(partner_name: str) -> bool
    async def generate_response(context: List[Dict], turn: int) -> str
    async def _call_api(messages: List[Dict]) -> Tuple[str, int]
    def _check_similarity(response: str) -> bool
    def _check_termination_signals(response: str) -> Optional[Dict]
```

**State Machine:**
```
┌─────────┐
│  IDLE   │
└────┬────┘
     │ run()
     ▼
┌─────────────┐    should_respond() = False
│  WAITING    │◄──────────────────────────────┐
└────┬────────┘                               │
     │ should_respond() = True                │
     ▼                                        │
┌─────────────┐                               │
│ GENERATING  │───────────────────────────────┤
└────┬────────┘  Circuit breaker OPEN         │
     │                                        │
     │ _call_api()                           │
     ▼                                        │
┌─────────────┐                               │
│ RESPONDING  │───────────────────────────────┤
└────┬────────┘  Similarity detected          │
     │                                        │
     │ Add to queue                          │
     ▼                                        │
┌─────────────┐                               │
│  WAITING    │───────────────────────────────┘
└─────────────┘
```

#### Provider Agents

Each provider agent extends `BaseAgent` and implements:

```python
async def _call_api(self, messages: List[Dict]) -> Tuple[str, int]:
    """Provider-specific API call implementation"""
    # 1. Build API request
    # 2. Run in executor (non-blocking)
    # 3. Parse response
    # 4. Return (content, tokens)
```

**Example: Claude Agent**
```python
class ClaudeAgent(BaseAgent):
    PROVIDER_NAME = "Claude"
    DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
    
    def __init__(self, api_key: str, *args, **kwargs):
        self.client = anthropic.Anthropic(api_key=api_key)
        super().__init__(*args, **kwargs)
    
    async def _call_api(self, messages: List[Dict]) -> Tuple[str, int]:
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.messages.create(...)
        )
        return response.content[0].text, response.usage.total_tokens
```

### 2. Circuit Breaker Pattern

**State Diagram:**
```
                  failure_count < threshold
        ┌───────────────────────────────────┐
        │                                   │
        │                                   ▼
   ┌────┴────┐                         ┌──────┐
   │  OPEN   │◄────failure_threshold───│CLOSED│
   └────┬────┘                         └──┬───┘
        │                                 │
        │ timeout elapsed                 │ success
        │                                 │
        ▼                                 │
   ┌─────────┐                            │
   │HALF_OPEN│────────success─────────────┘
   └────┬────┘
        │
        │ failure
        │
        └──────────────►OPEN
```

**Implementation:**
```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout_seconds=60):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def is_open(self) -> bool:
        if self.state == "CLOSED":
            return False
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout_seconds:
                self.state = "HALF_OPEN"
                return False
            return True
        return False
    
    def record_success(self):
        self.failure_count = 0
        self.state = "CLOSED"
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
```

### 3. Queue System

**Architecture:**
```
┌────────────────────────────────────────────┐
│         QueueInterface (Abstract)          │
│  + add_message(sender, content, metadata) │
│  + get_context(max_messages)              │
│  + get_last_sender()                      │
│  + mark_terminated(reason)                │
│  + is_terminated()                        │
│  + health_check()                         │
└────────────────┬───────────────────────────┘
                 │
         ┌───────┴────────┐
         │                │
    ┌────▼─────┐    ┌────▼─────┐
    │  SQLite  │    │  Redis   │
    │  Queue   │    │  Queue   │
    └──────────┘    └──────────┘
```

**SQLite Queue:**
```python
class SQLiteQueue(QueueInterface):
    def __init__(self, db_path: Path, logger: logging.Logger):
        self.db_path = db_path
        self.logger = logger
        self.lock = FileLock(f"{db_path}.lock")
        self._init_db()
    
    async def add_message(self, sender: str, content: str, 
                         metadata: Dict) -> Dict:
        async with self.lock:
            # Atomic write with file locking
            conn = sqlite3.connect(self.db_path)
            # ... insert logic
            conn.commit()
            conn.close()
```

**Redis Queue:**
```python
class RedisQueue(QueueInterface):
    def __init__(self, redis_url: str, logger: logging.Logger):
        self.redis = redis.from_url(redis_url)
        self.logger = logger
    
    async def add_message(self, sender: str, content: str,
                         metadata: Dict) -> Dict:
        # Atomic operation using Redis transactions
        pipe = self.redis.pipeline()
        pipe.rpush("messages", json.dumps(msg))
        pipe.hincrby("metadata", "total_turns", 1)
        pipe.execute()
```

---

## Data Flow

### 1. Conversation Initialization

```
┌──────────────────────────────────────────────────────────┐
│  1. User runs: aic-start --agent1 claude --agent2 gpt  │
└───────────────────────┬──────────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────────┐
│  2. ConversationStarter parses arguments                 │
│     - Validates agent types                              │
│     - Checks API keys                                    │
│     - Creates configuration                              │
└───────────────────────┬──────────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────────┐
│  3. Create queue (SQLite or Redis)                       │
│     - Initialize database/connection                     │
│     - Set up schema                                      │
│     - Seed initial message (deterministic first speaker) │
└───────────────────────┬──────────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────────┐
│  4. Create agent instances                               │
│     - Agent 1 (e.g., Claude)                            │
│     - Agent 2 (e.g., ChatGPT)                           │
│     - Each with circuit breaker, metrics, logger        │
└───────────────────────┬──────────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────────┐
│  5. Launch async tasks with asyncio.gather()            │
│     - Both agents run concurrently                      │
│     - Share queue for communication                     │
└───────────────────────┬──────────────────────────────────┘
                        │
                        ▼
                  Conversation Loop
```

### 2. Message Exchange Loop

```
Agent 1 (Claude)                    Queue                    Agent 2 (ChatGPT)
     │                               │                               │
     │ 1. Check should_respond()     │                               │
     ├──────────────────────────────►│                               │
     │ get_last_sender()             │                               │
     │◄──────────────────────────────┤                               │
     │                               │                               │
     │ 2. Get context                │                               │
     ├──────────────────────────────►│                               │
     │◄──────────────────────────────┤                               │
     │ get_context(max_messages=10)  │                               │
     │                               │                               │
     │ 3. Generate response          │                               │
     │ (call Claude API)             │                               │
     │                               │                               │
     │ 4. Check similarity           │                               │
     │ (loop detection)              │                               │
     │                               │                               │
     │ 5. Add message to queue       │                               │
     ├──────────────────────────────►│                               │
     │                               │                               │
     │                               │ 6. Check should_respond()     │
     │                               │◄──────────────────────────────┤
     │                               │                               │
     │                               │ 7. Get context                │
     │                               │◄──────────────────────────────┤
     │                               ├──────────────────────────────►│
     │                               │                               │
     │                               │ 8. Generate response          │
     │                               │ (call OpenAI API)             │
     │                               │                               │
     │                               │ 9. Add message to queue       │
     │                               │◄──────────────────────────────┤
     │                               │                               │
     │ 10. Repeat until terminated   │                               │
     │                               │                               │
```

### 3. Termination Flow

```
Agent detects termination condition
    │
    ├─► Max turns reached
    ├─► Termination phrase detected
    ├─► Circuit breaker opened
    ├─► Similarity threshold exceeded
    └─► User interruption (Ctrl+C)
    │
    ▼
Mark queue as terminated
queue.mark_terminated(reason)
    │
    ▼
Other agent checks termination
await queue.is_terminated()
    │
    ▼
Both agents exit gracefully
    │
    ▼
Metrics finalized
decrement_conversations()
    │
    ▼
Conversation stored in DB
```

---

## Concurrency Model

### Async Architecture

The platform uses Python's `asyncio` for concurrency:

**Key Concepts:**
1. **Event Loop**: Single-threaded async event loop
2. **Coroutines**: `async def` functions
3. **Tasks**: Concurrent execution with `asyncio.gather()`
4. **Executors**: Blocking I/O runs in thread pool

**Pattern:**
```python
async def run_conversation():
    # Both agents run concurrently
    await asyncio.gather(
        agent1.run(max_turns, "Agent2"),
        agent2.run(max_turns, "Agent1")
    )
```

### Non-Blocking API Calls

All AI provider API calls are non-blocking:

```python
async def _call_api(self, messages: List[Dict]) -> Tuple[str, int]:
    loop = asyncio.get_running_loop()
    
    # Run blocking SDK call in thread pool executor
    response = await loop.run_in_executor(
        None,  # Default ThreadPoolExecutor
        lambda: self.client.messages.create(...)
    )
    
    return parse_response(response)
```

**Benefits:**
- No blocking of event loop
- True concurrent API calls
- Better resource utilization
- Responsive to cancellation

### Race Condition Prevention

**Problem**: Both agents might try to respond simultaneously

**Solution**: Turn management with queue locking

```python
async def should_respond(self, partner_name: str) -> bool:
    # Check last sender (atomic operation)
    last_sender = await self.queue.get_last_sender()
    
    # Only respond if partner sent last message
    return last_sender != self.PROVIDER_NAME
```

**SQLite**: File locking with `FileLock`
```python
async def add_message(self, ...):
    async with self.lock:
        # Atomic write - only one agent at a time
        conn.execute(...)
        conn.commit()
```

**Redis**: Built-in atomic operations
```python
async def add_message(self, ...):
    # Pipeline ensures atomicity
    pipe = self.redis.pipeline()
    pipe.rpush("messages", msg)
    pipe.execute()
```

---

## Storage Architecture

### Database Schema (SQLite)

```sql
-- Messages table
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    metadata TEXT  -- JSON blob
);

-- Metadata table (key-value store)
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT  -- JSON or scalar
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_sender ON messages(sender);
CREATE INDEX IF NOT EXISTS idx_timestamp ON messages(timestamp);
```

**Example Data:**

Messages:
| id | sender | content | timestamp | metadata |
|----|--------|---------|-----------|----------|
| 1 | Claude | Hello! | 2025-11-03T10:00:00 | {"tokens": 10, "model": "claude-sonnet-4-5-20250929"} |
| 2 | ChatGPT | Hi there! | 2025-11-03T10:00:05 | {"tokens": 8, "model": "gpt-4o"} |

Metadata:
| key | value |
|-----|-------|
| total_turns | 2 |
| claude_turns | 1 |
| chatgpt_turns | 1 |
| total_tokens | 18 |
| terminated | 0 |

### Redis Data Structure

```
# Messages (list)
messages:0 → {"id": 1, "sender": "Claude", "content": "Hello!", ...}
messages:1 → {"id": 2, "sender": "ChatGPT", "content": "Hi!", ...}

# Metadata (hash)
metadata:total_turns → 2
metadata:claude_turns → 1
metadata:chatgpt_turns → 1
metadata:total_tokens → 18
metadata:terminated → 0
metadata:termination_reason → null

# Conversation lock (for distributed coordination)
conversation:lock → timestamp
```

---

## Observability Design

### Metrics Collection

**Architecture:**
```
Agent → record_call() → Prometheus Counter
     → record_latency() → Prometheus Histogram
     → record_tokens() → Prometheus Counter
     → record_error() → Prometheus Counter
```

**Metrics Definition:**
```python
API_CALLS = Counter(
    "ai_api_calls_total",
    "Total API calls made",
    ["provider", "model", "status"]
)

RESPONSE_LATENCY = Histogram(
    "ai_response_seconds",
    "Response latency in seconds",
    ["provider", "model"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

TOKEN_USAGE = Counter(
    "ai_tokens_total",
    "Total tokens used",
    ["provider", "model", "type"]  # type = input/output
)
```

### Tracing

**OpenTelemetry Integration:**
```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def generate_response(self, context, turn):
    with tracer.start_as_current_span("agent.generate_response") as span:
        span.set_attribute("agent.provider", self.PROVIDER_NAME)
        span.set_attribute("agent.turn", turn)
        
        # ... API call ...
        
        span.set_attribute("response.tokens", tokens)
        return response
```

**Trace Flow:**
```
conversation.start
└── agent1.run
    └── agent1.generate_response
        └── agent1.call_api
            └── http.post (to Claude API)
└── agent2.run
    └── agent2.generate_response
        └── agent2.call_api
            └── http.post (to OpenAI API)
```

### Logging

**Structured JSON Logging:**
```json
{
  "timestamp": "2025-11-03T10:00:00.123Z",
  "level": "INFO",
  "logger": "claude_agent",
  "event": "api_call_success",
  "provider": "Claude",
  "model": "claude-sonnet-4-5-20250929",
  "turn": 1,
  "tokens": 150,
  "latency": 1.234,
  "request_id": "abc-123"
}
```

---

## Security Architecture

### Defense in Depth

```
Layer 1: Input Validation
    ↓
Layer 2: LLM Guard Scanning
    ↓
Layer 3: API Call Execution
    ↓
Layer 4: Output Sanitization
    ↓
Layer 5: Logging (with key masking)
```

### Input Validation

**Path Traversal Prevention:**
```python
def validate_db_path(db_file: str) -> Path:
    allowed_dir = Path(config.DATA_DIR).resolve()
    db_path = Path(db_file).resolve()
    
    # Ensure path is within allowed directory
    try:
        db_path.relative_to(allowed_dir)
    except ValueError:
        raise ValueError("Path traversal detected")
    
    # Validate extension
    if db_path.suffix.lower() != ".db":
        raise ValueError("Invalid file extension")
    
    return db_path
```

### Output Sanitization

**XSS Prevention:**
```python
import bleach

def sanitize_content(content: str) -> str:
    # Strip all HTML tags
    clean = bleach.clean(content, tags=[], attributes={}, strip=True)
    
    # Remove non-printable characters
    clean = "".join(ch for ch in clean if ch.isprintable())
    
    return clean
```

### API Key Management

**Masking in Logs:**
```python
def mask_api_key(text: str) -> str:
    patterns = [
        (r"(sk-ant-[a-zA-Z0-9-]{20,})", "[ANTHROPIC_KEY]"),
        (r"(sk-[a-zA-Z0-9]{20,})", "[OPENAI_KEY]"),
        # ... more patterns
    ]
    
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    
    return text
```

---

## Design Patterns

### 1. Factory Pattern

**Agent Factory:**
```python
def create_agent(agent_type: str, ...) -> BaseAgent:
    info = get_agent_info(agent_type)
    cls = info["class"]
    return cls(...)
```

### 2. Strategy Pattern

**Queue Backend Strategy:**
```python
def create_queue(path: str, logger, use_redis: bool) -> QueueInterface:
    if use_redis:
        return RedisQueue(path, logger)
    else:
        return SQLiteQueue(Path(path), logger)
```

### 3. Circuit Breaker Pattern

**Prevents cascading failures** (see Circuit Breaker section above)

### 4. Template Method Pattern

**Base Agent defines workflow:**
```python
class BaseAgent:
    async def run(self, max_turns, partner_name):
        # Template method
        for turn in range(max_turns):
            if not await self.should_respond(partner_name):
                continue
            
            context = await self.get_context()
            response = await self.generate_response(context, turn)
            await self.add_to_queue(response)
    
    async def _call_api(self, messages):
        # Abstract method - subclasses implement
        raise NotImplementedError
```

### 5. Dependency Injection

**Agents receive dependencies:**
```python
def __init__(self, api_key, queue, logger, model, topic, timeout_minutes):
    self.api_key = api_key
    self.queue = queue  # Injected dependency
    self.logger = logger  # Injected dependency
    # ...
```

---

## Performance Characteristics

### Latency

**Typical Response Times:**
- SQLite queue operations: 1-5 ms
- Redis queue operations: 0.5-2 ms
- AI API calls: 1-10 seconds
- Total turn time: 1-10 seconds

**Bottlenecks:**
1. AI API latency (primary bottleneck)
2. Network latency
3. Queue lock contention (SQLite only)

### Throughput

**Messages per minute:**
- Single conversation: 6-60 messages/min (depending on API speed)
- Multiple conversations (Redis): Scales horizontally

### Resource Usage

**Per Conversation:**
- Memory: ~50-100 MB
- CPU: 5-10% (waiting for API)
- Disk I/O: Minimal (SQLite: ~1 KB per message)
- Network: Varies by API (1-10 KB per message)

---

## Scalability Considerations

### Horizontal Scaling

**Using Redis:**
```
┌──────────┐     ┌──────────┐     ┌──────────┐
│ Instance │────►│  Redis   │◄────│ Instance │
│    1     │     │  Queue   │     │    2     │
└──────────┘     └──────────┘     └──────────┘
      │               │                 │
      └───────────────┴─────────────────┘
                      │
                 Shared State
```

**Load Balancing:**
```
        ┌──────────────┐
        │ Load Balancer│
        └──────┬───────┘
               │
    ┌──────────┼──────────┐
    │          │          │
┌───▼───┐  ┌───▼───┐  ┌──▼────┐
│ App 1 │  │ App 2 │  │ App 3 │
└───┬───┘  └───┬───┘  └───┬───┘
    │          │          │
    └──────────┼──────────┘
               │
         ┌─────▼─────┐
         │   Redis   │
         └───────────┘
```

### Database Optimization

**SQLite:**
- File locking limits to single writer
- Good for: Single-instance deployments
- Optimization: Increase timeout, reduce lock contention

**Redis:**
- Distributed, no file locking
- Good for: Multi-instance deployments
- Optimization: Connection pooling, pipelining

### Caching Strategy

**Context Caching:**
```python
# Cache conversation context to reduce DB queries
@lru_cache(maxsize=128)
async def get_cached_context(conversation_id, max_messages):
    return await queue.get_context(max_messages)
```

---

## Future Enhancements

### Planned Features

1. **WebSocket Support**
   - Real-time UI updates
   - Streaming responses
   - Live conversation view

2. **Multi-Agent (3+)**
   - Round-robin turn management
   - Consensus mechanisms
   - Voting systems

3. **RAG Integration**
   - Vector database support
   - Document retrieval
   - Knowledge augmentation

4. **Kubernetes Deployment**
   - Helm charts
   - Horizontal Pod Autoscaler
   - Service mesh integration

5. **Advanced Observability**
   - Distributed tracing with Jaeger
   - Log aggregation with ELK
   - Custom dashboards

---

## Conclusion

The AI Conversation Platform is designed as a **production-ready, enterprise-grade system** with emphasis on:

- ✅ **Reliability**: Circuit breakers, retry logic, graceful degradation
- ✅ **Performance**: Async operations, efficient queue management
- ✅ **Observability**: Comprehensive metrics, tracing, logging
- ✅ **Security**: Input validation, output sanitization, secure credentials
- ✅ **Maintainability**: Clean architecture, dependency injection, design patterns
- ✅ **Scalability**: Horizontal scaling, pluggable backends

The architecture is flexible and extensible, allowing for easy addition of new AI providers, queue backends, and observability tools.

---

**Document Version**: 5.0.0  
**Last Updated**: 2025-11-03  
**Maintained by**: Paul Clark (@systemslibrarian)

---

[⬆ Back to Documentation Index](README.md)
