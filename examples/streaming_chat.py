#!/usr/bin/env python3
"""
Streaming Chat Example for Claude Code API

A simple terminal chat application demonstrating real-time streaming
responses from Claude using the Claude Code CLI.

Usage:
    python examples/streaming_chat.py
    python examples/streaming_chat.py --model sonnet
    python examples/streaming_chat.py --system "You are a pirate. Always respond in pirate speak."

Requirements:
    - Claude Code CLI installed: npm install -g @anthropic-ai/claude-code
    - Authenticated: claude auth login
"""

import argparse
import json
import shutil
import subprocess
import sys
from typing import Generator, Optional


# ANSI color codes for pretty output
class Colors:
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def stream_chat(
    prompt: str,
    model: str = "haiku",
    system: Optional[str] = None,
    max_turns: int = 1,
) -> Generator[str, None, None]:
    """
    Stream a chat response from Claude, yielding text chunks as they arrive.

    Args:
        prompt: The user prompt to send
        model: Model to use (haiku, sonnet, opus)
        system: Optional system prompt
        max_turns: Maximum conversation turns

    Yields:
        Text chunks as they are received from Claude

    Example:
        for chunk in stream_chat("Tell me a story"):
            print(chunk, end="", flush=True)
    """
    # Build command
    cmd = [
        "claude",
        "-p",  # Print mode (non-interactive)
        "--output-format",
        "stream-json",
        "--verbose",
        "--model",
        model,
        "--max-turns",
        str(max_turns),
    ]

    if system:
        cmd.extend(["--system-prompt", system])

    cmd.extend(["--", prompt])

    # Start process with streaming output
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,  # Line buffered
    )

    # Stream the output line by line
    try:
        for line in process.stdout:
            line = line.strip()
            if not line:
                continue

            try:
                msg = json.loads(line)
                msg_type = msg.get("type")

                # Handle different message types
                if msg_type == "assistant":
                    # Start of assistant response - content is in message.content
                    content = msg.get("message", {}).get("content", [])
                    for block in content:
                        if block.get("type") == "text":
                            yield block.get("text", "")

                elif msg_type == "content_block_delta":
                    # Streaming text delta
                    delta = msg.get("delta", {})
                    if delta.get("type") == "text_delta":
                        yield delta.get("text", "")

                elif msg_type == "result":
                    # Final result - yield if we haven't streamed yet
                    result_text = msg.get("result", "")
                    if result_text:
                        # Only yield if this is the final consolidated result
                        # and we haven't been streaming deltas
                        pass  # Already yielded via deltas

            except json.JSONDecodeError:
                # Not JSON, might be raw output
                continue

    finally:
        process.wait()

        # Check for errors
        if process.returncode != 0:
            stderr = process.stderr.read() if process.stderr else ""
            raise RuntimeError(f"Claude CLI error (exit {process.returncode}): {stderr}")


def chat_loop(model: str = "haiku", system: Optional[str] = None) -> None:
    """
    Run an interactive chat loop with streaming responses.

    Args:
        model: Model to use
        system: Optional system prompt
    """
    print(f"\n{Colors.BOLD}{Colors.CYAN}Claude Code Streaming Chat{Colors.RESET}")
    print(f"{Colors.DIM}Model: {model}{Colors.RESET}")
    if system:
        print(f"{Colors.DIM}System: {system[:50]}...{Colors.RESET}" if len(system) > 50 else f"{Colors.DIM}System: {system}{Colors.RESET}")
    print(f"{Colors.DIM}Type 'quit' or 'exit' to end the conversation{Colors.RESET}")
    print(f"{Colors.DIM}{'─' * 50}{Colors.RESET}\n")

    while True:
        try:
            # Get user input
            user_input = input(f"{Colors.GREEN}You:{Colors.RESET} ").strip()

            if not user_input:
                continue

            if user_input.lower() in ("quit", "exit", "q"):
                print(f"\n{Colors.DIM}Goodbye!{Colors.RESET}")
                break

            # Stream the response
            print(f"\n{Colors.CYAN}Claude:{Colors.RESET} ", end="", flush=True)

            try:
                response_text = ""
                for chunk in stream_chat(user_input, model=model, system=system):
                    print(chunk, end="", flush=True)
                    response_text += chunk

                # Ensure we end with a newline
                if response_text and not response_text.endswith("\n"):
                    print()
                print()  # Extra blank line for readability

            except RuntimeError as e:
                print(f"\n{Colors.RED}Error: {e}{Colors.RESET}\n")

        except KeyboardInterrupt:
            print(f"\n\n{Colors.DIM}Interrupted. Goodbye!{Colors.RESET}")
            break
        except EOFError:
            print(f"\n{Colors.DIM}Goodbye!{Colors.RESET}")
            break


def single_query(
    prompt: str,
    model: str = "haiku",
    system: Optional[str] = None,
) -> None:
    """
    Run a single streaming query and exit.

    Args:
        prompt: The prompt to send
        model: Model to use
        system: Optional system prompt
    """
    print(f"{Colors.CYAN}Claude:{Colors.RESET} ", end="", flush=True)

    try:
        for chunk in stream_chat(prompt, model=model, system=system):
            print(chunk, end="", flush=True)
        print()  # Final newline
    except RuntimeError as e:
        print(f"\n{Colors.RED}Error: {e}{Colors.RESET}")
        sys.exit(1)


def main():
    """Main entry point."""
    # Check for Claude CLI
    if not shutil.which("claude"):
        print(f"{Colors.RED}Error: Claude CLI not found{Colors.RESET}")
        print(f"{Colors.DIM}Install with: npm install -g @anthropic-ai/claude-code{Colors.RESET}")
        sys.exit(1)

    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Streaming chat with Claude",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Interactive chat
    python streaming_chat.py

    # Use a different model
    python streaming_chat.py --model sonnet

    # With a system prompt
    python streaming_chat.py --system "You are a helpful coding assistant"

    # Single query (non-interactive)
    python streaming_chat.py --query "What is Python?"
        """,
    )
    parser.add_argument(
        "--model",
        "-m",
        default="haiku",
        choices=["haiku", "sonnet", "opus"],
        help="Model to use (default: haiku)",
    )
    parser.add_argument(
        "--system",
        "-s",
        default=None,
        help="System prompt to customize Claude's behavior",
    )
    parser.add_argument(
        "--query",
        "-q",
        default=None,
        help="Single query mode (non-interactive)",
    )

    args = parser.parse_args()

    # Run in single query or interactive mode
    if args.query:
        single_query(args.query, model=args.model, system=args.system)
    else:
        chat_loop(model=args.model, system=args.system)


if __name__ == "__main__":
    main()
