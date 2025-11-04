"""Anthropic Claude Agent v5.0 with async support"""

from typing import List, Dict, Tuple, Any
import asyncio

from .base import BaseAgent
from core.config import config


class ClaudeAgent(BaseAgent):
    """Anthropic Claude agent with async API calls"""

    PROVIDER_NAME = "Claude"
    DEFAULT_MODEL = config.CLAUDE_DEFAULT_MODEL

    def __init__(self, api_key: str, *args, **kwargs):
        kwargs["api_key"] = api_key
        super().__init__(*args, **kwargs)

        try:
            from anthropic import Anthropic

            self.client: Any = Anthropic(api_key=api_key)
        except ImportError:  # pragma: no cover
            raise ImportError("Install: pip install anthropic")

    async def _call_api(self, messages: List[Dict]) -> Tuple[str, int]:
        """Call Claude API asynchronously"""
        system = self._build_system_prompt()

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.messages.create(  # type: ignore[attr-defined]
                model=self.model,
                max_tokens=config.MAX_TOKENS,
                temperature=config.TEMPERATURE,
                system=system,
                messages=messages,  # list[dict] is acceptable for SDK
            ),
        )

        content_block = response.content[0]
        content = content_block.text if hasattr(content_block, "text") else str(content_block)
        tokens = response.usage.input_tokens + response.usage.output_tokens
        return content, tokens
