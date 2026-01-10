#!/usr/bin/env python3
"""
Streaming Web Chat Example for Claude Code API

A web-based chat application with real-time streaming responses
using the Claude Code API's streaming endpoint.

Usage:
    # First start the API server
    make server

    # Then run this web chat
    uvicorn examples.streaming_web_chat:app --reload --port 7743
    # Open http://localhost:7743 in your browser

Requirements:
    pip install fastapi uvicorn httpx
    - Claude Code API server running on port 7742
"""

import json
import os

try:
    import httpx
except ImportError:
    raise ImportError("httpx required. Install with: pip install httpx")

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse

app = FastAPI(
    title="Claude Streaming Web Chat",
    description="Web-based streaming chat using Claude Code API",
    version="1.0.0",
)

# API configuration
API_URL = os.environ.get("CLAUDE_API_URL", "http://localhost:7742")
API_KEY = os.environ.get("CLAUDE_API_KEY")


# HTML template for the chat interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claude Streaming Chat</title>
    <style>
        :root {
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --accent: #10b981;
            --accent-hover: #059669;
            --user-bubble: #1e40af;
            --claude-bubble: #1e293b;
            --border: #334155;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            height: 100vh;
            display: flex;
            flex-direction: column;
        }

        .header {
            padding: 1rem 1.5rem;
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .header h1 { font-size: 1.25rem; font-weight: 600; }

        .header select {
            background: var(--bg-primary);
            color: var(--text-primary);
            border: 1px solid var(--border);
            padding: 0.5rem 1rem;
            border-radius: 0.5rem;
            font-size: 0.875rem;
            cursor: pointer;
        }

        .header .api-status {
            margin-left: auto;
            font-size: 0.75rem;
            color: var(--text-secondary);
        }

        .header .api-status.connected { color: var(--accent); }
        .header .api-status.error { color: #ef4444; }

        .chat-container {
            flex: 1;
            overflow-y: auto;
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .message {
            max-width: 80%;
            padding: 0.875rem 1.125rem;
            border-radius: 1rem;
            line-height: 1.5;
            white-space: pre-wrap;
            word-wrap: break-word;
        }

        .message.user {
            background: var(--user-bubble);
            align-self: flex-end;
            border-bottom-right-radius: 0.25rem;
        }

        .message.claude {
            background: var(--claude-bubble);
            align-self: flex-start;
            border-bottom-left-radius: 0.25rem;
            border: 1px solid var(--border);
        }

        .message.claude .label {
            color: var(--accent);
            font-weight: 600;
            font-size: 0.75rem;
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .message.streaming { border-color: var(--accent); }
        .message.error { border-color: #ef4444; }
        .message.error .label { color: #ef4444; }

        .input-container {
            padding: 1rem 1.5rem;
            background: var(--bg-secondary);
            border-top: 1px solid var(--border);
        }

        .input-wrapper {
            display: flex;
            gap: 0.75rem;
            max-width: 900px;
            margin: 0 auto;
        }

        #userInput {
            flex: 1;
            background: var(--bg-primary);
            color: var(--text-primary);
            border: 1px solid var(--border);
            padding: 0.875rem 1rem;
            border-radius: 0.75rem;
            font-size: 1rem;
            resize: none;
            min-height: 50px;
            max-height: 150px;
        }

        #userInput:focus { outline: none; border-color: var(--accent); }

        #sendBtn {
            background: var(--accent);
            color: white;
            border: none;
            padding: 0.875rem 1.5rem;
            border-radius: 0.75rem;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
        }

        #sendBtn:hover:not(:disabled) { background: var(--accent-hover); }
        #sendBtn:disabled { opacity: 0.5; cursor: not-allowed; }

        .empty-state {
            text-align: center;
            color: var(--text-secondary);
            padding: 3rem;
        }

        .empty-state h2 {
            font-size: 1.5rem;
            margin-bottom: 0.5rem;
            color: var(--text-primary);
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Claude Streaming Chat</h1>
        <select id="modelSelect">
            <option value="haiku">Haiku (Fast)</option>
            <option value="sonnet">Sonnet (Balanced)</option>
            <option value="opus">Opus (Powerful)</option>
        </select>
        <div class="api-status" id="apiStatus">Checking API...</div>
    </div>

    <div class="chat-container" id="chatContainer">
        <div class="empty-state">
            <h2>Start a conversation</h2>
            <p>Type a message below to chat with Claude</p>
        </div>
    </div>

    <div class="input-container">
        <div class="input-wrapper">
            <textarea id="userInput" placeholder="Type your message... (Enter to send)" rows="1"></textarea>
            <button id="sendBtn">Send</button>
        </div>
    </div>

    <script>
        const chatContainer = document.getElementById('chatContainer');
        const userInput = document.getElementById('userInput');
        const sendBtn = document.getElementById('sendBtn');
        const modelSelect = document.getElementById('modelSelect');
        const apiStatus = document.getElementById('apiStatus');

        let isStreaming = false;

        async function checkApiStatus() {
            try {
                const response = await fetch('/api/health');
                const data = await response.json();
                if (data.api_available) {
                    apiStatus.textContent = 'API Connected';
                    apiStatus.className = 'api-status connected';
                } else {
                    apiStatus.textContent = 'API Unavailable';
                    apiStatus.className = 'api-status error';
                }
            } catch (e) {
                apiStatus.textContent = 'API Error';
                apiStatus.className = 'api-status error';
            }
        }
        checkApiStatus();

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function addMessage(content, type, isStreaming = false) {
            const emptyState = chatContainer.querySelector('.empty-state');
            if (emptyState) emptyState.remove();

            const div = document.createElement('div');
            div.className = `message ${type}` + (isStreaming ? ' streaming' : '');

            if (type === 'claude') {
                div.innerHTML = `<div class="label">Claude</div><div class="content"></div>`;
                div.querySelector('.content').textContent = content;
            } else {
                div.textContent = content;
            }

            chatContainer.appendChild(div);
            chatContainer.scrollTop = chatContainer.scrollHeight;
            return div;
        }

        async function sendMessage() {
            const message = userInput.value.trim();
            if (!message || isStreaming) return;

            isStreaming = true;
            sendBtn.disabled = true;
            userInput.value = '';
            userInput.style.height = 'auto';

            addMessage(message, 'user');

            const claudeMessage = addMessage('', 'claude', true);
            const contentEl = claudeMessage.querySelector('.content');

            try {
                const model = modelSelect.value;
                const response = await fetch('/api/chat/stream', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({prompt: message, model: model})
                });

                if (!response.ok) {
                    const err = await response.json();
                    throw new Error(err.detail || 'Request failed');
                }

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let responseText = '';

                while (true) {
                    const {done, value} = await reader.read();
                    if (done) break;

                    const chunk = decoder.decode(value, {stream: true});
                    const lines = chunk.split('\\n');

                    for (const line of lines) {
                        if (!line.startsWith('data: ')) continue;

                        try {
                            const data = JSON.parse(line.slice(6));

                            if (data.type === 'chunk') {
                                responseText += data.text;
                                contentEl.textContent = responseText;
                                chatContainer.scrollTop = chatContainer.scrollHeight;
                            } else if (data.type === 'error') {
                                throw new Error(data.message);
                            }
                        } catch (e) {
                            if (e.message !== 'Unexpected end of JSON input') {
                                console.error('Parse error:', e);
                            }
                        }
                    }
                }

                claudeMessage.classList.remove('streaming');

            } catch (error) {
                claudeMessage.classList.remove('streaming');
                claudeMessage.classList.add('error');
                claudeMessage.querySelector('.label').textContent = 'Error';
                contentEl.textContent = error.message;
            } finally {
                isStreaming = false;
                sendBtn.disabled = false;
                userInput.focus();
            }
        }

        sendBtn.addEventListener('click', sendMessage);

        userInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        userInput.addEventListener('input', () => {
            userInput.style.height = 'auto';
            userInput.style.height = Math.min(userInput.scrollHeight, 150) + 'px';
        });

        userInput.focus();
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the chat interface."""
    return HTML_TEMPLATE


@app.get("/api/health")
async def api_health():
    """Check if the Claude Code API is available."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/health", timeout=5.0)
            if response.status_code == 200:
                return {"api_available": True, "api_url": API_URL}
    except Exception:
        pass
    return {"api_available": False, "api_url": API_URL}


async def proxy_stream(prompt: str, model: str, system: str = None):
    """Proxy streaming response from the API."""
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"

    payload = {"prompt": prompt, "model": model}
    if system:
        payload["system"] = system

    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            f"{API_URL}/llm/chat/stream",
            json=payload,
            headers=headers,
            timeout=120.0,
        ) as response:
            if response.status_code == 401:
                yield f"data: {json.dumps({'type': 'error', 'message': 'API authentication required'})}\n\n"
                return

            async for line in response.aiter_lines():
                if line:
                    yield f"{line}\n\n"


@app.post("/api/chat/stream")
async def chat_stream(request: dict):
    """
    Proxy streaming chat request to the Claude Code API.
    """
    prompt = request.get("prompt")
    model = request.get("model", "haiku")
    system = request.get("system")

    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")

    if model not in ("haiku", "sonnet", "opus"):
        raise HTTPException(status_code=400, detail="Invalid model")

    return StreamingResponse(
        proxy_stream(prompt, model, system),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@app.get("/health")
async def health():
    """Health check endpoint for this web chat server."""
    return {"status": "ok", "api_url": API_URL}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7743)
