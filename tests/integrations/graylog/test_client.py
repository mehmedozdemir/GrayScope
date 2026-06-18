"""Offline tests for GraylogClient using httpx's MockTransport."""
from __future__ import annotations

import httpx
import pytest

from app.integrations.graylog.client import GraylogClient
from app.integrations.graylog.exceptions import GraylogAuthError, GraylogTimeoutError


def _client(handler) -> GraylogClient:
    return GraylogClient(
        "https://graylog.example.com/api",
        token="tok",
        transport=httpx.MockTransport(handler),
    )


def test_test_connection_parses_version():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"cluster_id": "abc", "version": "5.1.2"})

    result = _client(handler).test_connection()

    assert result.cluster_id == "abc"
    assert result.version == "5.1.2"


def test_unauthorized_raises_auth_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "nope"})

    with pytest.raises(GraylogAuthError):
        _client(handler).test_connection()


def test_timeout_raises_timeout_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("slow")

    with pytest.raises(GraylogTimeoutError):
        _client(handler).test_connection()


def test_execute_search_parses_csv_and_strips_field_prefix():
    # Graylog returns CSV headers prefixed with "field: " (verified on 5.2.12).
    csv_body = '"field: timestamp","field: StatusCode"\n2026-01-01,500\n2026-01-02,404\n'

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=csv_body)

    rows = _client(handler).execute_search(
        query_string="StatusCode:500",
        streams=["s1"],
        timerange={"type": "relative", "range": 300},
        fields=["timestamp", "StatusCode"],
        size=150,
    )

    assert len(rows) == 2
    assert rows[0] == {"timestamp": "2026-01-01", "StatusCode": "500"}


def test_execute_search_omits_size_when_zero():
    import json

    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, text='"field: a"\n1\n')

    _client(handler).execute_search(
        query_string="*",
        streams=["s"],
        timerange={"type": "relative", "range": 60},
        fields=["a"],
        size=0,
    )

    assert "size" not in captured["body"]  # 0 → fetch all (no limit sent)
