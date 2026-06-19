"""SQLite connection management and schema creation.

Booleans are stored as INTEGER (0/1), datetimes as ISO-8601 TEXT, enums as TEXT.
Foreign keys are enforced on every connection (off by default in SQLite).
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from app.core import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS GraylogProfile (
    Id              INTEGER PRIMARY KEY AUTOINCREMENT,
    Name            TEXT    NOT NULL UNIQUE,
    BaseUrl         TEXT    NOT NULL,
    TokenEncrypted  TEXT    NOT NULL,
    IsDefault       INTEGER NOT NULL DEFAULT 0,
    IsActive        INTEGER NOT NULL DEFAULT 1,
    CreatedAt       TEXT    NOT NULL,
    UpdatedAt       TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS Query (
    Id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    Name                  TEXT    NOT NULL UNIQUE,
    GraylogProfileId      INTEGER NOT NULL,
    QueryTemplate         TEXT    NOT NULL,
    TimeRangeType         TEXT    NOT NULL,
    TimeRangeRangeSeconds INTEGER,
    TimeRangeFrom         TEXT,
    TimeRangeTo           TEXT,
    TimeRangeKeyword      TEXT,
    FieldsJson            TEXT    NOT NULL,
    DefaultSortField      TEXT,
    DefaultSortOrder      TEXT,
    ResultSize            INTEGER NOT NULL DEFAULT 150,
    CreatedAt             TEXT    NOT NULL,
    UpdatedAt             TEXT    NOT NULL,
    FOREIGN KEY (GraylogProfileId) REFERENCES GraylogProfile (Id)
);

CREATE TABLE IF NOT EXISTS QueryStream (
    Id         INTEGER PRIMARY KEY AUTOINCREMENT,
    QueryId    INTEGER NOT NULL,
    StreamId   TEXT    NOT NULL,
    StreamName TEXT    NOT NULL,
    FOREIGN KEY (QueryId) REFERENCES Query (Id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS QueryFolder (
    Id       INTEGER PRIMARY KEY AUTOINCREMENT,
    Name     TEXT    NOT NULL,
    ParentId INTEGER,
    FOREIGN KEY (ParentId) REFERENCES QueryFolder (Id) ON DELETE CASCADE
);
"""


def _migrate(conn: sqlite3.Connection) -> None:
    """Lightweight migrations for databases created before a schema change."""
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(Query)")}
    if "FolderId" not in columns:
        conn.execute("ALTER TABLE Query ADD COLUMN FolderId INTEGER")
    if "UsesCustomerParameter" in columns:
        conn.execute("ALTER TABLE Query DROP COLUMN UsesCustomerParameter")
    if "LastRunAt" not in columns:
        conn.execute("ALTER TABLE Query ADD COLUMN LastRunAt TEXT")
    if "LastRunCount" not in columns:
        conn.execute("ALTER TABLE Query ADD COLUMN LastRunCount INTEGER")
    # Legacy {Plaka} placeholder → {NetworkId}.
    conn.execute(
        "UPDATE Query SET QueryTemplate = REPLACE(QueryTemplate, '{Plaka}', '{NetworkId}')"
    )
    # Drop Customer table if it still exists from an older schema.
    conn.execute("DROP TABLE IF EXISTS Customer")
    conn.commit()


def connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Open a SQLite connection with row access by name and FK enforcement.

    Pass ``":memory:"`` for an ephemeral in-memory database (used by tests).
    """
    if db_path is None:
        db_path = config.get_db_path()

    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Create all tables if they do not already exist, then run migrations."""
    conn.executescript(SCHEMA)
    conn.commit()
    _migrate(conn)
