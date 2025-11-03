# 📚 AI Conversation Platform v5.0 — Documentation Hub

Welcome to the **AI Conversation Platform v5.0** documentation center — your complete guide to setup, configuration, development, and deployment.

---

## 🧭 Quick Start Summary

> Get running in under 2 minutes — ideal for first-time users.

### 1️⃣ Prerequisites
```bash
✓ Python 3.10+
✓ Docker 24+ (optional for full stack)
✓ At least one AI provider API key (OpenAI, Anthropic, etc.)
```

### 2️⃣ Clone & Setup
```bash
git clone https://github.com/systemslibrarian/ai-conversation-platform.git
cd ai-conversation-platform
cp .env.example .env
nano .env  # Add API keys
```

### 3️⃣ Launch (Pick One)
**Option A — Local Run**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync --all-extras
uv run aic-start --agent1 claude --agent2 chatgpt --topic "AI ethics" --yes
```

**Option B — Docker Stack**
```bash
docker compose up --build
```

### 4️⃣ Access Interfaces
| Service | URL | Description |
|----------|-----|-------------|
| Web UI | http://localhost:8501 | Streamlit dashboard |
| Prometheus | http://localhost:9090 | Metrics explorer |
| Grafana | http://localhost:3000 | Dashboard visualization (admin/admin) |

➡️ See full guides: [⚡ QUICK_START.md](../QUICK_START.md) · [🐳 DOCKER_README.md](../DOCKER_README.md)

---

## 📖 Documentation Overview

### 🏁 Getting Started
- [🚀 README](../README.md) — Project overview
- [⚡ QUICK_START.md](QUICK_START.md) — Fastest setup guide
- [🐳 DOCKER_README.md](DOCKER_README.md) — Container deployment
- [🔧 Installation Guide](#installation) — Detailed setup instructions

### 📘 Core Documentation
- [📋 CHANGELOG](CHANGELOG.md) — Version history and release notes
- [📊 MONITORING](MONITORING.md) — Prometheus + Grafana setup
- [🔄 UPGRADE_GUIDE](UPGRADE_GUIDE.md) — Migration from v4 → v5
- [📝 v5_UPGRADE_NOTES](v5_UPGRADE_NOTES.md) — Summary of improvements

### 👩‍💻 Development & Governance
- [🤝 CONTRIBUTING](../CONTRIBUTING.md) — Contribution guidelines
- [📜 CODE_OF_CONDUCT](../CODE_OF_CONDUCT.md) — Community standards
- [🔒 SECURITY](../SECURITY.md) — Security policy
- [⚖️ LICENSE](../LICENSE) — MIT license

---

## ⚡ Quick Start Guide (Expanded)

Follow the [QUICK_START.md](../QUICK_START.md) file for the full workflow.

```bash
# Install uv (faster dependency manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies
uv sync --all-extras

# Run first conversation
uv run aic-start --agent1 claude --agent2 chatgpt --topic "AI safety" --turns 10 --yes
```

**Want full-stack observability?** → Jump to the [Docker Deployment Guide](../DOCKER_README.md)

---

## 🐳 Docker Deployment Summary

### 1️⃣ Start Everything
```bash
docker compose up --build
```

### 2️⃣ Access Services
| Service | URL | Description |
|----------|-----|-------------|
| Streamlit UI | http://localhost:8501 | Secure web dashboard |
| Prometheus | http://localhost:9090 | Metrics monitoring |
| Grafana | http://localhost:3000 | Dashboards (admin/admin) |

### 3️⃣ Stop & Clean Up
```bash
docker compose down
```

### 4️⃣ Optional Enhancements
- Add Redis URL for distributed queueing
- Configure OTEL tracing for observability
- Enable TLS and external alerting

See [DOCKER_README.md](../DOCKER_README.md) for full details.

---

## 🧠 Architecture Overview

```
┌────────────────────────────────────────────────────┐
│                    User Interface                  │
│  ┌─────────────┐        ┌────────────────┐         │
│  │ CLI (aic-start) │    │ Web Dashboard │         │
│  └─────────────┘        └────────────────┘         │
└──────────┬───────────────────────┬────────────────┘
           │                       │
┌──────────▼───────────────────────▼───────────┐
│             Conversation Manager             │
│  - Async orchestration                       │
│  - Error handling, metrics, logging          │
└──────────┬───────────────────────────────────┘
           │
┌──────────▼───────────────────────────────────┐
│                 Agents Layer                 │
│  Claude / ChatGPT / Gemini / Grok / Perplexity │
│  - Async API calls, rate limiting, similarity │
│  - Circuit breaker & retry policy            │
└──────────┬───────────────────────────────────┘
           │
┌──────────▼───────────────────────────────────┐
│             Queue & Storage Layer             │
│  - SQLite or Redis backend                    │
│  - Atomic operations, message context         │
└──────────┬───────────────────────────────────┘
           │
┌──────────▼───────────────────────────────────┐
│            Observability Layer                │
│  - Prometheus metrics                         │
│  - Grafana dashboards                         │
│  - OpenTelemetry tracing                      │
└───────────────────────────────────────────────┘
```

---

## 🧩 Developer Essentials

### Local Development
```bash
uv sync --all-extras
uv run pytest
uv run ruff check .
uv run mypy .
```

### Code Style
- Follows PEP 8 (line length ≤ 100)
- Use **Ruff** for linting & formatting
- Use **Mypy** for type checks
- All public APIs require docstrings

### Commit Convention
```
feat: add new feature
fix: correct bug
docs: update documentation
test: add new tests
refactor: restructure code
```

---

## 📊 Monitoring Overview

Metrics, dashboards, and alerts are preconfigured.

| Metric | Type | Description |
|---------|------|-------------|
| `ai_api_calls_total` | Counter | Total API calls made |
| `ai_response_seconds` | Histogram | Response latency (seconds) |
| `ai_active_conversations` | Gauge | Active concurrent conversations |
| `ai_tokens_total` | Counter | Token usage count |
| `ai_errors_total` | Counter | Error count per provider |

Access via:
- **Prometheus** → http://localhost:9090
- **Grafana** → http://localhost:3000 (Dashboard: “AI Conversation Platform”)

---

## 🔒 Security Practices

- Environment keys stored in `.env` (never commit)
- Path validation + HTML sanitization in Streamlit UI
- LLM Guard integration for prompt injection prevention
- HTTPS recommended for Redis + Prometheus

---

## 🧪 Testing Suite

```bash
uv run pytest --cov
uv run pytest tests/test_agents.py -v
uv run pytest tests/test_queue.py -v
```

Maintains >90% test coverage.

---

## 🧭 Support & Links

| Resource | Description |
|-----------|-------------|
| [GitHub Repository](https://github.com/systemslibrarian/ai-conversation-platform) | Source code |
| [CHANGELOG](CHANGELOG.md) | Release notes |
| [UPGRADE_GUIDE](UPGRADE_GUIDE.md) | Migration from v4 |
| [MONITORING.md](MONITORING.md) | Metrics + dashboards |
| [QUICK_START.md](../QUICK_START.md) | New user guide |
| [DOCKER_README.md](../DOCKER_README.md) | Full container deployment |

---

<div align="center">

**Made with ❤️ by Paul Clark (@systemslibrarian)**  
**To God be the glory.**

[⬆ Back to Top](#-ai-conversation-platform-v50--documentation-hub)

</div>
