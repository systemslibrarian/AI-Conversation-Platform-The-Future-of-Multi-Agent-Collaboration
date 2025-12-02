# 🧪 Testing Guide — AI Conversation Platform v5.0

Comprehensive guide to **running tests**, **test file coverage**, **CI/CD integration**, and **development workflows**.

---

## ⚡ Quick Commands

```bash
# Run all tests
uv run pytest

# Stop at first failure (fast feedback)
uv run pytest --maxfail=1 -q

# With coverage report
uv run pytest --cov=agents --cov=core --cov-report=term-missing

# Specific test file
uv run pytest tests/test_agents.py -v

# Specific test class
uv run pytest tests/test_agents.py::TestCircuitBreaker -v

# Specific test function
uv run pytest tests/test_agents.py::TestCircuitBreaker::test_circuit_breaker_opens_after_failures -v

# HTML coverage report
uv run pytest --cov=agents --cov=core --cov-report=html
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows

# Parallel execution (requires pytest-xdist)
uv run pytest -n auto

# Verbose output with print statements
uv run pytest -vv -s

# Only failed tests from last run
uv run pytest --lf

# Show slowest tests
uv run pytest --durations=10
```

---

## 📁 Test Suite Structure

```
tests/
├── test_agents.py                              # Agent core functionality
├── test_agents_additional.py                   # Additional agent providers
├── test_common_utils.py                        # Utility functions
├── test_config_utils_metrics_comprehensive.py  # Configuration & metrics
├── test_integration_comprehensive.py           # End-to-end tests
├── test_metrics.py                             # Metrics recording
├── test_queue.py                               # Queue implementations
└── test_tracing.py                             # OpenTelemetry tracing
```

---

## 📖 Test File Reference

### `test_agents.py` — Core Agent Functionality

**What it covers:**
- **Circuit Breaker Pattern**: Opens after failures, closes after successes, half-open state
- **Claude Agent**: API calls, response parsing, error handling, system prompts
- **ChatGPT Agent**: API integration, token counting, temperature settings
- **Similarity Detection**: Repeated content detection, consecutive similar responses
- **Turn Management**: Max turns enforcement, proper termination
- **Security**: Input validation, content sanitization

**Key test classes:**
- `TestCircuitBreaker` — Circuit breaker state management
- `TestClaudeAgent` — Anthropic Claude integration
- `TestChatGPTAgent` — OpenAI ChatGPT integration
- `TestSimilarityDetection` — Loop prevention
- `TestAgentSecurity` — Security validations

**Coverage target**: 90%+ (Currently: ~93%)

### `test_agents_additional.py` — Additional Providers

**What it covers:**
- **Gemini Agent**: Google Generative AI integration, history formatting
- **Grok Agent**: xAI API integration, OpenAI-compatible interface
- **Perplexity Agent**: Perplexity API, online search capabilities

**Key test classes:**
- `TestGeminiAgent` — Google Gemini integration
- `TestGrokAgent` — xAI Grok integration
- `TestPerplexityAgent` — Perplexity integration

**Coverage target**: 85%+ (Currently: ~88%)

### `test_queue.py` — Queue Implementations

**What it covers:**
- **SQLite Queue**: Message storage, retrieval, metadata, atomic operations
- **Redis Queue**: Distributed queue operations, connection handling
- **Health Checks**: Queue health monitoring, error detection
- **Concurrency**: File locking, race condition prevention
- **Stress Testing**: High-volume message handling

**Key test classes:**
- `TestSQLiteQueue` — SQLite backend
- `TestRedisQueue` — Redis backend (requires Redis)
- `TestQueueStress` — Performance under load

**Coverage target**: 95%+ (Currently: ~96%)

### `test_config_utils_metrics_comprehensive.py` — Config & Metrics

**What it covers:**
- **Configuration Validation**: Pydantic validation, range checking
- **Logging Setup**: Structured logging, rotation, JSON formatting
- **API Key Masking**: Security pattern matching, log sanitization
- **Input Sanitization**: XSS prevention, SQL injection prevention
- **Metrics Server**: Prometheus endpoint, port configuration

**Key test classes:**
- `TestConfig` — Configuration validation
- `TestLogging` — Logging setup and utilities
- `TestSecurity` — Masking and sanitization
- `TestMetricsServer` — Metrics HTTP server

**Coverage target**: 90%+ (Currently: ~91%)

### `test_integration_comprehensive.py` — End-to-End Tests

**What it covers:**
- **Full Conversations**: Multi-turn agent interactions
- **Termination Conditions**: Max turns, timeouts, similarity loops
- **Concurrent Operations**: Multiple simultaneous conversations
- **Error Recovery**: API failures, retries, circuit breaker integration
- **Stress Testing**: High load scenarios

**Key test classes:**
- `TestFullConversation` — Complete conversation flows
- `TestTerminationConditions` — Stopping criteria
- `TestConcurrentConversations` — Parallel execution
- `TestStressScenarios` — Performance testing

**Coverage target**: 85%+ (Currently: ~87%)

### `test_common_utils.py` — Utility Functions

**What it covers:**
- **Similarity Calculation**: Shingle-based text comparison
- **API Key Masking**: Pattern matching for various providers
- **Content Sanitization**: Dangerous pattern removal
- **Jitter Functions**: Random backoff calculation
- **Hash Functions**: Message hashing

**Key test functions:**
- `test_simple_similarity_*` — Text similarity
- `test_mask_api_key_*` — Key masking
- `test_sanitize_content_*` — Content cleaning

**Coverage target**: 90%+ (Currently: ~92%)

### `test_metrics.py` — Metrics Collection

**What it covers:**
- **Counter Metrics**: API calls, tokens, errors
- **Histogram Metrics**: Response latency
- **Gauge Metrics**: Active conversations
- **Metric Recording**: Safe error handling

**Key test functions:**
- `test_record_call` — API call recording
- `test_record_latency` — Latency tracking
- `test_record_tokens` — Token usage
- `test_record_error` — Error counting

**Coverage target**: 85%+ (Currently: ~88%)

### `test_tracing.py` — OpenTelemetry

**What it covers:**
- **Tracer Setup**: OTLP endpoint configuration
- **Span Creation**: Distributed tracing spans
- **Error Handling**: Graceful degradation when tracing unavailable

**Key test functions:**
- `test_setup_tracing_with_endpoint` — Enabled tracing
- `test_setup_tracing_without_endpoint` — Disabled tracing
- `test_get_tracer` — Tracer retrieval

**Coverage target**: 85%+ (Currently: ~86%)

---

## 🎯 Coverage Targets & Status

| Module | Target | Current | Status |
|--------|--------|---------|--------|
| `agents/base.py` | 90% | 93% | ✅ |
| `agents/claude.py` | 90% | 94% | ✅ |
| `agents/chatgpt.py` | 90% | 93% | ✅ |
| `agents/gemini.py` | 85% | 88% | ✅ |
| `agents/grok.py` | 85% | 87% | ✅ |
| `agents/perplexity.py` | 85% | 88% | ✅ |
| `core/queue.py` | 95% | 96% | ✅ |
| `core/config.py` | 90% | 91% | ✅ |
| `core/common.py` | 90% | 92% | ✅ |
| `core/metrics.py` | 85% | 88% | ✅ |
| `core/tracing.py` | 85% | 86% | ✅ |
| **Overall** | **90%** | **91%** | ✅ |

---

## 🔧 Running Tests

### Prerequisites

```bash
# Install test dependencies
uv sync --all-extras

# Or manually install
uv pip install --system pytest pytest-asyncio pytest-cov redis
```

### Basic Test Execution

```bash
# Run all tests
uv run pytest

# Quick run (stop on first failure)
uv run pytest -q --maxfail=1 --disable-warnings

# Verbose output
uv run pytest -v

# Very verbose with print statements
uv run pytest -vv -s
```

### Coverage Reports

```bash
# Terminal report with missing lines
uv run pytest --cov=agents --cov=core --cov-report=term-missing

# Generate HTML report
uv run pytest --cov=agents --cov=core --cov-report=html

# Generate XML report (for CI/CD)
uv run pytest --cov=agents --cov=core --cov-report=xml

# Generate all reports
uv run pytest \
  --cov=agents --cov=core \
  --cov-report=term-missing \
  --cov-report=html \
  --cov-report=xml
```

### Selective Test Execution

```bash
# Run specific file
uv run pytest tests/test_agents.py

# Run specific class
uv run pytest tests/test_agents.py::TestCircuitBreaker

# Run specific test
uv run pytest tests/test_agents.py::TestCircuitBreaker::test_circuit_breaker_opens_after_failures

# Run tests matching pattern
uv run pytest -k "circuit_breaker"

# Run tests by marker (if defined)
uv run pytest -m slow
```

### Advanced Options

```bash
# Parallel execution (faster)
uv run pytest -n auto

# Show test durations
uv run pytest --durations=10

# Re-run only failed tests
uv run pytest --lf

# Run failed tests first, then all
uv run pytest --ff

# Drop into debugger on failure
uv run pytest --pdb

# Detailed failure output
uv run pytest --tb=long

# Capture output (default)
uv run pytest --capture=fd

# Don't capture output
uv run pytest --capture=no
```

---

## 📝 Writing Tests

### Test Structure (AAA Pattern)

```python
import pytest
from unittest.mock import Mock, patch

class TestFeature:
    """Test description"""

    @pytest.mark.asyncio
    async def test_feature_basic_functionality(self, mock_queue, logger):
        """Test that feature works in basic case"""
        # Arrange - Set up test data and mocks
        feature = NewFeature(queue=mock_queue, logger=logger)
        input_data = {"key": "value"}
        
        # Act - Execute the code under test
        result = await feature.process(input_data)
        
        # Assert - Verify expected outcomes
        assert result is not None
        assert result["status"] == "success"
        mock_queue.add_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_feature_error_handling(self, mock_queue, logger):
        """Test that feature handles errors correctly"""
        # Arrange
        feature = NewFeature(queue=mock_queue, logger=logger)
        mock_queue.add_message.side_effect = Exception("Database error")
        
        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            await feature.process({"key": "value"})
```

### Async Test Guidelines

```python
# ✅ CORRECT - Use @pytest.mark.asyncio decorator
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None

# ❌ WRONG - Missing decorator
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

### Mocking Best Practices

```python
# ✅ CORRECT - Mock at import location
with patch("openai.OpenAI") as mock_openai:
    mock_openai.return_value.chat.completions.create.return_value = response
    result = await agent.run()

# ❌ WRONG - Mock at definition location
with patch("agents.chatgpt.OpenAI") as mock_openai:
    # This won't work if imported before patching
    ...

# ✅ CORRECT - Mock external dependencies
@patch("anthropic.Anthropic")
async def test_claude_agent(mock_anthropic, mock_queue, logger):
    agent = ClaudeAgent(api_key="test-key", queue=mock_queue, logger=logger)
    ...

# ✅ CORRECT - Use fixtures for common mocks
@pytest.fixture
def mock_queue():
    queue = Mock(spec=QueueInterface)
    queue.add_message = Mock()
    queue.get_messages = Mock(return_value=[])
    return queue
```

### Test Coverage Guidelines

**What to test:**
- ✅ Happy path (normal operation)
- ✅ Error conditions (exceptions, invalid input)
- ✅ Edge cases (empty input, None, max values)
- ✅ Boundary values (0, 1, max)
- ✅ Integration points (API calls, database operations)

**What not to test:**
- ❌ Third-party library internals
- ❌ Language features (Python built-ins)
- ❌ Simple getters/setters without logic

**Example:**
```python
class TestMessageValidation:
    """Test message validation"""

    def test_valid_message(self):
        """Test that valid messages pass validation"""
        message = {"role": "user", "content": "Hello"}
        assert validate_message(message) is True

    def test_missing_role(self):
        """Test that messages without role fail"""
        message = {"content": "Hello"}
        with pytest.raises(ValueError, match="Missing required field: role"):
            validate_message(message)

    def test_empty_content(self):
        """Test that empty content fails"""
        message = {"role": "user", "content": ""}
        with pytest.raises(ValueError, match="Content cannot be empty"):
            validate_message(message)

    def test_max_length(self):
        """Test that content exceeding max length fails"""
        message = {"role": "user", "content": "x" * 100001}
        with pytest.raises(ValueError, match="Content exceeds maximum length"):
            validate_message(message)
```

---

## 🔄 CI/CD Integration

### GitHub Actions Workflow

The project uses GitHub Actions for continuous integration:

```yaml
# .github/workflows/ci.yml

jobs:
  fix-formatting:
    # Auto-fix formatting on main branch
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install ruff
      - run: ruff check . --fix
      - run: ruff format .

  test:
    # Run tests with coverage
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv pip install --system pytest pytest-asyncio pytest-cov redis -r requirements.txt
      - run: uv run pytest -q --maxfail=1 --disable-warnings --cov=. --cov-report=xml
      - uses: codecov/codecov-action@v4
        with:
          use_oidc: true
          files: ./coverage.xml

  codeql:
    # Security analysis
    runs-on: ubuntu-latest
    steps:
      - uses: github/codeql-action/init@v3
        with:
          languages: python
      - uses: github/codeql-action/analyze@v3
```

### Local CI Simulation

```bash
# Run the same checks as CI
./scripts/ci-local.sh

# Or manually:
ruff check . --fix
ruff format .
uv run pytest -q --maxfail=1 --disable-warnings
uv run pytest --cov=agents --cov=core --cov-report=xml
```

### Pre-commit Hooks

Install pre-commit hooks to catch issues before committing:

```bash
# Install pre-commit
uv pip install --system pre-commit

# Install hooks
uv run pre-commit install

# Run manually
uv run pre-commit run --all-files
```

**What runs on commit:**
- Ruff linting and formatting
- Mypy type checking
- Trailing whitespace removal
- YAML/JSON validation

---

## 🐛 Debugging Tests

### Common Issues

| Issue | Cause | Solution |
|-------|--------|----------|
| `ImportError` | Missing dependencies | Run `uv sync --all-extras` |
| `asyncio` event loop errors | Missing `@pytest.mark.asyncio` | Add decorator to async tests |
| Mock not called | Wrong patch location | Patch where imported, not where defined |
| Test hanging | Blocking operation | Ensure all operations are async |
| SQLite locked | Database not cleaned up | Use fixtures with proper teardown |
| Redis connection error | Redis not running | Start Redis or skip tests |

### Debug Techniques

```bash
# Drop into debugger on failure
uv run pytest --pdb

# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use built-in breakpoint()
breakpoint()

# Print statements (use -s flag)
uv run pytest -s
print(f"Debug: {variable}")

# Verbose test output
uv run pytest -vv

# Show local variables on failure
uv run pytest --showlocals

# Detailed traceback
uv run pytest --tb=long
```

### Isolating Failures

```bash
# Run only failed tests
uv run pytest --lf

# Stop on first failure
uv run pytest -x

# Run specific test that's failing
uv run pytest tests/test_agents.py::TestCircuitBreaker::test_specific_test -vv -s
```

---

## 📚 Testing Best Practices

### DO ✅

- **Write descriptive test names**: `test_circuit_breaker_opens_after_five_failures`
- **Use fixtures** for common setup/teardown
- **Mock external dependencies** (API calls, databases)
- **Test one thing per test** (focused, single assertion when possible)
- **Use arrange-act-assert pattern**
- **Add docstrings** to test classes and functions
- **Clean up resources** in teardown/fixtures
- **Use parametrize** for testing multiple inputs
- **Check coverage** before submitting PR

### DON'T ❌

- **Don't test implementation details** (test behavior, not internals)
- **Don't use sleep()** in tests (use mocks/fixtures)
- **Don't hardcode values** (use constants or config)
- **Don't skip tests** without good reason and explanation
- **Don't commit failing tests**
- **Don't test third-party code**
- **Don't forget error cases**

### Example: Parametrized Tests

```python
@pytest.mark.parametrize("api_key,expected", [
    ("sk-ant-1234567890", "[ANTHROPIC_KEY]"),
    ("sk-1234567890abcdef", "[OPENAI_KEY]"),
    ("pplx-1234567890", "[PERPLEXITY_KEY]"),
    ("AIza1234567890", "[API_KEY]"),
])
def test_mask_api_key_patterns(api_key, expected):
    """Test that various API key patterns are masked"""
    result = mask_api_key(f"Using key: {api_key}")
    assert expected in result
    assert api_key not in result
```

---

## 📊 Coverage Reports

### HTML Report

```bash
# Generate report
uv run pytest --cov=agents --cov=core --cov-report=html

# Open in browser
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

**What to look for:**
- Red lines = not covered (need tests)
- Green lines = covered
- Yellow lines = partially covered (branches)

### Terminal Report

```bash
# Show missing lines
uv run pytest --cov=agents --cov=core --cov-report=term-missing
```

**Output:**
```
agents/base.py           95%   45-47, 89-91
agents/claude.py         94%   23-25
core/queue.py            96%   67
```

### XML Report (for CI)

```bash
# Generate XML for Codecov/SonarQube
uv run pytest --cov=agents --cov=core --cov-report=xml
```

---

## 🎓 Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [Code Coverage Best Practices](https://about.codecov.io/blog/code-coverage-best-practices/)

---

<div align="center">

**Made with ❤️ by Paul Clark (@systemslibrarian)**  
**To God be the glory.**

[⬆️ Back to README](../README.md)

</div>
