"""Shared pytest fixtures."""
from __future__ import annotations

import sqlite3

import pytest

from app.data.database import connect, init_schema


@pytest.fixture
def conn() -> sqlite3.Connection:
    """An in-memory SQLite connection with the schema applied."""
    connection = connect(":memory:")
    init_schema(connection)
    yield connection
    connection.close()
