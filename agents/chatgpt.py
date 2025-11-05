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
        # --- THIS IS THE FIX ---
        # 1. Call super() FIRST, passing only the args it expects.
        #    'kwargs' (which contains queue, logger, etc.) is passed.
        #    'api_key' is a local variable and is NOT passed up.
        super().__init__(*args, **kwargs)
        # --- END OF FIX ---

        try:
            from openai import OpenAI

            # 2. Use the local 'api_key' variable to init the client.
            self.client = OpenAI(api_key=api_key)
        except ImportError:
            raise ImportError("Install: pip install openai")

    async def _call_api(self, messages: List[Dict]) -> Tuple[str, int]:
        """Call OpenAI API asynchronously"""
        assert self.client is not None, "Client not initialized"
        client = self.client  # Capture for lambda
        
        # --- THIS IS THE FIX ---
        # Get the system prompt and add it to the messages list
        system = self._build_system_prompt()
        api_messages = [{"role": "system", "content": system}] + messages
        # --- END OF FIX ---

        # Run blocking API call in executor
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model=self.model,
                messages=api_messages, # Use the modified list
                max_tokens=config.MAX_TOKENS,
                temperature=config.TEMPERATURE,
            ),
        )

        content = response.choices[0].message.content or ""
        tokens = response.usage.total_tokens if response.usage else 0

        return content, tokens
