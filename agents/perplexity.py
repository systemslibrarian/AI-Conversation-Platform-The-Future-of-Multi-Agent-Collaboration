"""Perplexity AI Agent v5.0 with async support"""

from typing import List, Dict, Tuple
import asyncio

from .base import BaseAgent
from core.config import config


class PerplexityAgent(BaseAgent):
    """Perplexity AI agent with async API calls"""

    PROVIDER_NAME = "Perplexity"
    DEFAULT_MODEL = config.PERPLEXITY_DEFAULT_MODEL

    def __init__(self, api_key: str, *args, **kwargs):
        super().__init__(*args, **kwargs, api_key=api_key)

        try:
            from openai import OpenAI

            self.client = OpenAI(api_key=api_key, base_url="https://api.perplexity.ai")
        except ImportError:
            raise ImportError("Install: pip install openai")

    async def _call_api(self, messages: List[Dict]) -> Tuple[str, int]:
        """Call Perplexity API asynchronously"""
        system = self._build_system_prompt()
        api_messages = [{"role": "system", "content": system}] + messages

        # Run blocking API call in executor
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.chat.completions.create(
                model=self.model,
                messages=api_messages,
                max_tokens=config.MAX_TOKENS,
                temperature=config.TEMPERATURE,
            ),
        )

        content = response.choices[0].message.content
        tokens = response.usage.total_tokens if response.usage else len(content) // 4

        return content, tokens
