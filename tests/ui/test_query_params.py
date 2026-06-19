"""Offscreen tests for run-screen parameter fields (defaults + preservation)."""
from __future__ import annotations

import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from app.data.database import connect, init_schema
from app.data.models.graylog_profile import GraylogProfile
from app.data.models.query import Query, TimeRangeType
from app.data.repositories.graylog_profile_repository import GraylogProfileRepository
from app.data.repositories.query_repository import QueryRepository
from app.services.stream_catalog_service import StreamCatalogService


@pytest.fixture(scope="module")
def qapp():
    from app.ui.stylesheets import apply_theme

    app = QApplication.instance() or QApplication([])
    apply_theme(app, "dark")
    return app


def _make_query(repo, profile_id, name, template):
    return repo.create(
        Query(
            Name=name,
            GraylogProfileId=profile_id,
            QueryTemplate=template,
            TimeRangeType=TimeRangeType.RELATIVE,
            TimeRangeRangeSeconds=60,
            FieldsJson=json.dumps(["timestamp"]),
        )
    )


def test_parameter_defaults_appear_on_selection(qapp):
    from app.ui.pages.queries_page import QueriesPage

    conn = connect(":memory:")
    init_schema(conn)
    profile = GraylogProfileRepository(conn).create(
        GraylogProfile(Name="P", BaseUrl="https://x/api", TokenEncrypted="enc")
    )
    repo = QueryRepository(conn)
    no_default = _make_query(repo, profile.Id, "A", "region:{region}")
    with_default = _make_query(repo, profile.Id, "B", "region:{region:TR-34}")

    page = QueriesPage(conn, StreamCatalogService())

    page._selected = no_default
    page._show_detail(no_default)
    assert page._param_fields["region"].text() == ""

    # Switching to a query whose default differs must show the new default,
    # not carry over the previous (empty) value.
    page._selected = with_default
    page._show_detail(with_default)
    assert page._param_fields["region"].text() == "TR-34"


def test_live_edit_preserves_entered_values(qapp):
    from app.ui.pages.queries_page import QueriesPage

    conn = connect(":memory:")
    init_schema(conn)
    profile = GraylogProfileRepository(conn).create(
        GraylogProfile(Name="P", BaseUrl="https://x/api", TokenEncrypted="enc")
    )
    repo = QueryRepository(conn)
    query = _make_query(repo, profile.Id, "A", "region:{region}")

    page = QueriesPage(conn, StreamCatalogService())
    page._selected = query
    page._show_detail(query)

    page._param_fields["region"].setText("TR-99")
    page._query_input.setText(page._query_input.text() + " AND s:{samId}")

    assert page._param_fields["region"].text() == "TR-99"  # kept
    assert "samId" in page._param_fields  # new field added
