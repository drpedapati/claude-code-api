# Getting Started

Get up and running with Claude Code API in under 5 minutes.

## 1. Install Claude Code CLI

```sh
npm install -g @anthropic-ai/claude-code
claude auth login
```

This opens a browser for OAuth authentication. Sign in with your Anthropic account.

## 2. Install the Python Package

```sh
pip install "git+https://github.com/drpedapati/claude-code-api.git#egg=claude-code-api[server]"
```

## 3. Verify Installation

```sh
claude-code-api &
curl http://localhost:8000/llm/status
```

You should see `{"available": true, ...}`.

## 4. Make Your First Request

```sh
curl -X POST http://localhost:8000/llm/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello, Claude!", "model": "haiku"}'
```

## 5. Use in Python

```python
from claude_code_api import claude_chat

response = claude_chat("What is the capital of France?")
print(response)  # "Paris"
```

## Next Steps

- See [README.md](README.md) for full API reference
- Try the `/llm/json` endpoint for structured responses
- Visit http://localhost:8000/docs for interactive API docs
