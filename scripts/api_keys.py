#!/usr/bin/env python3
"""
API Key Management for Claude Code API.

Usage:
    python scripts/api_keys.py create [--name NAME]
    python scripts/api_keys.py list
    python scripts/api_keys.py revoke HASH_PREFIX
    python scripts/api_keys.py rotate HASH_PREFIX [--name NAME]
    python scripts/api_keys.py verify KEY
"""

import argparse
import hashlib
import json
import os
import secrets
import sys
from datetime import datetime
from pathlib import Path

# Key format: cca_<32 hex chars> = 128 bits of entropy
KEY_PREFIX = "cca_"
KEY_LENGTH = 32  # hex chars after prefix

# Storage file
KEYS_FILE = Path(__file__).parent.parent / ".api-keys"


def generate_key() -> str:
    """Generate a new API key."""
    random_bytes = secrets.token_hex(KEY_LENGTH // 2)
    return f"{KEY_PREFIX}{random_bytes}"


def hash_key(key: str) -> str:
    """SHA256 hash of a key."""
    return hashlib.sha256(key.encode()).hexdigest()


def load_keys() -> dict:
    """Load keys from file. Returns {hash: metadata}."""
    if not KEYS_FILE.exists():
        return {}

    keys = {}
    for line in KEYS_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # Format: hash|name|created
        parts = line.split("|")
        if len(parts) >= 1:
            key_hash = parts[0]
            name = parts[1] if len(parts) > 1 else ""
            created = parts[2] if len(parts) > 2 else ""
            keys[key_hash] = {"name": name, "created": created}

    return keys


def save_keys(keys: dict) -> None:
    """Save keys to file."""
    lines = ["# Claude Code API Keys (SHA256 hashes)", "# Format: hash|name|created", ""]
    for key_hash, meta in keys.items():
        name = meta.get("name", "")
        created = meta.get("created", "")
        lines.append(f"{key_hash}|{name}|{created}")

    KEYS_FILE.write_text("\n".join(lines) + "\n")
    KEYS_FILE.chmod(0o600)  # Restrict permissions


def create_key(name: str = "") -> tuple[str, str]:
    """Create a new API key. Returns (key, hash)."""
    key = generate_key()
    key_hash = hash_key(key)
    created = datetime.now().strftime("%Y-%m-%d %H:%M")

    keys = load_keys()
    keys[key_hash] = {"name": name, "created": created}
    save_keys(keys)

    return key, key_hash


def list_keys() -> list[dict]:
    """List all keys with metadata."""
    keys = load_keys()
    result = []
    for key_hash, meta in keys.items():
        result.append({
            "hash": key_hash[:8],  # Show first 8 chars
            "full_hash": key_hash,
            "name": meta.get("name", ""),
            "created": meta.get("created", ""),
        })
    return result


def revoke_key(hash_prefix: str) -> bool:
    """Revoke a key by hash prefix. Returns True if found."""
    keys = load_keys()
    to_delete = None

    for key_hash in keys:
        if key_hash.startswith(hash_prefix):
            to_delete = key_hash
            break

    if to_delete:
        del keys[to_delete]
        save_keys(keys)
        return True
    return False


def rotate_key(hash_prefix: str, name: str = "") -> tuple[str, str] | None:
    """Revoke old key and create new one. Returns (new_key, new_hash) or None."""
    if revoke_key(hash_prefix):
        return create_key(name)
    return None


def verify_key(key: str) -> bool:
    """Verify if a key is valid."""
    key_hash = hash_key(key)
    keys = load_keys()
    return key_hash in keys


def main():
    parser = argparse.ArgumentParser(description="API Key Management")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # create
    create_parser = subparsers.add_parser("create", help="Create a new API key")
    create_parser.add_argument("--name", "-n", default="", help="Optional name/label")

    # list
    subparsers.add_parser("list", help="List all API keys")

    # revoke
    revoke_parser = subparsers.add_parser("revoke", help="Revoke an API key")
    revoke_parser.add_argument("hash", help="Hash prefix of key to revoke")

    # rotate
    rotate_parser = subparsers.add_parser("rotate", help="Rotate an API key")
    rotate_parser.add_argument("hash", help="Hash prefix of key to rotate")
    rotate_parser.add_argument("--name", "-n", default="", help="Name for new key")

    # verify
    verify_parser = subparsers.add_parser("verify", help="Verify an API key")
    verify_parser.add_argument("key", help="API key to verify")

    args = parser.parse_args()

    if args.command == "create":
        key, key_hash = create_key(args.name)
        print()
        print("  API Key created (save this - shown only once):")
        print()
        print(f"    {key}")
        print()
        print(f"  Hash: {key_hash[:8]} (for revocation)")
        if args.name:
            print(f"  Name: {args.name}")
        print()

    elif args.command == "list":
        keys = list_keys()
        if not keys:
            print("  No API keys found. Create one with: make api-key-create")
        else:
            print()
            print("  Hash      Name            Created")
            print("  " + "-" * 50)
            for k in keys:
                name = k["name"] or "(unnamed)"
                print(f"  {k['hash']}  {name:15} {k['created']}")
            print()

    elif args.command == "revoke":
        if revoke_key(args.hash):
            print(f"  Revoked key {args.hash}...")
        else:
            print(f"  No key found matching {args.hash}")
            sys.exit(1)

    elif args.command == "rotate":
        result = rotate_key(args.hash, args.name)
        if result:
            key, key_hash = result
            print()
            print(f"  Revoked old key {args.hash}...")
            print()
            print("  New API Key (save this - shown only once):")
            print()
            print(f"    {key}")
            print()
            print(f"  Hash: {key_hash[:8]}")
            print()
        else:
            print(f"  No key found matching {args.hash}")
            sys.exit(1)

    elif args.command == "verify":
        if verify_key(args.key):
            print("  Valid")
        else:
            print("  Invalid")
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
