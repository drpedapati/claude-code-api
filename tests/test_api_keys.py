"""
Tests for API key management (scripts/api_keys.py).
"""

import hashlib
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Import the module under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from api_keys import (
    KEY_PREFIX,
    generate_key,
    hash_key,
    load_keys,
    save_keys,
    create_key,
    list_keys,
    revoke_key,
    rotate_key,
    verify_key,
)


class TestKeyGeneration:
    """Tests for key generation."""

    def test_generate_key_format(self):
        """Generated keys should have correct format."""
        key = generate_key()
        assert key.startswith(KEY_PREFIX)
        assert len(key) == len(KEY_PREFIX) + 32  # cca_ + 32 hex chars

    def test_generate_key_uniqueness(self):
        """Each generated key should be unique."""
        keys = [generate_key() for _ in range(100)]
        assert len(set(keys)) == 100

    def test_generate_key_hex_chars(self):
        """Key body should be valid hex characters."""
        key = generate_key()
        body = key[len(KEY_PREFIX):]
        int(body, 16)  # Should not raise


class TestKeyHashing:
    """Tests for key hashing."""

    def test_hash_key_sha256(self):
        """Hash should be SHA256."""
        key = "cca_test123"
        expected = hashlib.sha256(key.encode()).hexdigest()
        assert hash_key(key) == expected

    def test_hash_key_deterministic(self):
        """Same key should produce same hash."""
        key = generate_key()
        assert hash_key(key) == hash_key(key)

    def test_hash_key_different_keys(self):
        """Different keys should produce different hashes."""
        key1 = generate_key()
        key2 = generate_key()
        assert hash_key(key1) != hash_key(key2)


class TestKeyStorage:
    """Tests for key file storage."""

    @pytest.fixture
    def temp_keys_file(self, tmp_path, monkeypatch):
        """Create a temporary keys file."""
        keys_file = tmp_path / ".api-keys"
        # Patch the KEYS_FILE constant
        import api_keys
        monkeypatch.setattr(api_keys, "KEYS_FILE", keys_file)
        return keys_file

    def test_load_keys_empty(self, temp_keys_file):
        """Loading from non-existent file returns empty dict."""
        keys = load_keys()
        assert keys == {}

    def test_save_and_load_keys(self, temp_keys_file):
        """Keys should round-trip through save/load."""
        test_keys = {
            "abc123": {"name": "test1", "created": "2024-01-01"},
            "def456": {"name": "test2", "created": "2024-01-02"},
        }
        save_keys(test_keys)
        loaded = load_keys()
        assert loaded == test_keys

    def test_save_keys_permissions(self, temp_keys_file):
        """Saved file should have restricted permissions."""
        save_keys({"test": {"name": "", "created": ""}})
        mode = temp_keys_file.stat().st_mode & 0o777
        assert mode == 0o600

    def test_load_keys_ignores_comments(self, temp_keys_file):
        """Comments in file should be ignored."""
        temp_keys_file.write_text("# Comment\n\nabc123|test|2024-01-01\n")
        keys = load_keys()
        assert len(keys) == 1
        assert "abc123" in keys


class TestKeyOperations:
    """Tests for key CRUD operations."""

    @pytest.fixture
    def temp_keys_file(self, tmp_path, monkeypatch):
        """Create a temporary keys file."""
        keys_file = tmp_path / ".api-keys"
        import api_keys
        monkeypatch.setattr(api_keys, "KEYS_FILE", keys_file)
        return keys_file

    def test_create_key(self, temp_keys_file):
        """Creating a key should return key and hash."""
        key, key_hash = create_key("test")

        assert key.startswith(KEY_PREFIX)
        assert len(key_hash) == 64  # SHA256 hex
        assert hash_key(key) == key_hash

    def test_create_key_persists(self, temp_keys_file):
        """Created key should be persisted to file."""
        key, key_hash = create_key("mykey")

        keys = load_keys()
        assert key_hash in keys
        assert keys[key_hash]["name"] == "mykey"

    def test_list_keys(self, temp_keys_file):
        """List should return all keys with metadata."""
        create_key("key1")
        create_key("key2")

        keys = list_keys()
        assert len(keys) == 2
        names = {k["name"] for k in keys}
        assert names == {"key1", "key2"}

    def test_list_keys_truncates_hash(self, temp_keys_file):
        """List should show truncated hash."""
        _, key_hash = create_key("test")

        keys = list_keys()
        assert keys[0]["hash"] == key_hash[:8]
        assert keys[0]["full_hash"] == key_hash

    def test_revoke_key(self, temp_keys_file):
        """Revoking should remove key."""
        _, key_hash = create_key("test")

        assert revoke_key(key_hash[:8])
        keys = load_keys()
        assert key_hash not in keys

    def test_revoke_key_not_found(self, temp_keys_file):
        """Revoking non-existent key returns False."""
        assert not revoke_key("nonexistent")

    def test_rotate_key(self, temp_keys_file):
        """Rotating should revoke old and create new."""
        old_key, old_hash = create_key("original")

        result = rotate_key(old_hash[:8], "rotated")
        assert result is not None

        new_key, new_hash = result
        assert new_key != old_key
        assert new_hash != old_hash

        keys = load_keys()
        assert old_hash not in keys
        assert new_hash in keys

    def test_rotate_key_not_found(self, temp_keys_file):
        """Rotating non-existent key returns None."""
        assert rotate_key("nonexistent") is None


class TestKeyVerification:
    """Tests for key verification."""

    @pytest.fixture
    def temp_keys_file(self, tmp_path, monkeypatch):
        """Create a temporary keys file."""
        keys_file = tmp_path / ".api-keys"
        import api_keys
        monkeypatch.setattr(api_keys, "KEYS_FILE", keys_file)
        return keys_file

    def test_verify_valid_key(self, temp_keys_file):
        """Valid key should verify."""
        key, _ = create_key("test")
        assert verify_key(key)

    def test_verify_invalid_key(self, temp_keys_file):
        """Invalid key should not verify."""
        create_key("test")  # Create a key so file exists
        assert not verify_key("cca_invalid")

    def test_verify_empty_file(self, temp_keys_file):
        """No keys should fail verification."""
        assert not verify_key("cca_anything")

    def test_verify_revoked_key(self, temp_keys_file):
        """Revoked key should not verify."""
        key, key_hash = create_key("test")
        revoke_key(key_hash[:8])
        assert not verify_key(key)
