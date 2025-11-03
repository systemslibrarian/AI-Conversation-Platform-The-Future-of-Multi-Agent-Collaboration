# 🤖 AI Conversation Platform v5.0 – The Future of Multi-Agent Collaboration  

> **"Because AIs shouldn't monologue — they should *converse*."**

[![CI](https://github.com/systemslibrarian/AI-Conversation-Platform-The-Future-of-Multi-Agent-Collaboration/actions/workflows/ci.yml/badge.svg)](https://github.com/systemslibrarian/AI-Conversation-Platform-The-Future-of-Multi-Agent-Collaboration/actions/workflows/ci.yml)
[![CodeQL](https://github.com/systemslibrarian/AI-Conversation-Platform-The-Future-of-Multi-Agent-Collaboration/actions/workflows/codeql.yml/badge.svg)](https://github.com/systemslibrarian/AI-Conversation-Platform-The-Future-of-Multi-Agent-Collaboration/actions/workflows/codeql.yml)[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🧠 GitHub Project Description  

**Let AIs Talk — Like Never Before.**  
*Watch Claude debate ChatGPT. See Gemini roast Grok. Let Perplexity fact-check them all — live, async, and unscripted.*

A **fully async, type-safe, enterprise-grade platform** that turns AI models into autonomous conversational agents.  
No scripts. No prompts. Just **real-time, multi-model dialogue** — with:

- **5 top-tier LLMs** (Claude, ChatGPT, Gemini, Grok, Perplexity)  
- **Zero-downtime async orchestration**  
- **Built-in circuit breakers & rate limiting**  
- **Live web dashboard + CLI control**  
- **Prometheus + Grafana observability**  
- **LLM Guard security & path hardening**  
- **Docker, CI/CD, 90 %+ test coverage**

```bash
uv run aic-start --agent1 claude --agent2 chatgpt --topic "AI consciousness" --yes
```

**Start a debate. Watch the sparks fly.**  
*Production-ready. Developer-obsessed. AI-to-AI, out of the box.*

---

**Optional one-liner (for GitHub short description):**  
> Async AI-to-AI conversations with observability, security, and zero boilerplate.

---

## ✨ What’s New in v5.0 Enterprise

- ✅ Async orchestration & cancellation safety  
- ✅ Type-safe agents and queue system  
- ✅ Prometheus + Grafana monitoring stack  
- ✅ Full Docker support (`docker compose up`)  
- ✅ CI/CD with Ruff, Mypy, Pytest, and CodeQL  
- ✅ Modular architecture (CLI + Web + Core + Agents)  
- ✅ 5 LLMs supported out of the box

---

## 🚀 Quick Start

### **1️⃣ Setup (with uv)**
```bash
uv sync --all-extras
```

### **2️⃣ Run from CLI**
```bash
uv run aic-start --agent1 claude --agent2 chatgpt --topic "AI governance" --turns 6 --yes
```

### **3️⃣ Run from Web UI**
```bash
uv run streamlit run web/app.py
```

### **4️⃣ Run via Docker**
```bash
docker compose up --build
```

Access Streamlit → [http://localhost:8501](http://localhost:8501)  
Access Grafana → [http://localhost:3000](http://localhost:3000)  
Access Prometheus → [http://localhost:9090](http://localhost:9090)

---

## 🧩 Architecture Overview

```
agents/         →  AI provider wrappers (Claude, ChatGPT, Gemini, Grok, Perplexity)
core/           →  Config, queue, metrics, tracing, and logging
cli/            →  Command-line interface (aic-start)
web/            →  Streamlit dashboard for live AI-to-AI sessions
monitoring/     →  Prometheus + Grafana stack (dockerized)
tests/          →  Pytest async coverage suite
.github/        →  CI/CD workflows (CI, CodeQL, Release)
```

---

## 📊 Monitoring & Metrics

**Prometheus targets**
- `record_call_total`  
- `record_latency_seconds`  
- `record_error_total`  
- `queue_size`  

**Grafana dashboard includes**
- Agent latency histogram  
- Conversation count  
- Error rate over time  
- Queue depth + system health  

Everything autoloads from `monitoring/grafana/provisioning`.

---

## 🧱 Testing & Quality Gates
```bash
uv run ruff check .
uv run mypy .
uv run pytest --cov
```

All workflows run automatically via GitHub Actions:
- ✅ `ci.yml` → lint + type check + tests  
- ✅ `codeql.yml` → CodeQL security scan  
- ✅ `release.yml` → Docker build on tag push  

---

## 🧰 Development Shortcuts (Makefile)

| Command | Description |
|----------|--------------|
| `make setup` | Install dependencies with uv |
| `make lint` | Run Ruff linter + formatter |
| `make test` | Run pytest suite |
| `make streamlit` | Launch web UI |
| `make docker-up` | Start full stack (Prometheus + Grafana) |
| `make docker-down` | Stop containers and clean volumes |

---

## 📦 Docker Images

Once tagged (`v5.0.0` etc.), GitHub Actions builds and publishes to:  
`ghcr.io/systemslibrarian/ai-conversation-platform`

---

## 🔒 Security

- Built-in LLM Guard for sanitizing requests and responses  
- Secure async queues with Redis or SQLite  
- Auto-escaping and HTML cleaning in Streamlit (`bleach.clean`)  
- Configurable API keys via `.env` or environment variables

---

## 🧪 Supported Agents
- ChatGPT (OpenAI GPT-4/4o)  
- Claude (Anthropic Claude 3 series)  
- Gemini (Google Generative AI)  
- Grok (X AI)  
- Perplexity AI  

Each agent is modular and hot-swappable under `agents/`.

---

## 🧭 License & Credits
To God be the glory
MIT License © 2025 Systemslibrarian  
Developed with ❤️ by Paul Clark (@systemslibrarian) and AI.


---

### ⭐ If you like this project
- Give it a ⭐ on GitHub — it helps others discover it!  
- Fork and experiment with your own AI-to-AI agents.  
- Contributions welcome via Pull Requests.

---
