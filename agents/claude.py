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
        # --- THIS IS THE FIX ---
        # 1. Call super() FIRST. 'api_key' is not passed up.
        super().__init__(*args, **kwargs)
        # --- END OF FIX ---

        try:
            import anthropic

            # 2. Use the local 'api_key' variable to init the client.
            self.client = anthropic.Anthropic(api_key=api_key)
        except ImportError:
            raise ImportError("Install: pip install anthropic")

    async def _call_api(self, messages: List[Dict]) -> Tuple[str, int]:
        """Call Claude API asynchronously"""
        assert self.client is not None, "Client not initialized"
        client = self.client  # Capture for lambda

        # --- THIS IS THE FIX ---
        # Get the system prompt. Claude uses a dedicated 'system' param.
        system = self._build_system_prompt()
        # 'messages' already contains the history from BaseAgent
        # --- END OF FIX ---

        # Run blocking API call in executor
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.messages.create(
                model=self.model,
                max_tokens=config.MAX_TOKENS,
                temperature=config.TEMPERATURE,
                system=system,  # Pass system prompt here
                messages=messages,  # Pass history here
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
