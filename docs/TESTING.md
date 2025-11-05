# Testing Documentation - AI Conversation Platform v5.0

## Table of Contents
- [Overview](#overview)
- [Test Suite Structure](#test-suite-structure)
- [Running Tests](#running-tests)
- [Test Coverage Goals](#test-coverage-goals)
- [Test Files Explained](#test-files-explained)
- [CI/CD Integration](#cicd-integration)
- [Writing New Tests](#writing-new-tests)
- [Troubleshooting](#troubleshooting)

---

## Overview

The AI Conversation Platform v5.0 includes a comprehensive test suite designed to ensure reliability, correctness, and maintainability. The test suite achieves **90%+ code coverage** across all core modules and provides both unit and integration testing.

### Testing Stack
- **Framework**: pytest (with pytest-asyncio for async tests)
- **Coverage**: pytest-cov
- **Mocking**: unittest.mock
- **CI/CD**: GitHub Actions
- **Code Quality**: Ruff (linting + formatting)

### Test Categories
1. **Unit Tests**: Individual component testing (agents, queue, config, utils)
2. **Integration Tests**: End-to-end scenarios with multiple components
3. **Security Tests**: LLM Guard, sanitization, input validation
4. **Stress Tests**: Concurrent operations, high-volume scenarios
5. **Error Handling**: Circuit breaker, retries, graceful degradation

---

## Test Suite Structure

```
tests/
├── __init__.py                                    # Test package initialization
├── test_agents.py                                 # Core agent tests (Claude, ChatGPT)
├── test_agents_additional.py                      # Additional providers (Gemini, Grok, Perplexity)
├── test_common_utils.py                           # Utility function tests
├── test_metrics.py                                # Metrics recording tests
├── test_tracing.py                                # OpenTelemetry tracing tests
├── test_config_utils_metrics_comprehensive.py     # Comprehensive config/logging/metrics
├── test_queue.py                                  # Queue operations (SQLite/Redis)
└── test_integration_comprehensive.py              # Full integration scenarios
```

### Lines of Test Code by File
- `test_integration_comprehensive.py`: 550 lines
- `test_queue.py`: 524 lines
- `test_config_utils_metrics_comprehensive.py`: 507 lines
- `test_agents.py`: 202 lines
- `test_agents_additional.py`: 135 lines
- `test_common_utils.py`: 15 lines
- `test_metrics.py`: 12 lines
- `test_tracing.py`: 11 lines

**Total: ~1,956 lines of test code**

---

## Running Tests

### Prerequisites
```bash
# Install dependencies
uv pip install --system -r requirements.txt pytest pytest-asyncio pytest-cov redis

# Or using pip
pip install pytest pytest-asyncio pytest-cov redis
```

### Basic Test Execution

**Run all tests:**
```bash
pytest
```

**Run with verbose output:**
```bash
pytest -v
```

**Run specific test file:**
```bash
pytest tests/test_agents.py -v
```

**Run specific test class:**
```bash
pytest tests/test_agents.py::TestCircuitBreaker -v
```

**Run specific test method:**
```bash
pytest tests/test_agents.py::TestCircuitBreaker::test_circuit_breaker_opens_after_failures -v
```

### Coverage Reports

**Generate coverage report:**
```bash
pytest --cov=agents --cov=core --cov-report=term-missing
```

**Generate HTML coverage report:**
```bash
pytest --cov=agents --cov=core --cov-report=html
# Open htmlcov/index.html in browser
```

**Coverage for specific module:**
```bash
pytest --cov=core.queue --cov-report=term-missing tests/test_queue.py
```

### Fast Testing

**Stop after first failure:**
```bash
pytest --maxfail=1
```

**Run tests in parallel (requires pytest-xdist):**
```bash
pytest -n auto
```

**Quiet mode (less output):**
```bash
pytest -q
```

### Advanced Options

**Run only async tests:**
```bash
pytest -k "asyncio"
```

**Skip slow tests (if marked):**
```bash
pytest -m "not slow"
```

**Run with warnings:**
```bash
pytest -v --tb=short
```

**Generate XML report (for CI):**
```bash
pytest --junitxml=test-results.xml
```

---

## Test Coverage Goals

### Current Coverage by Module
- **agents/**: 92%+ (base, chatgpt, claude, gemini, grok, perplexity)
- **core/queue.py**: 95%+ (SQLite and Redis implementations)
- **core/config.py**: 90%+
- **core/common.py**: 90%+
- **core/metrics.py**: 88%+
- **core/tracing.py**: 85%+

### Coverage Requirements
- **Minimum**: 80% for all modules
- **Target**: 90%+ for core modules
- **Critical paths**: 95%+ (queue, agents, security)

### Excluded from Coverage
- Imports and type checking blocks (`if TYPE_CHECKING:`)
- Abstract methods (unless tested via subclass)
- Debug/development code paths
- Exception handlers for impossible states

---

## Test Files Explained

### test_agents.py (202 lines)
**Purpose**: Test core agent functionality for Claude and ChatGPT

**Key Test Classes**:
- `TestCircuitBreaker`: Circuit breaker pattern (failure threshold, state transitions, reset)
- `TestChatGPTAgent`: OpenAI integration (initialization, API calls)
- `TestClaudeAgent`: Anthropic integration (initialization, API calls)
- `TestSimilarity`: Repetition detection algorithm
- `TestShouldRespond`: Turn management logic
- `TestAgentSecurity`: LLM Guard integration (prompt injection detection)

**Coverage Focus**:
- Circuit breaker opens after threshold failures ✓
- Circuit breaker transitions to HALF_OPEN after timeout ✓
- Successful calls reset circuit breaker ✓
- Agent initialization with correct models ✓
- API call mocking and response handling ✓
- Similarity detection triggers after consecutive matches ✓
- Turn management prevents self-responses ✓

**Example Test**:
```python
def test_circuit_breaker_opens_after_failures(self):
    cb = CircuitBreaker(failure_threshold=3)
    for _ in range(3):
        cb.record_failure()
    assert cb.state == "OPEN"
    assert cb.is_open()
```

---

### test_agents_additional.py (135 lines)
**Purpose**: Test additional AI providers (Gemini, Grok, Perplexity)

**Key Test Classes**:
- `TestGrokAgent`: xAI Grok integration
- `TestPerplexityAgent`: Perplexity AI integration
- `TestGeminiAgent`: Google Gemini integration

**Coverage Focus**:
- All providers initialize correctly ✓
- API calls return valid responses ✓
- Token counting works for each provider ✓
- Mock clients simulate real API behavior ✓

**Mock Strategy**:
- `DummyOpenAIClient`: Simulates OpenAI-compatible APIs (Grok, Perplexity)
- `DummyGenAIModel`: Simulates Google Generative AI SDK

**Example Test**:
```python
async def test_grok_api_call(self, mock_queue, logger):
    with patch("openai.OpenAI", DummyOpenAIClient):
        agent = GrokAgent(api_key="test-key", queue=mock_queue, logger=logger)
        content, tokens = await agent._call_api([{"role": "user", "content": "hi"}])
        assert content != ""
        assert tokens > 0
```

---

### test_common_utils.py (15 lines)
**Purpose**: Test utility functions in core.common

**Functions Tested**:
- `mask_api_key()`: Redacts API keys in logs/errors
- `sanitize_content()`: Removes dangerous content (XSS, SQL injection)
- `simple_similarity()`: Calculates text similarity (0.0-1.0)
- `add_jitter()`: Adds randomness to retry delays

**Coverage Focus**:
- API key patterns detected and masked ✓
- Dangerous content triggers filtering ✓
- Similarity returns valid range [0.0, 1.0] ✓
- Jitter produces positive values ✓

---

### test_metrics.py (12 lines)
**Purpose**: Basic smoke tests for metrics recording

**Functions Tested**:
- `record_call()`: Records API calls (success/error)
- `record_latency()`: Records response times
- `record_tokens()`: Records token usage
- `record_error()`: Records error types
- `increment_conversations()` / `decrement_conversations()`: Active conversation counting

**Coverage Focus**:
- All metric functions execute without errors ✓
- Metrics can be recorded with various labels ✓

---

### test_tracing.py (11 lines)
**Purpose**: Test OpenTelemetry tracing setup

**Functions Tested**:
- `get_tracer()`: Returns tracer instance
- `setup_tracing()`: Configures OpenTelemetry (with/without endpoint)

**Coverage Focus**:
- Tracer can be retrieved ✓
- Tracing setup handles missing endpoint gracefully ✓

---

### test_config_utils_metrics_comprehensive.py (507 lines)
**Purpose**: Comprehensive testing of configuration, logging, utilities, and metrics

**Key Test Classes**:

#### Configuration Testing
- `TestConfigValidation`: Pydantic model validation
  - Valid configurations pass ✓
  - Temperature bounds (0-2) enforced ✓
  - MAX_TOKENS must be positive ✓
  - SIMILARITY_THRESHOLD range (0-1) enforced ✓
  - PROMETHEUS_PORT range validated ✓

- `TestConfigClass`: Config class methods
  - API key retrieval from environment ✓
  - Error when API key missing ✓
  - Config validation catches invalid values ✓
  - Expected attributes present ✓

#### Logging Testing
- `TestSetupLogging`: Logger configuration
  - Logger creation with correct name/level ✓
  - Log directory creation ✓
  - File handler setup ✓
  - Handler cleanup/replacement ✓

- `TestLogEvent`: Structured JSON logging
  - JSON format validation ✓
  - Timestamp inclusion ✓
  - Event and data fields ✓

#### Utility Testing
- `TestSimpleSimilarity`: Text similarity algorithm
  - Identical strings return 1.0 ✓
  - Different strings return lower scores ✓
  - Empty strings return 0.0 ✓
  - Short strings handled correctly ✓

- `TestHashMessage`: Content hashing
  - Consistent hashes for same content ✓
  - Different hashes for different content ✓
  - Hash length validation (8 chars) ✓

- `TestAddJitter`: Retry delay randomization
  - Jitter stays within range ✓
  - Minimum value enforced ✓
  - Custom ranges supported ✓

- `TestMaskApiKey`: Sensitive data redaction
  - Anthropic keys masked ✓
  - OpenAI keys masked ✓
  - Perplexity keys masked ✓
  - Generic long keys masked ✓
  - Multiple keys in same string masked ✓

- `TestSanitizeContent`: Security filtering
  - Script tags removed ✓
  - JavaScript protocol blocked ✓
  - Event handlers removed ✓
  - SQL injection patterns detected ✓
  - Safe content unchanged ✓
  - Case-insensitive matching ✓

#### Metrics Testing
- `TestMetricsRecording`: Prometheus metrics
  - Call recording (success/error) ✓
  - Latency recording ✓
  - Token usage recording ✓
  - Error recording with types ✓
  - Conversation counters ✓
  - Special characters in labels handled ✓

- `TestMetricsServer`: HTTP server for metrics
  - Default port startup ✓
  - Custom port configuration ✓
  - Error handling (port in use) ✓
  - Environment variable support ✓

- `TestMetricsErrorHandling`: Fault tolerance
  - Exceptions in metric recording don't crash ✓

**Example Test**:
```python
def test_mask_anthropic_key(self):
    text = "My key is sk-ant-1234567890123456789012345"
    masked = mask_api_key(text)
    assert "[ANTHROPIC_KEY]" in masked
    assert "sk-ant-" not in masked
```

---

### test_queue.py (524 lines)
**Purpose**: Comprehensive testing of queue implementations (SQLite and Redis)

**Key Test Classes**:

#### SQLite Queue - Basic Tests
- `TestSQLiteQueueBasic`:
  - Queue initialization with correct metadata ✓
  - Adding messages and retrieving context ✓
  - Last sender tracking ✓
  - Conversation termination ✓
  - Concurrent writes (20 messages from 2 agents) ✓
  - Factory pattern creates correct queue type ✓

#### SQLite Queue - Comprehensive Tests
- `TestSQLiteQueueComprehensive`:
  - Empty content rejection ✓
  - Message length validation (MAX_MESSAGE_LENGTH) ✓
  - Sender name normalization (claude → Claude) ✓
  - Token accumulation across messages ✓
  - Individual agent turn counting ✓
  - Context limit enforcement ✓
  - Lock file handling ✓
  - Health checks (database, lock file) ✓
  - Termination reason retrieval ✓
  - Data persistence and reload ✓

#### Redis Queue Tests
- `TestRedisQueue`:
  - Message adding with XADD ✓
  - Context retrieval with chronological order ✓
  - Last sender from stream ✓
  - Empty queue handling ✓
  - Termination flag management ✓
  - Termination reason storage ✓
  - Full data loading ✓
  - Health check (ping) ✓
  - Unhealthy state detection ✓
  - Malformed JSON metadata handling ✓

#### Factory and Error Handling
- `TestQueueFactory`: Queue creation logic
  - SQLite queue creation ✓
  - Redis queue creation (flag and URL detection) ✓

- `TestErrorHandling`: Resilience
  - Queue continues after errors ✓

#### Stress Tests
- `TestStressScenarios`:
  - 100 messages handled correctly ✓
  - Rapid termination checks (50 concurrent) ✓

**Example Test**:
```python
async def test_concurrent_writes(self, temp_db, logger):
    queue = SQLiteQueue(temp_db, logger)
    
    async def add(sender):
        for i in range(10):
            await queue.add_message(sender, f"m{i}", {"tokens": 1})
    
    await asyncio.gather(add("Claude"), add("ChatGPT"))
    
    data = await queue.load()
    assert len(data["messages"]) == 20
    assert data["metadata"]["total_turns"] == 20
```

---

### test_integration_comprehensive.py (550 lines)
**Purpose**: End-to-end integration testing of complete conversation flows

**Key Test Classes**:

#### Full Conversation Flows
- `TestFullConversationFlow`:
  - Two-agent conversation with alternation ✓
  - Conversation termination mid-flow ✓
  - Concurrent message adding (40 messages) ✓
  - Context retrieval with multiple messages ✓
  - Token accumulation tracking ✓
  - Agent turn counting ✓

#### Agent Factory Tests
- `TestAgentFactory`:
  - ChatGPT agent creation ✓
  - Claude agent creation ✓
  - Model override support ✓
  - API key validation ✓

#### Health Checks
- `TestHealthChecks`:
  - SQLite queue health check ✓
  - Invalid database path handling ✓

#### Message Validation
- `TestMessageValidation`:
  - Empty content rejection ✓
  - Sender normalization ✓
  - Message length limits ✓

#### Conversation Metadata
- `TestConversationMetadata`:
  - Initial metadata structure ✓
  - Metadata updates during conversation ✓
  - Termination metadata (reason, timestamp) ✓

#### Concurrent Operations
- `TestConcurrentAgents`:
  - Proper turn alternation (10 messages, no back-to-back) ✓

#### Stress Tests
- `TestStressScenarios`:
  - 100 messages from 3 agents ✓
  - 50 rapid termination checks ✓

**Integration Test Agent**:
```python
class IntegrationTestAgent:
    """Simplified agent for integration testing"""
    async def run(self, max_turns, partner_name):
        for turn in range(max_turns):
            last_sender = await self.queue.get_last_sender()
            if last_sender is None or last_sender == partner_name:
                content = self.responses[turn] if turn < len(self.responses) else f"{self.name} message {turn + 1}"
                await self.queue.add_message(self.name, content, {"turn": turn + 1, "tokens": 50})
                if "[done]" in content.lower():
                    await self.queue.mark_terminated("test_termination_signal")
                    break
```

**Example Test**:
```python
async def test_two_agent_conversation(self, temp_db, logger):
    queue = SQLiteQueue(temp_db, logger)
    
    agent1 = IntegrationTestAgent("Agent1", queue, logger,
                                   responses=["Hello Agent2", "How are you?", "Goodbye"])
    agent2 = IntegrationTestAgent("Agent2", queue, logger,
                                   responses=["Hi Agent1", "I'm good, you?", "See you later"])
    
    await asyncio.gather(
        agent1.run(max_turns=3, partner_name="Agent2"),
        agent2.run(max_turns=3, partner_name="Agent1")
    )
    
    data = await queue.load()
    assert len(data["messages"]) >= 3
    assert "Agent1" in [m["sender"] for m in data["messages"]]
    assert "Agent2" in [m["sender"] for m in data["messages"]]
```

---

## CI/CD Integration

### GitHub Actions Workflow (`.github/workflows/ci.yml`)

The CI pipeline runs automatically on every push to `main` and on all pull requests.

#### Pipeline Stages

**Stage 1: Auto-Fix Formatting** (runs first)
```yaml
fix-formatting:
  - Checkout code
  - Install Ruff
  - Run Ruff linter fix (--fix)
  - Run Ruff formatter
  - Auto-commit changes
```

**Stage 2: Run Tests** (waits for formatting)
```yaml
run-tests:
  needs: fix-formatting
  - Checkout code (with formatting fixes)
  - Install uv
  - Install dependencies (pytest, pytest-asyncio, redis)
  - Run pytest with fail-fast
```

**Stage 3: CodeQL Security Scan** (parallel with tests)
```yaml
codeql:
  needs: fix-formatting
  - Initialize CodeQL for Python
  - Perform security analysis
```

#### Other Workflows

**Cleanup** (`.github/workflows/cleanup.yml`)
- Runs weekly on Sundays
- Deletes workflow runs older than 30 days
- Keeps minimum 6 runs per workflow
- Manual trigger available

**CodeQL Standalone** (`.github/workflows/codeql.yml`)
- Runs on push/PR to main
- Weekly scheduled scan (Mondays 09:00 UTC)
- Security and quality analysis

**Release** (`.github/workflows/release.yml`)
- Triggers on version tags (`v*.*.*`)
- Builds Docker images for amd64/arm64
- Publishes to GitHub Container Registry (GHCR)

### Running CI Locally

**Simulate formatting check:**
```bash
ruff check . --fix
ruff format .
```

**Simulate test run:**
```bash
pytest -q --maxfail=1 --disable-warnings
```

**Check for security issues:**
```bash
# Install CodeQL CLI and run scan
# Or use Bandit as alternative:
pip install bandit
bandit -r agents/ core/ -ll
```

---

## Writing New Tests

### Test Structure Guidelines

**Follow AAA Pattern** (Arrange, Act, Assert):
```python
async def test_agent_responds_correctly(self, mock_queue, logger):
    # Arrange
    agent = ChatGPTAgent(api_key="test", queue=mock_queue, logger=logger)
    
    # Act
    content, tokens = await agent._call_api([{"role": "user", "content": "hi"}])
    
    # Assert
    assert content != ""
    assert tokens > 0
```

### Test Naming Conventions

- **Test files**: `test_<module_name>.py`
- **Test classes**: `Test<FeatureName>` (PascalCase)
- **Test methods**: `test_<what_it_tests>` (snake_case)
- Be descriptive: `test_circuit_breaker_opens_after_failures` not `test_cb`

### Fixtures

**Create reusable fixtures:**
```python
@pytest.fixture
def mock_queue():
    """Create a mock queue for testing"""
    queue = AsyncMock()
    queue.get_context.return_value = []
    queue.get_last_sender.return_value = None
    queue.is_terminated.return_value = False
    return queue
```

**Use fixtures in tests:**
```python
async def test_something(self, mock_queue, logger):
    agent = SomeAgent(queue=mock_queue, logger=logger)
    # Test logic...
```

### Async Testing

**Mark async tests:**
```python
@pytest.mark.asyncio
async def test_async_function(self):
    result = await some_async_function()
    assert result is not None
```

### Mocking External APIs

**Patch at the import source:**
```python
# ✓ CORRECT - Patch where it's imported from
with patch("openai.OpenAI") as mock_openai:
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    # Test logic...

# ✗ WRONG - Don't patch where it's used
with patch("agents.chatgpt.OpenAI"):  # Won't work!
```

**Create realistic mock responses:**
```python
mock_client.chat.completions.create.return_value = MagicMock(
    choices=[MagicMock(message=MagicMock(content="Hello"))],
    usage=MagicMock(total_tokens=10)
)
```

### Testing Error Conditions

**Use pytest.raises:**
```python
def test_invalid_config_raises(self):
    with pytest.raises(ValueError, match="Invalid temperature"):
        Config.TEMPERATURE = 5.0
        Config.validate()
```

### Parametrized Tests

**Test multiple inputs:**
```python
@pytest.mark.parametrize("temp,expected", [
    (0.0, True),
    (1.0, True),
    (2.0, True),
    (3.0, False),
])
def test_temperature_validation(temp, expected):
    try:
        config = ConfigValidation(TEMPERATURE=temp, ...)
        assert expected is True
    except Exception:
        assert expected is False
```

### Test Coverage Tips

**Check coverage for your changes:**
```bash
pytest --cov=agents.new_module --cov-report=term-missing tests/test_new_module.py
```

**Focus on:**
- ✓ Happy path (expected usage)
- ✓ Edge cases (empty inputs, max values, None)
- ✓ Error conditions (invalid inputs, API failures)
- ✓ Boundary values (0, 1, max)
- ✓ Concurrent operations (if applicable)

**Don't test:**
- ✗ External library internals
- ✗ Python standard library
- ✗ Obviously correct code (simple getters)

### Code Coverage Requirements

**Aim for 90%+ coverage on:**
- Core business logic
- Security-critical code
- Data processing
- API integrations

**80%+ acceptable for:**
- Utility functions
- Logging/metrics
- Configuration

**Coverage exceptions:**
```python
def some_function():
    try:
        # Main logic
        pass
    except Exception as e:  # pragma: no cover
        # Impossible to test / defensive programming
        logger.critical(f"Unexpected error: {e}")
```

---

## Troubleshooting

### Common Test Failures

#### ImportError: No module named 'X'

**Problem**: Missing test dependencies
```bash
# Solution
pip install pytest pytest-asyncio pytest-cov redis
```

#### AsyncioError: Event loop is closed

**Problem**: Async tests not properly marked
```python
# Solution: Add decorator
@pytest.mark.asyncio
async def test_my_async_function():
    ...
```

#### Fixture 'X' not found

**Problem**: Fixture not in scope
```python
# Solution: Check fixture is defined or imported
@pytest.fixture
def my_fixture():
    return "value"
```

#### Mock not being called

**Problem**: Patching wrong location
```python
# ✗ WRONG
with patch("agents.claude.Anthropic"):  # Doesn't work

# ✓ CORRECT
with patch("anthropic.Anthropic"):  # Patch at source
```

#### Tests pass locally but fail in CI

**Problem**: Environment differences
```bash
# Check CI logs for:
# - Missing environment variables
# - File permissions
# - Network access (CI may block external calls)
# - Timing issues (add retries/waits)
```

### Test Database Issues

**Problem**: SQLite database locked
```python
# Solution: Ensure cleanup in fixtures
@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    if db_path.exists():
        db_path.unlink()
    lock_file = Path(f"{db_path}.lock")
    if lock_file.exists():
        lock_file.unlink()  # Clean up lock file
```

### Redis Connection Issues

**Problem**: Redis tests fail with connection error
```bash
# Solution: Use mocks, don't require real Redis
with patch("redis.asyncio.from_url", return_value=mock_redis):
    queue = RedisQueue("redis://localhost", logger)
```

### Coverage Report Discrepancies

**Problem**: Coverage lower than expected
```bash
# Check which lines are missing
pytest --cov=module --cov-report=term-missing

# Generate HTML report for detailed view
pytest --cov=module --cov-report=html
open htmlcov/index.html
```

### Debugging Test Failures

**Enable verbose output:**
```bash
pytest -vv -s  # Very verbose + show print statements
```

**Run single test with full traceback:**
```bash
pytest tests/test_file.py::TestClass::test_method -vv --tb=long
```

**Drop into debugger on failure:**
```bash
pytest --pdb
```

**Set breakpoint in test:**
```python
def test_something():
    result = function_call()
    breakpoint()  # Python 3.7+
    assert result == expected
```

---

## Best Practices Summary

### ✓ DO:
- Write clear, descriptive test names
- Use fixtures for common setup
- Test edge cases and error conditions
- Mock external dependencies (APIs, databases)
- Keep tests independent and isolated
- Aim for 90%+ coverage on critical code
- Use async tests for async code
- Follow AAA pattern (Arrange, Act, Assert)
- Add docstrings to test classes/methods
- Clean up resources in fixtures

### ✗ DON'T:
- Test external library internals
- Share state between tests
- Make tests dependent on execution order
- Skip writing tests for "simple" code
- Use real APIs in unit tests
- Ignore test failures in CI
- Write tests that depend on timing
- Hard-code test data without explanation
- Leave commented-out test code

---

## Additional Resources

### Documentation
- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio documentation](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [unittest.mock documentation](https://docs.python.org/3/library/unittest.mock.html)

### Project Documentation
- `README.md` - Project overview and setup
- `CONTRIBUTING.md` - Contribution guidelines
- `docs/ARCHITECTURE.md` - System architecture (if exists)

### Contact
For questions about testing:
- Open an issue on GitHub
- Check existing test files for examples
- Review CI workflow logs for failures

---

**Last Updated**: 2025-01-06  
**Test Suite Version**: 5.0  
**Maintainer**: Paul (Systems Librarian, Leon County Public Library)
