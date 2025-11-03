"""Agent integrations and factory for AI Conversation Platform."""

from __future__ import annotations

import os
from typing import Dict, List, Type

from .base import BaseAgent
from .chatgpt import ChatGPTAgent
from .claude import ClaudeAgent
from .gemini import GeminiAgent
from .grok import GrokAgent
from .perplexity import PerplexityAgent

# Public re-exports (so callers can: from agents import ChatGPTAgent, ...)
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

# Central registry for providers
_AGENT_REGISTRY: Dict[str, Dict[str, object]] = {
    "chatgpt": {
        "class": ChatGPTAgent,
        "env_key": "OPENAI_API_KEY",
        "default_model": getattr(ChatGPTAgent, "DEFAULT_MODEL", None),
    },
    "claude": {
        "class": ClaudeAgent,
        "env_key": "ANTHROPIC_API_KEY",
        "default_model": getattr(ClaudeAgent, "DEFAULT_MODEL", None),
    },
    "gemini": {
        "class": GeminiAgent,
        "env_key": "GOOGLE_API_KEY",
        "default_model": getattr(GeminiAgent, "DEFAULT_MODEL", None),
    },
    "grok": {
        "class": GrokAgent,
        "env_key": "XAI_API_KEY",
        "default_model": getattr(GrokAgent, "DEFAULT_MODEL", None),
    },
    "perplexity": {
        "class": PerplexityAgent,
        "env_key": "PERPLEXITY_API_KEY",
        "default_model": getattr(PerplexityAgent, "DEFAULT_MODEL", None),
    },
}


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


def get_agent_info(agent_type: str) -> Dict[str, object]:
    """Return the registry record for an agent type (case-insensitive)."""
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
    model: str | None = None,
    topic: str = "general",
    timeout: int = 30,
    api_key: str | None = None,
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
    info = get_agent_info(agent_type)
    cls: Type[BaseAgent] = info["class"]  # type: ignore[assignment]
    key = api_key or os.getenv(str(info["env_key"]))
    if not key:
        raise ValueError(
            f"Missing API key for {agent_type!r}. Set {info['env_key']} or pass api_key=..."
        )
    selected_model = model or info["default_model"]
    return cls(  # type: ignore[call-arg]
        api_key=key,
        queue=queue,
        logger=logger,
        model=selected_model,
        topic=topic,
        timeout_minutes=timeout,
    )
