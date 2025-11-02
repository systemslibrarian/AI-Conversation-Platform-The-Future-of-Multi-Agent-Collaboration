# v5.0.0 – AI-to-AI Conversation Platform

Highlights:
- Fully async agents with circuit breaker, metrics & tracing
- Deterministic first speaker to avoid turn-0 races
- Redis or SQLite persistence with file locking
- Streamlit UI + Prometheus metrics

Install:
```
pip install -e ".[dev]"
```

Run:
```
aic-start --agent1 claude --agent2 chatgpt --topic "AI governance" --turns 12 --yes
```