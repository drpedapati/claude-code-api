#!/usr/bin/env python3
"""
Streaming Chat Example for Claude Code API

A terminal chat application with real-time streaming responses
using the Claude Code API's streaming endpoint.

Usage:
    python examples/streaming_chat.py
    python examples/streaming_chat.py --model sonnet
    python examples/streaming_chat.py --api-key cca_yourkey

Requirements:
    - Claude Code API server running: make server
    - pip install httpx
"""

import argparse
import json
import os
import sys
from typing import Generator

try:
    import httpx
except ImportError:
    print("Error: httpx required. Install with: pip install httpx")
    sys.exit(1)


# ANSI color codes for pretty output
class Colors:
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


DEFAULT_API_URL = "http://localhost:7742"


def stream_chat(
    prompt: str,
    model: str = "haiku",
    system: str | None = None,
    api_url: str = DEFAULT_API_URL,
    api_key: str | None = None,
) -> Generator[str, None, None]:
    """
    Stream a chat response from the API, yielding text chunks as they arrive.

    Args:
        prompt: The user prompt to send
        model: Model to use (haiku, sonnet, opus)
        system: Optional system prompt
        api_url: API base URL
        api_key: Optional API key for authentication

    Yields:
        Text chunks as they are received
    """
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {"prompt": prompt, "model": model}
    if system:
        payload["system"] = system

    with httpx.stream(
        "POST",
        f"{api_url}/llm/chat/stream",
        json=payload,
        headers=headers,
        timeout=120.0,
    ) as response:
        if response.status_code == 401:
            raise RuntimeError("Authentication required. Use --api-key or set CLAUDE_API_KEY")

        response.raise_for_status()

        for line in response.iter_lines():
            if not line or not line.startswith("data: "):
                continue

            try:
                data = json.loads(line[6:])  # Skip "data: " prefix
                msg_type = data.get("type")

                if msg_type == "chunk":
                    text = data.get("text", "")
                    if text:
                        yield text
                elif msg_type == "error":
                    raise RuntimeError(data.get("message", "Unknown error"))

            except json.JSONDecodeError:
                continue


def chat_loop(
    model: str = "haiku",
    system: str | None = None,
    api_url: str = DEFAULT_API_URL,
    api_key: str | None = None,
    debug: bool = False,
) -> None:
    """
    Run an interactive chat loop with streaming responses.
    """
    print(f"\n{Colors.BOLD}{Colors.CYAN}Claude Code API Chat{Colors.RESET}")
    print(f"{Colors.DIM}API: {api_url}{Colors.RESET}")
    print(f"{Colors.DIM}Model: {model}{Colors.RESET}")
    if system:
        print(f"{Colors.DIM}System: {system[:50]}...{Colors.RESET}" if len(system) > 50 else f"{Colors.DIM}System: {system}{Colors.RESET}")
    if api_key:
        print(f"{Colors.DIM}Auth: API key configured{Colors.RESET}")
    if debug:
        print(f"{Colors.YELLOW}Debug mode: showing chunk boundaries{Colors.RESET}")
    print(f"{Colors.DIM}Type 'quit' or 'exit' to end the conversation{Colors.RESET}")
    print(f"{Colors.DIM}{'─' * 50}{Colors.RESET}\n")

    while True:
        try:
            user_input = input(f"{Colors.GREEN}You:{Colors.RESET} ").strip()

            if not user_input:
                continue

            if user_input.lower() in ("quit", "exit", "q"):
                print(f"\n{Colors.DIM}Goodbye!{Colors.RESET}")
                break

            print(f"\n{Colors.CYAN}Claude:{Colors.RESET} ", end="", flush=True)

            try:
                response_text = ""
                chunk_count = 0
                for chunk in stream_chat(
                    user_input,
                    model=model,
                    system=system,
                    api_url=api_url,
                    api_key=api_key,
                ):
                    chunk_count += 1
                    if debug:
                        print(f"{Colors.DIM}[{chunk_count}]{Colors.RESET}{chunk}", end="", flush=True)
                    else:
                        print(chunk, end="", flush=True)
                    response_text += chunk

                if response_text and not response_text.endswith("\n"):
                    print()
                if debug:
                    print(f"{Colors.DIM}(Received {chunk_count} chunks){Colors.RESET}")
                print()

            except RuntimeError as e:
                print(f"\n{Colors.RED}Error: {e}{Colors.RESET}\n")
            except httpx.ConnectError:
                print(f"\n{Colors.RED}Connection failed. Is the API server running?{Colors.RESET}")
                print(f"{Colors.DIM}Start with: make server{Colors.RESET}\n")

        except KeyboardInterrupt:
            print(f"\n\n{Colors.DIM}Interrupted. Goodbye!{Colors.RESET}")
            break
        except EOFError:
            print(f"\n{Colors.DIM}Goodbye!{Colors.RESET}")
            break


def single_query(
    prompt: str,
    model: str = "haiku",
    system: str | None = None,
    api_url: str = DEFAULT_API_URL,
    api_key: str | None = None,
    debug: bool = False,
) -> None:
    """Run a single streaming query and exit."""
    print(f"{Colors.CYAN}Claude:{Colors.RESET} ", end="", flush=True)

    try:
        chunk_count = 0
        for chunk in stream_chat(
            prompt,
            model=model,
            system=system,
            api_url=api_url,
            api_key=api_key,
        ):
            chunk_count += 1
            if debug:
                print(f"{Colors.DIM}[{chunk_count}]{Colors.RESET}{chunk}", end="", flush=True)
            else:
                print(chunk, end="", flush=True)
        print()
        if debug:
            print(f"{Colors.DIM}(Received {chunk_count} chunks){Colors.RESET}")
    except RuntimeError as e:
        print(f"\n{Colors.RED}Error: {e}{Colors.RESET}")
        sys.exit(1)
    except httpx.ConnectError:
        print(f"\n{Colors.RED}Connection failed. Is the API server running?{Colors.RESET}")
        print(f"{Colors.DIM}Start with: make server{Colors.RESET}")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Streaming chat with Claude via the Claude Code API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Start the API server first
    make server

    # Interactive chat with streaming
    python examples/streaming_chat.py

    # Use a different model
    python examples/streaming_chat.py --model sonnet

    # With a system prompt
    python examples/streaming_chat.py --system "You are a helpful coding assistant"

    # Single query (non-interactive)
    python examples/streaming_chat.py --query "What is Python?"

    # With API key authentication
    python examples/streaming_chat.py --api-key cca_yourkey

    # Debug mode - show chunk boundaries
    python examples/streaming_chat.py --debug
        """,
    )
    parser.add_argument(
        "--model", "-m",
        default="haiku",
        choices=["haiku", "sonnet", "opus"],
        help="Model to use (default: haiku)",
    )
    parser.add_argument(
        "--system", "-s",
        default=None,
        help="System prompt to customize Claude's behavior",
    )
    parser.add_argument(
        "--query", "-q",
        default=None,
        help="Single query mode (non-interactive)",
    )
    parser.add_argument(
        "--api-url",
        default=os.environ.get("CLAUDE_API_URL", DEFAULT_API_URL),
        help=f"API base URL (default: {DEFAULT_API_URL})",
    )
    parser.add_argument(
        "--api-key", "-k",
        default=os.environ.get("CLAUDE_API_KEY"),
        help="API key for authentication (or set CLAUDE_API_KEY env var)",
    )
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Debug mode: show chunk boundaries with [markers]",
    )

    args = parser.parse_args()

    # Check API is reachable
    try:
        response = httpx.get(f"{args.api_url}/health", timeout=5.0)
        if response.status_code != 200:
            print(f"{Colors.RED}API server not healthy{Colors.RESET}")
            sys.exit(1)
    except httpx.ConnectError:
        print(f"{Colors.RED}Cannot connect to API at {args.api_url}{Colors.RESET}")
        print(f"{Colors.DIM}Start the server with: make server{Colors.RESET}")
        sys.exit(1)

    if args.query:
        single_query(
            args.query,
            model=args.model,
            system=args.system,
            api_url=args.api_url,
            api_key=args.api_key,
            debug=args.debug,
        )
    else:
        chat_loop(
            model=args.model,
            system=args.system,
            api_url=args.api_url,
            api_key=args.api_key,
            debug=args.debug,
        )


if __name__ == "__main__":
    main()
