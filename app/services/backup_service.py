"""Query backup / restore service.

Exports all QueryFolder + Query + QueryStream records to a portable JSON file,
and imports them back — creating folders and queries that don't yet exist by name,
skipping duplicates.

Format (top-level object):
{
  "version": 1,
  "exported_at": "<ISO-8601>",
  "folders": [{"id": <int>, "name": "...", "parent_name": "..." | null}, ...],
  "queries": [
    {
      "name": "...",
      "folder": "..." | null,         ← folder Name (root-level if null)
      "profile_name": "...",          ← GraylogProfile.Name (matched on import)
      "query_template": "...",
      "time_range_type": "Relative" | "Absolute" | "Keyword",
      "time_range_seconds": <int> | null,
      "time_range_from": "<ISO>" | null,
      "time_range_to": "<ISO>" | null,
      "time_range_keyword": "..." | null,
      "fields": [...],
      "default_sort_field": "..." | null,
      "default_sort_order": "asc" | "desc" | null,
      "result_size": <int>,
      "streams": [{"stream_id": "...", "stream_name": "..."}, ...]
    },
    ...
  ]
}
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from app.data.models.query import Query, SortOrder, TimeRangeType
from app.data.models.query_folder import QueryFolder
from app.data.models.query_stream import QueryStream
from app.data.repositories.graylog_profile_repository import GraylogProfileRepository
from app.data.repositories.query_folder_repository import QueryFolderRepository
from app.data.repositories.query_repository import QueryRepository
from app.data.repositories.query_stream_repository import QueryStreamRepository

_VERSION = 1


def export_backup(conn: sqlite3.Connection) -> dict:
    folders = QueryFolderRepository(conn).get_all()
    queries = QueryRepository(conn).get_all()
    profiles = {p.Id: p for p in GraylogProfileRepository(conn).get_all()}
    streams_repo = QueryStreamRepository(conn)

    # Build folder id → name + parent_name maps.
    folder_by_id = {f.Id: f for f in folders}

    def folder_name(fid: int | None) -> str | None:
        return folder_by_id[fid].Name if fid and fid in folder_by_id else None

    def parent_name(f: QueryFolder) -> str | None:
        return folder_by_id[f.ParentId].Name if f.ParentId and f.ParentId in folder_by_id else None

    return {
        "version": _VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "folders": [
            {"name": f.Name, "parent_name": parent_name(f)}
            for f in folders
        ],
        "queries": [
            {
                "name": q.Name,
                "folder": folder_name(q.FolderId),
                "profile_name": profiles[q.GraylogProfileId].Name if q.GraylogProfileId in profiles else "",
                "query_template": q.QueryTemplate,
                "time_range_type": q.TimeRangeType.value,
                "time_range_seconds": q.TimeRangeRangeSeconds,
                "time_range_from": q.TimeRangeFrom.isoformat() if q.TimeRangeFrom else None,
                "time_range_to": q.TimeRangeTo.isoformat() if q.TimeRangeTo else None,
                "time_range_keyword": q.TimeRangeKeyword,
                "fields": json.loads(q.FieldsJson) if q.FieldsJson else [],
                "default_sort_field": q.DefaultSortField,
                "default_sort_order": q.DefaultSortOrder.value if q.DefaultSortOrder else None,
                "result_size": q.ResultSize,
                "streams": [
                    {"stream_id": s.StreamId, "stream_name": s.StreamName}
                    for s in streams_repo.get_by_query(q.Id)
                ],
            }
            for q in queries
        ],
    }


def import_backup(conn: sqlite3.Connection, data: dict) -> tuple[int, int, list[str]]:
    """Import backup data. Returns (queries_added, queries_skipped, warnings)."""
    if data.get("version", 0) != _VERSION:
        raise ValueError(f"Desteklenmeyen yedek formatı (version={data.get('version')}).")

    folders_repo = QueryFolderRepository(conn)
    queries_repo = QueryRepository(conn)
    streams_repo = QueryStreamRepository(conn)
    profiles = {p.Name: p for p in GraylogProfileRepository(conn).get_all()}
    existing_queries = {q.Name for q in queries_repo.get_all()}

    # ── Restore folders (by name, preserving hierarchy) ──────────────────
    # Two passes: first create root folders, then children.
    existing_folders = {f.Name: f for f in folders_repo.get_all()}

    def _ensure_folder(name: str, parent_name: str | None) -> QueryFolder:
        if name in existing_folders:
            return existing_folders[name]
        parent_id = existing_folders[parent_name].Id if parent_name and parent_name in existing_folders else None
        created = folders_repo.create(QueryFolder(Name=name, ParentId=parent_id))
        existing_folders[name] = created
        return created

    for entry in data.get("folders", []):
        parent = entry.get("parent_name")
        if parent and parent not in existing_folders:
            _ensure_folder(parent, None)
        _ensure_folder(entry["name"], parent)

    # ── Restore queries ───────────────────────────────────────────────────
    warnings: list[str] = []
    added = skipped = 0

    for qd in data.get("queries", []):
        name = qd["name"]
        if name in existing_queries:
            skipped += 1
            continue

        profile_name = qd.get("profile_name", "")
        if profile_name not in profiles:
            warnings.append(f"'{name}': '{profile_name}' profili bulunamadı, atlandı.")
            skipped += 1
            continue

        folder_id = None
        fn = qd.get("folder")
        if fn and fn in existing_folders:
            folder_id = existing_folders[fn].Id

        from datetime import datetime as _dt
        def _dt_or_none(v):
            return _dt.fromisoformat(v) if v else None

        sort_order = None
        if qd.get("default_sort_order"):
            try:
                sort_order = SortOrder(qd["default_sort_order"])
            except ValueError:
                pass

        q = Query(
            Name=name,
            GraylogProfileId=profiles[profile_name].Id,
            QueryTemplate=qd.get("query_template", ""),
            TimeRangeType=TimeRangeType(qd.get("time_range_type", "Relative")),
            TimeRangeRangeSeconds=qd.get("time_range_seconds"),
            TimeRangeFrom=_dt_or_none(qd.get("time_range_from")),
            TimeRangeTo=_dt_or_none(qd.get("time_range_to")),
            TimeRangeKeyword=qd.get("time_range_keyword"),
            FieldsJson=json.dumps(qd.get("fields", [])),
            DefaultSortField=qd.get("default_sort_field"),
            DefaultSortOrder=sort_order,
            FolderId=folder_id,
            ResultSize=qd.get("result_size", 150),
        )
        created = queries_repo.create(q)
        streams = [
            QueryStream(QueryId=created.Id, StreamId=s["stream_id"], StreamName=s["stream_name"])
            for s in qd.get("streams", [])
        ]
        if streams:
            streams_repo.replace_for_query(created.Id, streams)
        existing_queries.add(name)
        added += 1

    return added, skipped, warnings
