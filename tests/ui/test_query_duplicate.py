"""Offscreen test for duplicating a query (with streams and folder)."""
from __future__ import annotations

import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from app.data.database import connect, init_schema
from app.data.models.graylog_profile import GraylogProfile
from app.data.models.query import Query, TimeRangeType
from app.data.models.query_stream import QueryStream
from app.data.repositories.graylog_profile_repository import GraylogProfileRepository
from app.data.repositories.query_repository import QueryRepository
from app.data.repositories.query_stream_repository import QueryStreamRepository
from app.services.stream_catalog_service import StreamCatalogService


@pytest.fixture(scope="module")
def qapp():
    from app.ui.stylesheets import apply_theme

    app = QApplication.instance() or QApplication([])
    apply_theme(app, "dark")
    return app


def test_copy_query_duplicates_with_streams(qapp):
    from app.ui.pages.queries_page import QueriesPage

    conn = connect(":memory:")
    init_schema(conn)
    profile = GraylogProfileRepository(conn).create(
        GraylogProfile(Name="P", BaseUrl="https://x/api", TokenEncrypted="enc")
    )
    query = QueryRepository(conn).create(
        Query(
            Name="Orijinal",
            GraylogProfileId=profile.Id,
            UsesCustomerParameter=False,
            QueryTemplate="*",
            TimeRangeType=TimeRangeType.RELATIVE,
            TimeRangeRangeSeconds=60,
            FieldsJson=json.dumps(["timestamp"]),
            FolderId=None,
        )
    )
    streams_repo = QueryStreamRepository(conn)
    streams_repo.create(QueryStream(QueryId=query.Id, StreamId="s1", StreamName="All"))

    page = QueriesPage(conn, StreamCatalogService())
    page._copy_query(query.Id)

    all_queries = QueryRepository(conn).get_all()
    assert len(all_queries) == 2
    copy = next(q for q in all_queries if q.Id != query.Id)
    assert copy.Name == "Orijinal (kopya)"
    assert [s.StreamName for s in streams_repo.get_by_query(copy.Id)] == ["All"]
