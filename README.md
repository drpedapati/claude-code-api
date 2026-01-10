# Claude Code API

A Python wrapper and HTTP API for the [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) binary.

This package allows you to use Claude Code as an LLM backend in your applications, either as a Python library or via HTTP endpoints.

## Prerequisites

You need the Claude Code CLI installed and authenticated:

```bash
# Install Claude Code
npm install -g @anthropic-ai/claude-code

# Authenticate (opens browser for OAuth)
claude auth login
```

## Installation

### As a Python Library

```bash
# Install core library only
pip install git+https://github.com/drpedapati/claude-code-api.git

# Install with HTTP server support
pip install "git+https://github.com/drpedapati/claude-code-api.git#egg=claude-code-api[server]"
```

### From Source

```bash
git clone https://github.com/drpedapati/claude-code-api.git
cd claude-code-api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install with all dependencies
pip install -e ".[all]"
```

## Usage

### Python Library

```python
from claude_code_api import ClaudeClient, claude_chat, claude_json

# Using the client class
client = ClaudeClient(model="haiku")
result = client.chat("What is the capital of France?")
print(result.text)  # "Paris"

# With system prompt
result = client.chat(
    "Translate to Spanish: Hello",
    system="You are a translator. Return only the translation."
)
print(result.text)  # "Hola"

# Get JSON response
data = client.chat_json(
    "What are the first 5 prime numbers?",
    system="Return JSON: {primes: [numbers]}"
)
print(data["primes"])  # [2, 3, 5, 7, 11]

# Quick helpers
response = claude_chat("What is 2+2?")
data = claude_json("List 3 colors", system="Return JSON: {colors: [strings]}")
```

### HTTP Server

Start the server:

```bash
# Using the CLI
claude-code-api

# Or with uvicorn
uvicorn claude_code_api.server:app --host 0.0.0.0 --port 8000
```

API endpoints:

```bash
# Health check
curl http://localhost:8000/health

# Check status
curl http://localhost:8000/llm/status

# Chat
curl -X POST http://localhost:8000/llm/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is 2+2?", "model": "haiku"}'

# Get JSON response
curl -X POST http://localhost:8000/llm/json \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "List 3 colors",
    "system": "Return JSON: {colors: [strings]}",
    "model": "haiku"
  }'
```

API documentation available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Models

Available models:

| Model | Description | Best For |
|-------|-------------|----------|
| `haiku` | Fast, cost-effective | Quick queries, high volume |
| `sonnet` | Balanced performance | General use |
| `opus` | Most capable | Complex reasoning |

## Configuration

The Claude Code CLI handles authentication automatically. It will:

1. Use OAuth if you've logged in with `claude auth login`
2. Fall back to `ANTHROPIC_API_KEY` environment variable if set

**Note:** This library automatically removes `ANTHROPIC_API_KEY` from the subprocess environment to avoid conflicts with OAuth authentication. If you need API key auth, set it before installing Claude Code.

## Docker

```dockerfile
FROM python:3.11-slim

# Install Node.js for Claude Code CLI
RUN apt-get update && apt-get install -y nodejs npm
RUN npm install -g @anthropic-ai/claude-code

# Install Python package
COPY . /app
WORKDIR /app
RUN pip install -e ".[server]"

# Note: You'll need to handle authentication
# Either mount OAuth credentials or set ANTHROPIC_API_KEY

EXPOSE 8000
CMD ["claude-code-api"]
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
ruff format .

# Lint
ruff check .

# Type check
mypy claude_code_api
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Related

- [Claude Code Documentation](https://docs.anthropic.com/en/docs/claude-code)
- [Anthropic API](https://docs.anthropic.com/en/api)
