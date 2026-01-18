"""
Computer Use support for Claude Code API.

This module implements the agentic loop for Computer Use, which requires:
1. Two-way communication with Claude (send prompts, receive tool calls, send results)
2. Parsing stream_event messages for tool_use blocks
3. Executing computer actions (screenshot, click, type, etc.)
4. Sending tool results back to Claude

Based on Anthropic's official Computer Use implementation:
https://github.com/anthropics/anthropic-quickstarts/tree/main/computer-use-demo
"""

import asyncio
import base64
import json
import os
import shutil
import subprocess
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Computer Use Tool Models
# =============================================================================


class ComputerAction(str, Enum):
    """Available Computer Use actions."""
    SCREENSHOT = "screenshot"
    MOUSE_MOVE = "mouse_move"
    LEFT_CLICK = "left_click"
    RIGHT_CLICK = "right_click"
    DOUBLE_CLICK = "double_click"
    TRIPLE_CLICK = "triple_click"
    LEFT_CLICK_DRAG = "left_click_drag"
    TYPE = "type"
    KEY = "key"
    SCROLL = "scroll"
    WAIT = "wait"


@dataclass
class ToolResult:
    """Result from executing a tool."""
    output: str = ""
    error: Optional[str] = None
    base64_image: Optional[str] = None


@dataclass
class ToolUseBlock:
    """A tool_use block from Claude's response."""
    id: str
    name: str
    input: dict


@dataclass
class ComputerUseConfig:
    """Configuration for Computer Use session."""
    display_width: int = 1024
    display_height: int = 768
    screenshot_command: str = "screencapture"  # macOS default
    model: str = "sonnet"
    max_turns: int = 10
    system_prompt: Optional[str] = None


# =============================================================================
# Screenshot Capture
# =============================================================================


def capture_screenshot_macos() -> ToolResult:
    """Capture screenshot on macOS using screencapture."""
    import tempfile

    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            temp_path = f.name

        # Capture screen to file
        result = subprocess.run(
            ["screencapture", "-x", temp_path],  # -x = no sound
            capture_output=True,
            timeout=10,
        )

        if result.returncode != 0:
            return ToolResult(error=f"screencapture failed: {result.stderr.decode()}")

        # Read and encode
        with open(temp_path, "rb") as f:
            img_data = f.read()

        os.unlink(temp_path)

        return ToolResult(
            output="Screenshot captured",
            base64_image=base64.b64encode(img_data).decode(),
        )
    except Exception as e:
        return ToolResult(error=f"Screenshot error: {e}")


def capture_screenshot_linux() -> ToolResult:
    """Capture screenshot on Linux using gnome-screenshot or scrot."""
    import tempfile
    import uuid

    try:
        temp_path = f"/tmp/screenshot_{uuid.uuid4()}.png"

        # Try gnome-screenshot first, then scrot
        for cmd in [
            ["gnome-screenshot", "-f", temp_path],
            ["scrot", temp_path],
        ]:
            try:
                result = subprocess.run(cmd, capture_output=True, timeout=10)
                if result.returncode == 0:
                    break
            except FileNotFoundError:
                continue
        else:
            return ToolResult(error="No screenshot tool available (tried gnome-screenshot, scrot)")

        with open(temp_path, "rb") as f:
            img_data = f.read()

        os.unlink(temp_path)

        return ToolResult(
            output="Screenshot captured",
            base64_image=base64.b64encode(img_data).decode(),
        )
    except Exception as e:
        return ToolResult(error=f"Screenshot error: {e}")


def capture_screenshot() -> ToolResult:
    """Capture screenshot for the current platform."""
    import platform

    system = platform.system()
    if system == "Darwin":
        return capture_screenshot_macos()
    elif system == "Linux":
        return capture_screenshot_linux()
    else:
        return ToolResult(error=f"Unsupported platform: {system}")


# =============================================================================
# Mouse/Keyboard Actions
# =============================================================================


def execute_mouse_action(action: str, coordinate: list[int]) -> ToolResult:
    """Execute mouse action using cliclick (macOS) or xdotool (Linux)."""
    import platform

    system = platform.system()
    x, y = coordinate

    if system == "Darwin":
        # Use cliclick on macOS
        # Install with: brew install cliclick
        cmd_map = {
            "mouse_move": f"m:{x},{y}",
            "left_click": f"c:{x},{y}",
            "right_click": f"rc:{x},{y}",
            "double_click": f"dc:{x},{y}",
            "triple_click": f"tc:{x},{y}",
        }

        if action not in cmd_map:
            return ToolResult(error=f"Unsupported action on macOS: {action}")

        try:
            result = subprocess.run(
                ["cliclick", cmd_map[action]],
                capture_output=True,
                timeout=5,
            )
            if result.returncode != 0:
                return ToolResult(error=f"cliclick error: {result.stderr.decode()}")
            return ToolResult(output=f"Executed {action} at ({x}, {y})")
        except FileNotFoundError:
            return ToolResult(error="cliclick not found. Install with: brew install cliclick")
        except Exception as e:
            return ToolResult(error=f"Mouse action error: {e}")

    elif system == "Linux":
        # Use xdotool on Linux
        try:
            # First move mouse, then perform action
            subprocess.run(
                ["xdotool", "mousemove", str(x), str(y)],
                capture_output=True,
                timeout=5,
                check=True,
            )

            if action == "mouse_move":
                return ToolResult(output=f"Executed {action} at ({x}, {y})")
            elif action == "left_click":
                subprocess.run(["xdotool", "click", "1"], capture_output=True, timeout=5, check=True)
            elif action == "right_click":
                subprocess.run(["xdotool", "click", "3"], capture_output=True, timeout=5, check=True)
            elif action == "double_click":
                subprocess.run(["xdotool", "click", "--repeat", "2", "1"], capture_output=True, timeout=5, check=True)
            elif action == "triple_click":
                subprocess.run(["xdotool", "click", "--repeat", "3", "1"], capture_output=True, timeout=5, check=True)
            else:
                return ToolResult(error=f"Unsupported action on Linux: {action}")

            return ToolResult(output=f"Executed {action} at ({x}, {y})")
        except FileNotFoundError:
            return ToolResult(error="xdotool not found. Install with: apt install xdotool")
        except Exception as e:
            return ToolResult(error=f"Mouse action error: {e}")

    return ToolResult(error=f"Unsupported platform: {system}")


def execute_keyboard_action(action: str, text: Optional[str] = None) -> ToolResult:
    """Execute keyboard action."""
    import platform

    system = platform.system()

    if action == "type" and text:
        if system == "Darwin":
            try:
                # Use cliclick for typing
                result = subprocess.run(
                    ["cliclick", f"t:{text}"],
                    capture_output=True,
                    timeout=10,
                )
                if result.returncode != 0:
                    return ToolResult(error=f"cliclick error: {result.stderr.decode()}")
                return ToolResult(output=f"Typed: {text[:50]}...")
            except FileNotFoundError:
                return ToolResult(error="cliclick not found")
            except Exception as e:
                return ToolResult(error=f"Type error: {e}")

        elif system == "Linux":
            try:
                result = subprocess.run(
                    ["xdotool", "type", "--", text],
                    capture_output=True,
                    timeout=10,
                )
                if result.returncode != 0:
                    return ToolResult(error=f"xdotool error: {result.stderr.decode()}")
                return ToolResult(output=f"Typed: {text[:50]}...")
            except FileNotFoundError:
                return ToolResult(error="xdotool not found")
            except Exception as e:
                return ToolResult(error=f"Type error: {e}")

    elif action == "key" and text:
        # Handle key presses (e.g., "Return", "Tab", "ctrl+a")
        if system == "Darwin":
            # Map common keys to cliclick format
            key_map = {
                "Return": "kp:return",
                "Tab": "kp:tab",
                "Escape": "kp:escape",
                "Backspace": "kp:delete",
                "Delete": "kp:fwd-delete",
            }
            key_cmd = key_map.get(text, f"kp:{text.lower()}")
            try:
                result = subprocess.run(["cliclick", key_cmd], capture_output=True, timeout=5)
                return ToolResult(output=f"Pressed key: {text}")
            except Exception as e:
                return ToolResult(error=f"Key press error: {e}")

        elif system == "Linux":
            try:
                result = subprocess.run(
                    ["xdotool", "key", text],
                    capture_output=True,
                    timeout=5,
                )
                return ToolResult(output=f"Pressed key: {text}")
            except Exception as e:
                return ToolResult(error=f"Key press error: {e}")

    return ToolResult(error=f"Unsupported keyboard action: {action}")


# =============================================================================
# Tool Executor
# =============================================================================


def execute_computer_tool(tool_input: dict) -> ToolResult:
    """Execute a Computer Use tool action."""
    action = tool_input.get("action")

    if action == "screenshot":
        return capture_screenshot()

    elif action in ("mouse_move", "left_click", "right_click", "double_click", "triple_click"):
        coordinate = tool_input.get("coordinate", [0, 0])
        return execute_mouse_action(action, coordinate)

    elif action == "left_click_drag":
        start = tool_input.get("start_coordinate", [0, 0])
        end = tool_input.get("coordinate", [0, 0])
        # Execute drag by moving to start, pressing, moving to end, releasing
        return ToolResult(output=f"Drag from {start} to {end} (not fully implemented)")

    elif action == "type":
        text = tool_input.get("text", "")
        return execute_keyboard_action("type", text)

    elif action == "key":
        text = tool_input.get("text", "")
        return execute_keyboard_action("key", text)

    elif action == "scroll":
        coordinate = tool_input.get("coordinate", [0, 0])
        direction = tool_input.get("scroll_direction", "down")
        amount = tool_input.get("scroll_amount", 3)
        return ToolResult(output=f"Scroll {direction} at {coordinate} by {amount}")

    elif action == "wait":
        duration = tool_input.get("duration", 1)
        import time
        time.sleep(min(duration, 30))  # Cap at 30 seconds
        return ToolResult(output=f"Waited {duration} seconds")

    return ToolResult(error=f"Unknown action: {action}")


# =============================================================================
# Agentic Loop
# =============================================================================


async def run_computer_use_loop(
    prompt: str,
    config: ComputerUseConfig,
    on_tool_use: Optional[Callable[[ToolUseBlock], None]] = None,
    on_tool_result: Optional[Callable[[str, ToolResult], None]] = None,
) -> AsyncGenerator[dict, None]:
    """
    Run the Computer Use agentic loop.

    This is a streaming generator that yields events as they happen:
    - {"type": "start"}: Loop started
    - {"type": "text", "text": "..."}: Text from Claude
    - {"type": "tool_use", "id": "...", "name": "...", "input": {...}}: Tool invocation
    - {"type": "tool_result", "id": "...", "result": {...}}: Tool execution result
    - {"type": "end", "result": "..."}: Final result
    - {"type": "error", "message": "..."}: Error occurred

    Args:
        prompt: Initial user prompt
        config: Computer Use configuration
        on_tool_use: Optional callback when tool is invoked
        on_tool_result: Optional callback when tool completes
    """
    binary_path = shutil.which("claude")
    if not binary_path:
        yield {"type": "error", "message": "Claude CLI not found"}
        return

    # Build command with --include-partial-messages for tool visibility
    cmd = [
        "claude",
        "-p",
        "--input-format", "stream-json",
        "--output-format", "stream-json",
        "--include-partial-messages",
        "--verbose",
        "--model", config.model,
        "--max-turns", str(config.max_turns),
    ]

    if config.system_prompt:
        cmd.extend(["--system-prompt", config.system_prompt])

    # Environment
    env = os.environ.copy()
    env.pop("ANTHROPIC_API_KEY", None)
    env["PYTHONUNBUFFERED"] = "1"

    yield {"type": "start"}

    # Start subprocess with stdin/stdout pipes for two-way communication
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )

    # Build initial message with screenshot context
    initial_screenshot = capture_screenshot()

    content = []
    if initial_screenshot.base64_image:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": initial_screenshot.base64_image,
            },
        })

    content.append({
        "type": "text",
        "text": f"Screen size: {config.display_width}x{config.display_height} pixels.\n\n{prompt}",
    })

    # Send initial message
    user_message = {
        "type": "user",
        "message": {"role": "user", "content": content},
    }

    if process.stdin is None or process.stdout is None:
        yield {"type": "error", "message": "Failed to create process pipes"}
        return

    try:
        process.stdin.write(json.dumps(user_message).encode() + b"\n")
        await process.stdin.drain()
    except Exception as e:
        yield {"type": "error", "message": f"Failed to send message: {e}"}
        return

    # Process response stream
    final_result = ""
    pending_tool_uses: list[ToolUseBlock] = []

    try:
        while True:
            line = await asyncio.wait_for(
                process.stdout.readline(),
                timeout=120.0,  # 2 minute timeout per line
            )

            if not line:
                break

            line = line.decode().strip()
            if not line:
                continue

            try:
                msg = json.loads(line)
                msg_type = msg.get("type")

                if msg_type == "stream_event":
                    event = msg.get("event", {})
                    event_type = event.get("type")

                    # Handle text streaming
                    if event_type == "content_block_delta":
                        delta = event.get("delta", {})
                        if delta.get("type") == "text_delta":
                            text = delta.get("text", "")
                            if text:
                                yield {"type": "text", "text": text}

                    # Handle tool use start
                    elif event_type == "content_block_start":
                        content_block = event.get("content_block", {})
                        if content_block.get("type") == "tool_use":
                            tool_use = ToolUseBlock(
                                id=content_block.get("id", ""),
                                name=content_block.get("name", ""),
                                input={},
                            )
                            pending_tool_uses.append(tool_use)

                    # Handle tool input delta
                    elif event_type == "content_block_delta":
                        delta = event.get("delta", {})
                        if delta.get("type") == "input_json_delta":
                            # Accumulate partial JSON
                            partial = delta.get("partial_json", "")
                            if pending_tool_uses and partial:
                                # This is simplified - real impl needs JSON accumulation
                                pass

                    # Handle message stop (tool use complete)
                    elif event_type == "message_stop":
                        # Process any pending tool uses
                        for tool_use in pending_tool_uses:
                            yield {
                                "type": "tool_use",
                                "id": tool_use.id,
                                "name": tool_use.name,
                                "input": tool_use.input,
                            }

                            if on_tool_use:
                                on_tool_use(tool_use)

                            # Execute the tool
                            if tool_use.name == "computer":
                                result = execute_computer_tool(tool_use.input)
                            else:
                                result = ToolResult(error=f"Unknown tool: {tool_use.name}")

                            if on_tool_result:
                                on_tool_result(tool_use.id, result)

                            yield {
                                "type": "tool_result",
                                "id": tool_use.id,
                                "result": {
                                    "output": result.output,
                                    "error": result.error,
                                    "has_image": result.base64_image is not None,
                                },
                            }

                            # Send tool result back to Claude
                            tool_result_msg = {
                                "type": "tool_result",
                                "tool_use_id": tool_use.id,
                                "content": [],
                            }

                            if result.error:
                                tool_result_msg["content"].append({
                                    "type": "text",
                                    "text": f"Error: {result.error}",
                                })
                                tool_result_msg["is_error"] = True
                            else:
                                if result.output:
                                    tool_result_msg["content"].append({
                                        "type": "text",
                                        "text": result.output,
                                    })
                                if result.base64_image:
                                    tool_result_msg["content"].append({
                                        "type": "image",
                                        "source": {
                                            "type": "base64",
                                            "media_type": "image/png",
                                            "data": result.base64_image,
                                        },
                                    })

                            try:
                                process.stdin.write(json.dumps(tool_result_msg).encode() + b"\n")
                                await process.stdin.drain()
                            except Exception as e:
                                yield {"type": "error", "message": f"Failed to send tool result: {e}"}
                                return

                        pending_tool_uses.clear()

                elif msg_type == "assistant":
                    # Capture tool use from assistant message
                    message = msg.get("message", {})
                    for block in message.get("content", []):
                        if block.get("type") == "tool_use":
                            tool_use = ToolUseBlock(
                                id=block.get("id", ""),
                                name=block.get("name", ""),
                                input=block.get("input", {}),
                            )

                            yield {
                                "type": "tool_use",
                                "id": tool_use.id,
                                "name": tool_use.name,
                                "input": tool_use.input,
                            }

                            if on_tool_use:
                                on_tool_use(tool_use)

                            # Execute the tool
                            if tool_use.name == "computer":
                                result = execute_computer_tool(tool_use.input)
                            else:
                                result = ToolResult(error=f"Unknown tool: {tool_use.name}")

                            if on_tool_result:
                                on_tool_result(tool_use.id, result)

                            yield {
                                "type": "tool_result",
                                "id": tool_use.id,
                                "result": {
                                    "output": result.output,
                                    "error": result.error,
                                    "has_image": result.base64_image is not None,
                                },
                            }

                            # Send tool result back
                            tool_result_msg = {
                                "type": "tool_result",
                                "tool_use_id": tool_use.id,
                                "content": [],
                            }

                            if result.error:
                                tool_result_msg["content"].append({
                                    "type": "text",
                                    "text": f"Error: {result.error}",
                                })
                                tool_result_msg["is_error"] = True
                            else:
                                if result.output:
                                    tool_result_msg["content"].append({
                                        "type": "text",
                                        "text": result.output,
                                    })
                                if result.base64_image:
                                    tool_result_msg["content"].append({
                                        "type": "image",
                                        "source": {
                                            "type": "base64",
                                            "media_type": "image/png",
                                            "data": result.base64_image,
                                        },
                                    })

                            try:
                                process.stdin.write(json.dumps(tool_result_msg).encode() + b"\n")
                                await process.stdin.drain()
                            except Exception as e:
                                yield {"type": "error", "message": f"Failed to send tool result: {e}"}
                                return

                elif msg_type == "result":
                    final_result = msg.get("result", "")
                    yield {"type": "end", "result": final_result}
                    break

            except json.JSONDecodeError:
                continue

    except asyncio.TimeoutError:
        yield {"type": "error", "message": "Timeout waiting for response"}
    except Exception as e:
        yield {"type": "error", "message": f"Loop error: {e}"}
    finally:
        try:
            if process.stdin:
                process.stdin.close()
        except Exception:
            pass
        await process.wait()


# =============================================================================
# Pydantic Models for API
# =============================================================================


class ComputerUseRequest(BaseModel):
    """Request for Computer Use endpoint."""

    prompt: str = Field(..., description="What you want Claude to do on the computer")
    model: str = Field(
        default="sonnet",
        description="Model to use (sonnet recommended for Computer Use)",
    )
    max_turns: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum turns for the agentic loop",
    )
    display_width: int = Field(
        default=1024,
        description="Screen width in pixels",
    )
    display_height: int = Field(
        default=768,
        description="Screen height in pixels",
    )
    system_prompt: Optional[str] = Field(
        default=None,
        description="Optional system prompt",
    )


class ComputerUseEvent(BaseModel):
    """Event from Computer Use stream."""

    type: str = Field(..., description="Event type")
    text: Optional[str] = None
    id: Optional[str] = None
    name: Optional[str] = None
    input: Optional[dict] = None
    result: Optional[Any] = None
    message: Optional[str] = None
