"""
Tests for the FastAPI server.

These tests use TestClient for fast unit testing.
Integration tests require the claude CLI.
"""

import pytest
import shutil

from fastapi.testclient import TestClient

from claude_code_api.server import app


CLAUDE_AVAILABLE = shutil.which("claude") is not None

client = TestClient(app)


class TestHealthEndpoints:
    """Tests for health and status endpoints."""

    def test_health(self):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "claude-code-api"

    def test_status(self):
        """Test status endpoint."""
        response = client.get("/llm/status")
        assert response.status_code == 200
        data = response.json()
        assert "available" in data
        assert "binary_path" in data


@pytest.mark.skipif(not CLAUDE_AVAILABLE, reason="Claude CLI not installed")
class TestLLMEndpoints:
    """Integration tests for LLM endpoints."""

    @pytest.mark.integration
    def test_chat(self):
        """Test chat endpoint."""
        response = client.post(
            "/llm/chat",
            json={"prompt": "Reply with exactly: API_TEST", "model": "haiku"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "API_TEST" in data["text"]
        assert not data["is_error"]

    @pytest.mark.integration
    def test_chat_with_system(self):
        """Test chat with system prompt."""
        response = client.post(
            "/llm/chat",
            json={
                "prompt": "What is 5+5?",
                "system": "Only respond with the number",
                "model": "haiku",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "10" in data["text"]

    @pytest.mark.integration
    def test_json(self):
        """Test JSON endpoint."""
        response = client.post(
            "/llm/json",
            json={
                "prompt": "What is 2+2?",
                "system": 'Return JSON: {"answer": number}',
                "model": "haiku",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert data["answer"] == 4


class TestRequestValidation:
    """Tests for request validation."""

    def test_chat_missing_prompt(self):
        """Test chat without required prompt."""
        response = client.post("/llm/chat", json={"model": "haiku"})
        assert response.status_code == 422  # Validation error

    def test_chat_invalid_max_turns(self):
        """Test chat with invalid max_turns."""
        response = client.post(
            "/llm/chat",
            json={"prompt": "test", "max_turns": 100},  # Max is 10
        )
        assert response.status_code == 422


class TestOpenAPISchema:
    """Tests for API documentation."""

    def test_openapi_schema(self):
        """Test that OpenAPI schema is available."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert schema["info"]["title"] == "Claude Code API"

    def test_docs_available(self):
        """Test that Swagger UI is available."""
        response = client.get("/docs")
        assert response.status_code == 200
