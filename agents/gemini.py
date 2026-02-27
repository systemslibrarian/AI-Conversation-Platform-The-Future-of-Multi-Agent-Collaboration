"""Google Gemini Agent v5.0 with async support"""

import asyncio
from typing import Dict, List, Tuple

from core.config import config

from .base import BaseAgent


class GeminiAgent(BaseAgent):
    """Google Gemini agent with async API calls"""

    PROVIDER_NAME = "Gemini"
    DEFAULT_MODEL = config.GEMINI_DEFAULT_MODEL

    def __init__(self, api_key: str, *args, **kwargs):
        # --- THIS IS THE FIX ---
        # 1. Call super() FIRST. 'api_key' is not passed up.
        super().__init__(*args, **kwargs)
        # --- END OF FIX ---

        try:
            import google.generativeai as genai

            # 2. Use the local 'api_key' variable to configure
            genai.configure(api_key=api_key)

            # --- THIS IS THE FIX ---
            # Add system prompt to the model configuration
            system_instruction = self._build_system_prompt()
            self.client = genai.GenerativeModel(self.model, system_instruction=system_instruction)
            # --- END OF FIX ---

        except ImportError:
            raise ImportError("Install: pip install google-generativeai") from None

    async def _call_api(self, messages: List[Dict]) -> Tuple[str, int]:
        """Call Gemini API asynchronously"""
        assert self.client is not None, "Client not initialized"
        client = self.client  # Capture for closure

        # --- THIS IS THE FIX ---
        # Gemini wants history in a specific format.
        # The system prompt is already in self.client.
        # BaseAgent's _build_messages gives us user/assistant roles.

        history = []
        last_message = None

        # Process all but the last message into history
        for msg in messages[:-1]:
            # map 'assistant' to 'model'
            role = "user" if msg["role"] == "user" else "model"
            history.append({"role": role, "parts": [msg["content"]]})

        # The last message is the one we are "sending"
        if messages:
            last_message = messages[-1]["content"]
        # --- END OF FIX ---

        # Run blocking API call in executor
        loop = asyncio.get_running_loop()

        def _sync_call():
            chat = client.start_chat(history=history)
            return chat.send_message(last_message or "Continue.")

        response = await loop.run_in_executor(None, _sync_call)

        content = response.text

        # Estimate tokens (Gemini doesn't always provide usage info)
        tokens = len(content) // 4 + sum(len(m["content"]) // 4 for m in messages)

        return content, tokens
