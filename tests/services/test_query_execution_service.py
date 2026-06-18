"""Offline tests for query execution business rules (no network)."""
from __future__ import annotations

import pytest

from app.core.exceptions import QueryValidationError
from app.data.models.customer import Customer
from app.data.models.query import Query, TimeRangeType
from app.services.query_execution_service import _build_query_string, _build_timerange


def _query(**overrides) -> Query:
    base = dict(
        Name="q",
        GraylogProfileId=1,
        UsesCustomerParameter=True,
        QueryTemplate="NetworkId:{Plaka} AND NOT StatusCode:200",
        TimeRangeType=TimeRangeType.RELATIVE,
        FieldsJson='["timestamp"]',
        TimeRangeRangeSeconds=3600,
    )
    base.update(overrides)
    return Query(**base)


def test_placeholder_injection_replaces_plaka():
    query = _query()
    result = _build_query_string(query, Customer(NetworkId=34, Name="İstanbul"))
    assert result == "NetworkId:34 AND NOT StatusCode:200"


def test_missing_customer_raises_validation_error():
    with pytest.raises(QueryValidationError):
        _build_query_string(_query(), None)


def test_non_parametric_query_ignores_customer():
    query = _query(UsesCustomerParameter=False, QueryTemplate="StatusCode:500")
    assert _build_query_string(query, None) == "StatusCode:500"


def test_relative_timerange():
    assert _build_timerange(_query(TimeRangeRangeSeconds=600)) == {
        "type": "relative",
        "range": 600,
    }


def test_keyword_timerange():
    query = _query(TimeRangeType=TimeRangeType.KEYWORD, TimeRangeKeyword="yesterday")
    assert _build_timerange(query) == {"type": "keyword", "keyword": "yesterday"}
