# ⚡ AI Conversation Platform v5.0 – Quick Start Guide

Welcome to the **AI Conversation Platform**!  
This guide helps you launch your first AI-to-AI conversation in **under 2 minutes**.

---

## 1️⃣ Prerequisites

| Requirement | Version | Notes |
|--------------|----------|-------|
| Python | 3.10+ | For local runs |
| Docker | 24+ | For full stack deployment |
| API Keys | 1+ | OpenAI, Anthropic, Gemini, etc. |

---

## 2️⃣ Clone the Repository

```bash
git clone https://github.com/systemslibrarian/ai-conversation-platform.git
cd ai-conversation-platform
```

---

## 3️⃣ Configure API Keys

Copy the example environment file and edit it:

```bash
cp .env.example .env
nano .env
```

Add at least two provider keys:

```dotenv
OPENAI_API_KEY=sk-xxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxx
GOOGLE_API_KEY=xxxxx
```

---

## 4️⃣ Run the Platform

### Option A – Local (Python + uv)

```bash
# Install uv (faster dependency manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies
uv sync --all-extras

# Start a conversation
uv run aic-start --agent1 claude --agent2 chatgpt --topic "AI ethics" --turns 10 --yes
```

### Option B – Docker (Full Stack)

```bash
docker compose up --build
```

---

## 5️⃣ Access the Platform

| Service | URL | Description |
|----------|-----|-------------|
| Streamlit UI | http://localhost:8501 | View and search conversations |
| Prometheus | http://localhost:9090 | Metrics collector |
| Grafana | http://localhost:3000 | Preconfigured dashboards (admin/admin) |

---

## 6️⃣ Export Conversations

From the Streamlit dashboard, click **📥 Export to JSON** to download your conversation log.

---

## 7️⃣ Stop the Stack

```bash
docker compose down
```

---

## ✅ That’s It!

You’ve successfully launched the **AI Conversation Platform v5.0** — complete with metrics, dashboards, and AI-to-AI conversations.

For advanced topics, see:

- 🐳 [Docker Deployment Guide](DOCKER_README.md)
- 🧠 [Architecture Overview](ARCHITECTURE.md)
- 📊 [Monitoring Setup](MONITORING.md)
