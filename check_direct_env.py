#!/usr/bin/env python3
"""Direct environment check without dotenv"""

import os

api_keys = {
    "ANTHROPIC_API_KEY": "Claude",
    "OPENAI_API_KEY": "ChatGPT",
    "GOOGLE_API_KEY": "Gemini (primary)",
    "GEMINI_API_KEY": "Gemini (alt)",
    "XAI_API_KEY": "Grok",
    "PERPLEXITY_API_KEY": "Perplexity",
}

print("Direct Environment Variable Check")
print("=" * 60)
for env_var, agent_name in api_keys.items():
    value = os.environ.get(env_var)
    if value:
        masked = value[:8] + "..." if len(value) > 8 else "***"
        print(f"✓ {agent_name:20} ({env_var}): {masked}")
    else:
        print(f"✗ {agent_name:20} ({env_var}): NOT SET")

print("=" * 60)
print("\nNote: Gemini accepts either GOOGLE_API_KEY or GEMINI_API_KEY")
print("\nIf secrets are configured in Codespaces/devcontainer,")
print("they should appear above. If not, you need to:")
print("1. Create a .env file with your API keys, OR")
print("2. Set environment variables in your shell/container, OR")
print("3. Add secrets in GitHub Codespaces settings")
