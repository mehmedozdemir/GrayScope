"""Offline tests for query execution business rules (no network)."""
from __future__ import annotations

import pytest

from app.core.exceptions import QueryValidationError
from app.data.models.query import Query, TimeRangeType
from app.services.query_execution_service import (
    _build_query_string,
    _build_timerange,
    extract_parameters,
)


def _query(**overrides) -> Query:
    base = dict(
        Name="q",
        GraylogProfileId=1,
        UsesCustomerParameter=True,
        QueryTemplate="NetworkId:{NetworkId} AND NOT StatusCode:200",
        TimeRangeType=TimeRangeType.RELATIVE,
        FieldsJson='["timestamp"]',
        TimeRangeRangeSeconds=3600,
    )
    base.update(overrides)
    return Query(**base)


def test_extract_parameters_distinct_in_order():
    template = "a:{NetworkId} b:{samId} c:{NetworkId}"
    assert extract_parameters(template) == ["NetworkId", "samId"]


def test_extract_parameters_ignores_lucene_ranges():
    # {1 TO 5} is not an identifier, so it is not treated as a parameter.
    assert extract_parameters("age:{1 TO 5}") == []


def test_build_query_string_substitutes_named_params():
    template = "NetworkId:{NetworkId} AND service:{samId}"
    result = _build_query_string(template, {"NetworkId": "34", "samId": "abc"})
    assert result == "NetworkId:34 AND service:abc"


def test_missing_or_empty_param_raises():
    with pytest.raises(QueryValidationError):
        _build_query_string("x:{NetworkId}", {"NetworkId": ""})
    with pytest.raises(QueryValidationError):
        _build_query_string("x:{NetworkId}", {})


def test_template_without_params_is_unchanged():
    assert _build_query_string("StatusCode:500", {}) == "StatusCode:500"


def test_relative_timerange():
    assert _build_timerange(_query(TimeRangeRangeSeconds=600)) == {
        "type": "relative",
        "range": 600,
    }


def test_keyword_timerange():
    query = _query(TimeRangeType=TimeRangeType.KEYWORD, TimeRangeKeyword="yesterday")
    assert _build_timerange(query) == {"type": "keyword", "keyword": "yesterday"}
