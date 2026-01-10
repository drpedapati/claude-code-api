#!/usr/bin/env python3
"""
Streaming Web Chat Example for Claude Code API

A simple web-based chat application with real-time streaming responses
using FastAPI and Server-Sent Events (SSE).

Usage:
    uvicorn examples.streaming_web_chat:app --reload --port 8080
    # Then open http://localhost:8080 in your browser

Requirements:
    pip install fastapi uvicorn sse-starlette
    - Claude Code CLI installed: npm install -g @anthropic-ai/claude-code
    - Authenticated: claude auth login
"""

import json
import shutil
import subprocess
from typing import AsyncGenerator, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from sse_starlette.sse import EventSourceResponse

app = FastAPI(
    title="Claude Streaming Chat",
    description="Web-based streaming chat with Claude",
    version="1.0.0",
)


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

        .message.streaming {
            border-color: var(--accent);
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
        <h1>Claude Streaming Chat</h1>
        <select id="modelSelect">
            <option value="haiku">Haiku (Fast)</option>
            <option value="sonnet">Sonnet (Balanced)</option>
            <option value="opus">Opus (Powerful)</option>
        </select>
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

        let isStreaming = false;

        function addMessage(content, type, isStreaming = false) {
            // Remove empty state if present
            const emptyState = chatContainer.querySelector('.empty-state');
            if (emptyState) emptyState.remove();

            const div = document.createElement('div');
            div.className = `message ${type}` + (isStreaming ? ' streaming' : '');

            if (type === 'claude') {
                div.innerHTML = `<div class="label">Claude</div><div class="content">${content}</div>`;
            } else {
                div.textContent = content;
            }

            chatContainer.appendChild(div);
            chatContainer.scrollTop = chatContainer.scrollHeight;
            return div;
        }

        function showTypingIndicator() {
            const div = document.createElement('div');
            div.className = 'message claude streaming';
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
            if (!message || isStreaming) return;

            isStreaming = true;
            sendBtn.disabled = true;
            userInput.value = '';
            userInput.style.height = 'auto';

            // Add user message
            addMessage(message, 'user');

            // Show typing indicator
            showTypingIndicator();

            try {
                const model = modelSelect.value;
                const url = `/stream?prompt=${encodeURIComponent(message)}&model=${model}`;

                const eventSource = new EventSource(url);
                let claudeMessage = null;
                let responseText = '';

                eventSource.onmessage = (event) => {
                    const data = JSON.parse(event.data);

                    if (data.type === 'start') {
                        removeTypingIndicator();
                        claudeMessage = addMessage('', 'claude', true);
                    } else if (data.type === 'chunk') {
                        responseText += data.text;
                        if (claudeMessage) {
                            claudeMessage.querySelector('.content').textContent = responseText;
                            chatContainer.scrollTop = chatContainer.scrollHeight;
                        }
                    } else if (data.type === 'end') {
                        if (claudeMessage) {
                            claudeMessage.classList.remove('streaming');
                        }
                        eventSource.close();
                        isStreaming = false;
                        sendBtn.disabled = false;
                        userInput.focus();
                    } else if (data.type === 'error') {
                        removeTypingIndicator();
                        addMessage(`Error: ${data.message}`, 'claude');
                        eventSource.close();
                        isStreaming = false;
                        sendBtn.disabled = false;
                    }
                };

                eventSource.onerror = () => {
                    removeTypingIndicator();
                    if (isStreaming) {
                        addMessage('Connection error. Please try again.', 'claude');
                    }
                    eventSource.close();
                    isStreaming = false;
                    sendBtn.disabled = false;
                };

            } catch (error) {
                removeTypingIndicator();
                addMessage(`Error: ${error.message}`, 'claude');
                isStreaming = false;
                sendBtn.disabled = false;
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


async def generate_stream(
    prompt: str,
    model: str = "haiku",
    system: Optional[str] = None,
) -> AsyncGenerator[dict, None]:
    """
    Generate streaming response from Claude CLI.

    Yields SSE-formatted events with the response chunks.
    """
    # Check for Claude CLI
    if not shutil.which("claude"):
        yield {"event": "message", "data": json.dumps({"type": "error", "message": "Claude CLI not found"})}
        return

    # Build command
    cmd = [
        "claude",
        "-p",
        "--output-format",
        "stream-json",
        "--verbose",
        "--model",
        model,
        "--max-turns",
        "1",
    ]

    if system:
        cmd.extend(["--system-prompt", system])

    cmd.extend(["--", prompt])

    # Start streaming
    yield {"event": "message", "data": json.dumps({"type": "start"})}

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    try:
        for line in process.stdout:
            line = line.strip()
            if not line:
                continue

            try:
                msg = json.loads(line)
                msg_type = msg.get("type")

                if msg_type == "assistant":
                    content = msg.get("message", {}).get("content", [])
                    for block in content:
                        if block.get("type") == "text":
                            text = block.get("text", "")
                            if text:
                                yield {"event": "message", "data": json.dumps({"type": "chunk", "text": text})}

                elif msg_type == "content_block_delta":
                    delta = msg.get("delta", {})
                    if delta.get("type") == "text_delta":
                        text = delta.get("text", "")
                        if text:
                            yield {"event": "message", "data": json.dumps({"type": "chunk", "text": text})}

            except json.JSONDecodeError:
                continue

    except Exception as e:
        yield {"event": "message", "data": json.dumps({"type": "error", "message": str(e)})}

    finally:
        process.wait()
        yield {"event": "message", "data": json.dumps({"type": "end"})}


@app.get("/stream")
async def stream(
    prompt: str = Query(..., description="The prompt to send to Claude"),
    model: str = Query("haiku", description="Model to use: haiku, sonnet, opus"),
    system: Optional[str] = Query(None, description="Optional system prompt"),
):
    """
    Stream a response from Claude using Server-Sent Events.

    The response is streamed in real-time as Claude generates it.
    """
    if model not in ("haiku", "sonnet", "opus"):
        raise HTTPException(status_code=400, detail="Invalid model. Use: haiku, sonnet, opus")

    return EventSourceResponse(generate_stream(prompt, model, system))


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "claude_available": shutil.which("claude") is not None}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
