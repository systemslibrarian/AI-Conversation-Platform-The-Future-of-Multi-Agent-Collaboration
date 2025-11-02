"""Google Gemini Agent v5.0 with async support"""

from typing import List, Dict, Tuple
import asyncio

from .base import BaseAgent
from core.config import config


class GeminiAgent(BaseAgent):
    """Google Gemini agent with async API calls"""
    
    PROVIDER_NAME = "Gemini"
    DEFAULT_MODEL = config.GEMINI_DEFAULT_MODEL
    
    def __init__(self, api_key: str, *args, **kwargs):
        super().__init__(*args, **kwargs, api_key=api_key)
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(self.model)
        except ImportError:
            raise ImportError("Install: pip install google-generativeai")
    
    async def _call_api(self, messages: List[Dict]) -> Tuple[str, int]:
        """Call Gemini API asynchronously"""
        # Build history
        history = []
        last_message = None
        
        for msg in messages[:-1]:
            role = "user" if msg["role"] == "user" else "model"
            history.append({"role": role, "parts": [msg["content"]]})
        
        if messages:
            last_message = messages[-1]["content"]
        
        # Run blocking API call in executor
        loop = asyncio.get_event_loop()
        
        def _sync_call():
            chat = self.client.start_chat(history=history)
            return chat.send_message(last_message or "Continue.")
        
        response = await loop.run_in_executor(None, _sync_call)
        
        content = response.text
        
        # Estimate tokens (Gemini doesn't always provide usage info)
        tokens = len(content) // 4 + sum(len(m["content"]) // 4 for m in messages)
        
        return content, tokens
