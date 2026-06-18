"""Connection-test orchestration (CLAUDE.md §5: services own business rules).

Decrypts the stored token, builds a Graylog client and runs the test. The UI never
touches the token or the client directly.
"""
from __future__ import annotations

from app.core.encryption import decrypt_token
from app.data.models.graylog_profile import GraylogProfile
from app.integrations.graylog.client import GraylogClient
from app.integrations.graylog.schemas import ConnectionTestResult


def test_profile_connection(profile: GraylogProfile) -> ConnectionTestResult:
    """Run a connection test for a stored profile.

    Raises the relevant ``GraylogError`` subclass on failure (handled by the caller).
    """
    token = decrypt_token(profile.TokenEncrypted)
    client = GraylogClient(profile.BaseUrl, token)
    return client.test_connection()
