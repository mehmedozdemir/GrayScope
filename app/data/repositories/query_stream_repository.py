"""CRUD for the QueryStream table (streams bound to a query)."""
from __future__ import annotations

import sqlite3

from app.data.models.query_stream import QueryStream


def _row_to_model(row: sqlite3.Row) -> QueryStream:
    return QueryStream(
        Id=row["Id"],
        QueryId=row["QueryId"],
        StreamId=row["StreamId"],
        StreamName=row["StreamName"],
    )


class QueryStreamRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(self, query_stream: QueryStream) -> QueryStream:
        cursor = self._conn.execute(
            "INSERT INTO QueryStream (QueryId, StreamId, StreamName) VALUES (?, ?, ?)",
            (query_stream.QueryId, query_stream.StreamId, query_stream.StreamName),
        )
        self._conn.commit()
        query_stream.Id = cursor.lastrowid
        return query_stream

    def get_by_query(self, query_id: int) -> list[QueryStream]:
        rows = self._conn.execute(
            "SELECT * FROM QueryStream WHERE QueryId = ? ORDER BY StreamName COLLATE NOCASE",
            (query_id,),
        ).fetchall()
        return [_row_to_model(r) for r in rows]

    def replace_for_query(self, query_id: int, streams: list[QueryStream]) -> None:
        """Replace the full stream set bound to a query (used when editing a query)."""
        self._conn.execute("DELETE FROM QueryStream WHERE QueryId = ?", (query_id,))
        self._conn.executemany(
            "INSERT INTO QueryStream (QueryId, StreamId, StreamName) VALUES (?, ?, ?)",
            [(query_id, s.StreamId, s.StreamName) for s in streams],
        )
        self._conn.commit()

    def delete(self, query_stream_id: int) -> None:
        self._conn.execute(
            "DELETE FROM QueryStream WHERE Id = ?", (query_stream_id,)
        )
        self._conn.commit()
