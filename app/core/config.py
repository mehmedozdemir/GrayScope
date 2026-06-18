"""Application-wide settings and constants.

Paths can be overridden through environment variables so tests and alternative
deployments do not touch the user's real database or key file.
"""
from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "GrayScope"

# Header Graylog expects on every request (see PROJECT_PLAN.md §3.3).
REQUESTED_BY = "GrayScope"

# Graylog REST timeout in seconds (CLAUDE.md §7).
GRAYLOG_TIMEOUT_SECONDS = 10

# Default maximum number of records pulled per query execution (PROJECT_PLAN.md §4.3).
DEFAULT_RESULT_SIZE = 150

# Project root: <root>/app/core/config.py -> parents[2] == <root>.
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def get_db_path() -> Path:
    """Return the SQLite database path (env-overridable)."""
    override = os.environ.get("GRAYSCOPE_DB_PATH")
    if override:
        return Path(override).expanduser()
    return PROJECT_ROOT / "data" / "grayscope.db"


def get_key_dir() -> Path:
    """Return the directory that holds the Fernet key file (env-overridable)."""
    override = os.environ.get("GRAYSCOPE_KEY_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".grayscope"


def get_key_path() -> Path:
    """Return the full path to the Fernet key file."""
    return get_key_dir() / "secret.key"
