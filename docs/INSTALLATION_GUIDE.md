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
| **Python** | 3.10+ | 3.11+ |
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
# Install all dependencies including dev tools
uv sync --all-extras

# Or install without dev dependencies
uv sync
```

This installs:
- **Core dependencies**: `openai`, `anthropic`, `google-generativeai`, `streamlit`, `prometheus_client`, `opentelemetry-sdk`
- **Development tools** (with --all-extras): `pytest`, `pytest-asyncio`, `pytest-cov`, `ruff`, `mypy`, `redis`

### Step 4: Configure Environment
Copy and edit your environment variables file:

```bash
cp .env.example .env
nano .env  # or use your preferred editor
```

**Minimum Required Configuration** (at least 2 providers):
```dotenv
# Required: At least TWO API keys
ANTHROPIC_API_KEY=sk-ant-xxxxx
OPENAI_API_KEY=sk-xxxxx

# Optional: Additional providers
GOOGLE_API_KEY=xxxxx
XAI_API_KEY=xxxxx
PERPLEXITY_API_KEY=pplx-xxxxx

# Optional: Conversation settings
DEFAULT_MAX_TURNS=50
TEMPERATURE=0.7
MAX_TOKENS=1024

# Optional: Data directory
DATA_DIR=data

# Optional: Security features
ENABLE_LLM_GUARD=true
MAX_MESSAGE_LENGTH=100000

# Optional: Monitoring
PROMETHEUS_PORT=8000
```

See `.env.example` for all available configuration options.

### Step 5: Verify Installation
```bash
# Run tests
uv run pytest -v

# Check code formatting
uv run ruff check .

# Run type checker
uv run mypy .
```

### Step 6: Run a Test Conversation

**Interactive Mode (recommended):**
```bash
uv run aic-start
```

**Non-Interactive Mode:**
```bash
uv run aic-start --agent1 claude --agent2 chatgpt --topic "AI alignment" --turns 5 --yes
```

**With Custom Models:**
```bash
uv run aic-start \
  --agent1 claude --model1 claude-sonnet-4-5-20250929 \
  --agent2 chatgpt --model2 gpt-4o \
  --topic "The nature of consciousness" \
  --turns 20 \
  --db ./data/consciousness.db \
  --yes
```

#### Alternative Invocation Methods

If you prefer `pip` over `uv`, you can install the console script and run it directly:

```bash
# Editable install exposes the `aic-start` console script
python -m pip install -e .

# Run the CLI
aic-start --agent1 claude --agent2 chatgpt --yes
```

You can also run the CLI module explicitly without installing the console script:

```bash
python -m cli.start_conversation --agent1 claude --agent2 chatgpt --yes
```

Notes:
- Using `uv run aic-start` ensures the correct environment without globally installing.
- If `aic-start` is not found, verify you ran `pip install -e .` or use `python -m cli.start_conversation`.
- The flags are `--agent1`, `--agent2`, `--topic`, and `--turns` (not `--agents` or `--max-turns`).

### Step 7: Launch Streamlit UI (Optional)
```bash
uv run streamlit run web/app.py
```

Then open [http://localhost:8501](http://localhost:8501)

---

## 🐳 2. Docker Installation (Full Stack)

### Prerequisites
- Docker 24+ and Docker Compose v2
- `.env` file with API keys
- Ports available: 8501 (UI), 8000 (metrics), 9090 (Prometheus), 3000 (Grafana)

### Step 1: Configure Environment
```bash
cp .env.example .env
nano .env
```

Add at least two API keys:
```dotenv
ANTHROPIC_API_KEY=sk-ant-xxxxx
OPENAI_API_KEY=sk-xxxxx
```

### Step 2: Build and Start
```bash
docker compose up --build
```

This launches:
- **conversation** — Background conversation runner
- **ui** — Streamlit web interface (port 8501)
- **prometheus** — Metrics collector (port 9090)
- **grafana** — Dashboard visualization (port 3000)

### Step 3: Access Interfaces

| Service | URL | Credentials |
|----------|-----|-------------|
| **Streamlit UI** | http://localhost:8501 | None required |
| **Prometheus** | http://localhost:9090 | None required |
| **Grafana** | http://localhost:3000 | admin / admin |
| **Metrics Endpoint** | http://localhost:8000/metrics | None required |

### Step 4: Verify Containers
```bash
# Check status
docker compose ps

# View logs
docker compose logs -f

# View specific service logs
docker compose logs -f ui
docker compose logs -f conversation
```

### Step 5: Configure Docker Deployment

You can customize the conversation settings via environment variables in `.env`:

```dotenv
# Docker-specific configuration
AGENT1=claude
AGENT2=chatgpt
TOPIC=AI ethics and safety
TURNS=20
UI_PORT=8501
METRICS_PORT=8000
```

### Step 6: Stop and Clean
```bash
# Stop all services
docker compose down

# Remove volumes (deletes data)
docker compose down -v
```

---

## 🧩 3. Optional Components

### Redis (Distributed Queue)

For multi-instance deployments or distributed conversations:

**Option A: Docker**
```bash
docker run -d --name redis -p 6379:6379 redis:latest
```

**Option B: Local Installation**
```bash
# Ubuntu/Debian
sudo apt install redis-server

# macOS
brew install redis
brew services start redis
```

**Configure in .env:**
```dotenv
REDIS_URL=redis://localhost:6379/0

# For TLS connections
REDIS_URL=rediss://localhost:6379/0
```

### Standalone Prometheus

If running monitoring separately:
```bash
docker run -d -p 9090:9090 \
  -v $(pwd)/monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro \
  prom/prometheus:latest
```

### Standalone Grafana

```bash
docker run -d -p 3000:3000 \
  -v $(pwd)/monitoring/grafana/provisioning:/etc/grafana/provisioning \
  grafana/grafana:latest
```

---

## 🔐 4. Post-Installation Validation

### Verify Metrics Endpoint
```bash
curl http://localhost:8000/metrics
```

**Expected output:**
```
# HELP ai_api_calls_total Total API calls made
# TYPE ai_api_calls_total counter
ai_api_calls_total{provider="Claude",model="claude-sonnet-4-5-20250929",status="success"} 1.0

# HELP ai_response_seconds Response latency in seconds
# TYPE ai_response_seconds histogram
...
```

### Check Prometheus Targets
Visit http://localhost:9090/targets and verify:
- `conversation:8000` — UP
- `ui:8000` — UP

### Access Grafana Dashboard
1. Open http://localhost:3000
2. Login: `admin` / `admin`
3. Navigate to Dashboards → "AI Conversation Platform"

### Run Test Suite
```bash
# Quick test
uv run pytest -q --maxfail=1

# With coverage
uv run pytest --cov=agents --cov=core --cov-report=term-missing

# Specific test file
uv run pytest tests/test_agents.py -v
```

---

## 🧠 5. Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|--------|-----------|
| `ModuleNotFoundError` | Missing dependencies | Run `uv sync --all-extras` |
| `API key not set` | Missing environment variable | Check `.env` file has required keys |
| API Rate Limit | Provider throttling | Wait and retry, or add more API keys |
| `SQLite locked` error | File concurrency | Use Redis backend or ensure only one process |
| Port already in use | Another process using port | Change port in `.env` or stop conflicting service |
| No metrics showing | Prometheus misconfiguration | Verify `/metrics` endpoint accessible |
| Docker build fails | Network/dependency issue | Check `docker compose logs` for details |
| Container exits immediately | Invalid configuration | Check `docker compose logs conversation` |

### Debug Commands

```bash
# Check Python version
python --version  # Should be 3.10+

# Check uv installation
uv --version

# Verify API keys are set
echo $ANTHROPIC_API_KEY  # Should show your key

# Test direct API access
uv run python -c "from anthropic import Anthropic; print('OK')"
uv run python -c "from openai import OpenAI; print('OK')"

# Check SQLite database
sqlite3 data/shared_conversation.db "SELECT COUNT(*) FROM messages;"

# Test metrics endpoint
curl -v http://localhost:8000/metrics

# Docker debugging
docker compose config  # Validate docker-compose.yml
docker compose ps     # Check container status
docker compose logs --tail=50 ui  # Recent logs
```

### Performance Tuning

**For faster responses:**
```dotenv
# Reduce context window
MAX_CONTEXT_MSGS=5

# Lower token limit
MAX_TOKENS=512

# Increase temperature for more varied responses
TEMPERATURE=0.9
```

**For higher quality conversations:**
```dotenv
# Increase context
MAX_CONTEXT_MSGS=20

# Higher token limit
MAX_TOKENS=2048

# Lower temperature for more focused responses
TEMPERATURE=0.5
```

---

## 📋 6. Quick Reference

### Essential Commands

| Action | Command |
|--------|----------|
| **Install dependencies** | `uv sync --all-extras` |
| **Run conversation (interactive)** | `uv run aic-start` |
| **Run conversation (CLI)** | `uv run aic-start --agent1 claude --agent2 chatgpt --yes` |
| **Launch UI** | `uv run streamlit run web/app.py` |
| **Run tests** | `uv run pytest` |
| **Start Docker stack** | `docker compose up --build` |
| **Stop Docker** | `docker compose down` |
| **View logs** | `docker compose logs -f` |
| **Check metrics** | `curl http://localhost:8000/metrics` |

### File Locations

| Purpose | Location |
|---------|----------|
| Conversation databases | `data/*.db` |
| Logs | `logs/*.jsonl` |
| Configuration | `.env` |
| Docker config | `docker-compose.yml` |
| Prometheus config | `monitoring/prometheus/prometheus.yml` |
| Grafana dashboards | `monitoring/grafana/provisioning/` |

---

## 📚 Related Documents

- [⚡ Quick Start](docs/docs_README.md) — 2-minute getting started
- [🐳 Docker Guide](DOCKER_README.md) — Container deployment details
- [📊 Monitoring](MONITORING.md) — Metrics and dashboards
- [🔒 Security](SECURITY.md) — Security best practices
- [🧪 Testing](TESTING.md) — Testing guide
- [📖 Architecture](ARCHITECTURE.md) — System design
- [⬆️ Upgrade Guide](UPGRADE_GUIDE.md) — Migrating from v4.0

---

## ❓ Getting Help

- **Documentation Issues**: Open an issue on GitHub
- **Questions**: Check existing issues or discussions
- **Bug Reports**: See [CONTRIBUTING.md](CONTRIBUTING.md)
- **Security Issues**: See [SECURITY.md](SECURITY.md)

---

<div align="center">

**Made with ❤️ by Paul Clark (@systemslibrarian)**  
**To God be the glory.**

[⬆️ Back to README](README.md)

</div>
