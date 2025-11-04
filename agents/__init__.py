"""Agent integrations and factory for AI Conversation Platform (lazy-loaded)."""

from __future__ import annotations

import importlib
import os
from typing import Dict, List, Type, Any, Tuple, Optional, TYPE_CHECKING

from .base import BaseAgent  # Safe/light to import eagerly

__all__ = [
    "BaseAgent",
    "ChatGPTAgent",
    "ClaudeAgent",
    "GeminiAgent",
    "GrokAgent",
    "PerplexityAgent",
    "list_available_agents",
    "detect_configured_agents",
    "get_agent_info",
    "create_agent",
]

# For type checkers only: use BaseAgent aliases to avoid importing submodules.
# This satisfies mypy without forcing it to analyze providers at import time.
if TYPE_CHECKING:
    ChatGPTAgent = BaseAgent
    ClaudeAgent = BaseAgent
    GeminiAgent = BaseAgent
    GrokAgent = BaseAgent
    PerplexityAgent = BaseAgent

# Map public names to (module_path, class_name) for lazy loading.
_AGENT_SYMBOLS: Dict[str, Tuple[str, str]] = {
    "ChatGPTAgent": ("agents.chatgpt", "ChatGPTAgent"),
    "ClaudeAgent": ("agents.claude", "ClaudeAgent"),
    "GeminiAgent": ("agents.gemini", "GeminiAgent"),
    "GrokAgent": ("agents.grok", "GrokAgent"),
    "PerplexityAgent": ("agents.perplexity", "PerplexityAgent"),
}


def _load_class(symbol: str) -> Any:
    """Import the module and return the named class."""
    try:
        module_path, class_name = _AGENT_SYMBOLS[symbol]
    except KeyError as e:
        raise AttributeError(f"Unknown symbol {symbol!r}") from e
    module = importlib.import_module(module_path)
    try:
        return getattr(module, class_name)
    except AttributeError as e:
        raise ImportError(f"Cannot import name {class_name!r} from {module_path}") from e


def __getattr__(name: str) -> Any:  # PEP 562
    """Expose agent classes lazily as module attributes."""
    if name in _AGENT_SYMBOLS:
        obj = _load_class(name)
        globals()[name] = obj  # cache for speed
        return obj
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Provider registry uses symbols; real classes are resolved on demand.
_AGENT_REGISTRY: Dict[str, Dict[str, Any]] = {
    "chatgpt": {
        "symbol": "ChatGPTAgent",
        "env_key": "OPENAI_API_KEY",
        "default_model_attr": "DEFAULT_MODEL",
        "fallback_model": "gpt-4o",
    },
    "claude": {
        "symbol": "ClaudeAgent",
        "env_key": "ANTHROPIC_API_KEY",
        "default_model_attr": "DEFAULT_MODEL",
        "fallback_model": "claude-sonnet-4-5-20250929",
    },
    "gemini": {
        "symbol": "GeminiAgent",
        "env_key": "GOOGLE_API_KEY",
        "default_model_attr": "DEFAULT_MODEL",
        "fallback_model": "gemini-pro",
    },
    "grok": {
        "symbol": "GrokAgent",
        "env_key": "XAI_API_KEY",
        "default_model_attr": "DEFAULT_MODEL",
        "fallback_model": "grok-beta",
    },
    "perplexity": {
        "symbol": "PerplexityAgent",
        "env_key": "PERPLEXITY_API_KEY",
        "default_model_attr": "DEFAULT_MODEL",
        "fallback_model": "llama-3.1-sonar-large-128k-online",
    },
}


def _resolve_provider(agent_key: str) -> Tuple[Type[BaseAgent], str, str]:
    """Return (class, env_key, default_model_str) for an agent key."""
    rec = _AGENT_REGISTRY[agent_key]
    cls = _load_class(rec["symbol"])
    env_key: str = rec["env_key"]
    default_model = getattr(cls, rec["default_model_attr"], None) or rec["fallback_model"]
    return cls, env_key, str(default_model)


def list_available_agents() -> List[str]:
    return sorted(_AGENT_REGISTRY.keys())


def detect_configured_agents() -> List[str]:
    available: List[str] = []
    for key, meta in _AGENT_REGISTRY.items():
        if os.getenv(str(meta["env_key"])):
            available.append(key)
    return sorted(available)


def get_agent_info(agent_type: str) -> Dict[str, Any]:
    k = agent_type.strip().lower()
    if k not in _AGENT_REGISTRY:
        raise ValueError(
            f"Unknown agent type: {agent_type!r}. Known: {', '.join(list_available_agents())}"
        )
    return _AGENT_REGISTRY[k]


def create_agent(
    agent_type: str,
    queue,
    logger,
    *,
    model: Optional[str] = None,
    topic: str = "general",
    timeout: int = 30,
    api_key: Optional[str] = None,
) -> BaseAgent:
    """
    Construct a configured agent instance from the registry.
    """
    k = agent_type.strip().lower()
    if k not in _AGENT_REGISTRY:
        raise ValueError(
            f"Unknown agent type: {agent_type!r}. Known: {', '.join(list_available_agents())}"
        )

    cls, env_key, default_model = _resolve_provider(k)
    key = api_key or os.getenv(env_key)
    if not key:
        raise ValueError(f"Missing API key for {agent_type!r}. Set {env_key} or pass api_key=...")

    selected_model = model if model else default_model
    return cls(
        api_key=key,
        queue=queue,
        logger=logger,
        model=selected_model,
        topic=topic,
        timeout_minutes=timeout,
    )
