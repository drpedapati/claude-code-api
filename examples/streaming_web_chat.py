#!/usr/bin/env python3
"""
Web Chat Example for Claude Code API

A simple web-based chat application that connects to the Claude Code API.
Demonstrates using the API from a web frontend.

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

import os
from typing import Optional

try:
    import httpx
except ImportError:
    raise ImportError("httpx required. Install with: pip install httpx")

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse

app = FastAPI(
    title="Claude Web Chat",
    description="Web-based chat using Claude Code API",
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
    <title>Claude Web Chat</title>
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

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

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

        .header h1 {
            font-size: 1.25rem;
            font-weight: 600;
        }

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

        .header .api-status.connected {
            color: var(--accent);
        }

        .header .api-status.error {
            color: #ef4444;
        }

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

        .message.error {
            border-color: #ef4444;
        }

        .message.error .label {
            color: #ef4444;
        }

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

        #userInput:focus {
            outline: none;
            border-color: var(--accent);
        }

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

        #sendBtn:hover:not(:disabled) {
            background: var(--accent-hover);
        }

        #sendBtn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .typing-indicator {
            display: inline-flex;
            gap: 0.25rem;
            padding: 0.25rem 0;
        }

        .typing-indicator span {
            width: 8px;
            height: 8px;
            background: var(--accent);
            border-radius: 50%;
            animation: bounce 1.4s infinite ease-in-out;
        }

        .typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
        .typing-indicator span:nth-child(2) { animation-delay: -0.16s; }

        @keyframes bounce {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1); }
        }

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
        <h1>Claude Web Chat</h1>
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
            <textarea
                id="userInput"
                placeholder="Type your message... (Enter to send, Shift+Enter for new line)"
                rows="1"
            ></textarea>
            <button id="sendBtn">Send</button>
        </div>
    </div>

    <script>
        const chatContainer = document.getElementById('chatContainer');
        const userInput = document.getElementById('userInput');
        const sendBtn = document.getElementById('sendBtn');
        const modelSelect = document.getElementById('modelSelect');
        const apiStatus = document.getElementById('apiStatus');

        let isProcessing = false;

        // Check API status on load
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

        function addMessage(content, type, isError = false) {
            // Remove empty state if present
            const emptyState = chatContainer.querySelector('.empty-state');
            if (emptyState) emptyState.remove();

            const div = document.createElement('div');
            div.className = `message ${type}` + (isError ? ' error' : '');

            if (type === 'claude') {
                div.innerHTML = `<div class="label">${isError ? 'Error' : 'Claude'}</div><div class="content">${escapeHtml(content)}</div>`;
            } else {
                div.textContent = content;
            }

            chatContainer.appendChild(div);
            chatContainer.scrollTop = chatContainer.scrollHeight;
            return div;
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function showTypingIndicator() {
            const div = document.createElement('div');
            div.className = 'message claude';
            div.id = 'typingIndicator';
            div.innerHTML = `
                <div class="label">Claude</div>
                <div class="typing-indicator">
                    <span></span><span></span><span></span>
                </div>
            `;
            chatContainer.appendChild(div);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        function removeTypingIndicator() {
            const indicator = document.getElementById('typingIndicator');
            if (indicator) indicator.remove();
        }

        async function sendMessage() {
            const message = userInput.value.trim();
            if (!message || isProcessing) return;

            isProcessing = true;
            sendBtn.disabled = true;
            userInput.value = '';
            userInput.style.height = 'auto';

            // Add user message
            addMessage(message, 'user');

            // Show typing indicator
            showTypingIndicator();

            try {
                const model = modelSelect.value;
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({prompt: message, model: model})
                });

                removeTypingIndicator();

                const data = await response.json();

                if (response.ok && !data.is_error) {
                    addMessage(data.text, 'claude');
                } else {
                    addMessage(data.error || data.text || 'Unknown error', 'claude', true);
                }

            } catch (error) {
                removeTypingIndicator();
                addMessage(`Connection error: ${error.message}`, 'claude', true);
            } finally {
                isProcessing = false;
                sendBtn.disabled = false;
                userInput.focus();
            }
        }

        // Event listeners
        sendBtn.addEventListener('click', sendMessage);

        userInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        // Auto-resize textarea
        userInput.addEventListener('input', () => {
            userInput.style.height = 'auto';
            userInput.style.height = Math.min(userInput.scrollHeight, 150) + 'px';
        });

        // Focus input on load
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


@app.post("/api/chat")
async def chat(request: dict):
    """
    Proxy chat request to the Claude Code API.

    This endpoint forwards requests to the main API server,
    handling authentication if an API key is configured.
    """
    prompt = request.get("prompt")
    model = request.get("model", "haiku")
    system = request.get("system")

    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")

    if model not in ("haiku", "sonnet", "opus"):
        raise HTTPException(status_code=400, detail="Invalid model. Use: haiku, sonnet, opus")

    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"

    payload = {"prompt": prompt, "model": model}
    if system:
        payload["system"] = system

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_URL}/llm/chat",
                json=payload,
                headers=headers,
                timeout=120.0,
            )

            if response.status_code == 401:
                return {"is_error": True, "error": "API authentication required. Set CLAUDE_API_KEY environment variable."}

            data = response.json()
            return data

    except httpx.ConnectError:
        return {"is_error": True, "error": f"Cannot connect to API at {API_URL}. Is the server running?"}
    except Exception as e:
        return {"is_error": True, "error": str(e)}


@app.get("/health")
async def health():
    """Health check endpoint for this web chat server."""
    return {"status": "ok", "api_url": API_URL}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=7743)
