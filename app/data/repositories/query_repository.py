"""CRUD for the Query table."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from app.core.exceptions import DuplicateRecordError
from app.data.models.query import Query, SortOrder, TimeRangeType


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iso_or_none(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _dt_or_none(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _row_to_model(row: sqlite3.Row) -> Query:
    return Query(
        Id=row["Id"],
        Name=row["Name"],
        GraylogProfileId=row["GraylogProfileId"],
        UsesCustomerParameter=bool(row["UsesCustomerParameter"]),
        QueryTemplate=row["QueryTemplate"],
        TimeRangeType=TimeRangeType(row["TimeRangeType"]),
        TimeRangeRangeSeconds=row["TimeRangeRangeSeconds"],
        TimeRangeFrom=_dt_or_none(row["TimeRangeFrom"]),
        TimeRangeTo=_dt_or_none(row["TimeRangeTo"]),
        TimeRangeKeyword=row["TimeRangeKeyword"],
        FieldsJson=row["FieldsJson"],
        DefaultSortField=row["DefaultSortField"],
        DefaultSortOrder=(
            SortOrder(row["DefaultSortOrder"]) if row["DefaultSortOrder"] else None
        ),
        FolderId=row["FolderId"],
        ResultSize=row["ResultSize"],
        CreatedAt=datetime.fromisoformat(row["CreatedAt"]),
        UpdatedAt=datetime.fromisoformat(row["UpdatedAt"]),
    )


class QueryRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(self, query: Query) -> Query:
        timestamp = _now()
        try:
            cursor = self._conn.execute(
                """
                INSERT INTO Query
                    (Name, GraylogProfileId, UsesCustomerParameter, QueryTemplate,
                     TimeRangeType, TimeRangeRangeSeconds, TimeRangeFrom, TimeRangeTo,
                     TimeRangeKeyword, FieldsJson, DefaultSortField, DefaultSortOrder,
                     FolderId, ResultSize, CreatedAt, UpdatedAt)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    query.Name,
                    query.GraylogProfileId,
                    int(query.UsesCustomerParameter),
                    query.QueryTemplate,
                    query.TimeRangeType.value,
                    query.TimeRangeRangeSeconds,
                    _iso_or_none(query.TimeRangeFrom),
                    _iso_or_none(query.TimeRangeTo),
                    query.TimeRangeKeyword,
                    query.FieldsJson,
                    query.DefaultSortField,
                    query.DefaultSortOrder.value if query.DefaultSortOrder else None,
                    query.FolderId,
                    query.ResultSize,
                    timestamp,
                    timestamp,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise DuplicateRecordError(
                f"'{query.Name}' adında bir sorgu zaten var."
            ) from exc
        self._conn.commit()
        query.Id = cursor.lastrowid
        query.CreatedAt = datetime.fromisoformat(timestamp)
        query.UpdatedAt = query.CreatedAt
        return query

    def get_by_id(self, query_id: int) -> Query | None:
        row = self._conn.execute(
            "SELECT * FROM Query WHERE Id = ?", (query_id,)
        ).fetchone()
        return _row_to_model(row) if row else None

    def get_all(self) -> list[Query]:
        rows = self._conn.execute(
            "SELECT * FROM Query ORDER BY Name COLLATE NOCASE"
        ).fetchall()
        return [_row_to_model(r) for r in rows]

    def get_by_profile(self, profile_id: int) -> list[Query]:
        rows = self._conn.execute(
            "SELECT * FROM Query WHERE GraylogProfileId = ? ORDER BY Name COLLATE NOCASE",
            (profile_id,),
        ).fetchall()
        return [_row_to_model(r) for r in rows]

    def update(self, query: Query) -> Query:
        timestamp = _now()
        try:
            self._conn.execute(
                """
                UPDATE Query
                   SET Name = ?, GraylogProfileId = ?, UsesCustomerParameter = ?,
                       QueryTemplate = ?, TimeRangeType = ?, TimeRangeRangeSeconds = ?,
                       TimeRangeFrom = ?, TimeRangeTo = ?, TimeRangeKeyword = ?,
                       FieldsJson = ?, DefaultSortField = ?, DefaultSortOrder = ?,
                       FolderId = ?, ResultSize = ?, UpdatedAt = ?
                 WHERE Id = ?
                """,
                (
                    query.Name,
                    query.GraylogProfileId,
                    int(query.UsesCustomerParameter),
                    query.QueryTemplate,
                    query.TimeRangeType.value,
                    query.TimeRangeRangeSeconds,
                    _iso_or_none(query.TimeRangeFrom),
                    _iso_or_none(query.TimeRangeTo),
                    query.TimeRangeKeyword,
                    query.FieldsJson,
                    query.DefaultSortField,
                    query.DefaultSortOrder.value if query.DefaultSortOrder else None,
                    query.FolderId,
                    query.ResultSize,
                    timestamp,
                    query.Id,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise DuplicateRecordError(
                f"'{query.Name}' adında bir sorgu zaten var."
            ) from exc
        self._conn.commit()
        query.UpdatedAt = datetime.fromisoformat(timestamp)
        return query

    def delete(self, query_id: int) -> None:
        """Delete a query. Bound QueryStream rows are removed via ON DELETE CASCADE."""
        self._conn.execute("DELETE FROM Query WHERE Id = ?", (query_id,))
        self._conn.commit()
