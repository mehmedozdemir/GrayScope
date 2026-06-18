"""Test the legacy {Plaka} -> {NetworkId} template migration."""
from __future__ import annotations

import json

from app.data.database import _migrate, connect, init_schema
from app.data.models.graylog_profile import GraylogProfile
from app.data.models.query import Query, TimeRangeType
from app.data.repositories.graylog_profile_repository import GraylogProfileRepository
from app.data.repositories.query_repository import QueryRepository


def test_migration_renames_plaka_placeholder():
    conn = connect(":memory:")
    init_schema(conn)
    profile = GraylogProfileRepository(conn).create(
        GraylogProfile(Name="P", BaseUrl="https://x/api", TokenEncrypted="enc")
    )
    repo = QueryRepository(conn)
    created = repo.create(
        Query(
            Name="Legacy",
            GraylogProfileId=profile.Id,
            UsesCustomerParameter=True,
            QueryTemplate="NetworkId:{Plaka} AND NOT StatusCode:200",
            TimeRangeType=TimeRangeType.RELATIVE,
            TimeRangeRangeSeconds=60,
            FieldsJson=json.dumps(["timestamp"]),
        )
    )

    _migrate(conn)

    migrated = repo.get_by_id(created.Id)
    assert "{Plaka}" not in migrated.QueryTemplate
    assert "{NetworkId}" in migrated.QueryTemplate
