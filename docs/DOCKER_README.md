# 🐳 Docker Guide — Container Deployment

> Turn-key containers for the **AI Conversation Platform v5.0**: app + metrics + dashboards.  
> One command brings up the full stack with **Streamlit UI (8501)**, **Metrics (8000)**, **Prometheus (9090)**, and **Grafana (3000)**.

---

## 1) Prerequisites

- **Docker** 24+ and **Docker Compose** v2+
- At least **two AI provider API keys** (see `.env` configuration below)
- Open host ports: **8501** (UI), **8000** (metrics), **9090** (Prometheus), **3000** (Grafana)
- At least **4 GB RAM** (8 GB recommended)

---

## 2) Stack Architecture

| Component | Container | Port(s) | Description |
|-----------|-----------|---------|-------------|
| **Conversation Runner** | `conversation` | Internal | Background conversation orchestrator |
| **Streamlit UI** | `ui` | **8501**, **8000** | Web interface + metrics endpoint |
| **Prometheus** | `prometheus` | **9090** | Metrics collection and querying |
| **Grafana** | `grafana` | **3000** | Dashboard visualization |

### Data Flow
```
┌─────────────┐
│ conversation│ ──► Writes to SQLite DB
└─────────────┘
       │
       ▼
┌─────────────┐     ┌────────────┐     ┌─────────┐
│     ui      │────►│ prometheus │────►│ grafana │
│ (Streamlit) │     │            │     │         │
└─────────────┘     └────────────┘     └─────────┘
   :8501 :8000         :9090              :3000
```

---

## 3) Quick Start (Full Stack)

### Step 1: Clone Repository
```bash
git clone https://github.com/systemslibrarian/ai-conversation-platform.git
cd ai-conversation-platform
```

### Step 2: Configure Environment
```bash
# Copy example environment file
cp .env.example .env

# Edit with your API keys
nano .env
```

**Minimum configuration:**
```dotenv
# Required: At least 2 API keys
ANTHROPIC_API_KEY=sk-ant-xxxxx
OPENAI_API_KEY=sk-xxxxx

# Optional: Additional providers
GOOGLE_API_KEY=xxxxx
XAI_API_KEY=xxxxx
PERPLEXITY_API_KEY=pplx-xxxxx

# Optional: Conversation defaults
DEFAULT_MAX_TURNS=50
TEMPERATURE=0.7
MAX_TOKENS=1024

# Optional: Docker-specific settings
AGENT1=claude
AGENT2=chatgpt
TOPIC=AI governance
TURNS=12
UI_PORT=8501
METRICS_PORT=8000
```

### Step 3: Start the Stack
```bash
# Build and start all services
docker compose up --build

# Or in detached mode (background)
docker compose up -d --build
```

**What happens:**
1. Builds the `ai-conversation-platform:5.0` image
2. Starts `conversation` service (background runner)
3. Starts `ui` service (Streamlit interface)
4. Starts `prometheus` service (metrics collector)
5. Starts `grafana` service (dashboards)

### Step 4: Access Services

| Service | URL | Notes |
|---------|-----|-------|
| **Streamlit UI** | http://localhost:8501 | View/search conversations |
| **Metrics Endpoint** | http://localhost:8000/metrics | Raw Prometheus metrics |
| **Prometheus** | http://localhost:9090 | Query metrics, check targets |
| **Grafana** | http://localhost:3000 | Login: `admin` / `admin` |

### Step 5: Monitor Status
```bash
# Check service status
docker compose ps

# View logs (all services)
docker compose logs -f

# View specific service logs
docker compose logs -f ui
docker compose logs -f conversation
docker compose logs -f prometheus
```

### Step 6: Stop the Stack
```bash
# Stop all services (preserve data)
docker compose down

# Stop and remove volumes (delete data)
docker compose down -v
```

---

## 4) Environment Configuration

### API Keys (Required)
```dotenv
# At least TWO providers required for conversations
ANTHROPIC_API_KEY=sk-ant-xxxxx
OPENAI_API_KEY=sk-xxxxx
GOOGLE_API_KEY=xxxxx
XAI_API_KEY=xxxxx
PERPLEXITY_API_KEY=pplx-xxxxx
```

### Conversation Settings
```dotenv
# Default conversation parameters
DEFAULT_MAX_TURNS=50            # Max turns per agent
TEMPERATURE=0.7                 # LLM temperature (0.0-2.0)
MAX_TOKENS=1024                 # Max tokens per response
MAX_CONTEXT_MSGS=10             # Messages in context window

# Similarity detection (loop prevention)
SIMILARITY_THRESHOLD=0.85       # Similarity threshold (0.0-1.0)
MAX_CONSECUTIVE_SIMILAR=2       # Max similar responses before stop
```

### Docker-Specific Settings
```dotenv
# Which agents to run in 'conversation' service
AGENT1=claude
AGENT2=chatgpt

# Conversation topic for docker-compose
TOPIC=AI ethics and safety

# Number of turns for docker-compose
TURNS=12

# Port configuration
UI_PORT=8501
METRICS_PORT=8000
```

### Storage & Security
```dotenv
# Data directory (mounted as volume)
DATA_DIR=/data

# Security features
ENABLE_LLM_GUARD=true
MAX_MESSAGE_LENGTH=100000
```

### Monitoring
```dotenv
# Prometheus metrics port
PROMETHEUS_PORT=8000

# OpenTelemetry (optional)
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
```

### Redis (Optional)
```dotenv
# Use Redis instead of SQLite for distributed deployments
REDIS_URL=redis://redis:6379/0
```

---

## 5) Service Details

### Conversation Service
**Purpose**: Background conversation orchestrator  
**Image**: `ai-conversation-platform:5.0`  
**Command**: `aic-start --agent1 ${AGENT1} --agent2 ${AGENT2} --topic "${TOPIC}" --turns ${TURNS} --yes`  
**Volumes**:
- `./data:/data` — Conversation databases
- `./logs:/app/logs` — Structured logs

**Environment**:
- Reads from `.env` file
- `PROMETHEUS_PORT=8000`
- `DATA_DIR=/data`

### UI Service
**Purpose**: Web interface for viewing conversations  
**Image**: `ai-conversation-platform:5.0`  
**Command**: `streamlit run web/app.py --server.port 8501 --server.address 0.0.0.0`  
**Ports**:
- `8501` — Streamlit web UI
- `8000` — Prometheus metrics endpoint

**Volumes**:
- `./data:/data` — Access to conversation databases
- `./logs:/app/logs` — Access to logs

### Prometheus Service
**Purpose**: Metrics collection and storage  
**Image**: `prom/prometheus:latest`  
**Port**: `9090`  
**Configuration**: `monitoring/prometheus/prometheus.yml`  
**Scrape targets**:
- `conversation:8000` — Conversation metrics
- `ui:8000` — UI metrics

### Grafana Service
**Purpose**: Dashboard visualization  
**Image**: `grafana/grafana:latest`  
**Port**: `3000`  
**Credentials**: `admin` / `admin` (change on first login)  
**Configuration**: `monitoring/grafana/provisioning/`  
**Dashboards**: Pre-provisioned "AI Conversation Platform" dashboard

---

## 6) Common Operations

### View Logs
```bash
# All services, follow mode
docker compose logs -f

# Specific service
docker compose logs -f ui
docker compose logs -f conversation
docker compose logs -f prometheus
docker compose logs -f grafana

# Last 50 lines
docker compose logs --tail=50 ui

# Since timestamp
docker compose logs --since=2024-01-01T10:00:00 ui
```

### Restart Services
```bash
# Restart all services
docker compose restart

# Restart specific service
docker compose restart ui
docker compose restart conversation
```

### Rebuild After Code Changes
```bash
# Rebuild and restart
docker compose up --build

# Force rebuild (no cache)
docker compose build --no-cache
docker compose up
```

### Execute Commands in Container
```bash
# Open shell in ui container
docker compose exec ui /bin/bash

# Run pytest in container
docker compose exec ui pytest

# Check Python version
docker compose exec ui python --version

# View environment variables
docker compose exec ui env | grep API
```

### Scale Services
```bash
# Run multiple conversation instances (requires Redis)
docker compose up --scale conversation=3
```

### Health Checks
```bash
# Check container health
docker compose ps

# Test metrics endpoint
curl http://localhost:8000/metrics

# Check Prometheus targets
curl http://localhost:9090/api/v1/targets
```

---

## 7) Data Management

### Volumes and Persistence
```bash
# Local directories mounted as volumes
./data  → /data (conversation databases)
./logs  → /app/logs (structured logs)

# Grafana data (managed by Docker)
grafana-data (named volume)

# Prometheus data (managed by Docker)
prometheus-data (named volume)
```

### Backup Conversations
```bash
# Copy databases from container
docker compose cp ui:/data ./backup/

# Or directly from local directory
cp -r ./data ./backup/
```

### Clean Up Old Data
```bash
# Remove old databases
rm ./data/old_conversation_*.db

# Clean Docker volumes
docker compose down -v
```

---

## 8) Observability

### Prometheus Metrics
**Endpoint**: http://localhost:8000/metrics

**Available metrics:**
```
ai_api_calls_total{provider,model,status}
ai_response_seconds{provider,model}
ai_active_conversations
ai_tokens_total{provider,model,type}
ai_errors_total{provider,error_type}
```

**Query examples** (in Prometheus UI):
```promql
# API call rate by provider
rate(ai_api_calls_total[5m])

# P95 latency
histogram_quantile(0.95, rate(ai_response_seconds_bucket[5m]))

# Error rate
rate(ai_errors_total[5m])

# Total tokens used
sum(ai_tokens_total)
```

### Grafana Dashboards
**URL**: http://localhost:3000  
**Login**: `admin` / `admin`

**Pre-configured dashboard**: "AI Conversation Platform"

**Panels include:**
- API Call Rates (by provider, status)
- Response Latency (p50, p95, p99)
- Token Usage Trends
- Error Rates and Types
- Active Conversations
- Success Rate Percentage

### Logs
```bash
# Structured JSON logs in ./logs/
tail -f logs/conversation.jsonl | jq .
tail -f logs/ui.jsonl | jq .

# Filter by event type
cat logs/conversation.jsonl | jq 'select(.event=="api_call")'

# Count errors
cat logs/conversation.jsonl | jq 'select(.level=="ERROR")' | wc -l
```

---

## 9) Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|--------|-----------|
| Port already in use | Another service using port | Change port in `.env` or stop conflicting service |
| Container exits immediately | Invalid configuration | Check `docker compose logs conversation` |
| No metrics in Prometheus | Metrics endpoint not accessible | Verify `curl http://localhost:8000/metrics` |
| Grafana shows no data | Prometheus not scraping | Check Prometheus targets at `:9090/targets` |
| Out of memory | Insufficient RAM | Increase Docker memory limit or reduce `TURNS` |
| Permission denied on volumes | File ownership issues | Run `sudo chown -R $USER:$USER ./data ./logs` |

### Debug Commands
```bash
# Validate docker-compose.yml
docker compose config

# Check container resource usage
docker stats

# Inspect specific container
docker compose inspect ui

# Check network connectivity
docker compose exec ui curl http://conversation:8000/metrics
docker compose exec ui curl http://prometheus:9090/-/healthy

# View container environment
docker compose exec ui printenv | grep -E "API|PORT"

# Test database access
docker compose exec ui ls -la /data
docker compose exec ui sqlite3 /data/shared_conversation.db ".tables"
```

### Performance Tuning
```bash
# Increase Docker resources (Docker Desktop)
# Settings → Resources → Advanced
# - CPUs: 4+
# - Memory: 8+ GB
# - Swap: 2+ GB

# Optimize conversation settings in .env
MAX_CONTEXT_MSGS=5      # Reduce context window
MAX_TOKENS=512          # Reduce token limit
TURNS=10                # Fewer turns per test
```

---

## 10) Advanced Configuration

### Using Redis Instead of SQLite
```yaml
# Add to docker-compose.yml
services:
  redis:
    image: redis:latest
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data

volumes:
  redis-data:
```

```dotenv
# In .env
REDIS_URL=redis://redis:6379/0
```

### Custom Prometheus Configuration
Edit `monitoring/prometheus/prometheus.yml`:
```yaml
global:
  scrape_interval: 15s      # Adjust scrape interval
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'ai-conversation-platform'
    static_configs:
      - targets: ['conversation:8000', 'ui:8000']
    
  # Add additional scrape targets
  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
```

### Enable TLS/HTTPS
Use a reverse proxy like Nginx or Traefik:

```yaml
# Add to docker-compose.yml
services:
  nginx:
    image: nginx:latest
    ports:
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - ui
```

### External Alerting
Configure Alertmanager for Prometheus:
```yaml
services:
  alertmanager:
    image: prom/alertmanager:latest
    ports:
      - "9093:9093"
    volumes:
      - ./monitoring/alertmanager/config.yml:/etc/alertmanager/config.yml:ro
```

---

## 11) Production Deployment Checklist

- [ ] **Environment**: Set production API keys in `.env`
- [ ] **Security**: Change Grafana password from default
- [ ] **Secrets**: Use Docker secrets or external secret management
- [ ] **Persistence**: Configure named volumes for data persistence
- [ ] **Monitoring**: Set up alerts in Prometheus/Alertmanager
- [ ] **Backups**: Automate database backups
- [ ] **Logging**: Configure log aggregation (ELK, Splunk, etc.)
- [ ] **Networking**: Use Docker networks for service isolation
- [ ] **Resources**: Set resource limits in docker-compose.yml
- [ ] **Health Checks**: Configure health checks for all services
- [ ] **Updates**: Establish update/rollback procedures
- [ ] **Documentation**: Document deployment-specific configuration

---

## 12) Related Documentation

- [📋 Installation Guide](INSTALLATION_GUIDE.md) — Local Python setup
- [📊 Monitoring Guide](MONITORING.md) — Metrics and dashboards
- [🔒 Security Policy](../SECURITY.md) — Security best practices
- [📖 Architecture](ARCHITECTURE.md) — System design
- [⬆️ Upgrade Guide](UPGRADE_GUIDE.md) — Migration from v4.0

---

## 13) Getting Help

**Issues with Docker deployment?**
- Check [GitHub Issues](https://github.com/systemslibrarian/ai-conversation-platform/issues)
- Review existing discussions
- Open a new issue with:
  - `docker compose config` output
  - `docker compose logs` output
  - `.env` file (with secrets redacted)

---

<div align="center">

**Made with ❤️ by Paul Clark (@systemslibrarian)**  
**To God be the glory.**

[⬆️ Back to README](../README.md)

</div>
