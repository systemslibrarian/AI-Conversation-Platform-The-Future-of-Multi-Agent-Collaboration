<h1 align="center">🤖 AI Conversation Platform v5.0 — Enterprise Multi-Agent System</h1>

<p align="center"><em>"Because AIs shouldn't monologue — they should <strong>converse</strong>."</em></p>

<hr style="width:60%;margin:auto;border:1px solid #444;">

<p align="center">
  <!-- ✅ Unified CI + CodeQL Badge -->
  <a href="https://github.com/systemslibrarian/AI-Conversation-Platform-The-Future-of-Multi-Agent-Collaboration/actions/workflows/ci.yml">
    <img src="https://github.com/systemslibrarian/AI-Conversation-Platform-The-Future-of-Multi-Agent-Collaboration/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI & CodeQL Analysis">
  </a>

  <!-- ✅ Codecov Coverage -->
  <a href="https://app.codecov.io/gh/systemslibrarian/AI-Conversation-Platform-The-Future-of-Multi-Agent-Collaboration">
    <img src="https://codecov.io/gh/systemslibrarian/AI-Conversation-Platform-The-Future-of-Multi-Agent-Collaboration/branch/main/graph/badge.svg" alt="Code Coverage"/>
  </a>

  <!-- ✅ Linting, Typing, License -->
  <img src="https://img.shields.io/badge/lint-Ruff-3A86FF?logo=python&logoColor=white" alt="Ruff Lint">
  <img src="https://img.shields.io/badge/type--checked-mypy-blue" alt="Mypy Type Checking">
  <img src="https://img.shields.io/badge/license-MIT-yellow.svg" alt="MIT License">
  <img src="https://img.shields.io/badge/version-5.0.0-green.svg" alt="Version 5.0.0">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/docker-ready-blue?logo=docker" alt="Docker Ready">
  <img src="https://img.shields.io/badge/metrics-prometheus-orange?logo=prometheus" alt="Prometheus Metrics">
  <img src="https://img.shields.io/badge/dashboards-grafana-yellow?logo=grafana" alt="Grafana Dashboards">
</p>

---

## 🎯 What Is This?

**The AI Conversation Platform** is a production-ready, enterprise-grade system that enables **autonomous AI-to-AI conversations**. Watch different AI models debate, collaborate, and interact in real-time — completely unscripted.

### Key Features

- **🤝 Multi-Agent Orchestration** — Claude, ChatGPT, Gemini, Grok, Perplexity in dynamic conversations
- **⚡ Async-First Architecture** — Non-blocking API calls with `asyncio` and `run_in_executor`
- **🛡️ Production-Grade Reliability** — Circuit breakers, exponential backoff, similarity detection
- **🔒 Security Hardened** — Path validation, input sanitization, API key masking, optional LLM Guard
- **📊 Full Observability** — Prometheus metrics, Grafana dashboards, OpenTelemetry tracing
- **🧪 Comprehensive Testing** — 90%+ code coverage, pytest with async support
- **🐳 Container-Ready** — Docker Compose with health checks and orchestration
- **💻 Developer-Friendly** — Modern tooling (uv, Ruff, mypy), pre-commit hooks, CI/CD

---

## ⚡ Quick Start (2 minutes)

### 1️⃣ Prerequisites

| Requirement | Version | Notes |
|---|---:|---|
| Python | 3.10+ | 3.11+ recommended |
| Docker | 24+ | For full stack deployment |
| API Keys | 2+ | OpenAI, Anthropic, Gemini, xAI, or Perplexity |

### 2️⃣ Clone & Configure

```bash
# Clone repository
git clone https://github.com/systemslibrarian/ai-conversation-platform.git
cd ai-conversation-platform

# Configure API keys
cp .env.example .env
nano .env  # Add your API keys
```

**Minimum `.env` configuration:**
```dotenv
# At least TWO providers required
ANTHROPIC_API_KEY=sk-ant-xxxxx
OPENAI_API_KEY=sk-xxxxx
```

### 3️⃣ Run (Choose One)

#### Option A — Local Python (Fastest)
```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync --all-extras

# Run conversation (interactive)
uv run aic-start

# Or non-interactive
uv run aic-start --agent1 claude --agent2 chatgpt --topic "AI ethics" --turns 10 --yes
```

#### Option B — Docker Stack (Full Observability)
```bash
docker compose up --build
```

### 4️⃣ Access Interfaces

| Service | URL | Description |
|---|---|---|
| **Streamlit UI** | http://localhost:8501 | View/search conversations |
| **Metrics** | http://localhost:8000/metrics | Prometheus endpoint |
| **Prometheus** | http://localhost:9090 | Metrics explorer |
| **Grafana** | http://localhost:3000 | Dashboards (admin/admin) |

### 5️⃣ Export & Stop

**Export conversation:**
- Open Streamlit UI → Click "📥 Export to JSON"

**Stop services:**
```bash
docker compose down
```

---

## 📖 Documentation

### 🚀 Getting Started
- [📋 Installation Guide](docs/INSTALLATION_GUIDE.md) — Detailed setup instructions
- [🐳 Docker Guide](docs/DOCKER_README.md) — Container deployment
- [⚡ Quick Start](docs/docs_README.md) — Documentation hub

### 🛠️ Development
- [🧪 Testing Guide](docs/TESTING.md) — Test suite reference
- [🏗️ Architecture](docs/ARCHITECTURE.md) — System design
- [🤝 Contributing](docs/CONTRIBUTING.md) — Contribution guidelines
- [📜 Code of Conduct](docs/CODE_OF_CONDUCT.md) — Community standards

### 📊 Operations
- [📈 Monitoring](docs/MONITORING.md) — Metrics and dashboards
- [🔒 Security](docs/SECURITY.md) — Security policy
- [⬆️ Upgrade Guide](docs/UPGRADE_GUIDE.md) — v4.0 → v5.0 migration

---

## 🎮 Usage Examples

### Interactive Mode
```bash
uv run aic-start
```

**Prompts:**
1. Select first agent (claude/chatgpt/gemini/grok/perplexity)
2. Select second agent
3. Enter conversation topic
4. Set maximum turns per agent
5. Confirm and start

### CLI Mode (Automated)

**Basic conversation:**
```bash
uv run aic-start \
  --agent1 claude \
  --agent2 chatgpt \
  --topic "The nature of consciousness" \
  --turns 20 \
  --yes
```

**Custom models:**
```bash
uv run aic-start \
  --agent1 claude --model1 claude-sonnet-4-5-20250929 \
  --agent2 chatgpt --model2 gpt-4o \
  --topic "AI alignment strategies" \
  --turns 30 \
  --db ./data/alignment_discussion.db \
  --yes
```

**Available agents:** `claude`, `chatgpt`, `gemini`, `grok`, `perplexity`

### Docker Deployment

**Configure via environment:**
```dotenv
# In .env file
AGENT1=claude
AGENT2=gemini
TOPIC=Quantum computing and AI
TURNS=25
UI_PORT=8501
METRICS_PORT=8000
```

**Start stack:**
```bash
docker compose up --build
```

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────┐
│              User Interface Layer                │
│  ┌─────────────┐        ┌────────────────┐      │
│  │ CLI         │        │ Web Dashboard  │      │
│  │ (aic-start) │        │ (Streamlit)    │      │
│  └─────────────┘        └────────────────┘      │
└──────────┬────────────────────────┬──────────────┘
           │                        │
┌──────────▼────────────────────────▼──────────────┐
│         Conversation Manager (Async)             │
│  • Orchestration  • Error Handling               │
│  • Circuit Breaker  • Metrics Collection         │
└──────────┬──────────────────────────────────────┘
           │
┌──────────▼──────────────────────────────────────┐
│              Agents Layer (Async)                │
│  Claude │ ChatGPT │ Gemini │ Grok │ Perplexity  │
│  • API calls via run_in_executor                 │
│  • Rate limiting & backoff                       │
│  • Similarity detection                          │
└──────────┬──────────────────────────────────────┘
           │
┌──────────▼──────────────────────────────────────┐
│          Queue & Storage Layer                   │
│  SQLite (default) or Redis (distributed)         │
│  • Atomic operations  • Message context          │
└──────────┬──────────────────────────────────────┘
           │
┌──────────▼──────────────────────────────────────┐
│          Observability Layer                     │
│  • Prometheus (metrics at :8000/metrics)         │
│  • Grafana (dashboards at :3000)                 │
│  • OpenTelemetry (optional distributed tracing)  │
└─────────────────────────────────────────────────┘
```

---

## 🔧 Configuration

### Environment Variables

**API Keys (Required):**
```dotenv
ANTHROPIC_API_KEY=sk-ant-xxxxx
OPENAI_API_KEY=sk-xxxxx
GOOGLE_API_KEY=xxxxx
XAI_API_KEY=xxxxx
PERPLEXITY_API_KEY=pplx-xxxxx
```

**Conversation Settings:**
```dotenv
DEFAULT_MAX_TURNS=50           # Max turns per agent
TEMPERATURE=0.7                # LLM sampling temperature (0.0-2.0)
MAX_TOKENS=1024                # Max tokens per response
MAX_CONTEXT_MSGS=10            # Messages in context window
SIMILARITY_THRESHOLD=0.85      # Loop detection threshold
MAX_CONSECUTIVE_SIMILAR=2      # Turns before termination
```

**Storage & Security:**
```dotenv
DATA_DIR=data                  # Database directory
ENABLE_LLM_GUARD=true          # Prompt injection detection
MAX_MESSAGE_LENGTH=100000      # DoS prevention
```

**Monitoring:**
```dotenv
PROMETHEUS_PORT=8000           # Metrics endpoint
OTEL_EXPORTER_OTLP_ENDPOINT=   # OpenTelemetry (optional)
```

**Redis (Optional):**
```dotenv
REDIS_URL=redis://localhost:6379/0  # Distributed queue
```

See `.env.example` for complete configuration options.

---

## 📊 Monitoring & Metrics

### Available Metrics

| Metric | Type | Description |
|---------|------|-------------|
| `ai_api_calls_total` | Counter | Total API calls by provider/model/status |
| `ai_response_seconds` | Histogram | Response latency distribution |
| `ai_active_conversations` | Gauge | Currently active conversations |
| `ai_tokens_total` | Counter | Token usage by provider/model/type |
| `ai_errors_total` | Counter | Error count by provider/type |

### Access Points

- **Metrics Endpoint**: http://localhost:8000/metrics
- **Prometheus UI**: http://localhost:9090
- **Grafana Dashboards**: http://localhost:3000 (admin/admin)

### Pre-configured Dashboard

The Grafana dashboard "AI Conversation Platform" includes:
- API call rates and success rates
- Response latency percentiles (p50, p95, p99)
- Token usage trends
- Error rates and types
- Active conversation count

---

## 🧪 Development

### Setup Development Environment

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies with dev tools
uv sync --all-extras

# Install pre-commit hooks
uv run pre-commit install
```

### Code Quality

```bash
# Run tests
uv run pytest

# With coverage
uv run pytest --cov=agents --cov=core --cov-report=term-missing

# Linting
uv run ruff check .

# Auto-fix linting issues
uv run ruff check . --fix

# Format code
uv run ruff format .

# Type checking
uv run mypy .
```

### Test Coverage Targets

| Module | Target | Status |
|--------|--------|--------|
| `agents/*` | 90% | ✅ 91-94% |
| `core/queue.py` | 95% | ✅ 96% |
| `core/config.py` | 90% | ✅ 90%+ |
| `core/common.py` | 90% | ✅ 90%+ |
| `core/metrics.py` | 85% | ✅ 88% |
| `core/tracing.py` | 85% | ✅ 86% |

### Commit Convention

```
feat: add new feature
fix: correct bug
docs: update documentation
test: add new tests
refactor: restructure code
chore: maintenance tasks
```

---

## 🤝 Contributing

We welcome contributions! Please see:
- [Contributing Guide](docs/CONTRIBUTING.md) — How to contribute
- [Code of Conduct](docs/CODE_OF_CONDUCT.md) — Community standards
- [Testing Guide](docs/TESTING.md) — Writing tests
- [Architecture](docs/ARCHITECTURE.md) — System design

**Quick start:**
1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run quality checks
5. Submit pull request

---

## 🔒 Security

- **Input Validation**: Path traversal prevention, length limits
- **Output Sanitization**: XSS prevention in web UI
- **API Key Protection**: Masked in logs, never committed
- **Optional LLM Guard**: Prompt injection detection
- **Atomic Operations**: Race condition prevention

**Report vulnerabilities**: See [SECURITY.md](docs/SECURITY.md)

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

Built with:
- [Anthropic Claude](https://www.anthropic.com/) — AI conversation partner
- [OpenAI ChatGPT](https://openai.com/) — AI conversation partner
- [Google Gemini](https://deepmind.google/technologies/gemini/) — AI conversation partner
- [xAI Grok](https://x.ai/) — AI conversation partner
- [Perplexity](https://www.perplexity.ai/) — AI conversation partner
- [Streamlit](https://streamlit.io/) — Web interface
- [Prometheus](https://prometheus.io/) — Metrics collection
- [Grafana](https://grafana.com/) — Dashboard visualization

---

## 📞 Support & Links

| Resource | Link |
|----------|------|
| **GitHub Repository** | [ai-conversation-platform](https://github.com/systemslibrarian/ai-conversation-platform) |
| **Documentation** | [docs/](docs/) |
| **Issue Tracker** | [GitHub Issues](https://github.com/systemslibrarian/ai-conversation-platform/issues) |
| **Changelog** | [CHANGELOG.md](CHANGELOG.md) |

---

<div align="center">

**Made with ❤️ by Paul Clark (@systemslibrarian)**  
**To God be the glory.**

[![GitHub stars](https://img.shields.io/github/stars/systemslibrarian/ai-conversation-platform?style=social)](https://github.com/systemslibrarian/ai-conversation-platform)
[![GitHub forks](https://img.shields.io/github/forks/systemslibrarian/ai-conversation-platform?style=social)](https://github.com/systemslibrarian/ai-conversation-platform/fork)

</div>
