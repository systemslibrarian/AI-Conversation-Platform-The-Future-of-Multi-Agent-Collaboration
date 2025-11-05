# Test Suite Quick Reference

**AI Conversation Platform v5.0**

A quick reference guide for running and understanding the test suite.

---

## Quick Commands

```bash
# Run all tests
pytest

# Fast mode (stop at first failure)
pytest --maxfail=1 -q

# With coverage
pytest --cov=agents --cov=core --cov-report=term-missing

# Specific file
pytest tests/test_agents.py -v

# Specific test
pytest tests/test_agents.py::TestCircuitBreaker::test_circuit_breaker_opens_after_failures -v

# HTML coverage report
pytest --cov=agents --cov=core --cov-report=html && open htmlcov/index.html
```

---

## Test Files Overview

| File | LOC | What It Tests |
|------|-----|---------------|
| `test_integration_comprehensive.py` | 550 | End-to-end conversation flows, multi-agent scenarios |
| `test_queue.py` | 524 | SQLite/Redis queue operations, concurrency |
| `test_config_utils_metrics_comprehensive.py` | 507 | Config validation, logging, metrics, utilities |
| `test_agents.py` | 202 | Claude & ChatGPT agents, circuit breaker |
| `test_agents_additional.py` | 135 | Gemini, Grok, Perplexity agents |
| `test_common_utils.py` | 15 | Utility functions (masking, similarity) |
| `test_metrics.py` | 12 | Metrics recording smoke tests |
| `test_tracing.py` | 11 | OpenTelemetry tracing setup |

**Total:** ~1,956 lines of test code

---

## Test Categories

### Unit Tests
```bash
# Agents
pytest tests/test_agents.py -v
pytest tests/test_agents_additional.py -v

# Queue
pytest tests/test_queue.py::TestSQLiteQueueBasic -v

# Config & Utils
pytest tests/test_config_utils_metrics_comprehensive.py::TestConfigValidation -v
pytest tests/test_common_utils.py -v

# Metrics & Tracing
pytest tests/test_metrics.py -v
pytest tests/test_tracing.py -v
```

### Integration Tests
```bash
# Full conversation flows
pytest tests/test_integration_comprehensive.py -v

# Specific scenarios
pytest tests/test_integration_comprehensive.py::TestFullConversationFlow -v
pytest tests/test_integration_comprehensive.py::TestConcurrentAgents -v
```

### Stress Tests
```bash
# High-volume scenarios
pytest tests/test_queue.py::TestStressScenarios -v
pytest tests/test_integration_comprehensive.py::TestStressScenarios -v
```

---

## Coverage by Module

| Module | Target | Current |
|--------|--------|---------|
| `agents/base.py` | 90% | 92% |
| `agents/chatgpt.py` | 90% | 94% |
| `agents/claude.py` | 90% | 94% |
| `agents/gemini.py` | 90% | 91% |
| `agents/grok.py` | 90% | 91% |
| `agents/perplexity.py` | 90% | 91% |
| `core/queue.py` | 95% | 96% |
| `core/config.py` | 90% | 92% |
| `core/common.py` | 90% | 91% |
| `core/metrics.py` | 85% | 88% |
| `core/tracing.py` | 85% | 86% |

```bash
# Check specific module coverage
pytest --cov=agents.base --cov-report=term-missing tests/test_agents.py
pytest --cov=core.queue --cov-report=term-missing tests/test_queue.py
```

---

## Key Test Patterns

### Async Tests
```python
@pytest.mark.asyncio
async def test_async_function(self, mock_queue, logger):
    result = await some_async_function()
    assert result is not None
```

### Mocking APIs
```python
# Patch at import source, not usage location
with patch("openai.OpenAI") as mock_openai:
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="Hello"))],
        usage=MagicMock(total_tokens=10)
    )
    mock_openai.return_value = mock_client
    # Test with mock
```

### Fixtures
```python
@pytest.fixture
def mock_queue():
    """Create mock queue"""
    queue = AsyncMock()
    queue.get_context.return_value = []
    return queue

@pytest.fixture
def temp_db():
    """Create temporary database"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    if db_path.exists():
        db_path.unlink()
```

### Error Testing
```python
# Test expected exceptions
with pytest.raises(ValueError, match="Invalid input"):
    function_that_should_raise()

# Test validation
with pytest.raises(Exception):
    await queue.add_message("Agent", "", {})  # Empty content should fail
```

---

## What Each Test File Covers

### test_agents.py
- ✅ Circuit breaker (opens after failures, transitions, resets)
- ✅ ChatGPT agent (initialization, API calls)
- ✅ Claude agent (initialization, API calls)
- ✅ Similarity detection (repetition threshold)
- ✅ Turn management (should_respond logic)
- ✅ Security (LLM Guard integration)

**Run it:**
```bash
pytest tests/test_agents.py -v
```

### test_agents_additional.py
- ✅ Grok agent (xAI integration)
- ✅ Perplexity agent (search-enabled model)
- ✅ Gemini agent (Google AI)
- ✅ Mock implementations for testing

**Run it:**
```bash
pytest tests/test_agents_additional.py -v
```

### test_queue.py
- ✅ SQLite queue (basic operations, comprehensive tests)
- ✅ Redis queue (all operations with mocks)
- ✅ Message validation (empty content, length limits)
- ✅ Concurrent writes (20 messages from 2 agents)
- ✅ Context retrieval (with message limits)
- ✅ Termination handling
- ✅ Health checks
- ✅ Stress tests (100 messages, rapid checks)

**Run it:**
```bash
pytest tests/test_queue.py -v

# Just SQLite tests
pytest tests/test_queue.py::TestSQLiteQueueBasic -v
pytest tests/test_queue.py::TestSQLiteQueueComprehensive -v

# Just Redis tests
pytest tests/test_queue.py::TestRedisQueue -v
```

### test_config_utils_metrics_comprehensive.py
- ✅ Config validation (temperature, tokens, thresholds)
- ✅ API key retrieval
- ✅ Logging setup (directory creation, handlers)
- ✅ Structured JSON logging
- ✅ Text similarity algorithm
- ✅ Message hashing
- ✅ API key masking (multiple providers)
- ✅ Content sanitization (XSS, SQL injection)
- ✅ Metrics recording (calls, latency, tokens, errors)
- ✅ Metrics server (startup, ports, error handling)

**Run it:**
```bash
pytest tests/test_config_utils_metrics_comprehensive.py -v

# Specific sections
pytest tests/test_config_utils_metrics_comprehensive.py::TestConfigValidation -v
pytest tests/test_config_utils_metrics_comprehensive.py::TestMaskApiKey -v
pytest tests/test_config_utils_metrics_comprehensive.py::TestSanitizeContent -v
```

### test_integration_comprehensive.py
- ✅ Two-agent conversations (alternating turns)
- ✅ Termination handling (mid-conversation)
- ✅ Concurrent message adding (40 messages)
- ✅ Context retrieval (multiple messages)
- ✅ Token accumulation tracking
- ✅ Agent factory (create_agent function)
- ✅ Health checks (SQLite queue)
- ✅ Message validation (empty, length, normalization)
- ✅ Conversation metadata (initial, updates, termination)
- ✅ Turn alternation (proper back-and-forth)
- ✅ Stress scenarios (100 messages, rapid checks)

**Run it:**
```bash
pytest tests/test_integration_comprehensive.py -v

# Specific scenarios
pytest tests/test_integration_comprehensive.py::TestFullConversationFlow -v
pytest tests/test_integration_comprehensive.py::TestConcurrentAgents -v
pytest tests/test_integration_comprehensive.py::TestStressScenarios -v
```

---

## Common Test Failures & Fixes

### ImportError: No module named 'X'
```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov redis
```

### AsyncioError: Event loop is closed
```python
# Add decorator to async tests
@pytest.mark.asyncio
async def test_function():
    ...
```

### Mock not being called
```python
# ✗ WRONG - patching at wrong location
with patch("agents.claude.Anthropic"):

# ✓ CORRECT - patch at import source
with patch("anthropic.Anthropic"):
```

### SQLite database locked
```python
# Ensure cleanup in fixture
@pytest.fixture
def temp_db():
    # ... create db ...
    yield db_path
    if db_path.exists():
        db_path.unlink()
    # Also clean up lock file
    lock_file = Path(f"{db_path}.lock")
    if lock_file.exists():
        lock_file.unlink()
```

### Tests pass locally but fail in CI
```bash
# Check CI logs for:
# - Missing environment variables
# - File permissions
# - Timing issues (add waits/retries)

# Reproduce CI environment locally:
docker run -it python:3.11 bash
# ... install deps and run tests ...
```

---

## CI/CD Pipeline

### GitHub Actions Workflow

**Every push/PR automatically runs:**

1. **Auto-fix Formatting** (runs first)
   - `ruff check . --fix`
   - `ruff format .`
   - Auto-commits fixes

2. **Run Tests** (waits for formatting)
   - Installs dependencies
   - `pytest -q --maxfail=1 --disable-warnings`

3. **CodeQL Security Scan** (parallel with tests)
   - Static analysis for security issues

**View CI Status:**
```
https://github.com/yourusername/ai-conversation-platform/actions
```

**Simulate CI locally:**
```bash
# 1. Format check
ruff check . --fix
ruff format .

# 2. Run tests
pytest -q --maxfail=1 --disable-warnings

# 3. Coverage report
pytest --cov=agents --cov=core --cov-report=term-missing
```

---

## Debugging Tests

### Verbose Output
```bash
# Show all test output
pytest -vv -s

# Show only failed tests
pytest -vv --tb=short

# Show full tracebacks
pytest -vv --tb=long
```

### Single Test Debugging
```bash
# Run specific test with full output
pytest tests/test_agents.py::TestCircuitBreaker::test_circuit_breaker_opens_after_failures -vv -s

# Drop into debugger on failure
pytest --pdb tests/test_agents.py::TestCircuitBreaker::test_circuit_breaker_opens_after_failures
```

### Using Breakpoints
```python
def test_something():
    result = function_call()
    breakpoint()  # Execution pauses here
    assert result == expected
```

### Print Debugging
```python
@pytest.mark.asyncio
async def test_with_output(self, mock_queue, logger):
    print(f"Queue state: {mock_queue.get_last_sender.return_value}")
    result = await some_function()
    print(f"Result: {result}")
    assert result is not None
```

Run with `-s` flag to see print output:
```bash
pytest tests/test_file.py::test_with_output -s
```

---

## Test Writing Checklist

When adding new tests:

- [ ] Test follows AAA pattern (Arrange, Act, Assert)
- [ ] Test name is descriptive (`test_circuit_breaker_opens_after_failures`)
- [ ] Async tests have `@pytest.mark.asyncio` decorator
- [ ] Fixtures used for common setup
- [ ] External APIs are mocked
- [ ] Both happy path and error cases tested
- [ ] Edge cases covered (empty, None, max values)
- [ ] Test is independent (no shared state)
- [ ] Docstring explains what test validates
- [ ] Coverage maintained at 90%+

---

## Useful Test Commands

```bash
# Run tests matching pattern
pytest -k "test_circuit" -v

# Run tests NOT matching pattern
pytest -k "not redis" -v

# Run only failed tests from last run
pytest --lf

# Run tests in random order (requires pytest-random-order)
pytest --random-order

# Show slowest tests
pytest --durations=10

# Generate JUnit XML (for CI)
pytest --junitxml=test-results.xml

# Parallel execution (requires pytest-xdist)
pytest -n auto

# Stop after N failures
pytest --maxfail=3
```

---

## Coverage Tips

```bash
# Check coverage for new file
pytest --cov=agents.new_module --cov-report=term-missing tests/test_new_module.py

# Find uncovered lines
pytest --cov=core --cov-report=term-missing | grep "TOTAL"

# Generate detailed HTML report
pytest --cov=agents --cov=core --cov-report=html
open htmlcov/index.html

# Check coverage threshold
pytest --cov=agents --cov-report=term --cov-fail-under=90
```

**Coverage goals:**
- Core modules: **90%+**
- Critical paths: **95%+**
- Utilities: **80%+**

---

## Test Data & Fixtures

### Common Fixtures

```python
# Mock queue (for agent tests)
@pytest.fixture
def mock_queue():
    queue = AsyncMock()
    queue.get_context.return_value = []
    queue.get_last_sender.return_value = None
    queue.is_terminated.return_value = False
    return queue

# Temporary database (for queue tests)
@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    if db_path.exists():
        db_path.unlink()

# Logger (for all tests)
@pytest.fixture
def logger():
    return logging.getLogger("test")

# Mock Redis (for Redis queue tests)
@pytest.fixture
def mock_redis():
    redis_mock = AsyncMock()
    redis_mock.xadd.return_value = "1234567890-0"
    redis_mock.xrevrange.return_value = []
    redis_mock.ping.return_value = True
    return redis_mock
```

---

## Resources

**Documentation:**
- [TESTING.md](./TESTING.md) - Comprehensive testing guide
- [README.md](./README.md) - Project overview
- [CONTRIBUTING.md](./CONTRIBUTING.md) - Contribution guidelines

**External:**
- [pytest docs](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)

---

**Quick Start Testing:**
```bash
# Install, test, check coverage
pip install pytest pytest-asyncio pytest-cov
pytest
pytest --cov=agents --cov=core --cov-report=term-missing
```

**Last Updated**: 2025-01-06  
**Test Suite Version**: 5.0
