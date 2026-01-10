# Claude Code API Examples

Example applications demonstrating the Claude Code API library.

## Streaming Chat (Terminal)

A command-line chat application with real-time streaming responses.

```sh
# Interactive chat
python examples/streaming_chat.py

# Use a different model
python examples/streaming_chat.py --model sonnet

# With a custom system prompt
python examples/streaming_chat.py --system "You are a helpful coding assistant"

# Single query (non-interactive)
python examples/streaming_chat.py --query "What is Python?"
```

### Features

- Real-time streaming output
- Multiple model support (haiku, sonnet, opus)
- Custom system prompts
- Interactive and single-query modes
- Colorful terminal output

## Streaming Web Chat

A web-based chat application using FastAPI and Server-Sent Events (SSE).

```sh
# Install dependencies
pip install sse-starlette

# Run the server
uvicorn examples.streaming_web_chat:app --reload --port 8080

# Or run directly
python examples/streaming_web_chat.py
```

Then open http://localhost:8080 in your browser.

### Features

- Modern dark-themed UI
- Real-time streaming responses
- Model selection (haiku, sonnet, opus)
- Typing indicators
- Mobile-responsive design

## Requirements

Both examples require:

1. **Claude Code CLI** installed and authenticated:
   ```sh
   npm install -g @anthropic-ai/claude-code
   claude auth login
   ```

2. **Python packages**:
   ```sh
   # For terminal chat (no extra dependencies)
   python examples/streaming_chat.py

   # For web chat
   pip install fastapi uvicorn sse-starlette
   ```

## How Streaming Works

The Claude Code CLI supports streaming via the `--output-format stream-json` flag. The output is a series of JSON lines:

```json
{"type": "assistant", "message": {"content": [{"type": "text", "text": "Hello"}]}}
{"type": "content_block_delta", "delta": {"type": "text_delta", "text": " world"}}
{"type": "content_block_delta", "delta": {"type": "text_delta", "text": "!"}}
{"type": "result", "result": "Hello world!"}
```

The examples parse this stream in real-time to display text as it's generated.
