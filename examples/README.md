# Claude Code API Examples

Example applications demonstrating how to use the Claude Code API.

## Prerequisites

**Start the API server first:**

```sh
make server
```

The examples connect to the API at `http://localhost:7742`.

## Terminal Chat

A command-line chat application using the HTTP API.

```sh
# Interactive chat
python examples/streaming_chat.py

# Use a different model
python examples/streaming_chat.py --model sonnet

# With a custom system prompt
python examples/streaming_chat.py --system "You are a helpful coding assistant"

# Single query (non-interactive)
python examples/streaming_chat.py --query "What is Python?"

# With API key authentication
python examples/streaming_chat.py --api-key cca_yourkey

# Or use environment variable
export CLAUDE_API_KEY=cca_yourkey
python examples/streaming_chat.py

# Debug mode - see token boundaries
python examples/streaming_chat.py --debug
```

### Features

- **Real-time streaming** - tokens appear as they're generated
- Connects to the Claude Code API
- Multiple model support (haiku, sonnet, opus)
- Custom system prompts
- Interactive and single-query modes
- API key authentication support
- Colorful terminal output

## Web Chat

A web-based chat application using FastAPI.

```sh
# Start the API server (in one terminal)
make server

# Run the web chat (in another terminal)
uvicorn examples.streaming_web_chat:app --reload --port 7743

# Or run directly
python examples/streaming_web_chat.py
```

Then open http://localhost:7743 in your browser.

### Features

- **Real-time streaming** - watch responses appear token by token
- Modern dark-themed UI
- Model selection (haiku, sonnet, opus)
- API status indicator
- Mobile-responsive design
- Auth support via `CLAUDE_API_KEY` env var

## Configuration

### API URL

Both examples default to `http://localhost:7742`. Override with:

```sh
# Terminal chat
python examples/streaming_chat.py --api-url http://your-server:7742

# Web chat
CLAUDE_API_URL=http://your-server:7742 python examples/streaming_web_chat.py
```

### Authentication

If the API has authentication enabled (`.api-keys` file exists):

```sh
# Terminal chat
python examples/streaming_chat.py --api-key cca_yourkey

# Web chat (set env var before starting)
CLAUDE_API_KEY=cca_yourkey python examples/streaming_web_chat.py
```

## Requirements

```sh
pip install httpx fastapi uvicorn
```

Or install with the package:

```sh
pip install -e ".[examples]"
```
