# ============================================================================
# Claude Code API - Production Docker Image
# ============================================================================
# Multi-stage build for minimal image size
# Uses uv for fast, reproducible installs
# ============================================================================

# ----------------------------------------------------------------------------
# Stage 1: Build dependencies
# ----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set environment variables
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

# Install dependencies first (better layer caching)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --extra server

# Copy source and install project
COPY claude_code_api/ ./claude_code_api/
COPY README.md ./
RUN uv sync --frozen --no-dev --extra server

# ----------------------------------------------------------------------------
# Stage 2: Runtime image
# ----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Install Node.js for Claude Code CLI
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g @anthropic-ai/claude-code

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser \
    && mkdir -p /home/appuser/.claude \
    && chown -R appuser:appuser /home/appuser/.claude

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --from=builder /app/claude_code_api ./claude_code_api

# Set environment
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the server
CMD ["uvicorn", "claude_code_api.server:app", "--host", "0.0.0.0", "--port", "8000"]
