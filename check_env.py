#!/usr/bin/env python3
"""Check which API keys are configured"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
project_root = Path(__file__).parent
env_file = project_root / ".env"

print(f"Looking for .env file at: {env_file}")
print(f"File exists: {env_file.exists()}")
print()

load_dotenv()

api_keys = {
    "ANTHROPIC_API_KEY": "Claude",
    "OPENAI_API_KEY": "ChatGPT",
    "GOOGLE_API_KEY": "Gemini",
    "XAI_API_KEY": "Grok",
    "PERPLEXITY_API_KEY": "Perplexity",
}

print("API Key Configuration:")
print("=" * 60)
for env_var, agent_name in api_keys.items():
    value = os.getenv(env_var)
    if value:
        masked = value[:8] + "..." if len(value) > 8 else "***"
        print(f"✓ {agent_name:12} ({env_var}): {masked}")
    else:
        print(f"✗ {agent_name:12} ({env_var}): NOT SET")

print("=" * 60)
