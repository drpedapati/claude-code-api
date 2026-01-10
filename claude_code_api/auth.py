"""
API Key Authentication for Claude Code API.

Validates Bearer tokens against SHA256 hashes stored in .api-keys file.
"""

import hashlib
import os
from pathlib import Path
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Security scheme
security = HTTPBearer(auto_error=False)

# Paths to check for keys file
KEYS_FILE_PATHS = [
    Path(".api-keys"),  # Current directory
    Path(__file__).parent.parent / ".api-keys",  # Project root
    Path("/app/.api-keys"),  # Docker container
]


def _find_keys_file() -> Optional[Path]:
    """Find the .api-keys file."""
    for path in KEYS_FILE_PATHS:
        if path.exists():
            return path
    return None


def _load_key_hashes() -> set[str]:
    """Load valid key hashes from file or environment."""
    hashes = set()

    # From environment (comma-separated hashes)
    env_keys = os.environ.get("API_KEY_HASHES", "")
    if env_keys:
        for h in env_keys.split(","):
            h = h.strip()
            if h:
                hashes.add(h)

    # From file
    keys_file = _find_keys_file()
    if keys_file:
        for line in keys_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Format: hash|name|created
            key_hash = line.split("|")[0].strip()
            if key_hash:
                hashes.add(key_hash)

    return hashes


def _hash_key(key: str) -> str:
    """SHA256 hash of API key."""
    return hashlib.sha256(key.encode()).hexdigest()


def _is_auth_required() -> bool:
    """Check if authentication is required."""
    # Disabled via environment
    if os.environ.get("API_AUTH_DISABLED", "").lower() in ("1", "true", "yes"):
        return False

    # Required if keys file exists or env keys are set
    if os.environ.get("API_KEY_HASHES"):
        return True

    return _find_keys_file() is not None


def verify_api_key(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[str]:
    """
    Verify API key from Authorization header.

    Returns the key hash if valid, None if auth not required.
    Raises HTTPException if auth required but invalid/missing.
    """
    # Check if auth is required
    if not _is_auth_required():
        return None

    # No credentials provided
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Use: Authorization: Bearer <api-key>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate the key
    api_key = credentials.credentials
    key_hash = _hash_key(api_key)
    valid_hashes = _load_key_hashes()

    if key_hash not in valid_hashes:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return key_hash


# Dependency for protected routes
require_api_key = Depends(verify_api_key)
