"""Application-specific exception hierarchy.

Graylog integration errors live in ``app/integrations/graylog/exceptions.py``;
these cover the core/data layers.
"""
from __future__ import annotations


class GrayScopeError(Exception):
    """Base class for all GrayScope errors."""


class RecordNotFoundError(GrayScopeError):
    """A requested record does not exist."""


class DuplicateRecordError(GrayScopeError):
    """A uniqueness constraint (e.g. unique Name / NetworkId) was violated."""


class ProfileInUseError(GrayScopeError):
    """A Graylog profile cannot be deleted because queries still reference it."""


class EncryptionError(GrayScopeError):
    """Token encryption or decryption failed."""
