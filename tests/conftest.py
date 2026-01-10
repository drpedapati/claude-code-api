"""
Pytest configuration and shared fixtures.
"""

import pytest


@pytest.fixture(autouse=True)
def disable_auth_by_default(monkeypatch):
    """
    Disable API key auth for all tests by default.

    This ensures tests don't fail if someone has a .api-keys file.
    Auth-specific tests in test_auth.py override this with their own mocks.
    """
    monkeypatch.setenv("API_AUTH_DISABLED", "1")
