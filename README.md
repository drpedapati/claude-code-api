# Claude Code API

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

A Python wrapper and HTTP API for the [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code).

This library provides convenient access to Claude models through the Claude Code binary, enabling LLM inference in Python applications without direct API key management. Authentication is handled automatically via Claude Code's OAuth flow.

## Installation

### Prerequisites

Claude Code CLI must be installed and authenticated:

```sh
npm install -g @anthropic-ai/claude-code
claude auth login
```

### From PyPI (coming soon)

```sh
pip install claude-code-api
```

### From GitHub

```sh
# Core library only
pip install git+https://github.com/drpedapati/claude-code-api.git

# With HTTP server support
pip install "git+https://github.com/drpedapati/claude-code-api.git#egg=claude-code-api[server]"
```

### From Source

```sh
git clone https://github.com/drpedapati/claude-code-api.git
cd claude-code-api
pip install -e ".[all]"
```

## Usage

### Python Library

```python
from claude_code_api import ClaudeClient, claude_chat, claude_json

# Initialize a client
client = ClaudeClient(model="haiku")

# Simple chat
result = client.chat("What is the capital of France?")
print(result.text)  # "Paris"

# With system prompt
result = client.chat(
    "Translate to Spanish: Hello, how are you?",
    system="You are a translator. Return only the translation, nothing else."
)
print(result.text)  # "Hola, ¿cómo estás?"

# Get structured JSON response
data = client.chat_json(
    "What are the first 5 prime numbers?",
    system="Return JSON: {primes: [numbers]}"
)
print(data["primes"])  # [2, 3, 5, 7, 11]
```

#### Convenience Functions

For quick, one-off queries:

```python
from claude_code_api import claude_chat, claude_json

# Simple text response
response = claude_chat("What is 2+2?")

# JSON response
data = claude_json(
    "List 3 primary colors",
    system="Return JSON: {colors: [strings]}"
)
```

### HTTP Server

Start the server:

```sh
# Using the CLI entry point
claude-code-api

# Or with uvicorn directly
uvicorn claude_code_api.server:app --host 0.0.0.0 --port 8000
```

#### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check for load balancers |
| `GET` | `/llm/status` | Verify Claude CLI availability |
| `POST` | `/llm/chat` | Send prompt, receive text response |
| `POST` | `/llm/json` | Send prompt, receive parsed JSON |

#### Example Requests

```sh
# Health check
curl http://localhost:8000/health

# Chat request
curl -X POST http://localhost:8000/llm/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is 2+2?", "model": "haiku"}'

# JSON response
curl -X POST http://localhost:8000/llm/json \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "List 3 colors",
    "system": "Return JSON: {colors: [strings]}",
    "model": "haiku"
  }'
```

API documentation is available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Models

| Model | Description | Use Case |
|-------|-------------|----------|
| `haiku` | Fast, cost-effective | High-volume queries, simple tasks |
| `sonnet` | Balanced performance | General-purpose use |
| `opus` | Most capable | Complex reasoning, nuanced tasks |

## Configuration

The Claude Code CLI handles all authentication automatically:

1. **OAuth (recommended)**: Run `claude auth login` once to authenticate via browser
2. **API Key fallback**: Set `ANTHROPIC_API_KEY` environment variable

> [!NOTE]
> This library automatically removes `ANTHROPIC_API_KEY` from the subprocess environment when calling the CLI. This prevents conflicts between API key authentication and Claude Code's OAuth flow.

## API Reference

### ClaudeClient

```python
ClaudeClient(
    model: str = "haiku",      # Model: haiku, sonnet, opus
    max_turns: int = 1,        # Conversation turns (1 for single-shot)
    binary_path: str = None    # Path to claude binary (auto-detected)
)
```

#### Methods

**`chat(prompt, system=None) -> ClaudeResult`**

Send a prompt and receive a response.

```python
result = client.chat("Hello!")
print(result.text)       # Response text
print(result.model)      # Model used
print(result.is_error)   # True if error occurred
```

**`chat_json(prompt, system=None) -> dict`**

Send a prompt and receive a parsed JSON response.

```python
data = client.chat_json(
    "What is 2+2?",
    system="Return JSON: {answer: number}"
)
# Returns: {"answer": 4}
```

Raises `ValueError` if the response cannot be parsed as JSON.

### ClaudeResult

```python
@dataclass
class ClaudeResult:
    text: str                    # Response text
    model: str                   # Model used
    is_error: bool = False       # Whether an error occurred
    error_message: str = None    # Error details if is_error is True
```

## Error Handling

```python
from claude_code_api import ClaudeClient

client = ClaudeClient()

# Check for errors in result
result = client.chat("Hello")
if result.is_error:
    print(f"Error: {result.error_message}")
else:
    print(result.text)

# JSON parsing errors raise ValueError
try:
    data = client.chat_json("Write a poem")  # Not JSON!
except ValueError as e:
    print(f"Could not parse JSON: {e}")

# CLI errors raise RuntimeError
try:
    data = client.chat_json("Hello")
except RuntimeError as e:
    print(f"Claude CLI error: {e}")
```

## Development

```sh
# Clone and install with dev dependencies
git clone https://github.com/drpedapati/claude-code-api.git
cd claude-code-api
pip install -e ".[dev]"

# Run tests
pytest

# Run tests (skip integration tests requiring CLI)
pytest -m "not integration"

# Format code
ruff format .

# Lint
ruff check .

# Type check
mypy claude_code_api
```

## Requirements

- Python 3.10+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) (Node.js 18+)

## License

MIT License - see [LICENSE](LICENSE) for details.

## Related

- [Claude Code Documentation](https://docs.anthropic.com/en/docs/claude-code)
- [Anthropic API Reference](https://docs.anthropic.com/en/api)
- [anthropic-sdk-python](https://github.com/anthropics/anthropic-sdk-python)
