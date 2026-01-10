"""
Tests for the Claude Code API client.

These tests require the `claude` CLI to be installed and authenticated.
Skip tests with: pytest -m "not integration"
"""

import pytest
import shutil

from claude_code_api import ClaudeClient, ClaudeResult, claude_chat, claude_json


# Check if claude CLI is available
CLAUDE_AVAILABLE = shutil.which("claude") is not None


@pytest.mark.skipif(not CLAUDE_AVAILABLE, reason="Claude CLI not installed")
class TestClaudeClient:
    """Integration tests for ClaudeClient."""

    def test_init_default(self):
        """Test default initialization."""
        client = ClaudeClient()
        assert client.model == "haiku"
        assert client.max_turns == 1
        assert client.binary_path is not None

    def test_init_custom_model(self):
        """Test initialization with custom model."""
        client = ClaudeClient(model="sonnet")
        assert client.model == "sonnet"

    @pytest.mark.integration
    def test_chat_simple(self):
        """Test simple chat request."""
        client = ClaudeClient(model="haiku")
        result = client.chat("Reply with exactly: TEST_OK")

        assert isinstance(result, ClaudeResult)
        assert not result.is_error
        assert "TEST_OK" in result.text

    @pytest.mark.integration
    def test_chat_with_system(self):
        """Test chat with system prompt."""
        client = ClaudeClient(model="haiku")
        result = client.chat(
            "What is 2+2?",
            system="You are a calculator. Only respond with the number, nothing else.",
        )

        assert not result.is_error
        assert "4" in result.text

    @pytest.mark.integration
    def test_chat_json(self):
        """Test JSON response parsing."""
        client = ClaudeClient(model="haiku")
        data = client.chat_json(
            "What is 2+2?",
            system='Return ONLY valid JSON: {"answer": number}',
        )

        assert isinstance(data, dict)
        assert "answer" in data
        assert data["answer"] == 4

    @pytest.mark.integration
    def test_chat_json_invalid_response(self):
        """Test JSON parsing with invalid response."""
        client = ClaudeClient(model="haiku")

        # This should raise ValueError if response isn't valid JSON
        with pytest.raises(ValueError):
            client.chat_json(
                "Write a haiku about Python",
                system="Be creative and verbose",
            )


@pytest.mark.skipif(not CLAUDE_AVAILABLE, reason="Claude CLI not installed")
class TestConvenienceFunctions:
    """Tests for convenience functions."""

    @pytest.mark.integration
    def test_claude_chat(self):
        """Test claude_chat helper."""
        response = claude_chat("Reply with exactly: HELPER_OK")
        assert "HELPER_OK" in response

    @pytest.mark.integration
    def test_claude_json(self):
        """Test claude_json helper."""
        data = claude_json(
            "List 3 primary colors",
            system='Return ONLY valid JSON, no other text: {"colors": ["string1", "string2", "string3"]}',
        )
        assert isinstance(data, dict)
        assert "colors" in data
        assert isinstance(data["colors"], list)


class TestClaudeClientUnit:
    """Unit tests that don't require the CLI."""

    def test_init_no_binary(self, monkeypatch):
        """Test error when binary not found."""
        monkeypatch.setattr(shutil, "which", lambda x: None)

        with pytest.raises(RuntimeError, match="Claude binary not found"):
            ClaudeClient()

    def test_extract_json_direct(self):
        """Test JSON extraction from direct JSON."""
        client = ClaudeClient.__new__(ClaudeClient)
        result = client._extract_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_extract_json_markdown(self):
        """Test JSON extraction from markdown code block."""
        client = ClaudeClient.__new__(ClaudeClient)
        text = """Here is the JSON:
```json
{"key": "value"}
```
"""
        result = client._extract_json(text)
        assert result == {"key": "value"}

    def test_extract_json_embedded(self):
        """Test JSON extraction from embedded text."""
        client = ClaudeClient.__new__(ClaudeClient)
        text = 'The answer is {"key": "value"} as shown.'
        result = client._extract_json(text)
        assert result == {"key": "value"}

    def test_extract_json_invalid(self):
        """Test JSON extraction failure."""
        client = ClaudeClient.__new__(ClaudeClient)
        with pytest.raises(ValueError):
            client._extract_json("This is not JSON at all")
