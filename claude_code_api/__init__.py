"""
Claude Code API - Python wrapper for the Claude Code CLI binary.

This package provides a simple, production-ready interface for using
Claude Code as an LLM backend in your applications.

Usage:
    from claude_code_api import ClaudeClient, claude_chat, claude_json

    # Using the client class
    client = ClaudeClient(model="haiku")
    result = client.chat("Hello, Claude!")
    print(result.text)

    # Quick helpers
    response = claude_chat("What is 2+2?")
    data = claude_json("Return JSON: {answer: number}", system="Return only valid JSON")
"""

from .client import ClaudeClient, ClaudeResult, claude_chat, claude_json

__version__ = "0.1.0"
__all__ = ["ClaudeClient", "ClaudeResult", "claude_chat", "claude_json"]
