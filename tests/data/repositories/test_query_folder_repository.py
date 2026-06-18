"""Tests for QueryFolderRepository and Query.FolderId."""
from __future__ import annotations

import json

from app.data.models.graylog_profile import GraylogProfile
from app.data.models.query import Query, TimeRangeType
from app.data.models.query_folder import QueryFolder
from app.data.repositories.graylog_profile_repository import GraylogProfileRepository
from app.data.repositories.query_folder_repository import QueryFolderRepository
from app.data.repositories.query_repository import QueryRepository


def test_create_nested_folders_and_list(conn):
    repo = QueryFolderRepository(conn)
    root = repo.create(QueryFolder(Name="Şehir"))
    child = repo.create(QueryFolder(Name="Alt", ParentId=root.Id))

    folders = repo.get_all()
    assert {f.Name for f in folders} == {"Şehir", "Alt"}
    assert next(f for f in folders if f.Name == "Alt").ParentId == root.Id


def test_delete_folder_moves_queries_to_root(conn):
    profile = GraylogProfileRepository(conn).create(
        GraylogProfile(Name="P", BaseUrl="https://x/api", TokenEncrypted="enc")
    )
    folders = QueryFolderRepository(conn)
    queries = QueryRepository(conn)
    folder = folders.create(QueryFolder(Name="Klasör"))
    query = queries.create(
        Query(
            Name="Q",
            GraylogProfileId=profile.Id,
            UsesCustomerParameter=False,
            QueryTemplate="*",
            TimeRangeType=TimeRangeType.RELATIVE,
            TimeRangeRangeSeconds=60,
            FieldsJson=json.dumps(["timestamp"]),
            FolderId=folder.Id,
        )
    )
    assert queries.get_by_id(query.Id).FolderId == folder.Id

    folders.delete(folder.Id)

    assert queries.get_by_id(query.Id).FolderId is None
    assert folders.get_all() == []
