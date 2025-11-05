"""Centralized Configuration v5.0 with Pydantic validation"""

from dotenv import load_dotenv
import os
from typing import Any, Dict
from pydantic import BaseModel, Field, ValidationError

load_dotenv()


class ConfigValidation(BaseModel):
    """Pydantic model for configuration validation"""

    TEMPERATURE: float = Field(ge=0.0, le=2.0, description="Temperature for LLM sampling")
    MAX_TOKENS: int = Field(ge=1, le=32000, description="Maximum tokens per response")
    SIMILARITY_THRESHOLD: float = Field(
        ge=0.0, le=1.0, description="Similarity detection threshold"
    )
    MAX_CONSECUTIVE_SIMILAR: int = Field(
        ge=1, le=10, description="Max similar responses before termination"
    )
    DEFAULT_MAX_TURNS: int = Field(ge=1, le=1000, description="Default maximum conversation turns")
    DEFAULT_TIMEOUT_MINUTES: int = Field(ge=1, le=480, description="Default timeout in minutes")
    MAX_CONTEXT_MSGS: int = Field(ge=1, le=100, description="Maximum context messages")
    PROMETHEUS_PORT: int = Field(ge=1024, le=65535, description="Prometheus metrics port")

    class Config:
        extra = "forbid"  # Prevent unknown fields


class Config:
    """Centralized configuration management with validation"""

    # File paths
    DEFAULT_CONVERSATION_FILE = "shared_conversation.db"
    DEFAULT_LOG_DIR = "logs"
    DATA_DIR = os.getenv("DATA_DIR", "data")

    # Timing
    DEFAULT_MAX_TURNS = int(os.getenv("DEFAULT_MAX_TURNS", "50"))
    DEFAULT_TIMEOUT_MINUTES = int(os.getenv("DEFAULT_TIMEOUT_MINUTES", "30"))

    # Default models
    CLAUDE_DEFAULT_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")
    CHATGPT_DEFAULT_MODEL = os.getenv("CHATGPT_MODEL", "gpt-4o")
    GEMINI_DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
    GROK_DEFAULT_MODEL = os.getenv("GROK_MODEL", "grok-beta")
    PERPLEXITY_DEFAULT_MODEL = os.getenv("PERPLEXITY_MODEL", "llama-3.1-sonar-large-128k-online")

    # Similarity detection
    SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.85"))
    MAX_CONSECUTIVE_SIMILAR = int(os.getenv("MAX_CONSECUTIVE_SIMILAR", "2"))

    # Termination phrases
    TOPIC_DRIFT_PHRASES = ["[done]", "i can't continue", "off topic", "unrelated", "loop detected"]

    # Backoff settings
    INITIAL_BACKOFF = 2.0
    MAX_BACKOFF = 120.0
    BACKOFF_MULTIPLIER = 2.0
    JITTER_RANGE = 0.2

    # API settings
    TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", "1024"))
    MAX_CONTEXT_MSGS = int(os.getenv("MAX_CONTEXT_MSGS", "10"))

    # Redis settings
    REDIS_URL = os.getenv("REDIS_URL", "")
    USE_REDIS = bool(REDIS_URL)

    # Metrics
    PROMETHEUS_PORT = int(os.getenv("PROMETHEUS_PORT", "8000"))

    # OpenTelemetry
    OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")

    # Security
    MAX_MESSAGE_LENGTH = int(os.getenv("MAX_MESSAGE_LENGTH", "100000"))
    ENABLE_LLM_GUARD = os.getenv("ENABLE_LLM_GUARD", "true").lower() == "true"

    @classmethod
    def get_api_key(cls, env_var: str) -> str:
        """Get API key from environment"""
        key = os.getenv(env_var)
        if not key:
            raise ValueError(f"{env_var} not set in environment")
        return key

    @classmethod
    def validate(cls) -> None:
        """
        Validate configuration using Pydantic and update class attributes.

        Mock-safe: also works when ConfigValidation is patched to return a MagicMock.
        """
        try:
            validated = ConfigValidation(
                TEMPERATURE=cls.TEMPERATURE,
                MAX_TOKENS=cls.MAX_TOKENS,
                SIMILARITY_THRESHOLD=cls.SIMILARITY_THRESHOLD,
                MAX_CONSECUTIVE_SIMILAR=cls.MAX_CONSECUTIVE_SIMILAR,
                DEFAULT_MAX_TURNS=cls.DEFAULT_MAX_TURNS,
                DEFAULT_TIMEOUT_MINUTES=cls.DEFAULT_TIMEOUT_MINUTES,
                MAX_CONTEXT_MSGS=cls.MAX_CONTEXT_MSGS,
                PROMETHEUS_PORT=cls.PROMETHEUS_PORT,
            )
        except ValidationError as e:
            # keep existing contract for real validation failures
            raise ValueError(f"Invalid configuration: {e}")

        # Robustly extract a dict from either a Pydantic model, a dict, or a MagicMock
        data: Dict[str, Any]
        model_dump = getattr(validated, "model_dump", None)
        if callable(model_dump):
            data = model_dump()
        elif isinstance(validated, dict):
            data = validated
        else:
            try:
                data = dict(validated)  # type: ignore[arg-type]
            except Exception:
                maybe = getattr(validated, "data", {})
                data = maybe if isinstance(maybe, dict) else {}

        # Apply only known fields to the class
        for key, value in data.items():
            if hasattr(cls, key):
                setattr(cls, key, value)


# Export singleton instance
config = Config()

# Validate configuration on import
try:
    config.validate()
except ValueError as e:
    import warnings

    warnings.warn(f"Configuration validation warning: {e}")
