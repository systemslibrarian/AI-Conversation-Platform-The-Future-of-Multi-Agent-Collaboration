"""Prometheus metrics collection v5.0"""

import logging
import os
from typing import Optional

from prometheus_client import Counter, Gauge, Histogram, start_http_server

logger = logging.getLogger(__name__)

# Metrics
API_CALLS = Counter("ai_api_calls_total", "Total API calls made", ["provider", "model", "status"])

RESPONSE_LATENCY = Histogram(
    "ai_response_seconds",
    "Response latency in seconds",
    ["provider", "model"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

ACTIVE_CONVERSATIONS = Gauge("ai_active_conversations", "Number of active conversations")

TOKEN_USAGE = Counter(
    "ai_tokens_total",
    "Total tokens used",
    ["provider", "model", "type"],  # type = input/output
)

ERRORS = Counter("ai_errors_total", "Total errors encountered", ["provider", "error_type"])


def record_call(provider: str, model: str, status: str = "success") -> None:
    """Record an API call"""
    try:
        API_CALLS.labels(provider=provider, model=model, status=status).inc()
    except Exception as e:
        logger.error(f"Failed to record call metric: {e}")


def record_latency(provider: str, model: str, seconds: float) -> None:
    """Record response latency"""
    try:
        RESPONSE_LATENCY.labels(provider=provider, model=model).observe(seconds)
    except Exception as e:
        logger.error(f"Failed to record latency metric: {e}")


def record_tokens(provider: str, model: str, input_tokens: int, output_tokens: int) -> None:
    """Record token usage"""
    try:
        TOKEN_USAGE.labels(provider=provider, model=model, type="input").inc(input_tokens)
        TOKEN_USAGE.labels(provider=provider, model=model, type="output").inc(output_tokens)
    except Exception as e:
        logger.error(f"Failed to record token metric: {e}")


def record_error(provider: str, error_type: str) -> None:
    """Record an error"""
    try:
        ERRORS.labels(provider=provider, error_type=error_type).inc()
    except Exception as e:
        logger.error(f"Failed to record error metric: {e}")


def increment_conversations() -> None:
    """Increment active conversations"""
    try:
        ACTIVE_CONVERSATIONS.inc()
    except Exception as e:
        logger.error(f"Failed to increment conversations: {e}")


def decrement_conversations() -> None:
    """Decrement active conversations"""
    try:
        ACTIVE_CONVERSATIONS.dec()
    except Exception as e:
        logger.error(f"Failed to decrement conversations: {e}")


def start_metrics_server(port: Optional[int] = None) -> None:
    """Start Prometheus metrics HTTP server

    If port is None, read PROMETHEUS_PORT from the environment and use 8000 as fallback.
    """
    if port is None:
        port = int(os.getenv("PROMETHEUS_PORT", "8000"))

    try:
        start_http_server(port)
        logger.info(f"Prometheus metrics server started on port {port}")
    except OSError as e:
        logger.warning(f"Could not start metrics server on port {port}: {e}")
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")
