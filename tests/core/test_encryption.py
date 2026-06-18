"""Tests for the Fernet encryption helpers."""
from __future__ import annotations

import pytest

from app.core import encryption


@pytest.fixture(autouse=True)
def isolated_key_dir(tmp_path, monkeypatch):
    """Point the key file at a temp dir so tests never touch the real ~/.grayscope."""
    monkeypatch.setenv("GRAYSCOPE_KEY_DIR", str(tmp_path))


def test_encrypt_then_decrypt_round_trips():
    token = "abc123-secret-token"

    ciphertext = encryption.encrypt_token(token)

    assert ciphertext != token
    assert encryption.decrypt_token(ciphertext) == token


def test_mask_token_shows_only_last_four():
    assert encryption.mask_token("abcd1234") == "****1234"
