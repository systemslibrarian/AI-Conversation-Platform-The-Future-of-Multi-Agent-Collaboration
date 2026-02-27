# syntax=docker/dockerfile:1.7-labs

# ---------- Stage 1: build ----------
FROM python:3.11.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps needed for building wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy project metadata first for better caching
COPY pyproject.toml /build/pyproject.toml
COPY README.md /build/README.md

# Install production dependencies only (no dev extras)
RUN pip install --upgrade pip && \
    pip install --no-cache-dir . || pip install --no-cache-dir -e .

# ---------- Stage 2: runtime ----------
FROM python:3.11.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

WORKDIR /app

# Copy source code
COPY core /app/core
COPY agents /app/agents
COPY cli /app/cli
COPY web /app/web

# Create non-root user
RUN useradd -ms /bin/bash runner && chown -R runner:runner /app
USER runner

# Expose default ports
# 8501 = Streamlit UI, 8000 = Prometheus metrics
EXPOSE 8501 8000

# Default command runs the interactive starter (overridden by docker-compose)
CMD ["aic-start", "--yes"]