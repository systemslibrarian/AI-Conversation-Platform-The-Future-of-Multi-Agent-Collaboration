# syntax=docker/dockerfile:1.7-labs
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy project metadata first for better caching
COPY pyproject.toml /app/pyproject.toml
COPY README.md /app/README.md

# Install production dependencies
RUN pip install --upgrade pip && \
    pip install ".[dev]" || pip install -e .

# Copy the rest of the source
COPY core /app/core
COPY agents /app/agents
COPY cli /app/cli
COPY app.py /app/app.py

# Create non-root user
RUN useradd -ms /bin/bash runner && chown -R runner:runner /app
USER runner

# Expose default ports
# 8501 = Streamlit UI, 8000 = Prometheus metrics
EXPOSE 8501 8000

# Default command runs the interactive starter (overridden by docker-compose)
CMD ["aic-start", "--yes"]