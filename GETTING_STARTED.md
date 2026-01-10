# Getting Started

Get up and running with Claude Code API in under 5 minutes.

## 1. Install Claude Code CLI

```sh
npm install -g @anthropic-ai/claude-code
claude auth login
```

This opens a browser for OAuth authentication. Sign in with your Anthropic account.

## 2. Clone and Install

```sh
git clone https://github.com/drpedapati/claude-code-api.git
cd claude-code-api

# Using uv (recommended)
uv sync

# Or pip
pip install -e ".[server]"
```

## 3. Start the Server

```sh
make server
```

The API runs on port 7742 to avoid conflicts with common dev ports.

## 4. Verify Installation

```sh
curl http://localhost:7742/health
# {"status":"ok","service":"claude-code-api","version":"0.1.0"}

curl http://localhost:7742/llm/status
# {"available":true,"version":"1.0.43"}
```

## 5. Make Your First Request

```sh
curl -X POST http://localhost:7742/llm/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello, Claude!", "model": "haiku"}'
```

## 6. Use in Python

```python
from claude_code_api import claude_chat, claude_json

# Simple chat
response = claude_chat("What is the capital of France?")
print(response)  # "Paris"

# Structured JSON
data = claude_json(
    "List 3 primary colors",
    system="Return JSON: {colors: [strings]}"
)
print(data["colors"])  # ["red", "blue", "yellow"]
```

## 7. Secure Your API (Optional)

If exposing the API on a network, add authentication:

```sh
# Create an API key
make api-key-create NAME=myapp
# Shows: cca_a1b2c3... (save this!)

# Use it in requests
curl -H "Authorization: Bearer cca_your_key_here" \
  http://localhost:7742/llm/chat \
  -d '{"prompt": "Hello"}'
```

Auth is automatically enabled when `.api-keys` exists.

## Next Steps

- See [README.md](README.md) for full documentation
- Try the `/llm/json` endpoint for structured responses
- Visit http://localhost:7742/docs for interactive API docs
- Run `make help` to see all available commands
