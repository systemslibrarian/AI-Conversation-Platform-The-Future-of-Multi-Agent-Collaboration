"""Agent integrations and factory for AI Conversation Platform (lazy-loaded)."""

from __future__ import annotations

import importlib
import os
from typing import Dict, List, Type, Any, Tuple, Optional, TYPE_CHECKING

from .base import BaseAgent  # BaseAgent is light and safe to import eagerly

# ---- Public API --------------------------------------------------------------

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

# For type checkers only (won't execute at runtime)
if TYPE_CHECKING:
    from .chatgpt import ChatGPTAgent as ChatGPTAgent
    from .claude import ClaudeAgent as ClaudeAgent
    from .gemini import GeminiAgent as GeminiAgent
    from .grok import GrokAgent as GrokAgent
    from .perplexity import PerplexityAgent as PerplexityAgent

# ---- Lazy resolution machinery ----------------------------------------------

# Map public names to (module_path, class_name)
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
    """Lazy expose agent classes as module attributes."""
    if name in _AGENT_SYMBOLS:
        obj = _load_class(name)
        globals()[name] = obj  # cache for subsequent lookups
        return obj
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# ---- Registry (uses lazy loading) -------------------------------------------

# Each provider entry references the public symbol name; real class is loaded on demand.
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
    """
    Return (class, env_key, default_model_str) for an agent key.
    This loads the class lazily and pulls its DEFAULT_MODEL if present.
    """
    rec = _AGENT_REGISTRY[agent_key]
    cls = _load_class(rec["symbol"])
    env_key: str = rec["env_key"]
    # Read the class's DEFAULT_MODEL if defined; otherwise use fallback.
    default_model = getattr(cls, rec["default_model_attr"], None) or rec["fallback_model"]
    return cls, env_key, str(default_model)


# ---- Public helpers ----------------------------------------------------------


def list_available_agents() -> List[str]:
    """Return all agent keys known to the registry."""
    return sorted(_AGENT_REGISTRY.keys())


def detect_configured_agents() -> List[str]:
    """Return agents with required API keys present in the environment."""
    available: List[str] = []
    for key, meta in _AGENT_REGISTRY.items():
        if os.getenv(str(meta["env_key"])):
            available.append(key)
    return sorted(available)


def get_agent_info(agent_type: str) -> Dict[str, Any]:
    """Return the registry record for an agent type (case-insensitive)."""
    k = agent_type.strip().lower()
    if k not in _AGENT_REGISTRY:
        raise ValueError(
            f"Unknown agent type: {agent_type!r}. Known: {', '.join(list_available_agents())}"
        )
    return _AGENT_REGISTRY[k]


# ---- Factory ----------------------------------------------------------------


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

    Parameters
    ----------
    agent_type : str
        One of: chatgpt, claude, gemini, grok, perplexity
    queue : QueueInterface
        Your queue instance (Redis/SQLite)
    logger : logging.Logger
        Logger for the agent
    model : str | None
        Optional model override; falls back to agent DEFAULT_MODEL
    topic : str
        Optional conversation topic seed
    timeout : int
        Timeout (minutes) for the agent loop
    api_key : str | None
        Optional explicit key; falls back to env var
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
