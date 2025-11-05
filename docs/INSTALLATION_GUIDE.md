# 🔧 Installation Guide — Detailed Setup Instructions

Welcome to the **AI Conversation Platform v5.0** installation guide!  
This document walks you through installing and configuring the platform for local or containerized use.

---

## 🧭 Overview

You can install and run the platform in two main ways:

| Method | Best For | Description |
|---------|-----------|-------------|
| **Local (Python + uv)** | Developers | Full control, editable code, great for testing and contributions |
| **Docker Compose** | Production / DevOps | One-command deployment with Prometheus, Grafana, and Streamlit UI |

---

## 🖥️ System Requirements

| Component | Minimum | Recommended |
|------------|-----------|-------------|
| **OS** | Linux / macOS / Windows 10+ | Linux or macOS |
| **Python** | 3.10 | 3.11+ |
| **Docker** | 24+ | Latest stable |
| **RAM** | 4 GB | 8 GB+ for multi-agent conversations |
| **Storage** | 1 GB | SSD preferred |

---

## ⚙️ 1. Local Installation (Python + uv)

### Step 1: Clone the Repository
```bash
git clone https://github.com/systemslibrarian/ai-conversation-platform.git
cd ai-conversation-platform
```

### Step 2: Install uv (Faster than pip)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
Then restart your shell to make sure `uv` is on PATH.

### Step 3: Sync Dependencies
```bash
uv sync --all-extras
```

This installs:
- Core dependencies (`openai`, `anthropic`, `google-generativeai`, `streamlit`)
- Development tools (`pytest`, `ruff`, `mypy`)
- Monitoring and tracing libraries (`prometheus_client`, `opentelemetry-sdk`)

### Step 4: Configure Environment
Copy and edit your environment variables file:

```bash
cp .env.example .env
nano .env
```

Set your provider API keys (at least two recommended):
```dotenv
OPENAI_API_KEY=sk-xxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxx
GOOGLE_API_KEY=xxxxx
```

### Step 5: Verify Installation
```bash
uv run pytest
uv run ruff check .
uv run mypy .
```

### Step 6: Run a Test Conversation
```bash
uv run aic-start --agent1 claude --agent2 chatgpt --topic "AI alignment" --turns 5 --yes
```

**Optional:** Launch Streamlit UI
```bash
uv run streamlit run web/app.py
```

Then open [http://localhost:8501](http://localhost:8501)

---

## 🐳 2. Docker Installation (Full Stack)

### Step 1: Build and Start
```bash
docker compose up --build
```

This launches:
- **App** — Streamlit UI (port 8501)
- **Prometheus** — Metrics (port 9090)
- **Grafana** — Dashboards (port 3000)

### Step 2: Access Interfaces

| Service | URL | Description |
|----------|-----|-------------|
| Streamlit UI | http://localhost:8501 | Secure dashboard for conversations |
| Prometheus | http://localhost:9090 | Real-time metrics |
| Grafana | http://localhost:3000 | Dashboards (login: admin / admin) |

### Step 3: Environment Variables

The `.env` file is automatically read by the container.  
Example minimal config:

```dotenv
OPENAI_API_KEY=sk-xxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxx
PROMETHEUS_PORT=8000
ENABLE_LLM_GUARD=true
DATA_DIR=/data
```

### Step 4: Verify Containers
```bash
docker compose ps
docker compose logs -f app
```

### Step 5: Stop and Clean
```bash
docker compose down
```

To remove all data volumes:
```bash
docker compose down -v
```

---

## 🧩 3. Optional Components

### Redis (Distributed Queue)
If you want multi-instance conversations:

```bash
docker run -d --name redis -p 6379:6379 redis
export REDIS_URL=redis://localhost:6379/0
```

Enable in `.env`:
```dotenv
USE_REDIS=true
REDIS_URL=redis://localhost:6379/0
```

### Prometheus (Metrics Only)
If running manually:
```bash
docker run -p 9090:9090 prom/prometheus
```

### Grafana (Dashboards Only)
```bash
docker run -d -p 3000:3000 grafana/grafana
```

---

## 🔍 4. Post-Installation Validation

Run this command to confirm metrics exposure:
```bash
curl http://localhost:8000/metrics
```

Expected output includes:
```
# HELP ai_api_calls_total Total API calls
# TYPE ai_api_calls_total counter
ai_api_calls_total{provider="Claude",status="success"} 1.0
```

Also verify the dashboard:
- [Prometheus Metrics](http://localhost:9090)
- [Grafana Dashboards](http://localhost:3000)

---

## 🧠 5. Troubleshooting

| Issue | Cause | Solution |
|-------|--------|-----------|
| `ModuleNotFoundError` | Missing dependencies | Run `uv sync --all-extras` |
| API Rate Limit | Provider throttling | Retry later or use more API keys |
| SQLite “locked” error | File concurrency | Use Redis backend |
| Port already in use | Another process | Change `PROMETHEUS_PORT` or `streamlit --server.port` |
| No metrics showing | Prometheus misconfig | Check `/metrics` endpoint |

---

## 🧾 Summary

| Method | Command | Description |
|--------|----------|-------------|
| Local Run | `uv run aic-start` | Quick testing via CLI |
| Full Stack | `docker compose up` | Complete deployment with dashboards |
| Stop All | `docker compose down` | Shut down the platform |
| Logs | `docker compose logs -f` | Follow real-time logs |

---

## 📚 Related Documents

- [⚡ QUICK_START.md](QUICK_START.md)
- [🐳 DOCKER_README.md](DOCKER_README.md)
- [📊 MONITORING.md](MONITORING.md)
- [🔒 SECURITY.md](../SECURITY.md)
- [📖 ARCHITECTURE.md](ARCHITECTURE.md)

---

<div align="center">

**Made with ❤️ by Paul Clark (@systemslibrarian)**  
**To God be the glory.**

</div>
