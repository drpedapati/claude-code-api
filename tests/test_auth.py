"""
Tests for API key authentication middleware.
"""

import hashlib
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from claude_code_api.auth import (
    verify_api_key,
    _hash_key,
    _load_key_hashes,
    _is_auth_required,
    _find_keys_file,
)


# Test fixtures
@pytest.fixture
def temp_keys_file(tmp_path):
    """Create a temporary keys file."""
    keys_file = tmp_path / ".api-keys"
    return keys_file


@pytest.fixture
def test_app():
    """Create a test FastAPI app with auth."""
    app = FastAPI()

    @app.get("/public")
    def public_endpoint():
        return {"status": "public"}

    @app.get("/protected")
    def protected_endpoint(_: str = Depends(verify_api_key)):
        return {"status": "protected"}

    return app


class TestHashKey:
    """Tests for key hashing."""

    def test_hash_key_sha256(self):
        """Should produce SHA256 hash."""
        key = "cca_test123"
        expected = hashlib.sha256(key.encode()).hexdigest()
        assert _hash_key(key) == expected

    def test_hash_key_consistent(self):
        """Same input should produce same hash."""
        key = "cca_mykey"
        assert _hash_key(key) == _hash_key(key)


class TestLoadKeyHashes:
    """Tests for loading key hashes."""

    def test_load_from_env(self, monkeypatch):
        """Should load hashes from environment."""
        monkeypatch.setenv("API_KEY_HASHES", "hash1,hash2,hash3")
        # Clear file paths
        monkeypatch.setattr("claude_code_api.auth._find_keys_file", lambda: None)

        hashes = _load_key_hashes()
        assert hashes == {"hash1", "hash2", "hash3"}

    def test_load_from_file(self, temp_keys_file, monkeypatch):
        """Should load hashes from file."""
        temp_keys_file.write_text("abc123|name1|date1\ndef456|name2|date2\n")
        monkeypatch.setattr("claude_code_api.auth._find_keys_file", lambda: temp_keys_file)
        monkeypatch.delenv("API_KEY_HASHES", raising=False)

        hashes = _load_key_hashes()
        assert "abc123" in hashes
        assert "def456" in hashes

    def test_load_ignores_comments(self, temp_keys_file, monkeypatch):
        """Should ignore comment lines."""
        temp_keys_file.write_text("# Comment\n\nabc123|name|date\n")
        monkeypatch.setattr("claude_code_api.auth._find_keys_file", lambda: temp_keys_file)
        monkeypatch.delenv("API_KEY_HASHES", raising=False)

        hashes = _load_key_hashes()
        assert len(hashes) == 1
        assert "abc123" in hashes

    def test_load_combines_env_and_file(self, temp_keys_file, monkeypatch):
        """Should combine env and file hashes."""
        temp_keys_file.write_text("filehash|name|date\n")
        monkeypatch.setattr("claude_code_api.auth._find_keys_file", lambda: temp_keys_file)
        monkeypatch.setenv("API_KEY_HASHES", "envhash")

        hashes = _load_key_hashes()
        assert "filehash" in hashes
        assert "envhash" in hashes


class TestIsAuthRequired:
    """Tests for auth requirement detection."""

    def test_auth_disabled_by_env(self, monkeypatch):
        """Should be disabled when API_AUTH_DISABLED=1."""
        monkeypatch.setenv("API_AUTH_DISABLED", "1")
        assert not _is_auth_required()

    def test_auth_disabled_by_env_true(self, monkeypatch):
        """Should be disabled when API_AUTH_DISABLED=true."""
        monkeypatch.setenv("API_AUTH_DISABLED", "true")
        assert not _is_auth_required()

    def test_auth_required_when_env_keys(self, monkeypatch):
        """Should be required when API_KEY_HASHES is set."""
        monkeypatch.setenv("API_KEY_HASHES", "somehash")
        monkeypatch.delenv("API_AUTH_DISABLED", raising=False)
        assert _is_auth_required()

    def test_auth_required_when_file_exists(self, temp_keys_file, monkeypatch):
        """Should be required when .api-keys exists."""
        temp_keys_file.write_text("hash|name|date\n")
        monkeypatch.setattr("claude_code_api.auth._find_keys_file", lambda: temp_keys_file)
        monkeypatch.delenv("API_KEY_HASHES", raising=False)
        monkeypatch.delenv("API_AUTH_DISABLED", raising=False)
        assert _is_auth_required()

    def test_auth_not_required_no_config(self, monkeypatch):
        """Should not be required when no config exists."""
        monkeypatch.setattr("claude_code_api.auth._find_keys_file", lambda: None)
        monkeypatch.delenv("API_KEY_HASHES", raising=False)
        monkeypatch.delenv("API_AUTH_DISABLED", raising=False)
        assert not _is_auth_required()


class TestVerifyApiKey:
    """Tests for the verify_api_key dependency."""

    def test_no_auth_required_allows_request(self, test_app, monkeypatch):
        """When auth not required, requests pass without key."""
        monkeypatch.setattr("claude_code_api.auth._is_auth_required", lambda: False)
        client = TestClient(test_app)

        response = client.get("/protected")
        assert response.status_code == 200

    def test_auth_required_no_key_401(self, test_app, monkeypatch):
        """When auth required and no key, return 401."""
        monkeypatch.setattr("claude_code_api.auth._is_auth_required", lambda: True)
        client = TestClient(test_app)

        response = client.get("/protected")
        assert response.status_code == 401
        assert "API key required" in response.json()["detail"]

    def test_auth_required_invalid_key_401(self, test_app, monkeypatch):
        """When auth required and key invalid, return 401."""
        monkeypatch.setattr("claude_code_api.auth._is_auth_required", lambda: True)
        monkeypatch.setattr("claude_code_api.auth._load_key_hashes", lambda: {"validhash"})
        client = TestClient(test_app)

        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer cca_invalidkey"}
        )
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]

    def test_auth_required_valid_key_200(self, test_app, monkeypatch):
        """When auth required and key valid, allow request."""
        valid_key = "cca_myvalidkey123"
        valid_hash = _hash_key(valid_key)

        monkeypatch.setattr("claude_code_api.auth._is_auth_required", lambda: True)
        monkeypatch.setattr("claude_code_api.auth._load_key_hashes", lambda: {valid_hash})
        client = TestClient(test_app)

        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {valid_key}"}
        )
        assert response.status_code == 200


class TestServerIntegration:
    """Integration tests with the actual server."""

    @pytest.fixture
    def client_no_auth(self, monkeypatch):
        """Client with auth disabled."""
        monkeypatch.setattr("claude_code_api.auth._is_auth_required", lambda: False)
        from claude_code_api.server import app
        return TestClient(app)

    @pytest.fixture
    def client_with_auth(self, monkeypatch):
        """Client with auth enabled and a valid key."""
        valid_key = "cca_testkey123456789012345678901234"
        valid_hash = _hash_key(valid_key)

        monkeypatch.setattr("claude_code_api.auth._is_auth_required", lambda: True)
        monkeypatch.setattr("claude_code_api.auth._load_key_hashes", lambda: {valid_hash})

        from claude_code_api.server import app
        return TestClient(app), valid_key

    def test_health_always_public(self, client_with_auth):
        """Health endpoint should always be accessible."""
        client, _ = client_with_auth
        response = client.get("/health")
        assert response.status_code == 200

    def test_models_always_public(self, client_with_auth):
        """Models endpoint should always be accessible."""
        client, _ = client_with_auth
        response = client.get("/llm/models")
        assert response.status_code == 200

    def test_status_requires_auth(self, client_with_auth):
        """Status endpoint should require auth."""
        client, valid_key = client_with_auth

        # Without key
        response = client.get("/llm/status")
        assert response.status_code == 401

        # With key
        response = client.get(
            "/llm/status",
            headers={"Authorization": f"Bearer {valid_key}"}
        )
        assert response.status_code == 200

    def test_chat_requires_auth(self, client_with_auth):
        """Chat endpoint should require auth."""
        client, _ = client_with_auth

        response = client.post(
            "/llm/chat",
            json={"prompt": "test"}
        )
        assert response.status_code == 401

    def test_docs_always_public(self, client_with_auth):
        """Docs should always be accessible."""
        client, _ = client_with_auth
        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_always_public(self, client_with_auth):
        """OpenAPI schema should always be accessible."""
        client, _ = client_with_auth
        response = client.get("/openapi.json")
        assert response.status_code == 200
