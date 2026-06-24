"""Query backup / restore service.

Exports GraylogProfiles + QueryFolders + Queries + QueryStreams to JSON.
Imports them back, matching by name and skipping duplicates.

Token note: TokenEncrypted is exported as-is (Fernet-encrypted, machine-specific key).
On the same machine the token decrypts correctly. On a different machine decryption
fails gracefully — the profile is created with an empty placeholder token and the user
is warned to re-enter the token in profile settings.

Format (version 2):
{
  "version": 2,
  "exported_at": "<ISO-8601>",
  "profiles": [
    {
      "name": "...",
      "base_url": "...",
      "token_encrypted": "...",   ← Fernet-encrypted, machine-specific
      "is_default": bool,
      "is_active": bool
    }, ...
  ],
  "folders": [{"name": "...", "parent_name": "..." | null}, ...],
  "queries": [
    {
      "name": "...",
      "folder": "..." | null,
      "profile_name": "...",
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
    }, ...
  ]
}
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from app.data.models.graylog_profile import GraylogProfile
from app.data.models.query import Query, SortOrder, TimeRangeType
from app.data.models.query_folder import QueryFolder
from app.data.models.query_stream import QueryStream
from app.data.repositories.graylog_profile_repository import GraylogProfileRepository
from app.data.repositories.query_folder_repository import QueryFolderRepository
from app.data.repositories.query_repository import QueryRepository
from app.data.repositories.query_stream_repository import QueryStreamRepository

_VERSION = 2
_PLACEHOLDER_TOKEN = "PLACEHOLDER"


def export_backup(conn: sqlite3.Connection, include_tokens: bool = True) -> dict:
    all_profiles = GraylogProfileRepository(conn).get_all()
    folders = QueryFolderRepository(conn).get_all()
    queries = QueryRepository(conn).get_all()
    profiles_by_id = {p.Id: p for p in all_profiles}
    streams_repo = QueryStreamRepository(conn)

    folder_by_id = {f.Id: f for f in folders}

    def folder_name(fid: int | None) -> str | None:
        return folder_by_id[fid].Name if fid and fid in folder_by_id else None

    def parent_name(f: QueryFolder) -> str | None:
        return folder_by_id[f.ParentId].Name if f.ParentId and f.ParentId in folder_by_id else None

    return {
        "version": _VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "profiles": [
            {
                "name": p.Name,
                "base_url": p.BaseUrl,
                "token_encrypted": p.TokenEncrypted if include_tokens else "",
                "is_default": p.IsDefault,
                "is_active": p.IsActive,
            }
            for p in all_profiles
        ],
        "folders": [
            {"name": f.Name, "parent_name": parent_name(f)}
            for f in folders
        ],
        "queries": [
            {
                "name": q.Name,
                "folder": folder_name(q.FolderId),
                "profile_name": profiles_by_id[q.GraylogProfileId].Name if q.GraylogProfileId in profiles_by_id else "",
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


def import_backup(conn: sqlite3.Connection, data: dict) -> tuple[int, int, int, list[str]]:
    """Import backup data.

    Returns (profiles_added, queries_added, queries_skipped, warnings).
    Version 1 files (no profiles section) are still supported.
    """
    version = data.get("version", 1)
    if version not in (1, 2):
        raise ValueError(f"Desteklenmeyen yedek formatı (version={version}).")

    profiles_repo = GraylogProfileRepository(conn)
    folders_repo = QueryFolderRepository(conn)
    queries_repo = QueryRepository(conn)
    streams_repo = QueryStreamRepository(conn)

    warnings: list[str] = []
    profiles_added = 0

    # ── Restore profiles ─────────────────────────────────────────────────
    existing_profiles = {p.Name: p for p in profiles_repo.get_all()}

    for pd in data.get("profiles", []):
        name = pd["name"]
        if name in existing_profiles:
            continue

        # Try to use the exported encrypted token directly (same-machine restore).
        # If the token is a placeholder or decryption will fail on import, the user
        # must re-enter it via profile settings — we still create the profile record.
        token = pd.get("token_encrypted") or _PLACEHOLDER_TOKEN
        try:
            from app.core.encryption import decrypt_token
            decrypt_token(token)  # validate token is decryptable on this machine
        except Exception:
            token = _PLACEHOLDER_TOKEN
            warnings.append(
                f"'{name}' profilinin token'ı bu makinede çözülemedi. "
                "Profil oluşturuldu — lütfen Ayarlar'dan token'ı yeniden girin."
            )

        profile = GraylogProfile(
            Name=name,
            BaseUrl=pd.get("base_url", ""),
            TokenEncrypted=token,
            IsDefault=pd.get("is_default", False),
            IsActive=pd.get("is_active", True),
        )
        created = profiles_repo.create(profile)
        existing_profiles[name] = created
        profiles_added += 1

    # ── Restore folders ───────────────────────────────────────────────────
    existing_folders = {f.Name: f for f in folders_repo.get_all()}

    def _ensure_folder(name: str, parent: str | None) -> QueryFolder:
        if name in existing_folders:
            return existing_folders[name]
        parent_id = existing_folders[parent].Id if parent and parent in existing_folders else None
        created = folders_repo.create(QueryFolder(Name=name, ParentId=parent_id))
        existing_folders[name] = created
        return created

    for entry in data.get("folders", []):
        p = entry.get("parent_name")
        if p and p not in existing_folders:
            _ensure_folder(p, None)
        _ensure_folder(entry["name"], p)

    # ── Restore queries ───────────────────────────────────────────────────
    existing_queries = {q.Name for q in queries_repo.get_all()}
    added = skipped = 0

    for qd in data.get("queries", []):
        name = qd["name"]
        if name in existing_queries:
            skipped += 1
            continue

        profile_name = qd.get("profile_name", "")
        if profile_name not in existing_profiles:
            warnings.append(f"'{name}': '{profile_name}' profili bulunamadı, sorgu atlandı.")
            skipped += 1
            continue

        folder_id = None
        fn = qd.get("folder")
        if fn and fn in existing_folders:
            folder_id = existing_folders[fn].Id

        def _dt_or_none(v):
            from datetime import datetime as _dt
            return _dt.fromisoformat(v) if v else None

        sort_order = None
        if qd.get("default_sort_order"):
            try:
                sort_order = SortOrder(qd["default_sort_order"])
            except ValueError:
                pass

        q = Query(
            Name=name,
            GraylogProfileId=existing_profiles[profile_name].Id,
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

    return profiles_added, added, skipped, warnings
