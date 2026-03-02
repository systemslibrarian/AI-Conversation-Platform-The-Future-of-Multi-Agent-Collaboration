<h1 align="center">🤖 AI Conversation Platform — Enterprise Multi-Agent System</h1>

<p align="center"><em>"Because AIs shouldn't monologue — they should <strong>converse</strong>."</em></p>

<hr style="width:60%;margin:auto;border:1px solid #444;">

<p align="center">
  <!-- 🧪 CI + Security -->
  <!-- CI Status: Uses ci.yml (Tests + Formatting) -->
  <a href="https://github.com/systemslibrarian/AI-Conversation-Platform-The-Future-of-Multi-Agent-Collaboration/actions/workflows/ci.yml">
    <img src="https://github.com/systemslibrarian/AI-Conversation-Platform-The-Future-of-Multi-Agent-Collaboration/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI Status">
  </a>

  <!-- CodeQL Status -->
  <a href="https://github.com/systemslibrarian/AI-Conversation-Platform-The-Future-of-Multi-Agent-Collaboration/actions/workflows/codeql-analysis.yml">
    <img src="https://github.com/systemslibrarian/AI-Conversation-Platform-The-Future-of-Multi-Agent-Collaboration/actions/workflows/codeql-analysis.yml/badge.svg?branch=main" alt="CodeQL Security Scan">
  </a>

  <!-- 📊 Codecov Coverage -->
  <a href="https://app.codecov.io/gh/systemslibrarian/AI-Conversation-Platform-The-Future-of-Multi-Agent-Collaboration">
    <img src="https://codecov.io/gh/systemslibrarian/AI-Conversation-Platform-The-Future-of-Multi-Agent-Collaboration/branch/main/graph/badge.svg" alt="Code Coverage">
  </a>

  <!-- 🧹 Linting + Typing -->
  <img src="https://img.shields.io/badge/Lint-Ruff-46A9FC?logo=ruff&logoColor=white" alt="Ruff Linting">
  <img src="https://img.shields.io/badge/Type%20Check-Mypy%20(strict)-3776AB?logo=python&logoColor=white" alt="Mypy Type Checking">

  <!-- ⚖️ License + Version -->
  <img src="https://img.shields.io/badge/License-MIT-green.svg?logo=open-source-initiative&logoColor=white" alt="MIT License">
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

> 🌐 **[View Live Demo Site](https://systemslibrarian.github.io/AI-Conversation-Platform-The-Future-of-Multi-Agent-Collaboration/)** — See the platform overview and quick start guide.

### Key Features

- **🤝 Multi-Agent Orchestration** — Claude, ChatGPT, Gemini, Grok, Perplexity in dynamic conversations
- **⚡ Async-First Architecture** — Non-blocking API calls with `asyncio` and `run_in_executor`
- **🛡️ Production-Grade Reliability** — Circuit breakers, exponential backoff, similarity detection
- **🔒 Security Hardened** — Path validation, input sanitization, API key masking, optional LLM Guard
- **📊 Full Observability** — Prometheus metrics, Grafana dashboards, OpenTelemetry tracing
- **🧪 Comprehensive Testing** — 90%+ code coverage, pytest with async support
- **🐳 Container-Ready** — Docker Compose with health checks and orchestration
- **💻 Developer-Friendly** — Modern tooling (uv, Ruff, mypy), pre-commit hooks, CI/CD
- **🌐 Web Demo** — Interactive Flask-based demo with real-time SSE streaming

---

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
| **Web Demo** | http://localhost:5000 | Interactive AI conversation demo |
| Streamlit UI | http://localhost:8501 | View/search conversations |
| Prometheus | http://localhost:9090 | Metrics |
| Grafana | http://localhost:3000 | Dashboards (admin/admin) |

### 6) Run the Interactive Web Demo
```bash
cd web
python demo.py
# Open http://localhost:5000 in your browser
```
The web demo lets you configure two AI agents, set a topic, and watch them debate in real-time with SSE streaming.

### 7) Export conversations
Use the Streamlit UI **📥 Export to JSON**.

### 7) Stop
```bash
docker compose down
```

---

## 🔑 API Key Configuration

The platform auto-loads API keys from `.env` files using `python-dotenv`. You have three options:

### Option 1: Local `.env` file (recommended for local dev)
```bash
# Copy template and add your keys
cp .env.example .env
nano .env

# Keys are auto-loaded when you run the app
uv run aic-start --agent1 chatgpt --agent2 gemini --topic "test" --turns 3 --yes
```

### Option 2: GitHub Codespaces Secrets (recommended for Codespaces)
```bash
# Set user-level secrets (available to all your Codespaces)
gh secret set OPENAI_API_KEY --user
gh secret set GOOGLE_API_KEY --user
gh secret set ANTHROPIC_API_KEY --user

# Restart Codespace to load secrets
# Keys are automatically available in the environment
```

### Option 3: Manual environment variables
```bash
# Export keys in your current shell
export OPENAI_API_KEY="sk-..."
export GOOGLE_API_KEY="AIza..."
export ANTHROPIC_API_KEY="sk-ant-..."

# Run immediately
uv run aic-start --agent1 chatgpt --agent2 gemini --topic "test" --turns 3 --yes
```

**Required keys by agent:**
| Agent | Environment Variable | Get Key From |
|---|---|---|
| `chatgpt` | `OPENAI_API_KEY` | https://platform.openai.com/api-keys |
| `gemini` | `GOOGLE_API_KEY` or `GEMINI_API_KEY` | https://aistudio.google.com/app/apikey |
| `claude` | `ANTHROPIC_API_KEY` | https://console.anthropic.com/settings/keys |
| `grok` | `XAI_API_KEY` | https://console.x.ai/ |
| `perplexity` | `PERPLEXITY_API_KEY` | https://www.perplexity.ai/settings/api |

**Note:** You need at least **two** agents configured to start a conversation.

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
uv run aic-start \
  --agent1 claude \
  --agent2 chatgpt \
  --topic "The nature of consciousness" \
  --turns 20 \
  --db ./data/consciousness.db \
  --yes
```

### CLI Flags Reference

- `--agent1`, `--agent2`: Agent types to run. Supported: `gemini`, `chatgpt`, `claude`, `grok`, `perplexity` (requires corresponding API keys).
- `--model1`, `--model2`: Optional model overrides per agent. Examples: `gemini-2.0-flash`, `gpt-4o`.
- `--topic`: Conversation topic text.
- `--turns`: Maximum turns per agent (integer). Note: use `--turns`, not `--max-turns`.
- `--db`: SQLite file for shared conversation state. Default: `shared_conversation.db`.
- `--yes`: Non-interactive mode; skips menu prompts.

Notes:
- The CLI does not support `--agents` or `--max-turns`. Use the flags above.
- At least two providers must be available. Set `OPENAI_API_KEY` and either `GOOGLE_API_KEY` or `GEMINI_API_KEY`.
- Logs: `logs/conversation.jsonl`. Data/state: `data/` or the specified `--db`.

### Viewing Conversation Results

After a conversation completes, you can view the results in several ways:

**1. Quick Summary (statistics only):**
```bash
python view_conversation.py summary
```

**2. View First N Messages:**
```bash
# First 3 messages:
python view_conversation.py 3

# First 5 messages:
python view_conversation.py 5
```

**3. View Full Conversation:**
```bash
python view_conversation.py
```

**4. Query SQLite Directly:**
```bash
# Quick preview:
sqlite3 shared_conversation.db "SELECT id, sender, substr(content, 1, 100) FROM messages;"

# Full conversation:
sqlite3 shared_conversation.db "SELECT sender, content FROM messages ORDER BY id;"

# Message statistics:
sqlite3 -header -column shared_conversation.db \
  "SELECT id, sender, length(content) as chars FROM messages;"
```

**5. Web UI (visual interface with filtering):**
```bash
cd web
uv run streamlit run app.py
```
Then open http://localhost:8501 to browse conversations with syntax highlighting.

### Recommended Invocation

- Preferred: use the installed console script (after `uv sync` or `pip install -e .`):
```bash
aic-start --agent1 gemini --agent2 chatgpt --model1 gemini-2.0-flash --model2 gpt-4o --topic "AI ethics in multi-agent systems" --turns 6 --yes
```

- Or run as a module from the repo root (no `sys.path` hacks needed):
```bash
python -m cli.start_conversation --agent1 gemini --agent2 chatgpt --model1 gemini-2.0-flash --model2 gpt-4o --topic "AI ethics in multi-agent systems" --turns 6 --yes
```

Note: running the file directly via `python cli/start_conversation.py` is supported, but using the console script or module form is more robust and CI-friendly.


### Troubleshooting

- Invalid flags: Use `--agent1/--agent2`, `--model1/--model2`, `--turns`, `--yes`. The CLI does not support `--agents` or `--max-turns`.
- Missing async plugin: If tests fail with "async def functions are not natively supported", install `pytest-asyncio` and set `[tool.pytest.ini_options] asyncio_mode = "auto"` in `pyproject.toml`.
- Pytest stdin capture: If you see errors like `OSError: pytest: reading from stdin while output is captured!`, re-run with `-s` to disable output capture (e.g., `pytest -q -s`). This is required for CLI tests that prompt for input.
- Gemini model 404: Use valid models like `gemini-2.0-flash`. The deprecated `gemini-pro` will 404.
- Termination state: The queue preserves termination flags across runs; explicit resets are handled by application logic.

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
- **GitHub Pages Site**: `docs/index.html` — Landing page for the project

---

## 🌐 GitHub Pages Setup

The project includes a static landing page at `docs/index.html` deployed automatically via GitHub Actions.

### Activating GitHub Pages

1. Go to your repository on GitHub
2. Click **Settings** → **Pages** (in the left sidebar under "Code and automation")
3. Under **Source**, select **GitHub Actions**
4. The deployment workflow (`.github/workflows/pages.yml`) will automatically deploy on pushes to `main`

Your site will be available at:
```
https://systemslibrarian.github.io/AI-Conversation-Platform-The-Future-of-Multi-Agent-Collaboration/
```

To trigger a manual deployment, go to **Actions** → **Deploy GitHub Pages** → **Run workflow**.

The landing page showcases the platform features, provides a demo preview, and links to the quick start guide.

---

## � Deploy Live Demo (Render)

Deploy the interactive web demo to Render for free:

### One-Click Deploy
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/systemslibrarian/AI-Conversation-Platform-The-Future-of-Multi-Agent-Collaboration)

### Manual Setup
1. Go to [render.com](https://render.com) and sign up (free)
2. Click **New** → **Blueprint**
3. Connect your GitHub repo
4. Render will detect `render.yaml` and configure the service
5. Add your API keys in the Render dashboard under **Environment**:
   - `OPENAI_API_KEY` (required for ChatGPT)
   - `ANTHROPIC_API_KEY` (required for Claude)
   - `GOOGLE_API_KEY` (required for Gemini)
   - Add others as needed

Your live demo will be at: `https://ai-conversation-demo.onrender.com`

**Note:** Free tier spins down after inactivity. First request may take 30-60 seconds while it spins up.

---

## �🛡️ Security & Compliance
See `docs/SECURITY.md` for how to report vulnerabilities and best practices.

---

## 📄 License
MIT — see `LICENSE` in the repository root.
