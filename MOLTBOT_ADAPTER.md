# Moltbot/Clawdbot Adapter

This branch adds an Anthropic-compatible endpoint (`/v1/messages`) that allows moltbot/clawdbot to use claude-code-api as a drop-in replacement for direct Anthropic API calls.

## Why Use This?

**The Problem:** Moltbot uses the `pi-ai` library which extracts OAuth tokens from Claude Code CLI and uses them directly for API calls. This may violate Anthropic's SDK terms of service.

**The Solution:** This adapter wraps the Claude Code CLI binary properly, letting it handle authentication internally. Moltbot just calls this HTTP endpoint instead of making direct Anthropic API calls.

## Setup

### 1. Start the adapter server

```bash
cd claude-code-api
make server
# Server runs on http://localhost:7742
```

### 2. Configure Moltbot

Add to your moltbot config (e.g., `config.yaml` or through the wizard):

```yaml
models:
  providers:
    anthropic-adapter:
      baseUrl: "http://localhost:7742"
      apiKey: "dummy"  # Required by pi-ai but not used (CLI handles auth)
      api: "anthropic-messages"
      models:
        - id: claude-sonnet-4-5-20250929
          name: Claude Sonnet 4.5 (via CLI)
          contextWindow: 200000
          maxTokens: 64000
          input: ["text", "image"]
          cost:
            input: 3
            output: 15
        - id: claude-opus-4-5-20251101
          name: Claude Opus 4.5 (via CLI)
          contextWindow: 200000
          maxTokens: 64000
          input: ["text", "image"]
          cost:
            input: 5
            output: 25
        - id: claude-haiku-4-5-20251001
          name: Claude Haiku 4.5 (via CLI)
          contextWindow: 200000
          maxTokens: 64000
          input: ["text", "image"]
          cost:
            input: 1
            output: 5
```

### 3. Test the endpoint

```bash
# Test the Anthropic-compatible endpoint
curl -X POST http://localhost:7742/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5-20250929",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                          Moltbot                                │
│                             │                                   │
│                             ▼                                   │
│                    pi-ai library                                │
│                             │                                   │
│                             │ POST /v1/messages                 │
│                             ▼                                   │
├─────────────────────────────────────────────────────────────────┤
│                    Claude-Code-API                              │
│                    (this server)                                │
│                             │                                   │
│                             │ subprocess.run()                  │
│                             ▼                                   │
│                    Claude CLI Binary                            │
│                   (handles OAuth internally)                    │
│                             │                                   │
│                             ▼                                   │
│                     Anthropic API                               │
└─────────────────────────────────────────────────────────────────┘
```

## Supported Features

| Feature | Status |
|---------|--------|
| Text messages | ✅ Full |
| System prompts | ✅ Full |
| Streaming | ✅ SSE format |
| Multi-turn | ⚠️ Last user message only |
| Images | ❌ Not yet (use /llm/query) |
| Tools | ❌ Not yet |

## Limitations

- **Multi-turn conversations**: Currently extracts only the last user message. The Claude CLI handles sessions differently than the API.
- **Images**: Not supported in the `/v1/messages` adapter yet. Use `/llm/query` for image support.
- **Tools/Function calling**: Not implemented in adapter. Use `/llm/query` for tools.

## Development

```bash
# Run tests
make test

# Start in dev mode
uvicorn claude_code_api.server:app --reload --port 7742
```
