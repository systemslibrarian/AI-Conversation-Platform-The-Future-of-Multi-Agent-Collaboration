"""Common utilities v5.0"""

import hashlib
import json
import logging
import random
import re
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict


def setup_logging(agent_name: str, log_dir: str = "logs") -> logging.Logger:
    """Setup structured JSON logging"""
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    log_file = log_path / f"{agent_name}.jsonl"

    logger = logging.getLogger(agent_name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # File handler
    handler = RotatingFileHandler(log_file, maxBytes=10_000_000, backupCount=5)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)

    # Console handler
    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    logger.addHandler(console)

    return logger


def log_event(logger: logging.Logger, event_type: str, data: Dict[str, Any]):
    """Log a structured event"""
    event = {"timestamp": datetime.now().isoformat(), "event": event_type, **data}
    logger.info(json.dumps(event))


def simple_similarity(text1: str, text2: str) -> float:
    """Calculate similarity using shingles (word n-grams)"""

    def shingle(t, n=3):
        words = t.lower().split()
        if len(words) < n:
            return set([t.lower()])
        return set(" ".join(words[i : i + n]) for i in range(len(words) - n + 1))

    s1, s2 = shingle(text1), shingle(text2)
    if not (s1 | s2):
        return 0.0
    return len(s1 & s2) / len(s1 | s2)


def hash_message(content: str) -> str:
    """Generate hash of message"""
    return hashlib.md5(content.encode()).hexdigest()[:8]


def add_jitter(value: float, jitter_range: float = 0.2) -> float:
    """Add random jitter for backoff"""
    return max(0.1, value * (1.0 + random.uniform(-jitter_range, jitter_range)))


def mask_api_key(text: str) -> str:
    """Mask API keys in logs for security"""
    # Mask common API key patterns
    patterns = [
        (r"(sk-ant-[a-zA-Z0-9-]{20,})", "[ANTHROPIC_KEY]"),
        (r"(sk-[a-zA-Z0-9]{20,})", "[OPENAI_KEY]"),
        (r"(pplx-[a-zA-Z0-9]{20,})", "[PERPLEXITY_KEY]"),
        (r"([A-Za-z0-9]{30,})", "[API_KEY]"),
    ]

    masked = text
    for pattern, replacement in patterns:
        masked = re.sub(pattern, replacement, masked)

    return masked


def sanitize_content(content: str) -> str:
    """Sanitize model output for logging (prevent injection attacks)"""
    # Remove potential script tags, SQL injection patterns, etc.
    dangerous_patterns = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"DROP\s+TABLE",
        r"DELETE\s+FROM",
    ]

    sanitized = content
    for pattern in dangerous_patterns:
        sanitized = re.sub(pattern, "[FILTERED]", sanitized, flags=re.IGNORECASE)

    return sanitized
