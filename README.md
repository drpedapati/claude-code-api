# Claude Code API

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

A Python wrapper and HTTP API for the [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code).

Access Claude models through the Claude Code binary without direct API key management. Authentication is handled automatically via Claude Code's OAuth flow.

## Quick Start

```sh
# Install Claude Code CLI
npm install -g @anthropic-ai/claude-code
claude auth login

# Clone and run
git clone https://github.com/drpedapati/claude-code-api.git
cd claude-code-api
make server

# Test it
curl http://localhost:7742/health
curl -X POST http://localhost:7742/llm/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is 2+2?", "model": "haiku"}'
```

## Installation

### From Source (Recommended)

```sh
git clone https://github.com/drpedapati/claude-code-api.git
cd claude-code-api

# Using uv (fast)
uv sync

# Or pip
pip install -e ".[all]"
```

### From GitHub

```sh
pip install git+https://github.com/drpedapati/claude-code-api.git
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

# Get structured JSON response
data = client.chat_json(
    "What are the first 5 prime numbers?",
    system="Return JSON: {primes: [numbers]}"
)
print(data["primes"])  # [2, 3, 5, 7, 11]

# Convenience functions for one-off queries
response = claude_chat("What is 2+2?")
data = claude_json("List 3 colors", system="Return JSON: {colors: [strings]}")
```

### HTTP Server

```sh
# Start server (port 7742)
make server

# Or directly
uvicorn claude_code_api.server:app --host 0.0.0.0 --port 7742
```

#### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/llm/status` | Claude CLI availability |
| `GET` | `/llm/models` | List available models |
| `POST` | `/llm/chat` | Text response |
| `POST` | `/llm/json` | JSON response |

#### Example Requests

```sh
# Health check
curl http://localhost:7742/health
# {"status":"ok","service":"claude-code-api","version":"0.1.0"}

# Chat
curl -X POST http://localhost:7742/llm/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is 2+2?", "model": "haiku"}'
# {"text":"4","model":"haiku","is_error":false}

# JSON response
curl -X POST http://localhost:7742/llm/json \
  -H "Content-Type: application/json" \
  -d '{"prompt": "List 3 colors", "system": "Return JSON only: {colors: [strings]}", "model": "haiku"}'
# {"colors":["red","blue","green"]}
```

**API Docs**: http://localhost:7742/docs

## Models

| Model | API ID | Speed | Pricing (MTok) |
|-------|--------|-------|----------------|
| `haiku` | `claude-haiku-4-5-20251001` | Fastest | $1 / $5 |
| `sonnet` | `claude-sonnet-4-5-20250929` | Balanced | $3 / $15 |
| `opus` | `claude-opus-4-5-20251101` | Most capable | $5 / $25 |

## API Key Security

Protect your API with simple key-based authentication.

### Create & Manage Keys

```sh
# Create a new API key
make api-key-create NAME=myapp
# Shows: cca_a1b2c3d4... (save this!)

# List all keys (shows hashes only)
make api-key-list

# Revoke a key
make api-key-revoke HASH=5d41

# Rotate (revoke + create new)
make api-key-rotate HASH=5d41 NAME=myapp-v2
```

### Using Keys

```sh
# With curl
curl -H "Authorization: Bearer cca_your_key_here" \
  http://localhost:7742/llm/chat \
  -d '{"prompt": "Hello"}'

# Without key (when .api-keys exists)
# Returns: 401 Unauthorized
```

### How It Works

- Keys are `cca_` prefix + 32 random hex chars
- Only SHA256 hashes are stored in `.api-keys`
- If `.api-keys` doesn't exist, auth is disabled
- `/health` and `/docs` are always public

### Docker/Production

```sh
# Mount keys file
docker run -v $(pwd)/.api-keys:/app/.api-keys ...

# Or via environment (comma-separated hashes)
API_KEY_HASHES="hash1,hash2" make docker-run

# Disable auth entirely
API_AUTH_DISABLED=1 make docker-run
```

## Streaming Examples

Interactive streaming chat demos are included:

```sh
# Terminal chat with real-time streaming
make chat

# Web chat with SSE (opens on port 7743)
make chat-web
make chat-web-stop
```

The examples demonstrate:
- Real-time token streaming via `--include-partial-messages`
- Async subprocess handling for web servers
- Server-Sent Events (SSE) for browser streaming

## Docker

```sh
# Build and run
make docker-build
make docker-run

# With OAuth token (for authenticated requests)
export CLAUDE_CODE_OAUTH_TOKEN="your-token"  # from: claude setup-token
make docker-run

# Test container
make docker-test
```

The container:
- Runs on port 7742
- Persists Claude data in `claude-code-data` volume
- Includes Claude Code CLI pre-installed

## Production Deployment (Kamal)

Deploy to any server with [Kamal 2.9+](https://kamal-deploy.org/).

### Setup

```sh
# Install Kamal
gem install kamal

# Configure secrets
cp .kamal/secrets.example .kamal/secrets
# Edit with: KAMAL_REGISTRY_PASSWORD, CLAUDE_CODE_OAUTH_TOKEN

# Set environment
export KAMAL_SERVER_IP="your.server.ip"
export KAMAL_REGISTRY_USERNAME="your-github-username"
export KAMAL_SSH_USER="your-ssh-user"
```

### Deploy

```sh
# First time (installs Docker, proxy, etc.)
make kamal-setup

# Deploy updates
make kamal-deploy

# View logs
make kamal-logs

# Rollback
make kamal-rollback
```

### Architecture Notes

- **ARM64 VMs**: Set `arch: arm64` in `config/deploy.yml` for Apple Silicon
- **SSL**: Enable via `ssl: true` in proxy config when using a domain
- **Secrets**: Stored in `.kamal/secrets` (gitignored)

## Development

```sh
# Install with dev dependencies
make dev

# Run tests
make test           # All tests
make test-quick     # Unit tests only (no CLI)
make test-gist      # SDK spec tests

# Code quality
make lint           # Check code
make format         # Format code
make typecheck      # Type check

# Status
make status         # Check server status
make help           # All commands
```

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make server` | Start API server (port 7742) |
| `make stop` | Stop server |
| `make chat` | Interactive terminal chat |
| `make chat-web` | Web chat (port 7743) |
| `make api-key-create` | Create new API key |
| `make api-key-list` | List API keys |
| `make api-key-revoke` | Revoke a key |
| `make docker-build` | Build Docker image |
| `make docker-run` | Run container |
| `make kamal-deploy` | Deploy to production |
| `make test` | Run all tests |
| `make help` | Show all commands |

## Configuration

Authentication is automatic via Claude Code:

1. **OAuth (recommended)**: `claude auth login` (one-time browser auth)
2. **Token (Docker/CI)**: `claude setup-token` to generate OAuth token

> **Note**: `ANTHROPIC_API_KEY` is automatically removed from the subprocess environment to prevent conflicts with Claude Code's OAuth flow.

## Requirements

- Python 3.10+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) (Node.js 18+)

## License

MIT License - see [LICENSE](LICENSE) for details.

## Related

- [Claude Code Documentation](https://docs.anthropic.com/en/docs/claude-code)
- [Anthropic API Reference](https://docs.anthropic.com/en/api)
- [Kamal Deployment](https://kamal-deploy.org/)
