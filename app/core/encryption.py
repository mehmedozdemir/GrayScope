"""Fernet-based encryption helpers for Graylog tokens.

Security rules (CLAUDE.md §6):
- Tokens are never stored as plaintext; they are Fernet-encrypted before persisting.
- The Fernet key is never embedded in source code. It lives in a per-user key file
  (default ``~/.grayscope/secret.key``) with owner-only (0600) permissions.
- Tokens must never appear in plaintext in logs/exceptions — use :func:`mask_token`.
"""
from __future__ import annotations

import os
import stat
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from app.core import config
from app.core.exceptions import EncryptionError


def _restrict_permissions(path: Path) -> None:
    """Best-effort restrict the key file to the owner only (0600).

    On POSIX this enforces owner read/write. On Windows ``os.chmod`` support is
    limited, so this is best-effort there; the file still lives under the user
    profile directory and is git-ignored.
    """
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except (OSError, NotImplementedError):
        # Windows / restricted filesystems: nothing more we can portably do here.
        pass


def get_or_create_key() -> bytes:
    """Return the Fernet key, generating and persisting it on first use."""
    key_path = config.get_key_path()
    if key_path.exists():
        return key_path.read_bytes()

    key_path.parent.mkdir(parents=True, exist_ok=True)
    key = Fernet.generate_key()
    key_path.write_bytes(key)
    _restrict_permissions(key_path)
    return key


def _fernet() -> Fernet:
    return Fernet(get_or_create_key())


def encrypt_token(plaintext: str) -> str:
    """Encrypt a Graylog token, returning a UTF-8 ciphertext string for storage."""
    if not plaintext:
        raise EncryptionError("Şifrelenecek token boş olamaz.")
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_token(ciphertext: str) -> str:
    """Decrypt a stored token. Raises :class:`EncryptionError` on tampering/bad key."""
    try:
        return _fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise EncryptionError("Token çözülemedi (geçersiz anahtar veya bozuk veri).") from exc


def mask_token(token: str) -> str:
    """Mask a token for safe display/logging, e.g. ``****1234``."""
    if not token:
        return "****"
    return "****" + token[-4:]
