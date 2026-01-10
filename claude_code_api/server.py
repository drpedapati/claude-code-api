"""
FastAPI server exposing Claude Code as an HTTP API.

Endpoints:
    GET  /health          - Health check
    GET  /llm/status      - Check if Claude CLI is available
    GET  /llm/models      - List available models
    POST /llm/chat        - Send a prompt, get text response
    POST /llm/json        - Send a prompt, get JSON response

Run with:
    uvicorn claude_code_api.server:app --host 0.0.0.0 --port 7742
"""

import shutil
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
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
