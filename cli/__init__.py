"""Command-line interface package for AI Conversation Platform.

This module exposes the primary CLI entrypoint that allows users to launch
autonomous AI-to-AI conversations via the `aic-start` command or directly
through Python execution.
"""

from .start_conversation import main

__all__ = ["main"]
