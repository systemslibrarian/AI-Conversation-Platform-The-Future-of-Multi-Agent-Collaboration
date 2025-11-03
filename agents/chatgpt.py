"""OpenAI ChatGPT Agent v5.0 with async support"""

from typing import List, Dict, Tuple
import asyncio

from .base import BaseAgent
from core.config import config


class ChatGPTAgent(BaseAgent):
    """OpenAI ChatGPT agent with async API calls"""

    PROVIDER_NAME = "ChatGPT"
    DEFAULT_MODEL = config.CHATGPT_DEFAULT_MODEL

    def __init__(self, api_key: str, *args, **kwargs):
        kwargs.pop('api_key', None)  # Remove api_key if it exists in kwargs
        super().__init__(*args, api_key=api_key, **kwargs)

        try:
            from openai import OpenAI

            self.client = OpenAI(api_key=api_key)
        except ImportError:
            raise ImportError("Install: pip install openai")

    async def _call_api(self, messages: List[Dict]) -> Tuple[str, int]:
        """Call OpenAI API asynchronously"""
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

        content = response.choices[0].message.content or ""
        tokens = response.usage.total_tokens if response.usage else 0

        return content, tokens