"""CRUD for the QueryFolder table (nested folders for organizing queries)."""
from __future__ import annotations

import sqlite3

from app.data.models.query_folder import QueryFolder


def _row_to_model(row: sqlite3.Row) -> QueryFolder:
    return QueryFolder(Id=row["Id"], Name=row["Name"], ParentId=row["ParentId"])


class QueryFolderRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(self, folder: QueryFolder) -> QueryFolder:
        cursor = self._conn.execute(
            "INSERT INTO QueryFolder (Name, ParentId) VALUES (?, ?)",
            (folder.Name, folder.ParentId),
        )
        self._conn.commit()
        folder.Id = cursor.lastrowid
        return folder

    def get_all(self) -> list[QueryFolder]:
        rows = self._conn.execute(
            "SELECT * FROM QueryFolder ORDER BY Name COLLATE NOCASE"
        ).fetchall()
        return [_row_to_model(r) for r in rows]

    def rename(self, folder_id: int, name: str) -> None:
        self._conn.execute(
            "UPDATE QueryFolder SET Name = ? WHERE Id = ?", (name, folder_id)
        )
        self._conn.commit()

    def _descendant_ids(self, folder_id: int) -> list[int]:
        """Return ``folder_id`` and all of its descendant folder ids."""
        all_folders = self.get_all()
        children: dict[int | None, list[int]] = {}
        for folder in all_folders:
            children.setdefault(folder.ParentId, []).append(folder.Id)

        result = [folder_id]
        stack = [folder_id]
        while stack:
            current = stack.pop()
            for child in children.get(current, []):
                result.append(child)
                stack.append(child)
        return result

    def delete(self, folder_id: int) -> None:
        """Delete a folder and its subfolders; queries inside move to root (FolderId=NULL)."""
        ids = self._descendant_ids(folder_id)
        placeholders = ",".join("?" * len(ids))
        self._conn.execute(
            f"UPDATE Query SET FolderId = NULL WHERE FolderId IN ({placeholders})", ids
        )
        # ON DELETE CASCADE removes subfolders when the root of the subtree is deleted.
        self._conn.execute("DELETE FROM QueryFolder WHERE Id = ?", (folder_id,))
        self._conn.commit()
