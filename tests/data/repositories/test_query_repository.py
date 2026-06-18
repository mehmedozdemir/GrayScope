"""Happy-path tests for QueryRepository."""
from __future__ import annotations

from app.data.models.graylog_profile import GraylogProfile
from app.data.models.query import Query, TimeRangeType
from app.data.repositories.graylog_profile_repository import GraylogProfileRepository
from app.data.repositories.query_repository import QueryRepository


def _make_profile(conn) -> int:
    profile = GraylogProfileRepository(conn).create(
        GraylogProfile(
            Name="Ana Sunucu",
            BaseUrl="https://graylog.example.com:9000/api",
            TokenEncrypted="encrypted-token",
        )
    )
    return profile.Id


def test_create_and_get_query(conn):
    profile_id = _make_profile(conn)
    repo = QueryRepository(conn)

    created = repo.create(
        Query(
            Name="Şehir bazlı 200 dışı yanıtlar",
            GraylogProfileId=profile_id,
            UsesCustomerParameter=True,
            QueryTemplate="NetworkId:{Plaka} AND NOT StatusCode:200",
            TimeRangeType=TimeRangeType.RELATIVE,
            TimeRangeRangeSeconds=3600,
            FieldsJson='["timestamp", "StatusCode"]',
        )
    )

    assert created.Id is not None

    fetched = repo.get_by_id(created.Id)
    assert fetched is not None
    assert fetched.TimeRangeType is TimeRangeType.RELATIVE
    assert fetched.UsesCustomerParameter is True
    assert fetched.ResultSize == 150
    assert "{Plaka}" in fetched.QueryTemplate
