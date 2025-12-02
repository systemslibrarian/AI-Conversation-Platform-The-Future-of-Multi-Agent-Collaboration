#!/usr/bin/env python3
"""List available Gemini models"""
import os
import sys

# Check for API key
api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

if not api_key:
    print("Error: GEMINI_API_KEY or GOOGLE_API_KEY not set")
    sys.exit(1)

try:
    import google.generativeai as genai
    
    genai.configure(api_key=api_key)
    
    print("Available Gemini Models:")
    print("=" * 60)
    
    for model in genai.list_models():
        if 'generateContent' in model.supported_generation_methods:
            print(f"\n✓ {model.name}")
            print(f"  Display Name: {model.display_name}")
            print(f"  Description: {model.description[:100]}..." if len(model.description) > 100 else f"  Description: {model.description}")
    
    print("\n" + "=" * 60)
    print("\nTo use a model, specify just the part after 'models/'")
    print("Example: gemini-1.5-flash-latest")
    
except ImportError:
    print("Error: google-generativeai not installed")
    print("Run: pip install google-generativeai")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
