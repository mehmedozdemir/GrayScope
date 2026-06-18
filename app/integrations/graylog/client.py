"""httpx-based Graylog REST client.

Holds no business logic (CLAUDE.md §5): it only builds, sends and parses HTTP
requests, mapping transport/HTTP failures to Graylog integration exceptions.
"""
from __future__ import annotations

import httpx

from app.core.config import GRAYLOG_TIMEOUT_SECONDS, REQUESTED_BY
from app.integrations.graylog.exceptions import (
    GraylogAuthError,
    GraylogConnectionError,
    GraylogTimeoutError,
)
from app.integrations.graylog.schemas import ConnectionTestResult, StreamInfo


class GraylogClient:
    def __init__(
        self,
        base_url: str,
        token: str,
        timeout: float = GRAYLOG_TIMEOUT_SECONDS,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        # BaseUrl already includes the "/api" suffix (PROJECT_PLAN.md §4.1).
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._timeout = timeout
        self._transport = transport  # injected only in tests

    def _headers(self, accept: str = "application/json") -> dict[str, str]:
        return {"Accept": accept, "X-Requested-By": REQUESTED_BY}

    def _request(self, method: str, path: str, accept: str = "application/json", **kwargs) -> httpx.Response:
        url = f"{self._base_url}/{path.lstrip('/')}"
        try:
            with httpx.Client(timeout=self._timeout, transport=self._transport) as client:
                response = client.request(
                    method,
                    url,
                    auth=(self._token, "token"),  # Graylog token auth pattern.
                    headers=self._headers(accept),
                    **kwargs,
                )
        except httpx.TimeoutException as exc:
            raise GraylogTimeoutError("Graylog sunucusuna ulaşılamadı (zaman aşımı).") from exc
        except httpx.HTTPError as exc:
            raise GraylogConnectionError("Graylog sunucusuna bağlanılamadı.") from exc

        if response.status_code in (401, 403):
            raise GraylogAuthError(
                "Kimlik doğrulama başarısız — token geçersiz veya süresi dolmuş."
            )
        return response

    def test_connection(self) -> ConnectionTestResult:
        """Hit GET /system to verify reachability and credentials (PROJECT_PLAN.md §3.2)."""
        response = self._request("GET", "/system")
        response.raise_for_status()
        payload = response.json()
        return ConnectionTestResult(
            cluster_id=payload.get("cluster_id"),
            version=payload.get("version"),
        )

    def get_streams(self) -> list[StreamInfo]:
        """List streams (GET /streams) for query stream selection."""
        response = self._request("GET", "/streams")
        response.raise_for_status()
        payload = response.json()
        return [
            StreamInfo(id=item["id"], title=item.get("title", item["id"]))
            for item in payload.get("streams", [])
        ]

    def execute_search(
        self,
        query_string: str,
        streams: list[str],
        timerange: dict,
        fields: list[str],
        size: int,
    ) -> list[dict[str, str]]:
        """Run a message search via POST /search/messages (Graylog 5.1 Scripting API).

        The endpoint returns CSV; rows are parsed into field→value dicts and
        truncated to ``size`` client-side (the export endpoint has no native limit).
        Response-shape assumption documented in PROJECT_PLAN.md §3.2 / §8.
        """
        body = {
            "streams": streams,
            "timerange": timerange,
            "query_string": {"type": "elasticsearch", "query_string": query_string},
            "fields_in_order": fields,
        }
        response = self._request("POST", "/search/messages", accept="text/csv", json=body)
        response.raise_for_status()

        import csv
        import io

        reader = csv.DictReader(io.StringIO(response.text))
        rows: list[dict[str, str]] = []
        for index, row in enumerate(reader):
            if index >= size:
                break
            rows.append(row)
        return rows
