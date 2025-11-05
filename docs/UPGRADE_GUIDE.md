# Upgrade Guide — v4.0 → v5.0 Enterprise Edition

This guide walks you through upgrading from v4.0 to v5.0 and summarizes what changed to achieve a “10/10” production rating. The “What’s New” section below merges the former v5 upgrade notes into a single, definitive file.

---

## 🎯 What’s New in v5.0 (Highlights)

- Modern packaging: **`pyproject.toml` + uv**  
- **mypy strict** across the codebase  
- Security: **LLM Guard**, path validation, API key masking  
- Async correctness: non-blocking API calls via **`run_in_executor`**  
- CI/CD with GitHub Actions, coverage reporting  
- Pre-commit (Ruff + mypy), 90%+ test coverage  
- Health checks and Docker Compose orchestration  
- CLI flags for non-interactive usage  
- Pydantic-validated configuration

---

## ✅ Before You Start (Prereqs)

- Python 3.10+  
- Your existing v4.0 installation  
- API keys in `.env`  
- Optional: existing conversation DBs to carry forward  

---

## 🚀 Step-by-Step Upgrade

### 1) Back up v4.0 data
```bash
mkdir -p ~/ai-platform-backup
cp -r /path/to/v4/*.db ~/ai-platform-backup/
cp /path/to/v4/.env ~/ai-platform-backup/
cp -r /path/to/v4/logs ~/ai-platform-backup/
```

### 2) Install uv
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3) Get v5.0 code
```bash
git clone https://github.com/yourusername/ai-platform-v5.git
cd ai-platform-v5
# or: git pull && checkout the v5.0 tag in your existing repo
```

### 4) Migrate configuration
```bash
cp ~/ai-platform-backup/.env .env
cat >> .env << 'EOF'

# New in v5.0
DATA_DIR=data
ENABLE_LLM_GUARD=true
MAX_MESSAGE_LENGTH=100000
EOF
```

### 5) Install dependencies
```bash
uv sync     # recommended
# or: pip install -e .
```

### 6) Migrate databases
```bash
mkdir -p data
cp ~/ai-platform-backup/*.db data/
# Schema-compatible; no migration needed
```

### 7) (Dev) Pre-commit hooks
```bash
uv run pre-commit install
```

### 8) Verify
```bash
uv run pytest -v
uv run pytest --cov
```

### 9) Run v5.0
```bash
# Interactive
uv run aic-start

# Non-interactive flags
uv run aic-start --agent1 claude --agent2 chatgpt --yes
```

---

## 🔄 Code & API Migration Notes

- **Imports**: `agents/`, `core/queue.py`, `core/config.py` new layout  
- **Async**: queue and agent calls are now `async`/`await`  
- **CLI**: `aic-start` console script replaces `python start_conversation.py`  
- **Config**: Pydantic validation; new keys like `DATA_DIR`, `ENABLE_LLM_GUARD`  

---

## 🐳 Docker Changes

- Full stack via `docker compose up --build`  
- Health checks for services; ordered startup; named volumes  

---

## 📊 Observability

- Prometheus metrics at `:8000/metrics`  
- Grafana dashboards at `:3000`  
- OpenTelemetry optional via `OTEL_EXPORTER_OTLP_ENDPOINT`  

---

## 🛡️ Security Additions

- LLM Guard (prompt injection detection)  
- Strict path validation in the web UI  
- API key masking in logs  

---

## 🧪 CI/CD & Quality

- GitHub Actions: auto-fix/format, tests (fail-fast), CodeQL/pip-audit  
- Coverage targets 90%+ on core paths  

---

## 🧷 Troubleshooting (common)

- **Module not found** → `uv sync` (or `pip install -e .`)  
- **mypy failures** → fix types or relax where necessary  
- **DB locked** → prefer Redis for distributed access; ensure test fixture cleanup  
