# 🐳 Docker Guide — Container Deployment

> Turn-key containers for the **AI Conversation Platform v5.0**: app + metrics + dashboards.  
> One command brings up the full stack with **Streamlit UI (8501)**, **Prometheus (8000/9090)**, and **Grafana (3000)**.

---

## 1) Prerequisites

- Docker 24+ and Docker Compose v2
- At least one (ideally two) AI provider API keys (see `.env` below)
- Open host ports: `8501` (UI), `8000` (metrics), `9090` (Prometheus), `3000` (Grafana)

---

## 2) Files & Ports (what this stack runs)

| Component | File(s) | Port(s) | Notes |
|---|---|---:|---|
| **App (Streamlit UI)** | `Dockerfile`, `docker-compose.yml` | **8501** | Secure UI with path validation & sanitization. |
| **Platform Metrics** | `core/metrics.py` (exposed by app) | **8000** | Prometheus-scrapable metrics. |
| **Prometheus** | `prometheus.yml` (compose-mounted) | **9090** | Scrapes the app’s metrics endpoint. |
| **Grafana** | `provisioning/dashboards/*.json` | **3000** | Pre-provisioned dashboard “AI Conversation Platform”. Default login `admin/admin`. |

---

## 3) Quick start (full stack)

```bash
# 1) Clone & enter the repo
git clone https://github.com/systemslibrarian/ai-conversation-platform.git
cd ai-conversation-platform

# 2) Create and edit your .env (see below)
cp .env.example .env
nano .env   # add API keys, adjust ports if needed

# 3) Bring everything up
docker compose up --build

# (Optional) detached mode
docker compose up -d
```

**Open:**  
- Web UI → http://localhost:8501  
- Metrics → http://localhost:8000/metrics  
- Prometheus → http://localhost:9090  
- Grafana → http://localhost:3000 (login: `admin` / `admin`)

Stop the stack:
```bash
docker compose down
```

---

## 4) Environment (.env)

Create `.env` (never commit it):

```dotenv
# At least 2 keys recommended
ANTHROPIC_API_KEY=sk-ant-xxxxx
OPENAI_API_KEY=sk-xxxxx
GOOGLE_API_KEY=xxxxx
XAI_API_KEY=xxxxx
PERPLEXITY_API_KEY=pplx-xxxxx

# Conversation defaults
DEFAULT_MAX_TURNS=50
TEMPERATURE=0.7
MAX_TOKENS=1024

# Data & security
DATA_DIR=data
ENABLE_LLM_GUARD=true
MAX_MESSAGE_LENGTH=100000

# Metrics & tracing
PROMETHEUS_PORT=8000
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318  # optional
```

---

## 5) Build images separately (optional)

```bash
docker build -t ai-platform:5.0 .
```

---

## 6) Health, logs & common operations

```bash
docker compose logs -f
docker compose logs -f app
docker compose down -v
docker compose build --no-cache
docker compose up
```

---

## 7) Observability (built-in)

- Metrics: http://localhost:8000/metrics  
- Grafana Dashboard: http://localhost:3000  
- Prometheus: http://localhost:9090  

---

## 8) Security hardening

- Keep `.env` secret, use Docker secrets or env vars.
- Restrict ports to trusted networks.
- Streamlit enforces `.db` safety under `DATA_DIR`.
- API rate limits handled via agent logic.

---

## 9) Scaling & Production Notes

- Redis optional for distributed queues.
- TLS via nginx/Traefik reverse proxy.
- Named volumes persist Grafana & Prometheus data.
- Compatible with v4→v5 upgrade instructions.

---

**Happy Shipping!**
