"""Happy-path tests for QueryStreamRepository."""
from __future__ import annotations

from app.data.models.graylog_profile import GraylogProfile
from app.data.models.query import Query, TimeRangeType
from app.data.models.query_stream import QueryStream
from app.data.repositories.graylog_profile_repository import GraylogProfileRepository
from app.data.repositories.query_repository import QueryRepository
from app.data.repositories.query_stream_repository import QueryStreamRepository


def _make_query(conn) -> int:
    profile = GraylogProfileRepository(conn).create(
        GraylogProfile(
            Name="Ana Sunucu",
            BaseUrl="https://graylog.example.com:9000/api",
            TokenEncrypted="encrypted-token",
        )
    )
    query = QueryRepository(conn).create(
        Query(
            Name="Test Sorgusu",
            GraylogProfileId=profile.Id,
            QueryTemplate="StatusCode:500",
            TimeRangeType=TimeRangeType.KEYWORD,
            TimeRangeKeyword="yesterday",
            FieldsJson='["timestamp"]',
        )
    )
    return query.Id


def test_create_and_get_by_query(conn):
    query_id = _make_query(conn)
    repo = QueryStreamRepository(conn)

    repo.create(
        QueryStream(QueryId=query_id, StreamId="000000000000000000000001", StreamName="All messages")
    )

    streams = repo.get_by_query(query_id)
    assert len(streams) == 1
    assert streams[0].StreamName == "All messages"
    assert streams[0].Id is not None
