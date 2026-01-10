#!/usr/bin/env python3
"""
Streaming Chat Example for Claude Code API

A simple terminal chat application demonstrating how to use
the Claude Code API for chat requests.

Usage:
    python examples/streaming_chat.py
    python examples/streaming_chat.py --model sonnet
    python examples/streaming_chat.py --api-key cca_yourkey

Requirements:
    - Claude Code API server running: make server
    - pip install httpx
"""

import argparse
import os
import sys

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


def chat(
    prompt: str,
    model: str = "haiku",
    system: str | None = None,
    api_url: str = DEFAULT_API_URL,
    api_key: str | None = None,
) -> str:
    """
    Send a chat request to the Claude Code API.

    Args:
        prompt: The user prompt to send
        model: Model to use (haiku, sonnet, opus)
        system: Optional system prompt
        api_url: API base URL
        api_key: Optional API key for authentication

    Returns:
        The response text from Claude
    """
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {"prompt": prompt, "model": model}
    if system:
        payload["system"] = system

    response = httpx.post(
        f"{api_url}/llm/chat",
        json=payload,
        headers=headers,
        timeout=120.0,
    )

    if response.status_code == 401:
        raise RuntimeError("Authentication required. Use --api-key or create a key with: make api-key-create")

    response.raise_for_status()
    data = response.json()

    if data.get("is_error"):
        raise RuntimeError(data.get("text", "Unknown error"))

    return data.get("text", "")


def chat_loop(
    model: str = "haiku",
    system: str | None = None,
    api_url: str = DEFAULT_API_URL,
    api_key: str | None = None,
) -> None:
    """
    Run an interactive chat loop.

    Args:
        model: Model to use
        system: Optional system prompt
        api_url: API base URL
        api_key: Optional API key
    """
    print(f"\n{Colors.BOLD}{Colors.CYAN}Claude Code API Chat{Colors.RESET}")
    print(f"{Colors.DIM}API: {api_url}{Colors.RESET}")
    print(f"{Colors.DIM}Model: {model}{Colors.RESET}")
    if system:
        print(f"{Colors.DIM}System: {system[:50]}...{Colors.RESET}" if len(system) > 50 else f"{Colors.DIM}System: {system}{Colors.RESET}")
    if api_key:
        print(f"{Colors.DIM}Auth: API key configured{Colors.RESET}")
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

            # Send request
            print(f"\n{Colors.CYAN}Claude:{Colors.RESET} ", end="", flush=True)

            try:
                response = chat(
                    user_input,
                    model=model,
                    system=system,
                    api_url=api_url,
                    api_key=api_key,
                )
                print(response)
                print()  # Extra blank line for readability

            except RuntimeError as e:
                print(f"\n{Colors.RED}Error: {e}{Colors.RESET}\n")
            except httpx.HTTPStatusError as e:
                print(f"\n{Colors.RED}HTTP Error: {e.response.status_code}{Colors.RESET}\n")
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
) -> None:
    """
    Run a single query and exit.

    Args:
        prompt: The prompt to send
        model: Model to use
        system: Optional system prompt
        api_url: API base URL
        api_key: Optional API key
    """
    print(f"{Colors.CYAN}Claude:{Colors.RESET} ", end="", flush=True)

    try:
        response = chat(prompt, model=model, system=system, api_url=api_url, api_key=api_key)
        print(response)
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
        description="Chat with Claude via the Claude Code API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Start the API server first
    make server

    # Interactive chat
    python examples/streaming_chat.py

    # Use a different model
    python examples/streaming_chat.py --model sonnet

    # With a system prompt
    python examples/streaming_chat.py --system "You are a helpful coding assistant"

    # Single query (non-interactive)
    python examples/streaming_chat.py --query "What is Python?"

    # With API key authentication
    python examples/streaming_chat.py --api-key cca_yourkey
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
    parser.add_argument(
        "--api-url",
        default=os.environ.get("CLAUDE_API_URL", DEFAULT_API_URL),
        help=f"API base URL (default: {DEFAULT_API_URL})",
    )
    parser.add_argument(
        "--api-key",
        "-k",
        default=os.environ.get("CLAUDE_API_KEY"),
        help="API key for authentication (or set CLAUDE_API_KEY env var)",
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

    # Run in single query or interactive mode
    if args.query:
        single_query(
            args.query,
            model=args.model,
            system=args.system,
            api_url=args.api_url,
            api_key=args.api_key,
        )
    else:
        chat_loop(
            model=args.model,
            system=args.system,
            api_url=args.api_url,
            api_key=args.api_key,
        )


if __name__ == "__main__":
    main()
