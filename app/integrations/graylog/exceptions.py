"""Graylog integration errors (kept separate from core app exceptions)."""
from __future__ import annotations


class GraylogError(Exception):
    """Base class for all Graylog integration errors."""


class GraylogConnectionError(GraylogError):
    """The Graylog server could not be reached (network / DNS / refused)."""


class GraylogTimeoutError(GraylogError):
    """The Graylog request exceeded the configured timeout."""


class GraylogAuthError(GraylogError):
    """Authentication failed — token invalid or expired (HTTP 401/403)."""
