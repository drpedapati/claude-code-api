"""
FastAPI server exposing Claude Code as an HTTP API.

Endpoints:
    GET  /health             - Health check
    GET  /llm/status         - Check if Claude CLI is available
    GET  /llm/models         - List available models
    POST /llm/chat           - Send a prompt, get text response
    POST /llm/chat/stream    - Send a prompt, get streaming response (SSE)
    POST /llm/json           - Send a prompt, get JSON response
    POST /llm/query          - Full SDK query with tools, sessions, usage tracking
    POST /llm/query/stream   - Full SDK query with token-level streaming

Run with:
    uvicorn claude_code_api.server:app --host 0.0.0.0 --port 7742
"""

import asyncio
import json
import os
import shutil
from typing import AsyncGenerator, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .auth import verify_api_key
from .client import ClaudeClient

app = FastAPI(
    title="Claude Code API",
    description="HTTP API wrapper for the Claude Code CLI binary",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# =============================================================================
# Request/Response Models
# =============================================================================


class ChatRequest(BaseModel):
    """Request body for chat endpoints."""

    prompt: str = Field(..., description="The user prompt to send to Claude")
    system: Optional[str] = Field(
        default=None, description="Optional system prompt to customize behavior"
    )
    model: str = Field(
        default="haiku",
        description="Model to use: haiku (fast), sonnet (balanced), opus (powerful)",
    )
    max_turns: int = Field(
        default=1, ge=1, le=10, description="Maximum conversation turns"
    )


class ChatResponse(BaseModel):
    """Response from chat endpoint."""

    text: str = Field(..., description="The response text from Claude")
    model: str = Field(..., description="Model used for the response")
    is_error: bool = Field(default=False, description="Whether an error occurred")
    error_message: Optional[str] = Field(
        default=None, description="Error message if is_error is true"
    )


class StatusResponse(BaseModel):
    """Response from status endpoint."""

    available: bool = Field(..., description="Whether Claude CLI is available")
    binary_path: Optional[str] = Field(
        default=None, description="Path to the Claude binary"
    )
    version: Optional[str] = Field(
        default=None, description="Claude CLI version if available"
    )


class HealthResponse(BaseModel):
    """Response from health check endpoint."""

    status: str = Field(default="ok", description="Service status")
    service: str = Field(default="claude-code-api", description="Service name")
    version: str = Field(default="0.1.0", description="API version")


class ModelInfo(BaseModel):
    """Information about a Claude model."""

    id: str = Field(..., description="Model identifier (alias for Claude Code CLI)")
    api_id: str = Field(..., description="Official Anthropic API model ID")
    name: str = Field(..., description="Human-readable model name")
    description: str = Field(..., description="Model description")
    context_window: int = Field(..., description="Context window size in tokens")
    max_output: int = Field(..., description="Maximum output tokens")
    input_price: str = Field(..., description="Price per million input tokens")
    output_price: str = Field(..., description="Price per million output tokens")


class ModelsResponse(BaseModel):
    """Response from models endpoint."""

    models: list[ModelInfo] = Field(..., description="Available models")


# Available models - aligned with official Anthropic API
# See: https://platform.claude.com/docs/en/about-claude/models/overview
AVAILABLE_MODELS = [
    ModelInfo(
        id="haiku",
        api_id="claude-haiku-4-5-20251001",
        name="Claude Haiku 4.5",
        description="Our fastest model with near-frontier intelligence",
        context_window=200_000,
        max_output=64_000,
        input_price="$1",
        output_price="$5",
    ),
    ModelInfo(
        id="sonnet",
        api_id="claude-sonnet-4-5-20250929",
        name="Claude Sonnet 4.5",
        description="Our smart model for complex agents and coding",
        context_window=200_000,
        max_output=64_000,
        input_price="$3",
        output_price="$15",
    ),
    ModelInfo(
        id="opus",
        api_id="claude-opus-4-5-20251101",
        name="Claude Opus 4.5",
        description="Premium model combining maximum intelligence with practical performance",
        context_window=200_000,
        max_output=64_000,
        input_price="$5",
        output_price="$25",
    ),
]


# =============================================================================
# Query API Models (Full SDK Support)
# =============================================================================


class ImageInput(BaseModel):
    """Base64-encoded image for multimodal queries."""

    data: str = Field(..., description="Base64-encoded image data")
    media_type: str = Field(
        default="image/png",
        description="MIME type: image/png, image/jpeg, image/gif, image/webp",
    )


class UsageInfo(BaseModel):
    """Token usage information."""

    input_tokens: int = Field(default=0, description="Input tokens used")
    output_tokens: int = Field(default=0, description="Output tokens generated")
    cache_read_input_tokens: int = Field(default=0, description="Tokens read from cache")
    cache_creation_input_tokens: int = Field(default=0, description="Tokens cached")


class ModelUsageInfo(BaseModel):
    """Per-model usage breakdown."""

    input_tokens: int = Field(default=0, alias="inputTokens")
    output_tokens: int = Field(default=0, alias="outputTokens")
    cache_read_input_tokens: int = Field(default=0, alias="cacheReadInputTokens")
    cache_creation_input_tokens: int = Field(default=0, alias="cacheCreationInputTokens")
    cost_usd: float = Field(default=0.0, alias="costUSD")

    class Config:
        populate_by_name = True


class QueryRequest(BaseModel):
    """
    Full SDK query request with images, tool control, sessions, and budgets.

    This is the advanced endpoint that exposes the full Claude Agent SDK capabilities.
    For simple text queries, use /llm/chat instead.
    """

    prompt: str = Field(..., description="The user prompt to send to Claude")
    images: Optional[list[ImageInput]] = Field(
        default=None,
        description="Optional images to include (base64-encoded). Supports PNG, JPEG, GIF, WebP.",
    )
    system: Optional[str] = Field(
        default=None, description="Optional system prompt to customize behavior"
    )
    model: str = Field(
        default="haiku",
        description="Model to use: haiku (fast), sonnet (balanced), opus (powerful)",
    )
    max_turns: int = Field(
        default=1, ge=1, le=100, description="Maximum conversation turns"
    )

    # Tool control
    allowed_tools: Optional[list[str]] = Field(
        default=None,
        description="Whitelist of tools Claude can use (e.g., ['Bash', 'Read', 'Edit']). Empty list disables all tools.",
    )
    disallowed_tools: Optional[list[str]] = Field(
        default=None,
        description="Blacklist of tools Claude cannot use (e.g., ['Bash(git:*)', 'Write'])",
    )

    # Session management
    session_id: Optional[str] = Field(
        default=None,
        description="UUID of a previous session to resume. Must be a valid UUID.",
    )
    continue_session: bool = Field(
        default=False,
        description="Continue the most recent session (alternative to session_id)",
    )

    # Budget control
    max_budget_usd: Optional[float] = Field(
        default=None,
        ge=0.01,
        le=100.0,
        description="Maximum dollar amount to spend on this query",
    )


class QueryResponse(BaseModel):
    """
    Full SDK response with usage tracking, costs, and session info.

    Contains all metadata from the Claude Agent SDK result message.
    """

    text: str = Field(..., description="The response text from Claude")
    model: str = Field(..., description="Model used for the response")

    # Session info
    session_id: Optional[str] = Field(
        default=None, description="Session ID for resuming this conversation"
    )
    num_turns: int = Field(default=1, description="Number of conversation turns")

    # Cost tracking
    total_cost_usd: float = Field(default=0.0, description="Total cost in USD")
    duration_ms: int = Field(default=0, description="Total duration in milliseconds")

    # Usage stats
    usage: Optional[UsageInfo] = Field(default=None, description="Token usage breakdown")
    model_usage: Optional[dict[str, ModelUsageInfo]] = Field(
        default=None, description="Per-model usage breakdown"
    )

    # Status
    is_error: bool = Field(default=False, description="Whether an error occurred")
    error_message: Optional[str] = Field(
        default=None, description="Error message if is_error is true"
    )


# =============================================================================
# Endpoints
# =============================================================================


@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    """
    Health check endpoint.

    Returns basic service information for load balancers and monitoring.
    """
    return HealthResponse()


@app.get("/llm/models", response_model=ModelsResponse, tags=["LLM"])
def llm_models():
    """
    List available Claude models.

    Returns the models that can be used with the chat and json endpoints.
    """
    return ModelsResponse(models=AVAILABLE_MODELS)


@app.get("/llm/status", response_model=StatusResponse, tags=["LLM"])
def llm_status(_: Optional[str] = Depends(verify_api_key)):
    """
    Check if the Claude CLI binary is available.

    This endpoint verifies that:
    1. The `claude` binary is in PATH
    2. It can be executed successfully

    Use this to verify the service is properly configured before making requests.
    """
    import subprocess

    binary_path = shutil.which("claude")

    if not binary_path:
        return StatusResponse(available=False)

    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        version = result.stdout.strip() if result.returncode == 0 else None
        return StatusResponse(
            available=result.returncode == 0,
            binary_path=binary_path,
            version=version,
        )
    except Exception:
        return StatusResponse(available=False, binary_path=binary_path)


@app.post("/llm/chat", response_model=ChatResponse, tags=["LLM"])
def llm_chat(request: ChatRequest, _: Optional[str] = Depends(verify_api_key)):
    """
    Send a prompt to Claude and get a text response.

    This endpoint provides direct access to Claude via the CLI binary.
    Authentication is handled automatically by the binary.

    **Example Request:**
    ```json
    {
        "prompt": "What is the capital of France?",
        "model": "haiku"
    }
    ```

    **Example Response:**
    ```json
    {
        "text": "The capital of France is Paris.",
        "model": "haiku",
        "is_error": false
    }
    ```
    """
    try:
        client = ClaudeClient(model=request.model, max_turns=request.max_turns)
        result = client.chat(request.prompt, system=request.system)

        return ChatResponse(
            text=result.text,
            model=result.model,
            is_error=result.is_error,
            error_message=result.error_message,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


async def stream_chat_response(
    prompt: str,
    model: str = "haiku",
    system: Optional[str] = None,
    max_turns: int = 1,
) -> AsyncGenerator[str, None]:
    """
    Stream chat response from Claude CLI using SSE format.

    Yields Server-Sent Events with token-level streaming.
    """
    binary_path = shutil.which("claude")
    if not binary_path:
        yield f"data: {json.dumps({'type': 'error', 'message': 'Claude CLI not found'})}\n\n"
        return

    cmd = [
        "claude",
        "-p",
        "--output-format", "stream-json",
        "--include-partial-messages",
        "--verbose",
        "--model", model,
        "--max-turns", str(max_turns),
    ]

    if system:
        cmd.extend(["--system-prompt", system])

    cmd.extend(["--", prompt])

    # Remove ANTHROPIC_API_KEY to force CLI auth
    env = os.environ.copy()
    env.pop("ANTHROPIC_API_KEY", None)
    env["PYTHONUNBUFFERED"] = "1"

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )

    yield f"data: {json.dumps({'type': 'start'})}\n\n"

    has_streamed = False

    try:
        while True:
            line = await process.stdout.readline()
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

                    if event_type == "content_block_delta":
                        delta = event.get("delta", {})
                        if delta.get("type") == "text_delta":
                            text = delta.get("text", "")
                            if text:
                                has_streamed = True
                                yield f"data: {json.dumps({'type': 'chunk', 'text': text})}\n\n"

                elif msg_type == "result" and not has_streamed:
                    result_text = msg.get("result", "")
                    if result_text:
                        yield f"data: {json.dumps({'type': 'chunk', 'text': result_text})}\n\n"

            except json.JSONDecodeError:
                continue

    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    finally:
        await process.wait()
        yield f"data: {json.dumps({'type': 'end'})}\n\n"


@app.post("/llm/chat/stream", tags=["LLM"])
async def llm_chat_stream(request: ChatRequest, _: Optional[str] = Depends(verify_api_key)):
    """
    Send a prompt to Claude and get a streaming response.

    Returns Server-Sent Events (SSE) with token-level streaming.
    Each event contains a JSON object with type and data.

    **Event Types:**
    - `start`: Stream started
    - `chunk`: Text chunk (has `text` field)
    - `end`: Stream complete
    - `error`: Error occurred (has `message` field)

    **Example Usage (curl):**
    ```bash
    curl -N -X POST http://localhost:7742/llm/chat/stream \\
      -H "Content-Type: application/json" \\
      -d '{"prompt": "Tell me a short story", "model": "haiku"}'
    ```

    **Example Events:**
    ```
    data: {"type": "start"}
    data: {"type": "chunk", "text": "Once"}
    data: {"type": "chunk", "text": " upon"}
    data: {"type": "chunk", "text": " a"}
    data: {"type": "chunk", "text": " time"}
    data: {"type": "end"}
    ```
    """
    return StreamingResponse(
        stream_chat_response(
            prompt=request.prompt,
            model=request.model,
            system=request.system,
            max_turns=request.max_turns,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/llm/json", tags=["LLM"])
def llm_json(request: ChatRequest, _: Optional[str] = Depends(verify_api_key)):
    """
    Send a prompt to Claude and get a parsed JSON response.

    The prompt should ask Claude to return JSON. This endpoint parses
    the response and returns the JSON object directly.

    **Tips for reliable JSON responses:**
    - Use a system prompt like: "Return ONLY valid JSON. No other text."
    - Specify the expected format in the prompt

    **Example Request:**
    ```json
    {
        "prompt": "What are the first 3 prime numbers?",
        "system": "Return JSON with format: {primes: [numbers]}",
        "model": "haiku"
    }
    ```

    **Example Response:**
    ```json
    {
        "primes": [2, 3, 5]
    }
    ```
    """
    try:
        client = ClaudeClient(model=request.model, max_turns=request.max_turns)
        result = client.chat_json(request.prompt, system=request.system)
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"JSON parse error: {str(e)}")
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# =============================================================================
# Query API (Full SDK Support)
# =============================================================================


async def execute_query(request: QueryRequest) -> QueryResponse:
    """
    Execute a full SDK query using --input-format stream-json.

    This provides access to images, tool control, sessions, and usage tracking.
    """
    binary_path = shutil.which("claude")
    if not binary_path:
        return QueryResponse(
            text="",
            model=request.model,
            is_error=True,
            error_message="Claude CLI not found",
        )

    # Build command
    cmd = [
        "claude",
        "-p",
        "--input-format", "stream-json",
        "--output-format", "stream-json",
        "--verbose",
        "--model", request.model,
        "--max-turns", str(request.max_turns),
    ]

    # System prompt
    if request.system:
        cmd.extend(["--system-prompt", request.system])

    # Tool control
    if request.allowed_tools is not None:
        if len(request.allowed_tools) == 0:
            cmd.extend(["--tools", ""])  # Disable all tools
        else:
            cmd.extend(["--allowedTools", ",".join(request.allowed_tools)])

    if request.disallowed_tools:
        cmd.extend(["--disallowedTools", ",".join(request.disallowed_tools)])

    # Session management
    if request.session_id:
        cmd.extend(["--resume", request.session_id])
    elif request.continue_session:
        cmd.extend(["--continue"])

    # Budget control
    if request.max_budget_usd:
        cmd.extend(["--max-budget-usd", str(request.max_budget_usd)])

    # Build message content
    content = []

    # Add images first
    if request.images:
        for img in request.images:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": img.media_type,
                    "data": img.data,
                },
            })

    # Add text prompt
    content.append({"type": "text", "text": request.prompt})

    # Build the user message
    user_message = {
        "type": "user",
        "message": {
            "role": "user",
            "content": content,
        },
    }

    # Remove ANTHROPIC_API_KEY to force CLI auth
    env = os.environ.copy()
    env.pop("ANTHROPIC_API_KEY", None)
    env["PYTHONUNBUFFERED"] = "1"

    # Execute with stdin input
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )

    # Send message via stdin
    stdin_data = json.dumps(user_message).encode()
    stdout, stderr = await process.communicate(input=stdin_data)

    # Parse output
    result_text = ""
    session_id = None
    total_cost_usd = 0.0
    duration_ms = 0
    num_turns = 1
    usage_info = None
    model_usage = None
    is_error = False
    error_message = None

    for line in stdout.decode().strip().split("\n"):
        if not line.strip():
            continue
        try:
            msg = json.loads(line)
            msg_type = msg.get("type")

            if msg_type == "result":
                result_text = msg.get("result", "")
                session_id = msg.get("session_id")
                total_cost_usd = msg.get("total_cost_usd", 0.0)
                duration_ms = msg.get("duration_ms", 0)
                num_turns = msg.get("num_turns", 1)
                is_error = msg.get("is_error", False)

                # Parse usage
                usage = msg.get("usage", {})
                if usage:
                    usage_info = UsageInfo(
                        input_tokens=usage.get("input_tokens", 0),
                        output_tokens=usage.get("output_tokens", 0),
                        cache_read_input_tokens=usage.get("cache_read_input_tokens", 0),
                        cache_creation_input_tokens=usage.get("cache_creation_input_tokens", 0),
                    )

                # Parse model usage
                raw_model_usage = msg.get("modelUsage", {})
                if raw_model_usage:
                    model_usage = {}
                    for model_name, stats in raw_model_usage.items():
                        model_usage[model_name] = ModelUsageInfo(
                            inputTokens=stats.get("inputTokens", 0),
                            outputTokens=stats.get("outputTokens", 0),
                            cacheReadInputTokens=stats.get("cacheReadInputTokens", 0),
                            cacheCreationInputTokens=stats.get("cacheCreationInputTokens", 0),
                            costUSD=stats.get("costUSD", 0.0),
                        )

        except json.JSONDecodeError:
            continue

    # Check for errors
    if process.returncode != 0 and not result_text:
        is_error = True
        error_message = f"Exit code {process.returncode}"
        if stderr:
            error_message += f": {stderr.decode()[:500]}"

    return QueryResponse(
        text=result_text,
        model=request.model,
        session_id=session_id,
        num_turns=num_turns,
        total_cost_usd=total_cost_usd,
        duration_ms=duration_ms,
        usage=usage_info,
        model_usage=model_usage,
        is_error=is_error,
        error_message=error_message,
    )


@app.post("/llm/query", response_model=QueryResponse, tags=["LLM"])
async def llm_query(request: QueryRequest, _: Optional[str] = Depends(verify_api_key)):
    """
    Full SDK query with images, tool control, sessions, and usage tracking.

    This is the advanced endpoint that exposes the complete Claude Agent SDK capabilities.
    For simple text-only queries, use /llm/chat instead.

    **Features:**
    - **Images**: Include base64-encoded images for multimodal queries
    - **Tool Control**: Whitelist or blacklist tools Claude can use
    - **Sessions**: Resume previous conversations with session_id
    - **Budgets**: Set maximum spend per query
    - **Usage Tracking**: Get detailed token counts and costs

    **Example Request (with image):**
    ```json
    {
        "prompt": "What color is this image?",
        "images": [{"data": "iVBORw0KGgo...", "media_type": "image/png"}],
        "model": "haiku"
    }
    ```

    **Example Request (with tool control):**
    ```json
    {
        "prompt": "List files in the current directory",
        "allowed_tools": ["Bash", "Read"],
        "max_turns": 3,
        "model": "sonnet"
    }
    ```

    **Example Request (resume session):**
    ```json
    {
        "prompt": "Continue our previous conversation",
        "session_id": "abc123-def456-...",
        "model": "haiku"
    }
    ```

    **Example Response:**
    ```json
    {
        "text": "The image shows a red square.",
        "model": "haiku",
        "session_id": "abc123-def456-...",
        "num_turns": 1,
        "total_cost_usd": 0.0025,
        "duration_ms": 1234,
        "usage": {
            "input_tokens": 150,
            "output_tokens": 25,
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 100
        },
        "is_error": false
    }
    ```
    """
    try:
        return await execute_query(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# =============================================================================
# CLI Entry Point
# =============================================================================


def main():
    """Run the server from command line."""
    import uvicorn

    uvicorn.run(
        "claude_code_api.server:app",
        host="0.0.0.0",
        port=7742,
        reload=False,
    )


if __name__ == "__main__":
    main()
