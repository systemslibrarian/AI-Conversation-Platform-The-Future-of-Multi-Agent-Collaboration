.PHONY: help setup lint test run streamlit docker-build docker-up docker-down clean

help:
	@echo "Targets:"
	@echo "  setup        - install all dependencies with uv"
	@echo "  lint         - run Ruff linter, formatter, and Codespell"
	@echo "  test         - run pytest with coverage"
	@echo "  run          - start interactive AI-to-AI conversation"
	@echo "  streamlit    - run Streamlit UI"
	@echo "  docker-build - build Docker image"
	@echo "  docker-up    - run docker compose up (with build)"
	@echo "  docker-down  - stop docker compose stack"
	@echo "  clean        - remove caches, venv, build artifacts"

setup:
	uv sync --all-extras

lint:
	uv run ruff check . --fix
	uv run ruff format .
	uv run codespell

# --- Enhanced coverage run across all key modules ---
test:
	uv run pytest -q --cov=agents --cov=core --cov=cli --cov=web --cov-report=term-missing

run:
	uv run aic-start --agent1 $${AGENT1:-claude} --agent2 $${AGENT2:-chatgpt} --topic "$${TOPIC:-AI governance}" --turns $${TURNS:-8} --yes

streamlit:
	uv run streamlit run web/app.py

docker-build:
	docker build -t ai-conversation-platform:5.0 .

docker-up:
	docker compose up --build

docker-down:
	docker compose down

clean:
	rm -rf .venv __pycache__ .pytest_cache .ruff_cache dist build htmlcov .coverage logs/*.jsonl
