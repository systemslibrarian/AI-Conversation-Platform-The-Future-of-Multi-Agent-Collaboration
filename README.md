<h1 align="center">🤖 AI Conversation Platform v5.0 — Enterprise Multi-Agent System</h1>

<p align="center"><em>"Because AIs shouldn't monologue — they should <strong>converse</strong>."</em></p>

<hr style="width:60%;margin:auto;border:1px solid #444;">

<p align="center">
  <!-- 🧪 CI + Security -->
  <a href="https://github.com/systemslibrarian/AI-Conversation-Platform-The-Future-of-Multi-Agent-Collaboration/actions/workflows/ci.yml">
    <img src="https://github.com/systemslibrarian/AI-Conversation-Platform-The-Future-of-Multi-Agent-Collaboration/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI Status">
  </a>
  <a href="https://github.com/systemslibrarian/AI-Conversation-Platform-The-Future-of-Multi-Agent-Collaboration/actions/workflows/codeql.yml">
    <img src="https://github.com/systemslibrarian/AI-Conversation-Platform-The-Future-of-Multi-Agent-Collaboration/actions/workflows/codeql.yml/badge.svg" alt="CodeQL Security Scan">
  </a>

  <!-- 📊 Coverage -->
  <a href="https://app.codecov.io/gh/systemslibrarian/AI-Conversation-Platform-The-Future-of-Multi-Agent-Collaboration">
    <img src="https://codecov.io/gh/systemslibrarian/AI-Conversation-Platform-The-Future-of-Multi-Agent-Collaboration/branch/main/graph/badge.svg?token=YOUR_CODECOV_TOKEN" alt="Code Coverage">
  </a>

  <!-- 🧹 Linting + Typing -->
  <img src="https://img.shields.io/badge/Lint-Ruff-46A9FC?logo=ruff&logoColor=white" alt="Ruff Linting">
  <img src="https://img.shields.io/badge/Type%20Check-Mypy%20(strict)-3776AB?logo=python&logoColor=white" alt="Mypy Type Checking">

  <!-- ⚖️ License + Version -->
  <img src="https://img.shields.io/badge/License-MIT-green.svg?logo=open-source-initiative&logoColor=white" alt="MIT License">
  <img src="https://img.shields.io/badge/Version-5.0.0-blue.svg?logo=semantic-release&logoColor=white" alt="Version 5.0.0">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white" alt="Docker Ready">
  <img src="https://img.shields.io/badge/Metrics-Prometheus-E6522C?logo=prometheus&logoColor=white" alt="Prometheus Metrics">
  <img src="https://img.shields.io/badge/Dashboards-Grafana-F46800?logo=grafana&logoColor=white" alt="Grafana Dashboards">
</p>

---

## 🎯 What Is This?

**The AI Conversation Platform** is a production-ready, enterprise-grade system that enables **autonomous AI-to-AI conversations**. Watch different AI models debate, collaborate, and interact in real-time — completely unscripted.

## ⚡ Quick Start (2 minutes)

### 1) Prerequisites
| Requirement | Version | Notes |
|---|---:|---|
| Python | 3.10+ | Local runs |
| Docker | 24+ | Full stack |
| API Keys | 1+ | OpenAI, Anthropic, Gemini, etc. |

### 2) Clone
```bash
git clone https://github.com/systemslibrarian/ai-conversation-platform.git
cd ai-conversation-platform
```

### 3) Configure API keys
```bash
cp .env.example .env
nano .env
```
Add at least two providers:
```dotenv
OPENAI_API_KEY=sk-xxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxx
GOOGLE_API_KEY=xxxxx
```

### 4) Run

**Option A — Local (Python + uv)**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync --all-extras
uv run aic-start --agent1 claude --agent2 chatgpt --topic "AI ethics" --turns 10 --yes
```

**Option B — Docker (Full stack)**
```bash
docker compose up --build
```

### 5) Access services
| Service | URL | Description |
|---|---|---|
| Streamlit UI | http://localhost:8501 | View/search conversations |
| Prometheus | http://localhost:9090 | Metrics |
| Grafana | http://localhost:3000 | Dashboards (admin/admin) |

### 6) Export conversations
Use the Streamlit UI **📥 Export to JSON**.

### 7) Stop
```bash
docker compose down
```

---

## ✨ Key Features
- **Multi-agent orchestration** (Claude, ChatGPT, Gemini, Grok, Perplexity)
- **Async by default** with circuit breakers, backoff, similarity loop checks
- **Security**: path validation, API key masking, optional LLM Guard
- **Observability**: Prometheus metrics, Grafana dashboards, OpenTelemetry traces
- **Developer DX**: uv, CLI, pre-commit (Ruff + mypy), extensive tests

---

## 🚀 Usage (CLI)
```bash
# Interactive setup
uv run aic-start

# Non-interactive
uv run aic-start   --agent1 claude   --agent2 chatgpt   --topic "The nature of consciousness"   --turns 20   --db ./data/consciousness.db   --yes
```

---

## 🧭 Documentation Map
Core docs live in **/docs**:

- **Installation**: `docs/INSTALLATION_GUIDE.md`
- **Docker/Compose**: `docs/DOCKER_README.md`
- **Architecture**: `docs/ARCHITECTURE.md`
- **Testing (Quick Reference merged)**: `docs/TESTING.md`
- **Upgrade v4 → v5 (v5 Notes merged)**: `docs/UPGRADE_GUIDE.md`
- **Monitoring**: `docs/MONITORING.md`
- **Security**: `docs/SECURITY.md`
- **Contributing / Code of Conduct**: `docs/CONTRIBUTING.md`, `docs/CODE_OF_CONDUCT.md`
- **Docs Hub**: `docs/docs_README.md`
- **Docs Summary**: `docs/DOCUMENTATION_SUMMARY.md`

---

## 🛡️ Security & Compliance
See `docs/SECURITY.md` for how to report vulnerabilities and best practices.

---

## 📄 License
MIT — see `LICENSE` in the repository root.
