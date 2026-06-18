"""CRUD for the GraylogProfile table."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from app.core.exceptions import DuplicateRecordError, ProfileInUseError
from app.data.models.graylog_profile import GraylogProfile


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_model(row: sqlite3.Row) -> GraylogProfile:
    return GraylogProfile(
        Id=row["Id"],
        Name=row["Name"],
        BaseUrl=row["BaseUrl"],
        TokenEncrypted=row["TokenEncrypted"],
        IsDefault=bool(row["IsDefault"]),
        IsActive=bool(row["IsActive"]),
        CreatedAt=datetime.fromisoformat(row["CreatedAt"]),
        UpdatedAt=datetime.fromisoformat(row["UpdatedAt"]),
    )


class GraylogProfileRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(self, profile: GraylogProfile) -> GraylogProfile:
        timestamp = _now()
        try:
            cursor = self._conn.execute(
                """
                INSERT INTO GraylogProfile
                    (Name, BaseUrl, TokenEncrypted, IsDefault, IsActive, CreatedAt, UpdatedAt)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile.Name,
                    profile.BaseUrl,
                    profile.TokenEncrypted,
                    int(profile.IsDefault),
                    int(profile.IsActive),
                    timestamp,
                    timestamp,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise DuplicateRecordError(
                f"'{profile.Name}' adında bir profil zaten var."
            ) from exc
        self._conn.commit()
        profile.Id = cursor.lastrowid
        profile.CreatedAt = datetime.fromisoformat(timestamp)
        profile.UpdatedAt = profile.CreatedAt
        return profile

    def get_by_id(self, profile_id: int) -> GraylogProfile | None:
        row = self._conn.execute(
            "SELECT * FROM GraylogProfile WHERE Id = ?", (profile_id,)
        ).fetchone()
        return _row_to_model(row) if row else None

    def get_all(self, only_active: bool = False) -> list[GraylogProfile]:
        sql = "SELECT * FROM GraylogProfile"
        if only_active:
            sql += " WHERE IsActive = 1"
        sql += " ORDER BY Name COLLATE NOCASE"
        return [_row_to_model(r) for r in self._conn.execute(sql).fetchall()]

    def update(self, profile: GraylogProfile) -> GraylogProfile:
        timestamp = _now()
        try:
            self._conn.execute(
                """
                UPDATE GraylogProfile
                   SET Name = ?, BaseUrl = ?, TokenEncrypted = ?, IsDefault = ?,
                       IsActive = ?, UpdatedAt = ?
                 WHERE Id = ?
                """,
                (
                    profile.Name,
                    profile.BaseUrl,
                    profile.TokenEncrypted,
                    int(profile.IsDefault),
                    int(profile.IsActive),
                    timestamp,
                    profile.Id,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise DuplicateRecordError(
                f"'{profile.Name}' adında bir profil zaten var."
            ) from exc
        self._conn.commit()
        profile.UpdatedAt = datetime.fromisoformat(timestamp)
        return profile

    def clear_default_except(self, keep_id: int) -> None:
        """Unset IsDefault on every profile except ``keep_id`` (single-default rule)."""
        self._conn.execute(
            "UPDATE GraylogProfile SET IsDefault = 0 WHERE Id != ?", (keep_id,)
        )
        self._conn.commit()

    def delete(self, profile_id: int) -> None:
        """Delete a profile. Blocked if any Query still references it."""
        count = self._conn.execute(
            "SELECT COUNT(*) FROM Query WHERE GraylogProfileId = ?", (profile_id,)
        ).fetchone()[0]
        if count:
            raise ProfileInUseError(
                f"Bu profile bağlı {count} sorgu var, önce onları silin/taşıyın."
            )
        self._conn.execute("DELETE FROM GraylogProfile WHERE Id = ?", (profile_id,))
        self._conn.commit()
