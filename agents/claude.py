"""Anthropic Claude Agent v5.0 with async support"""

import asyncio
from typing import Dict, List, Tuple

from core.config import config

from .base import BaseAgent


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
            raise ImportError("Install: pip install anthropic") from None

    def _normalize_messages(self, messages: List[Dict]) -> List[Dict]:
        """Shape history for the Anthropic API: merge consecutive same-role
        messages and ensure the list starts with a user turn."""
        merged: List[Dict] = []
        for msg in messages:
            if merged and merged[-1]["role"] == msg["role"]:
                merged[-1] = {
                    "role": msg["role"],
                    "content": f"{merged[-1]['content']}\n\n{msg['content']}",
                }
            else:
                merged.append({"role": msg["role"], "content": msg["content"]})

        if not merged or merged[0]["role"] != "user":
            merged.insert(0, {"role": "user", "content": self._kickoff_message()})
        return merged

    async def _call_api(self, messages: List[Dict]) -> Tuple[str, int]:
        """Call Claude API asynchronously"""
        assert self.client is not None, "Client not initialized"
        client = self.client  # Capture for lambda

        # Claude uses a dedicated 'system' param; history goes in 'messages'.
        system = self._build_system_prompt()
        api_messages = self._normalize_messages(messages)

        # Run blocking API call in executor
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.messages.create(
                model=self.model,
                max_tokens=config.MAX_TOKENS,
                temperature=config.TEMPERATURE,
                system=system,  # Pass system prompt here
                messages=api_messages,  # Pass history here
            ),
        )

        # Handle TextBlock union - extract text from first content block.
        # The content list can be empty (e.g. max_tokens exhausted on refusal).
        if response.content:
            content_block = response.content[0]
            if hasattr(content_block, "text"):
                content = content_block.text
            else:
                content = str(content_block)
        else:
            content = ""

        tokens = response.usage.input_tokens + response.usage.output_tokens

        return content, tokens
