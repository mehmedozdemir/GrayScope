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
    ) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
        """Run a message search, auto-detecting Graylog API version.

        Returns ``(selected_rows, all_rows)`` where ``selected_rows`` contains
        only the requested ``fields`` and ``all_rows`` contains every field
        available in each message (used by the "Tüm Alanları Göster" detail view).
        For the 5.x CSV path ``all_rows`` equals ``selected_rows`` because the
        CSV response carries only the requested columns.
        """
        body: dict = {
            "query": query_string,
            "streams": streams,
            "timerange": timerange,
            "fields": fields,
        }
        if size and size > 0:
            body["size"] = size

        response = self._request("POST", "/search/messages", accept="text/csv", json=body)

        if response.status_code == 404:
            # Graylog 2.x — fall back to universal search REST API.
            return self._execute_search_legacy(query_string, streams, timerange, fields, size)

        response.raise_for_status()

        import csv
        import io

        reader = csv.reader(io.StringIO(response.text))
        try:
            header = [col.removeprefix("field: ") for col in next(reader)]
        except StopIteration:
            return [], []
        selected_rows = [dict(zip(header, row)) for row in reader]

        if not selected_rows:
            return [], []

        # Fetch all fields for the detail view via the legacy endpoint (available
        # in both 5.x and 2.x). Pass no fields so every message field is returned.
        try:
            _, all_rows = self._execute_search_legacy(
                query_string, streams, timerange, fields=[], size=size
            )
        except Exception:
            all_rows = selected_rows

        return selected_rows, all_rows

    def _execute_search_legacy(
        self,
        query_string: str,
        streams: list[str],
        timerange: dict,
        fields: list[str],
        size: int,
    ) -> list[dict[str, str]]:
        """Graylog 2.x universal search API.

        Endpoints:
          GET /search/universal/relative  — timerange.type == "relative"
          GET /search/universal/absolute  — timerange.type == "absolute"
          GET /search/universal/keyword   — timerange.type == "keyword"

        Response: {"messages": [{"message": {...}}, ...]}
        """
        tr_type = timerange.get("type", "relative")

        # Do NOT send ?fields= — we want every field from each message so that
        # the "Tüm Alanları Göster" detail view can show the full raw record.
        # selected_rows is filtered client-side to the user's chosen columns.
        params: dict = {
            "query": query_string,
            "limit": size if size > 0 else 150,
        }
        if streams:
            params["filter"] = "streams:" + ",".join(streams)

        if tr_type == "relative":
            params["range"] = timerange.get("range", 300)
            path = "/search/universal/relative"
        elif tr_type == "absolute":
            params["from"] = timerange.get("from", "")
            params["to"] = timerange.get("to", "")
            path = "/search/universal/absolute"
        else:  # keyword
            params["keyword"] = timerange.get("keyword", "last 5 minutes")
            path = "/search/universal/keyword"

        response = self._request("GET", path, params=params)
        response.raise_for_status()
        payload = response.json()

        messages = payload.get("messages", [])
        if not messages:
            return [], []

        raw_msgs = [msg.get("message", {}) for msg in messages]

        # selected_rows: only the columns the user configured
        cols = fields if fields else sorted(raw_msgs[0].keys())
        selected_rows = [
            {col: str(raw.get(col, "")) for col in cols}
            for raw in raw_msgs
        ]
        # all_rows: every field present across all messages (union)
        all_fields = sorted({k for raw in raw_msgs for k in raw.keys()})
        all_rows = [
            {col: str(raw.get(col, "")) for col in all_fields}
            for raw in raw_msgs
        ]
        return selected_rows, all_rows
