#!/usr/bin/env python3
"""
Claude Agent SDK Specification Tests

Beautiful terminal output testing each feature from the SDK spec.
Reference: https://gist.github.com/SamSaffron/603648958a8c18ceae34939a8951d417
"""

import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Callable, Optional

# ═══════════════════════════════════════════════════════════════════════════════
# Terminal Formatting
# ═══════════════════════════════════════════════════════════════════════════════

class Style:
    """ANSI escape codes for terminal styling."""
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"

    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"

    RESET = "\033[0m"

    # Symbols
    CHECK = "✓"
    CROSS = "✗"
    ARROW = "→"
    DOT = "●"
    WARN = "⚠"


def print_header(title: str):
    """Print a section header."""
    width = 70
    print()
    print(f"{Style.CYAN}{'═' * width}{Style.RESET}")
    print(f"{Style.BOLD}{Style.CYAN}  {title}{Style.RESET}")
    print(f"{Style.CYAN}{'═' * width}{Style.RESET}")
    print()


def print_subheader(title: str):
    """Print a subsection header."""
    print(f"\n{Style.BOLD}{Style.WHITE}  {title}{Style.RESET}")
    print(f"{Style.DIM}  {'─' * 60}{Style.RESET}")


def print_test(name: str, passed: bool, detail: str = "", duration_ms: int = 0):
    """Print a test result line."""
    if passed:
        status = f"{Style.GREEN}{Style.CHECK}{Style.RESET}"
        color = Style.GREEN
    else:
        status = f"{Style.RED}{Style.CROSS}{Style.RESET}"
        color = Style.RED

    time_str = f"{Style.DIM}({duration_ms}ms){Style.RESET}" if duration_ms else ""
    detail_str = f" {Style.DIM}{Style.ARROW} {detail}{Style.RESET}" if detail else ""

    print(f"    {status} {color}{name}{Style.RESET}{detail_str} {time_str}")


def print_skip(name: str, reason: str):
    """Print a skipped test."""
    print(f"    {Style.YELLOW}{Style.WARN}{Style.RESET} {Style.DIM}{name} (skipped: {reason}){Style.RESET}")


def print_info(msg: str):
    """Print info message."""
    print(f"    {Style.DIM}{msg}{Style.RESET}")


def print_json(data: dict, indent: int = 6):
    """Print formatted JSON."""
    prefix = " " * indent
    formatted = json.dumps(data, indent=2)
    for line in formatted.split("\n"):
        print(f"{prefix}{Style.DIM}{line}{Style.RESET}")


# ═══════════════════════════════════════════════════════════════════════════════
# Test Framework
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TestResult:
    name: str
    passed: bool
    detail: str = ""
    duration_ms: int = 0
    skipped: bool = False
    skip_reason: str = ""


class TestRunner:
    def __init__(self):
        self.results: list[TestResult] = []
        self.claude_available = shutil.which("claude") is not None

    def run_test(self, name: str, test_fn: Callable[[], tuple[bool, str]]) -> TestResult:
        """Run a single test and record result."""
        start = time.time()
        try:
            passed, detail = test_fn()
            duration_ms = int((time.time() - start) * 1000)
            result = TestResult(name, passed, detail, duration_ms)
        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            result = TestResult(name, False, str(e), duration_ms)

        self.results.append(result)
        print_test(result.name, result.passed, result.detail, result.duration_ms)
        return result

    def skip_test(self, name: str, reason: str) -> TestResult:
        """Skip a test."""
        result = TestResult(name, False, skipped=True, skip_reason=reason)
        self.results.append(result)
        print_skip(name, reason)
        return result

    def require_claude(self, name: str, test_fn: Callable[[], tuple[bool, str]]) -> TestResult:
        """Run test only if Claude CLI is available."""
        if not self.claude_available:
            return self.skip_test(name, "Claude CLI not installed")
        return self.run_test(name, test_fn)

    def print_summary(self):
        """Print test summary."""
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed and not r.skipped)
        skipped = sum(1 for r in self.results if r.skipped)
        total = len(self.results)

        print()
        print(f"{Style.CYAN}{'═' * 70}{Style.RESET}")
        print(f"{Style.BOLD}  Summary{Style.RESET}")
        print(f"{Style.DIM}  {'─' * 60}{Style.RESET}")

        if failed == 0:
            print(f"    {Style.GREEN}{Style.DOT} All tests passed!{Style.RESET}")
        else:
            print(f"    {Style.RED}{Style.DOT} Some tests failed{Style.RESET}")

        print()
        print(f"    {Style.GREEN}{passed} passed{Style.RESET}  ", end="")
        if failed > 0:
            print(f"{Style.RED}{failed} failed{Style.RESET}  ", end="")
        if skipped > 0:
            print(f"{Style.YELLOW}{skipped} skipped{Style.RESET}  ", end="")
        print(f"{Style.DIM}{total} total{Style.RESET}")
        print()

        return failed == 0


# ═══════════════════════════════════════════════════════════════════════════════
# SDK Specification Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_cli_exists() -> tuple[bool, str]:
    """Test: Claude CLI binary exists."""
    path = shutil.which("claude")
    if path:
        return True, path
    return False, "claude not in PATH"


def test_cli_version() -> tuple[bool, str]:
    """Test: Claude CLI reports version."""
    result = subprocess.run(["claude", "--version"], capture_output=True, text=True)
    if result.returncode == 0:
        return True, result.stdout.strip()
    return False, result.stderr


def test_cli_stream_json() -> tuple[bool, str]:
    """Test: CLI supports stream-json output."""
    result = subprocess.run(
        ["claude", "-p", "--output-format", "stream-json", "--verbose",
         "--model", "haiku", "--max-turns", "1", "--", "Reply: TEST"],
        capture_output=True, text=True, timeout=30,
        env={**os.environ, "ANTHROPIC_API_KEY": ""}  # Remove API key
    )

    if result.returncode != 0:
        return False, f"Exit code {result.returncode}"

    # Check for expected message types
    has_system = False
    has_result = False

    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        try:
            msg = json.loads(line)
            if msg.get("type") == "system":
                has_system = True
            if msg.get("type") == "result":
                has_result = True
        except json.JSONDecodeError:
            continue

    if has_system and has_result:
        return True, "system + result messages"
    return False, f"system={has_system}, result={has_result}"


def test_message_system_init() -> tuple[bool, str]:
    """Test: System message contains expected fields."""
    result = subprocess.run(
        ["claude", "-p", "--output-format", "stream-json", "--verbose",
         "--model", "haiku", "--max-turns", "1", "--", "Hi"],
        capture_output=True, text=True, timeout=30,
        env={**os.environ, "ANTHROPIC_API_KEY": ""}
    )

    for line in result.stdout.strip().split("\n"):
        try:
            msg = json.loads(line)
            if msg.get("type") == "system" and msg.get("subtype") == "init":
                required = ["session_id", "model", "tools", "cwd"]
                missing = [f for f in required if f not in msg]
                if missing:
                    return False, f"missing: {missing}"
                return True, f"session={msg['session_id'][:8]}..."
        except json.JSONDecodeError:
            continue

    return False, "no system init message"


def test_message_result_success() -> tuple[bool, str]:
    """Test: Result message has expected structure."""
    result = subprocess.run(
        ["claude", "-p", "--output-format", "stream-json", "--verbose",
         "--model", "haiku", "--max-turns", "1", "--", "Say OK"],
        capture_output=True, text=True, timeout=30,
        env={**os.environ, "ANTHROPIC_API_KEY": ""}
    )

    for line in result.stdout.strip().split("\n"):
        try:
            msg = json.loads(line)
            if msg.get("type") == "result":
                if msg.get("subtype") == "success" and not msg.get("is_error"):
                    cost = msg.get("total_cost_usd", 0)
                    return True, f"cost=${cost:.4f}"
                return False, f"subtype={msg.get('subtype')}"
        except json.JSONDecodeError:
            continue

    return False, "no result message"


def test_model_selection_haiku() -> tuple[bool, str]:
    """Test: Model selection works (haiku)."""
    result = subprocess.run(
        ["claude", "-p", "--output-format", "stream-json", "--verbose",
         "--model", "haiku", "--max-turns", "1", "--", "Hi"],
        capture_output=True, text=True, timeout=30,
        env={**os.environ, "ANTHROPIC_API_KEY": ""}
    )

    for line in result.stdout.strip().split("\n"):
        try:
            msg = json.loads(line)
            if msg.get("type") == "system" and msg.get("subtype") == "init":
                model = msg.get("model", "")
                if "haiku" in model.lower():
                    return True, model
                return False, f"expected haiku, got {model}"
        except json.JSONDecodeError:
            continue

    return False, "no model info"


def test_system_prompt() -> tuple[bool, str]:
    """Test: System prompt customization."""
    result = subprocess.run(
        ["claude", "-p", "--output-format", "stream-json", "--verbose",
         "--model", "haiku", "--max-turns", "1",
         "--system-prompt", "Reply with only the word BANANA",
         "--", "What should you say?"],
        capture_output=True, text=True, timeout=30,
        env={**os.environ, "ANTHROPIC_API_KEY": ""}
    )

    for line in result.stdout.strip().split("\n"):
        try:
            msg = json.loads(line)
            if msg.get("type") == "result":
                text = msg.get("result", "").upper()
                if "BANANA" in text:
                    return True, "BANANA in response"
                return False, f"got: {text[:50]}"
        except json.JSONDecodeError:
            continue

    return False, "no result"


def test_max_turns() -> tuple[bool, str]:
    """Test: Max turns limit works."""
    result = subprocess.run(
        ["claude", "-p", "--output-format", "stream-json", "--verbose",
         "--model", "haiku", "--max-turns", "1", "--", "Hello"],
        capture_output=True, text=True, timeout=30,
        env={**os.environ, "ANTHROPIC_API_KEY": ""}
    )

    for line in result.stdout.strip().split("\n"):
        try:
            msg = json.loads(line)
            if msg.get("type") == "result":
                turns = msg.get("num_turns", 0)
                if turns <= 1:
                    return True, f"turns={turns}"
                return False, f"turns={turns} (expected ≤1)"
        except json.JSONDecodeError:
            continue

    return False, "no result"


def test_python_client_import() -> tuple[bool, str]:
    """Test: Python client imports correctly."""
    try:
        from claude_code_api import ClaudeClient, ClaudeResult, claude_chat, claude_json
        return True, "all exports available"
    except ImportError as e:
        return False, str(e)


def test_python_client_init() -> tuple[bool, str]:
    """Test: ClaudeClient initializes."""
    try:
        from claude_code_api import ClaudeClient
        client = ClaudeClient(model="haiku", max_turns=1)
        return True, f"model={client.model}"
    except Exception as e:
        return False, str(e)


def test_python_client_chat() -> tuple[bool, str]:
    """Test: ClaudeClient.chat() works."""
    try:
        from claude_code_api import ClaudeClient
        client = ClaudeClient(model="haiku", max_turns=1)
        result = client.chat("Reply with exactly: PYTEST")
        if "PYTEST" in result.text:
            return True, f"'{result.text.strip()[:30]}'"
        return False, f"unexpected: {result.text[:50]}"
    except Exception as e:
        return False, str(e)


def test_python_client_system_prompt() -> tuple[bool, str]:
    """Test: ClaudeClient.chat() with system prompt."""
    try:
        from claude_code_api import ClaudeClient
        client = ClaudeClient(model="haiku", max_turns=1)
        result = client.chat("What is 7+7?", system="Only respond with the number, nothing else")
        if "14" in result.text:
            return True, f"response={result.text.strip()}"
        return False, f"expected 14, got: {result.text}"
    except Exception as e:
        return False, str(e)


def test_python_client_json() -> tuple[bool, str]:
    """Test: ClaudeClient.chat_json() parses JSON."""
    try:
        from claude_code_api import ClaudeClient
        client = ClaudeClient(model="haiku", max_turns=1)
        data = client.chat_json(
            "What are the first 3 even numbers?",
            system='Return JSON only: {"numbers": [list of integers]}'
        )
        if isinstance(data, dict) and "numbers" in data:
            return True, f"numbers={data['numbers']}"
        return False, f"unexpected: {data}"
    except Exception as e:
        return False, str(e)


def test_python_helper_chat() -> tuple[bool, str]:
    """Test: claude_chat() helper function."""
    try:
        from claude_code_api import claude_chat
        response = claude_chat("Reply with: HELPER_OK")
        if "HELPER_OK" in response:
            return True, "helper works"
        return False, f"got: {response[:30]}"
    except Exception as e:
        return False, str(e)


def test_python_helper_json() -> tuple[bool, str]:
    """Test: claude_json() helper function."""
    try:
        from claude_code_api import claude_json
        data = claude_json("Return number 42", system='Return JSON: {"value": number}')
        if isinstance(data, dict) and data.get("value") == 42:
            return True, f"value={data['value']}"
        return False, f"got: {data}"
    except Exception as e:
        return False, str(e)


def test_json_extraction_direct() -> tuple[bool, str]:
    """Test: JSON extraction from direct JSON."""
    try:
        from claude_code_api import ClaudeClient
        client = ClaudeClient.__new__(ClaudeClient)
        result = client._extract_json('{"key": "value"}')
        if result == {"key": "value"}:
            return True, "direct parse"
        return False, f"got: {result}"
    except Exception as e:
        return False, str(e)


def test_json_extraction_markdown() -> tuple[bool, str]:
    """Test: JSON extraction from markdown block."""
    try:
        from claude_code_api import ClaudeClient
        client = ClaudeClient.__new__(ClaudeClient)
        text = """Here is the JSON:
```json
{"key": "value"}
```
"""
        result = client._extract_json(text)
        if result == {"key": "value"}:
            return True, "markdown block"
        return False, f"got: {result}"
    except Exception as e:
        return False, str(e)


def test_json_extraction_embedded() -> tuple[bool, str]:
    """Test: JSON extraction from embedded text."""
    try:
        from claude_code_api import ClaudeClient
        client = ClaudeClient.__new__(ClaudeClient)
        result = client._extract_json('The answer is {"key": "value"} as shown.')
        if result == {"key": "value"}:
            return True, "embedded"
        return False, f"got: {result}"
    except Exception as e:
        return False, str(e)


def test_error_handling_no_binary() -> tuple[bool, str]:
    """Test: Error when binary not found."""
    try:
        import shutil as sh
        from claude_code_api import ClaudeClient

        # Temporarily mock shutil.which
        original = sh.which
        sh.which = lambda x: None

        try:
            client = ClaudeClient()
            sh.which = original
            return False, "should have raised"
        except RuntimeError as e:
            sh.which = original
            if "not found" in str(e).lower():
                return True, "RuntimeError raised"
            return False, str(e)
    except Exception as e:
        return False, str(e)


# ═══════════════════════════════════════════════════════════════════════════════
# Main Test Runner
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Run all SDK specification tests."""
    runner = TestRunner()

    # Banner
    print()
    print(f"{Style.BOLD}{Style.CYAN}")
    print("   ╔═══════════════════════════════════════════════════════════════╗")
    print("   ║           Claude Agent SDK Specification Tests                ║")
    print("   ╚═══════════════════════════════════════════════════════════════╝")
    print(f"{Style.RESET}")

    # ─────────────────────────────────────────────────────────────────────────
    print_header("1. CLI Interface (Section 3)")
    # ─────────────────────────────────────────────────────────────────────────

    print_subheader("3.1 Base Command")
    runner.run_test("Claude CLI exists", test_cli_exists)
    runner.run_test("Claude CLI version", test_cli_version)

    print_subheader("3.2 Required Flags")
    runner.require_claude("--output-format stream-json", test_cli_stream_json)

    print_subheader("3.3 Optional Flags")
    runner.require_claude("--model selection", test_model_selection_haiku)
    runner.require_claude("--system-prompt", test_system_prompt)
    runner.require_claude("--max-turns", test_max_turns)

    # ─────────────────────────────────────────────────────────────────────────
    print_header("2. Message Protocol (Section 4)")
    # ─────────────────────────────────────────────────────────────────────────

    print_subheader("4.2 System Message")
    runner.require_claude("System init message fields", test_message_system_init)

    print_subheader("4.5 Result Message")
    runner.require_claude("Result success structure", test_message_result_success)

    # ─────────────────────────────────────────────────────────────────────────
    print_header("3. Python Client Implementation (Section 12)")
    # ─────────────────────────────────────────────────────────────────────────

    print_subheader("12.1 Client Initialization")
    runner.run_test("Import claude_code_api", test_python_client_import)
    runner.run_test("ClaudeClient.__init__", test_python_client_init)

    print_subheader("12.2 Core Methods")
    runner.require_claude("ClaudeClient.chat()", test_python_client_chat)
    runner.require_claude("ClaudeClient.chat() + system", test_python_client_system_prompt)
    runner.require_claude("ClaudeClient.chat_json()", test_python_client_json)

    print_subheader("12.3 Convenience Functions")
    runner.require_claude("claude_chat() helper", test_python_helper_chat)
    runner.require_claude("claude_json() helper", test_python_helper_json)

    # ─────────────────────────────────────────────────────────────────────────
    print_header("4. JSON Extraction (Response Parsing)")
    # ─────────────────────────────────────────────────────────────────────────

    print_subheader("Strategy 1: Direct JSON")
    runner.run_test("Parse direct JSON", test_json_extraction_direct)

    print_subheader("Strategy 2: Markdown Code Block")
    runner.run_test("Extract from ```json block", test_json_extraction_markdown)

    print_subheader("Strategy 3: Embedded JSON")
    runner.run_test("Extract from prose", test_json_extraction_embedded)

    # ─────────────────────────────────────────────────────────────────────────
    print_header("5. Error Handling (Section 11)")
    # ─────────────────────────────────────────────────────────────────────────

    print_subheader("11.1 Error Conditions")
    runner.run_test("Binary not found error", test_error_handling_no_binary)

    # ─────────────────────────────────────────────────────────────────────────
    # Summary
    # ─────────────────────────────────────────────────────────────────────────

    success = runner.print_summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
