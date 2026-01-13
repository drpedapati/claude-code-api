# Claude Code API Skill

Use this API to access Claude models via HTTP. The API wraps the Claude Code CLI and handles authentication automatically.

## Hosting / Base URL

You can point this skill at:
- Hosted instance (examples below): https://claude.cincibrainlab.com
- Self-hosted server: run the API and use `http://localhost:7742` or your server URL.

## Getting an API Key

To call authenticated endpoints you need a `cca_` API key.

- Hosted instance: request a key from the server operator.
- Self-hosted: run `make api-key-create NAME=myapp` on the server and save the printed key.

For self-hosting setup, see `GETTING_STARTED.md` or `README.md`.

## Authentication

All endpoints except `/health` require a Bearer token:

```
Authorization: Bearer cca_your_api_key_here
```

Examples below use `https://claude.cincibrainlab.com`. Replace with your own base URL if self-hosting.

## Endpoints

### 1. Simple Chat (`POST /llm/chat`)

For basic text queries without usage tracking.

```bash
curl -X POST https://claude.cincibrainlab.com/llm/chat \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is 2+2?", "model": "haiku"}'
```

**Request:**
```json
{
  "prompt": "Your question here",
  "model": "haiku",           // haiku (fast), sonnet (balanced), opus (powerful)
  "system": "Optional system prompt",
  "max_turns": 1              // 1-10
}
```

**Response:**
```json
{
  "text": "4",
  "model": "haiku",
  "is_error": false,
  "error_message": null
}
```

### 2. Full Query (`POST /llm/query`)

Advanced endpoint with images, tool control, sessions, and usage tracking.

```bash
curl -X POST https://claude.cincibrainlab.com/llm/query \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Describe this image", "images": [{"data": "base64...", "media_type": "image/png"}], "model": "haiku"}'
```

**Request:**
```json
{
  "prompt": "Your question here",
  "model": "haiku",

  // Optional: Images (base64-encoded)
  "images": [
    {"data": "iVBORw0KGgo...", "media_type": "image/png"}
  ],

  // Optional: System prompt
  "system": "You are a helpful assistant",

  // Optional: Tool control
  "allowed_tools": ["Read", "Bash", "Edit"],    // Whitelist (empty array disables all)
  "disallowed_tools": ["Write"],                 // Blacklist

  // Optional: Session management
  "session_id": "uuid-from-previous-response",   // Resume a session
  "continue_session": true,                      // Continue most recent session

  // Optional: Limits
  "max_turns": 5,              // 1-100
  "max_budget_usd": 1.0        // 0.01-100.0
}
```

**Response:**
```json
{
  "text": "This is a red square image.",
  "model": "haiku",
  "session_id": "abc123-def456-...",
  "num_turns": 1,
  "total_cost_usd": 0.0025,
  "duration_ms": 1234,
  "usage": {
    "input_tokens": 150,
    "output_tokens": 25,
    "cache_read_input_tokens": 1000,
    "cache_creation_input_tokens": 100
  },
  "model_usage": {
    "claude-haiku-4-5-20251001": {
      "inputTokens": 150,
      "outputTokens": 25,
      "costUSD": 0.0025
    }
  },
  "is_error": false,
  "error_message": null
}
```

### 3. Streaming Chat (`POST /llm/chat/stream`)

Real-time token streaming via Server-Sent Events.

```bash
curl -N -X POST https://claude.cincibrainlab.com/llm/chat/stream \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Tell me a story", "model": "haiku"}'
```

**Events:**
```
data: {"type": "start"}
data: {"type": "chunk", "text": "Once"}
data: {"type": "chunk", "text": " upon"}
data: {"type": "chunk", "text": " a"}
data: {"type": "chunk", "text": " time"}
data: {"type": "end"}
```

### 4. JSON Response (`POST /llm/json`)

Get structured JSON output.

```bash
curl -X POST https://claude.cincibrainlab.com/llm/json \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "List 3 colors", "system": "Return JSON: {colors: [strings]}", "model": "haiku"}'
```

**Response:**
```json
{
  "colors": ["red", "blue", "green"]
}
```

### 5. Health Check (`GET /health`)

No authentication required.

```bash
curl https://claude.cincibrainlab.com/health
```

**Response:**
```json
{
  "status": "ok",
  "service": "claude-code-api",
  "version": "0.1.0"
}
```

### 6. Models List (`GET /llm/models`)

```bash
curl -H "Authorization: Bearer $API_KEY" https://claude.cincibrainlab.com/llm/models
```

## Models

| ID | Name | Speed | Use Case |
|----|------|-------|----------|
| `haiku` | Claude Haiku 4.5 | Fastest | Quick tasks, high volume |
| `sonnet` | Claude Sonnet 4.5 | Balanced | Complex coding, analysis |
| `opus` | Claude Opus 4.5 | Most capable | Research, difficult problems |

## Common Patterns

### Image Analysis

```json
{
  "prompt": "What objects are in this image?",
  "images": [{"data": "BASE64_PNG_DATA", "media_type": "image/png"}],
  "model": "haiku"
}
```

### Multi-turn Conversation

```json
// First request
{"prompt": "My name is Alice", "model": "haiku"}
// Response includes session_id: "abc123..."

// Second request (resume)
{"prompt": "What is my name?", "session_id": "abc123...", "model": "haiku"}
// Response: "Your name is Alice"
```

### Restricted Tool Use

```json
{
  "prompt": "Read the README.md file",
  "allowed_tools": ["Read"],
  "max_turns": 3,
  "model": "sonnet"
}
```

### Budget-Limited Query

```json
{
  "prompt": "Write a comprehensive analysis",
  "max_budget_usd": 0.50,
  "max_turns": 10,
  "model": "opus"
}
```

## Error Handling

All endpoints return errors in this format:

```json
{
  "text": "",
  "is_error": true,
  "error_message": "Description of the error"
}
```

HTTP status codes:
- `401` - Missing or invalid API key
- `422` - Invalid request (bad JSON, validation error)
- `500` - Internal server error
- `503` - Claude CLI unavailable

## Rate Limits

No hard rate limits, but costs are tracked per request. Use `max_budget_usd` to control spending.

## OpenAPI Docs

Interactive documentation available at:
- Swagger UI: https://claude.cincibrainlab.com/docs
- ReDoc: https://claude.cincibrainlab.com/redoc
