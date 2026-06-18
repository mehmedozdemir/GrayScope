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
