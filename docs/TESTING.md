# 🧪 Testing – AI Conversation Platform v5.0

A single source for **how to run tests**, **what each file covers**, **coverage targets**, and **CI integration**.
This document consolidates the former Test Reference into the main testing guide for simplicity.

---

## Quick Commands

```bash
# Run all tests
pytest

# Stop at first failure (fast)
pytest --maxfail=1 -q

# With coverage
pytest --cov=agents --cov=core --cov-report=term-missing

# Specific file / class / test
pytest tests/test_agents.py -v
pytest tests/test_agents.py::TestCircuitBreaker -v
pytest tests/test_agents.py::TestCircuitBreaker::test_circuit_breaker_opens_after_failures -v

# HTML coverage
pytest --cov=agents --cov=core --cov-report=html && open htmlcov/index.html
```
(Use `xdg-open` or `start` on Linux/Windows.)

---

## Test Suite Structure

```
tests/
├── test_agents.py
├── test_agents_additional.py
├── test_common_utils.py
├── test_metrics.py
├── test_tracing.py
├── test_config_utils_metrics_comprehensive.py
├── test_queue.py
└── test_integration_comprehensive.py
```

---

## What Each File Covers (condensed)

- **`test_integration_comprehensive.py`** – Full conversation flows, termination, concurrency, stress.  
- **`test_queue.py`** – SQLite/Redis queues, validation, health checks, stress.  
- **`test_config_utils_metrics_comprehensive.py`** – Config validation, logging, masking, sanitization, metrics server.  
- **`test_agents.py`** – Circuit breaker, Claude/ChatGPT integration, similarity, turn mgmt, security.  
- **`test_agents_additional.py`** – Gemini, Grok, Perplexity integrations.  
- **`test_common_utils.py`** – masking, similarity, sanitization helpers.  
- **`test_metrics.py`** – metrics recording smoke tests.  
- **`test_tracing.py`** – OpenTelemetry tracer setup.  

---

## Coverage Targets

| Module | Target | Typical |
|---|---:|---:|
| `agents/*` | 90% | 91–94% |
| `core/queue.py` | 95% | 96% |
| `core/config.py` | 90% | 90%+ |
| `core/common.py` | 90% | 90%+ |
| `core/metrics.py` | 85% | 88% |
| `core/tracing.py` | 85% | 86% |

---

## Running Tests (details)

**Prereqs**
```bash
# minimal tooling
pip install pytest pytest-asyncio pytest-cov
# or ensure uv/pip installs testing deps per project config
```

**Common patterns**
```python
# async test
@pytest.mark.asyncio
async def test_async(): ...

# patch where imported (e.g., openai.OpenAI)
with patch("openai.OpenAI") as mock: ...
```

**Speed & Debugging**
```bash
pytest -n auto                # parallel (requires pytest-xdist)
pytest -vv -s                 # very verbose + print() output
pytest --pdb                  # drop into debugger on failure
pytest --durations=10         # slowest tests
pytest --lf                   # only failed from last run
```

---

## CI/CD Integration (GitHub Actions)

Every push/PR runs:
1) **Auto-fix & format** (Ruff)  
2) **Tests** (fail-fast mode + coverage)  
3) **Security scanning** (CodeQL / pip-audit)  

Local simulation:
```bash
ruff check . --fix && ruff format .
pytest -q --maxfail=1 --disable-warnings
pytest --cov=agents --cov=core --cov-report=term-missing
```

---

## Troubleshooting (highlights)

- **ImportError / missing deps** → install test deps (pytest, pytest-asyncio, pytest-cov).  
- **Asyncio event loop issues** → ensure `@pytest.mark.asyncio`.  
- **Mock not called** → patch at import source (e.g., `openai.OpenAI`).  
- **SQLite locked** → clean up DB + lockfile in fixtures.  

---

## Writing New Tests (checklist)

- Descriptive names & docstrings  
- AAA pattern (Arrange/Act/Assert)  
- Fixtures for common setup  
- Mock external APIs  
- Cover happy path + errors + edge cases  
- Maintain coverage thresholds
