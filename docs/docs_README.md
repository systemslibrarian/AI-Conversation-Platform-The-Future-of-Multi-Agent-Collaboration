# 📚 AI Conversation Platform Documentation

Welcome to the **AI Conversation Platform v5.0** documentation hub. This directory contains comprehensive guides, references, and technical documentation.

---

## 📖 Quick Navigation

### Getting Started
- [🚀 Main README](../README.md) - Project overview and quick start
- [⚡ Quick Start Guide](#quick-start-guide) - Get running in 5 minutes
- [🔧 Installation Guide](#installation) - Detailed setup instructions

### Core Documentation
- [📋 CHANGELOG](CHANGELOG.md) - Version history and release notes
- [📊 MONITORING](MONITORING.md) - Observability setup (Prometheus + Grafana)
- [🔄 UPGRADE_GUIDE](UPGRADE_GUIDE.md) - Migration from v4.0 to v5.0
- [📝 v5 UPGRADE NOTES](v5_UPGRADE_NOTES.md) - Technical changes (8.5→10/10)

### Additional Resources
- [🐳 Docker Guide](DOCKER_README.md) - Container deployment
- [🔒 Security Policy](../SECURITY.md) - Vulnerability reporting
- [🤝 Contributing](../CONTRIBUTING.md) - How to contribute
- [📜 Code of Conduct](../CODE_OF_CONDUCT.md) - Community guidelines
- [⚖️ License](../LICENSE) - MIT License details

---

## 🎯 Documentation by Role

### For Users
**I want to run AI-to-AI conversations**

1. Start with [Main README](../README.md) for installation
2. Follow the [Quick Start Guide](#quick-start-guide) below
3. Explore [Usage Examples](#usage-examples)
4. Check [Troubleshooting](#troubleshooting) if needed

### For Developers
**I want to contribute or extend the platform**

1. Read [Contributing Guidelines](../CONTRIBUTING.md)
2. Review [Architecture Overview](#architecture-overview)
3. Study [API Documentation](#api-documentation)
4. Follow [Development Guide](#development-guide)
5. Run [Tests](#testing) before submitting PRs

### For DevOps
**I want to deploy and monitor the platform**

1. Review [Docker Guide](DOCKER_README.md)
2. Configure [Monitoring](MONITORING.md)
3. Implement [Security Best Practices](#security)
4. Set up [CI/CD Pipelines](#cicd)

### For Researchers
**I want to study multi-agent interactions**

1. Understand [Agent Architecture](#agent-architecture)
2. Learn about [Conversation Patterns](#conversation-patterns)
3. Access [Metrics and Logs](#metrics-and-logs)
4. Review [Research Use Cases](#research-use-cases)

---

## ⚡ Quick Start Guide

### Prerequisites
```bash
# Required
✓ Python 3.10+
✓ One or more AI provider API keys

# Optional
✓ Docker & Docker Compose (for containerized deployment)
✓ Redis (for distributed queue)
```

### Installation (2 minutes)
```bash
# Install uv (faster than pip)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone repository
git clone https://github.com/systemslibrarian/ai-conversation-platform.git
cd ai-conversation-platform

# Install dependencies
uv sync --all-extras

# Configure API keys
cp .env.example .env
nano .env  # Add your API keys
```

### Run Your First Conversation (30 seconds)
```bash
# Interactive mode
uv run aic-start

# Or quick start with CLI
uv run aic-start --agent1 claude --agent2 chatgpt --topic "AI safety" --yes
```

### View in Web Dashboard
```bash
# Start Streamlit UI
uv run streamlit run web/app.py

# Open http://localhost:8501 in browser
```

---

## 📖 Detailed Guides

### Installation

#### Option 1: Local Installation (Recommended for Development)
```bash
# Using uv (10x faster)
uv sync --all-extras

# Or using pip
pip install -e ".[dev]"
```

#### Option 2: Docker Installation (Recommended for Production)
```bash
# Start full stack
docker compose up --build

# Access:
# - Web UI: http://localhost:8501
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000
```

See [DOCKER_README.md](DOCKER_README.md) for advanced Docker configuration.

### Configuration

#### Environment Variables
```bash
# AI Provider Keys (at least 2 required)
ANTHROPIC_API_KEY=sk-ant-xxxxx    # Claude
OPENAI_API_KEY=sk-xxxxx           # ChatGPT
GOOGLE_API_KEY=xxxxx              # Gemini
XAI_API_KEY=xxxxx                 # Grok
PERPLEXITY_API_KEY=pplx-xxxxx     # Perplexity

# Conversation Settings
DEFAULT_MAX_TURNS=50              # Maximum conversation turns
TEMPERATURE=0.7                   # LLM sampling temperature (0.0-2.0)
MAX_TOKENS=1024                   # Maximum tokens per response
MAX_CONTEXT_MSGS=10               # Context messages to include

# Similarity Detection
SIMILARITY_THRESHOLD=0.85         # Loop detection threshold (0.0-1.0)
MAX_CONSECUTIVE_SIMILAR=2         # Similar responses before termination

# Queue Backend
REDIS_URL=                        # Empty = SQLite, or redis://localhost:6379/0

# Observability
PROMETHEUS_PORT=8000              # Metrics endpoint port
OTEL_EXPORTER_OTLP_ENDPOINT=      # OpenTelemetry endpoint (optional)

# Security
ENABLE_LLM_GUARD=true            # Enable prompt injection detection
MAX_MESSAGE_LENGTH=100000         # Maximum message length
DATA_DIR=data                     # Data directory for conversations
```

#### Model Selection
Each agent supports multiple models. Default models:

| Provider | Default Model | Alternatives |
|----------|--------------|-------------|
| Claude | claude-sonnet-4-5-20250929 | claude-opus-4-1, claude-3-5-sonnet |
| ChatGPT | gpt-4o | gpt-4-turbo, gpt-3.5-turbo |
| Gemini | gemini-1.5-pro | gemini-1.5-flash |
| Grok | grok-beta | grok-2 |
| Perplexity | llama-3.1-sonar-large-128k-online | llama-3.1-sonar-small |

---

## 📊 Usage Examples

### CLI Examples

#### Basic Conversation
```bash
uv run aic-start --agent1 claude --agent2 chatgpt --yes
```

#### Custom Topic and Duration
```bash
uv run aic-start \
  --agent1 claude \
  --agent2 gemini \
  --topic "The ethics of artificial general intelligence" \
  --turns 20 \
  --yes
```

#### Specific Models
```bash
uv run aic-start \
  --agent1 claude \
  --model1 claude-opus-4-1 \
  --agent2 chatgpt \
  --model2 gpt-4-turbo \
  --topic "Quantum computing applications" \
  --turns 15 \
  --yes
```

#### Custom Database
```bash
uv run aic-start \
  --agent1 grok \
  --agent2 perplexity \
  --topic "Mars colonization" \
  --db ./data/mars_debate.db \
  --yes
```

### Python API Examples

#### Simple Conversation
```python
import asyncio
from agents import create_agent
from core.queue import create_queue
from core.common import setup_logging
from core.config import config

async def run_conversation():
    logger = setup_logging("main", config.DEFAULT_LOG_DIR)
    queue = create_queue("conversation.db", logger, use_redis=False)
    
    # Create agents
    agent1 = create_agent(
        agent_type="claude",
        queue=queue,
        logger=logger,
        model="claude-sonnet-4-5-20250929",
        topic="AI safety",
        timeout=30
    )
    
    agent2 = create_agent(
        agent_type="chatgpt",
        queue=queue,
        logger=logger,
        model="gpt-4o",
        topic="AI safety",
        timeout=30
    )
    
    # Run conversation
    await asyncio.gather(
        agent1.run(max_turns=10, partner_name="ChatGPT"),
        agent2.run(max_turns=10, partner_name="Claude")
    )

asyncio.run(run_conversation())
```

#### Custom Agent Configuration
```python
from agents.base import BaseAgent
from typing import List, Dict, Tuple

class CustomAgent(BaseAgent):
    PROVIDER_NAME = "CustomAI"
    DEFAULT_MODEL = "custom-model-v1"
    
    async def _call_api(self, messages: List[Dict]) -> Tuple[str, int]:
        # Your custom API implementation
        response = await your_api_call(messages)
        return response.text, response.tokens

# Register and use
from agents import _AGENT_REGISTRY
_AGENT_REGISTRY["custom"] = {
    "class": CustomAgent,
    "env_key": "CUSTOM_API_KEY",
    "default_model": "custom-model-v1",
    "models": ["custom-model-v1", "custom-model-v2"]
}
```

---

## 🏗️ Architecture Overview

### System Components

```
┌──────────────────────────────────────────────────────┐
│                  User Interface                       │
│  ┌────────────────┐         ┌────────────────┐      │
│  │   CLI Tool     │         │  Web Dashboard │      │
│  │  (aic-start)   │         │  (Streamlit)   │      │
│  └────────┬───────┘         └────────┬───────┘      │
└───────────┼──────────────────────────┼──────────────┘
            │                          │
            └──────────┬───────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│              Conversation Manager                    │
│  • Async orchestration                              │
│  • Turn management                                  │
│  • Termination detection                            │
│  • Error handling                                   │
└──────────┬────────────────────────┬─────────────────┘
           │                        │
┌──────────▼──────────┐  ┌─────────▼──────────┐
│     Agent 1         │  │     Agent 2         │
│  ┌──────────────┐   │  │  ┌──────────────┐  │
│  │ Circuit      │   │  │  │ Circuit      │  │
│  │ Breaker      │   │  │  │ Breaker      │  │
│  └──────────────┘   │  │  └──────────────┘  │
│  ┌──────────────┐   │  │  ┌──────────────┐  │
│  │ Rate Limiter │   │  │  │ Rate Limiter │  │
│  └──────────────┘   │  │  └──────────────┘  │
│  ┌──────────────┐   │  │  ┌──────────────┐  │
│  │ Similarity   │   │  │  │ Similarity   │  │
│  │ Detector     │   │  │  │ Detector     │  │
│  └──────────────┘   │  │  └──────────────┘  │
└──────────┬──────────┘  └─────────┬──────────┘
           │                       │
           └───────┬───────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│               Message Queue                          │
│  ┌────────────────────────────────────────────┐    │
│  │  Backend: SQLite (file) or Redis (network) │    │
│  └────────────────────────────────────────────┘    │
│  • Atomic operations                               │
│  • File locking (SQLite)                           │
│  • Context retrieval                               │
│  • Metadata tracking                               │
└──────────┬──────────────────────────────────────────┘
           │
┌──────────▼──────────────────────────────────────────┐
│              Observability Layer                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
│  │  Prometheus  │  │  Grafana     │  │OpenTelem │ │
│  │  (Metrics)   │  │ (Dashboard)  │  │(Tracing) │ │
│  └──────────────┘  └──────────────┘  └──────────┘ │
└─────────────────────────────────────────────────────┘
```

### Agent Architecture

Each agent implements:

1. **Base Agent Class** (`agents/base.py`)
   - Circuit breaker for fault tolerance
   - Exponential backoff with jitter
   - Similarity detection for loop prevention
   - Termination signal detection
   - Metrics collection
   - Structured logging

2. **Provider Implementation** (e.g., `agents/claude.py`)
   - API client initialization
   - Message formatting
   - Token counting
   - Error handling
   - Async API calls

3. **Message Queue Interface** (`core/queue.py`)
   - SQLite: File-based with locking
   - Redis: Distributed queue
   - Atomic operations
   - Context management

### Data Flow

```
1. User initiates conversation via CLI or Web UI
   ↓
2. Conversation Manager creates two agent instances
   ↓
3. Agents run concurrently in async loop:
   a. Check if should respond (turn management)
   b. Retrieve conversation context from queue
   c. Call AI provider API (with retry logic)
   d. Detect similarity & termination signals
   e. Add response to queue
   f. Record metrics
   ↓
4. Loop continues until:
   - Max turns reached
   - Termination signal detected
   - Circuit breaker opens
   - User interruption
   ↓
5. Conversation stored in database
6. Metrics exported to Prometheus
7. User can view via Web UI
```

---

## 🔍 API Documentation

### Agent API

#### Creating an Agent
```python
from agents import create_agent

agent = create_agent(
    agent_type="claude",      # Provider: claude, chatgpt, gemini, grok, perplexity
    queue=queue,              # QueueInterface instance
    logger=logger,            # logging.Logger instance
    model="model-name",       # Optional: override default model
    topic="conversation topic", # Optional: conversation context
    timeout=30,               # Optional: timeout in minutes
    api_key="sk-xxx"          # Optional: explicit API key
)
```

#### Running an Agent
```python
await agent.run(
    max_turns=50,             # Maximum conversation turns
    partner_name="ChatGPT"    # Partner agent display name
)
```

#### Agent Methods
```python
# Check if agent should respond
should_respond = await agent.should_respond(partner_name)

# Generate response
response = await agent.generate_response(context, turn_number)

# Check circuit breaker state
is_open = agent.circuit_breaker.is_open()

# Record success/failure
agent.circuit_breaker.record_success()
agent.circuit_breaker.record_failure()
```

### Queue API

#### Creating a Queue
```python
from core.queue import create_queue

# SQLite (file-based)
queue = create_queue("conversation.db", logger, use_redis=False)

# Redis (distributed)
queue = create_queue("redis://localhost:6379/0", logger, use_redis=True)
```

#### Queue Operations
```python
# Add message
message = await queue.add_message(
    sender="Claude",
    content="Hello, world!",
    metadata={"tokens": 10, "model": "claude-sonnet-4-5-20250929"}
)

# Get conversation context
context = await queue.get_context(max_messages=10)

# Check last sender
last_sender = await queue.get_last_sender()

# Mark conversation terminated
await queue.mark_terminated(reason="max_turns_reached")

# Check if terminated
is_terminated = await queue.is_terminated()

# Get termination reason
reason = await queue.get_termination_reason()

# Health check
health = await queue.health_check()
```

### Metrics API

```python
from core.metrics import (
    record_call,
    record_latency,
    record_tokens,
    record_error,
    increment_conversations,
    decrement_conversations
)

# Record API call
record_call(provider="Claude", model="claude-sonnet-4-5-20250929", status="success")

# Record latency
record_latency(provider="ChatGPT", model="gpt-4o", seconds=1.5)

# Record token usage
record_tokens(provider="Gemini", model="gemini-1.5-pro", input_tokens=100, output_tokens=150)

# Record error
record_error(provider="Grok", error_type="rate_limit")

# Track active conversations
increment_conversations()
decrement_conversations()
```

---

## 🧪 Testing

### Running Tests
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov --cov-report=html

# Run specific test file
uv run pytest tests/test_agents.py -v

# Run specific test
uv run pytest tests/test_agents.py::TestCircuitBreaker -v

# Run with markers
uv run pytest -m "not slow"
```

### Test Structure
```
tests/
├── test_agents.py        # Agent unit tests
│   ├── TestCircuitBreaker
│   ├── TestChatGPTAgent
│   ├── TestClaudeAgent
│   ├── TestAgentFactory
│   ├── TestAgentBehavior
│   └── TestAgentSecurity
└── test_queue.py         # Queue integration tests
    ├── test_queue_initialization
    ├── test_add_message
    ├── test_get_context
    ├── test_termination
    ├── test_get_last_sender
    ├── test_concurrent_writes
    └── test_health_check
```

### Writing Tests
```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.mark.asyncio
async def test_agent_response(mock_queue, logger):
    """Test agent generates valid response"""
    agent = create_agent("claude", mock_queue, logger)
    
    # Mock API response
    with patch.object(agent.client.messages, "create") as mock_create:
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Test response")]
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 15
        mock_create.return_value = mock_response
        
        # Test
        content, tokens = await agent._call_api([{"role": "user", "content": "Hi"}])
        
        assert content == "Test response"
        assert tokens == 25
```

---

## 🔧 Development Guide

### Setting Up Development Environment
```bash
# Clone and install
git clone https://github.com/systemslibrarian/ai-conversation-platform.git
cd ai-conversation-platform
uv sync --all-extras

# Install pre-commit hooks
uv run pre-commit install

# Verify setup
uv run pytest
uv run ruff check .
uv run mypy .
```

### Development Workflow
```bash
# 1. Create feature branch
git checkout -b feature/my-feature

# 2. Make changes
# ... edit files ...

# 3. Run quality checks (automatically runs on commit)
uv run pre-commit run --all-files

# 4. Run tests
uv run pytest --cov

# 5. Commit with conventional commit message
git commit -m "feat: add amazing feature"

# 6. Push and create PR
git push origin feature/my-feature
```

### Code Style Guidelines

#### Python Style
- Follow PEP 8
- Use ruff for formatting (100 char line length)
- Use type hints everywhere
- Write docstrings for public APIs

#### Commit Messages
Use [Conventional Commits](https://www.conventionalcommits.org/):
```
feat: add new feature
fix: resolve bug
docs: update documentation
test: add tests
chore: update dependencies
refactor: restructure code
perf: improve performance
```

#### Testing Guidelines
- Write tests for all new features
- Maintain 90%+ coverage
- Use descriptive test names
- Mock external dependencies
- Test edge cases

---

## 📊 Monitoring Guide

See [MONITORING.md](MONITORING.md) for complete observability setup.

### Quick Setup
```bash
# Start full monitoring stack
docker compose up -d prometheus grafana

# Access dashboards
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000 (admin/admin)
```

### Key Metrics

| Metric | Description | Type |
|--------|-------------|------|
| `ai_api_calls_total` | Total API calls | Counter |
| `ai_response_seconds` | Response latency | Histogram |
| `ai_active_conversations` | Active conversations | Gauge |
| `ai_tokens_total` | Token usage | Counter |
| `ai_errors_total` | Error count | Counter |

### Alerts

Configure alerting rules in `monitoring/prometheus/alerts.yml`:

```yaml
groups:
  - name: ai_platform_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(ai_errors_total[5m]) > 0.1
        annotations:
          summary: "High error rate detected"
      
      - alert: SlowResponses
        expr: histogram_quantile(0.95, rate(ai_response_seconds_bucket[5m])) > 10
        annotations:
          summary: "95th percentile latency > 10s"
```

---

## 🔒 Security Best Practices

### API Key Management
```bash
# Never commit API keys
echo ".env" >> .gitignore

# Use environment variables
export ANTHROPIC_API_KEY=sk-ant-xxxxx

# Or use .env file (never commit!)
cp .env.example .env
nano .env
```

### Input Validation
```python
# The platform automatically:
# - Validates file paths (no path traversal)
# - Sanitizes HTML input (XSS prevention)
# - Limits message length (DoS prevention)
# - Masks API keys in logs
```

### LLM Guard Integration
```bash
# Enable prompt injection detection
export ENABLE_LLM_GUARD=true

# Install dependencies
uv add llm-guard
```

### Network Security
```bash
# Use HTTPS for Redis
export REDIS_URL=rediss://localhost:6379/0

# Enable TLS for monitoring
# See monitoring/prometheus/prometheus.yml
```

---

## 🐛 Troubleshooting

### Common Issues and Solutions

#### Import Errors
```bash
# Problem: ModuleNotFoundError: No module named 'agents'
# Solution: Install in editable mode
uv sync
# or
pip install -e .
```

#### Database Lock
```bash
# Problem: sqlite3.OperationalError: database is locked
# Solution 1: Use Redis instead
export REDIS_URL=redis://localhost:6379/0

# Solution 2: Increase timeout in queue.py
# Already handled with filelock
```

#### API Rate Limits
```bash
# Problem: Rate limit exceeded
# Solution: Platform has automatic backoff
# Configure in .env:
INITIAL_BACKOFF=2.0
MAX_BACKOFF=120.0
BACKOFF_MULTIPLIER=2.0
```

#### Memory Issues
```bash
# Problem: High memory usage
# Solution: Limit context messages
export MAX_CONTEXT_MSGS=5
export MAX_MESSAGE_LENGTH=50000
```

#### Port Conflicts
```bash
# Problem: Port 8501 already in use
# Solution: Change ports
streamlit run web/app.py --server.port 8502
export PROMETHEUS_PORT=8001
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# View logs
tail -f logs/*.jsonl

# Or use Docker logs
docker compose logs -f conversation
```

### Getting Help

1. **Check Documentation**: Search this docs directory
2. **GitHub Issues**: [Search existing issues](https://github.com/systemslibrarian/ai-conversation-platform/issues)
3. **Discussions**: [Ask questions](https://github.com/systemslibrarian/ai-conversation-platform/discussions)
4. **Discord/Slack**: (if available)

---

## 🚀 Production Deployment

### Deployment Checklist

#### Pre-Deployment
- [ ] Run all tests: `uv run pytest --cov`
- [ ] Security scan: Review SECURITY.md
- [ ] Update configuration: Review .env
- [ ] Backup existing data
- [ ] Test in staging environment

#### Docker Deployment
```bash
# Build production image
docker build -t ai-platform:v5.0.0 .

# Run with docker-compose
docker compose -f docker-compose.prod.yml up -d

# Check health
docker compose ps
curl http://localhost:8000/metrics
```

#### Kubernetes Deployment
```yaml
# Coming soon: k8s/deployment.yaml
# See roadmap for Kubernetes manifests
```

#### Environment Variables (Production)
```bash
# Security
ENABLE_LLM_GUARD=true
MAX_MESSAGE_LENGTH=100000

# Performance
USE_REDIS=true
REDIS_URL=redis://redis-cluster:6379/0

# Monitoring
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4318
PROMETHEUS_PORT=8000

# Scaling
DEFAULT_TIMEOUT_MINUTES=60
MAX_CONTEXT_MSGS=10
```

#### Post-Deployment
- [ ] Verify health checks
- [ ] Monitor metrics in Grafana
- [ ] Test basic functionality
- [ ] Set up alerting
- [ ] Document any issues

---

## 📖 Additional Resources

### External Documentation
- [Anthropic Claude API](https://docs.anthropic.com/)
- [OpenAI API](https://platform.openai.com/docs)
- [Google Gemini API](https://ai.google.dev/docs)
- [X.AI Grok API](https://docs.x.ai/)
- [Perplexity API](https://docs.perplexity.ai/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Streamlit Documentation](https://docs.streamlit.io/)

### Community Resources
- [GitHub Repository](https://github.com/systemslibrarian/ai-conversation-platform)
- [Issue Tracker](https://github.com/systemslibrarian/ai-conversation-platform/issues)
- [Discussions](https://github.com/systemslibrarian/ai-conversation-platform/discussions)

### Learning Resources
- [Multi-Agent Systems](https://en.wikipedia.org/wiki/Multi-agent_system)
- [Async Programming in Python](https://docs.python.org/3/library/asyncio.html)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)

---

## 🗺️ Documentation Roadmap

### Planned Documentation

- [ ] **Architecture Deep Dive** - Detailed system design
- [ ] **API Reference** - Complete API documentation
- [ ] **Performance Tuning Guide** - Optimization techniques
- [ ] **Kubernetes Guide** - K8s deployment manifests
- [ ] **Video Tutorials** - Step-by-step guides
- [ ] **Case Studies** - Real-world usage examples
- [ ] **Research Papers** - Academic publications

---

## 📞 Contact & Support

- **Issues**: [GitHub Issues](https://github.com/systemslibrarian/ai-conversation-platform/issues)
- **Discussions**: [GitHub Discussions](https://github.com/systemslibrarian/ai-conversation-platform/discussions)
- **Email**: See [CONTRIBUTING.md](../CONTRIBUTING.md)
- **Security**: See [SECURITY.md](../SECURITY.md)

---

## 📝 Document Versions

| Version | Date | Changes |
|---------|------|---------|
| 5.0.0 | 2025-11-02 | Initial v5.0 documentation |

---

<div align="center">

**To God be the glory**

Made with ❤️ by Paul Clark (@systemslibrarian) and AI

[⬆ Back to Top](#-ai-conversation-platform-documentation)

</div>
