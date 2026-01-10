"""
Claude Code CLI client - calls the Claude binary for LLM inference.

This module wraps the `claude` CLI binary, which handles authentication
via OAuth or ANTHROPIC_API_KEY automatically.

Based on: https://gist.github.com/SamSaffron/603648958a8c18ceae34939a8951d417

CLI Usage:
    claude --print --output-format stream-json --verbose [OPTIONS] -- "prompt"

Options:
    --model <model>         Model: opus, sonnet, haiku (default: haiku)
    --max-turns <n>         Max conversation turns (default: 1)
    --system-prompt <text>  Custom system instructions
"""

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass
class ClaudeResult:
    """Result from a Claude query."""

    text: str
    model: str
    is_error: bool = False
    error_message: Optional[str] = None


class ClaudeClient:
    """
    Client for the Claude Code CLI binary.

    This provides LLM inference by spawning the `claude` binary,
    which handles authentication via ANTHROPIC_API_KEY or OAuth.

    Example:
        client = ClaudeClient(model="haiku")
        result = client.chat("What is the capital of France?")
        print(result.text)  # "Paris"

        # With system prompt
        result = client.chat(
            "Translate to Spanish: Hello",
            system="You are a translator. Return only the translation."
        )
    """

    def __init__(
        self,
        model: str = "haiku",
        max_turns: int = 1,
        binary_path: Optional[str] = None,
    ):
        """
        Initialize the Claude client.

        Args:
            model: Model alias (opus, sonnet, haiku) or full model ID.
                   Default is "haiku" for fast, cost-effective responses.
            max_turns: Maximum conversation turns. Default 1 for single-shot.
            binary_path: Path to claude binary. Auto-detected if not specified.

        Raises:
            RuntimeError: If the claude binary is not found.
        """
        self.model = model
        self.max_turns = max_turns
        self.binary_path = binary_path or shutil.which("claude")

        if not self.binary_path:
            raise RuntimeError(
                "Claude binary not found. Install with: npm install -g @anthropic-ai/claude-code"
            )

    def chat(
        self,
        prompt: str,
        system: Optional[str] = None,
    ) -> ClaudeResult:
        """
        Send a chat message and get the response.

        Args:
            prompt: The user prompt to send to Claude.
            system: Optional system prompt to override Claude's defaults.
                    Use this to customize Claude's behavior.

        Returns:
            ClaudeResult containing the response text and metadata.

        Example:
            result = client.chat("Hello!")
            if not result.is_error:
                print(result.text)
        """
        cmd = [
            "claude",
            "-p",  # Print mode (non-interactive)
            "--output-format",
            "stream-json",
            "--verbose",
            "--model",
            self.model,
            "--max-turns",
            str(self.max_turns),
        ]

        if system:
            cmd.extend(["--system-prompt", system])

        cmd.extend(["--", prompt])

        # Clean environment to avoid conflicts with Claude Code OAuth
        # If ANTHROPIC_API_KEY is set (e.g., from dotenv), it can conflict
        # with Claude Code's OAuth authentication
        env = os.environ.copy()
        env.pop("ANTHROPIC_API_KEY", None)

        result = subprocess.run(cmd, capture_output=True, text=True, env=env)

        if result.returncode != 0:
            error_detail = f"Exit code {result.returncode}"
            if result.stderr:
                error_detail += f"\nstderr: {result.stderr[:500]}"
            if result.stdout:
                error_detail += f"\nstdout: {result.stdout[:500]}"
            return ClaudeResult(
                text="",
                model=self.model,
                is_error=True,
                error_message=error_detail,
            )

        response_text = self._parse_response(result.stdout)

        return ClaudeResult(
            text=response_text,
            model=self.model,
            is_error=not response_text,
            error_message="Empty response" if not response_text else None,
        )

    def chat_json(
        self,
        prompt: str,
        system: Optional[str] = None,
    ) -> dict:
        """
        Send a chat message and parse the response as JSON.

        Args:
            prompt: The user prompt (should ask for JSON output).
            system: Optional system prompt. Consider using something like:
                    "Return ONLY valid JSON. No other text."

        Returns:
            Parsed JSON dict from the response.

        Raises:
            ValueError: If the response cannot be parsed as JSON.
            RuntimeError: If Claude returns an error.

        Example:
            data = client.chat_json(
                "What are the first 3 prime numbers?",
                system="Return JSON: {primes: [numbers]}"
            )
            print(data["primes"])  # [2, 3, 5]
        """
        result = self.chat(prompt, system=system)

        if result.is_error:
            raise RuntimeError(f"Claude error: {result.error_message}")

        return self._extract_json(result.text)

    def _parse_response(self, stdout: str) -> str:
        """Parse stream-json output and extract the result text."""
        for line in stdout.strip().split("\n"):
            if not line.strip():
                continue
            try:
                msg = json.loads(line)
                if msg.get("type") == "result":
                    return msg.get("result", "")
            except json.JSONDecodeError:
                continue
        return ""

    def _extract_json(self, text: str) -> dict:
        """Extract JSON from response text (handles markdown code blocks)."""
        text = text.strip()

        # Strategy 1: Direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Strategy 2: Extract from markdown code block
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Strategy 3: Find JSON object in text
        obj_match = re.search(r"\{[\s\S]*\}", text)
        if obj_match:
            try:
                return json.loads(obj_match.group(0))
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Could not extract JSON from response: {text[:200]}")


# Convenience functions for quick usage


def claude_chat(
    prompt: str, system: Optional[str] = None, model: str = "haiku"
) -> str:
    """
    Quick helper for single-shot Claude queries.

    Args:
        prompt: The user prompt.
        system: Optional system prompt.
        model: Model to use (default: haiku for speed).

    Returns:
        Response text.

    Raises:
        RuntimeError: If Claude returns an error.

    Example:
        response = claude_chat("What is 2+2?")
        print(response)  # "4"
    """
    client = ClaudeClient(model=model)
    result = client.chat(prompt, system=system)
    if result.is_error:
        raise RuntimeError(result.error_message)
    return result.text


def claude_json(
    prompt: str, system: Optional[str] = None, model: str = "haiku"
) -> dict:
    """
    Quick helper for JSON-returning Claude queries.

    Args:
        prompt: The user prompt (should ask for JSON).
        system: Optional system prompt.
        model: Model to use (default: haiku).

    Returns:
        Parsed JSON dict.

    Example:
        data = claude_json(
            "List 3 colors",
            system="Return JSON: {colors: [strings]}"
        )
        print(data["colors"])  # ["red", "blue", "green"]
    """
    client = ClaudeClient(model=model)
    return client.chat_json(prompt, system=system)
