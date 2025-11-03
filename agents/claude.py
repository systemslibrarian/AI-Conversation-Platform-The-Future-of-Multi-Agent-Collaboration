"""Anthropic Claude Agent v5.0 with async support"""

from typing import List, Dict, Tuple
import asyncio

from .base import BaseAgent
from core.config import config


class ClaudeAgent(BaseAgent):
    """Anthropic Claude agent with async API calls"""

    PROVIDER_NAME = "Claude"
    DEFAULT_MODEL = config.CLAUDE_DEFAULT_MODEL

    def __init__(self, api_key: str, *args, **kwargs):
        kwargs.pop('api_key', None)  # Remove api_key if it exists in kwargs
        super().__init__(*args, api_key=api_key, **kwargs)

        try:
            import anthropic

            self.client = anthropic.Anthropic(api_key=api_key)
        except ImportError:
            raise ImportError("Install: pip install anthropic")

    async def _call_api(self, messages: List[Dict]) -> Tuple[str, int]:
        """Call Claude API asynchronously"""
        system = self._build_system_prompt()

        # Run blocking API call in executor
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.messages.create(
                model=self.model,
                max_tokens=config.MAX_TOKENS,
                temperature=config.TEMPERATURE,
                system=system,
                messages=messages,  # type: ignore[arg-type]
            ),
        )

        # Handle TextBlock union - extract text from first content block
        content_block = response.content[0]
        if hasattr(content_block, "text"):
            content = content_block.text
        else:
            content = str(content_block)
        
        tokens = response.usage.input_tokens + response.usage.output_tokens

        return content, tokens