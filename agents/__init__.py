
"""Agents package: factory functions and helpers."""

import os
from typing import Dict, List, Type

from .base import BaseAgent
from .chatgpt import ChatGPTAgent
from .claude import ClaudeAgent
from .gemini import GeminiAgent
from .grok import GrokAgent
from .perplexity import PerplexityAgent

_AGENT_REGISTRY: Dict[str, Dict] = {
    "chatgpt": {
        "class": ChatGPTAgent,
        "env_key": "OPENAI_API_KEY",
        "models": [ChatGPTAgent.DEFAULT_MODEL, "gpt-4o-mini"]
    },
    "claude": {
        "class": ClaudeAgent,
        "env_key": "ANTHROPIC_API_KEY",
        "models": [ClaudeAgent.DEFAULT_MODEL, "claude-3-5-sonnet-latest"]
    },
    "gemini": {
        "class": GeminiAgent,
        "env_key": "GOOGLE_API_KEY",
        "models": [GeminiAgent.DEFAULT_MODEL, "gemini-1.5-flash"]
    },
    "grok": {
        "class": GrokAgent,
        "env_key": "XAI_API_KEY",
        "models": [GrokAgent.DEFAULT_MODEL, "grok-2"]
    },
    "perplexity": {
        "class": PerplexityAgent,
        "env_key": "PERPLEXITY_API_KEY",
        "models": [PerplexityAgent.DEFAULT_MODEL]
    },
}

def list_available_agents() -> List[str]:
    return list(_AGENT_REGISTRY.keys())

def detect_configured_agents() -> List[str]:
    available = []
    for k, v in _AGENT_REGISTRY.items():
        if os.getenv(v["env_key"]):
            available.append(k)
    return available

def get_agent_info(agent_type: str) -> Dict:
    agent_type = agent_type.lower()
    if agent_type not in _AGENT_REGISTRY:
        raise ValueError(f"Unknown agent type: {agent_type}")
    return _AGENT_REGISTRY[agent_type]

def create_agent(agent_type: str, queue, logger, model: str = None, topic: str = "general", timeout: int = 30, api_key: str = None) -> BaseAgent:
    info = get_agent_info(agent_type)
    cls = info["class"]
    key = api_key or os.getenv(info["env_key"])
    if not key:
        raise ValueError(f"{info['env_key']} not set for {agent_type}")
    model = model or info["models"][0]
    return cls(
        api_key=key,
        queue=queue,
        logger=logger,
        model=model,
        topic=topic,
        timeout_minutes=timeout
    )
