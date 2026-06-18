"""Query execution orchestration (CLAUDE.md §5).

Owns the business rules: ``{Plaka}`` placeholder injection, time-range computation,
and the Graylog call. The UI passes data in and gets a result back; it never builds
queries or talks to the client directly.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from app.core.encryption import decrypt_token
from app.core.exceptions import QueryValidationError
from app.data.models.customer import Customer
from app.data.models.graylog_profile import GraylogProfile
from app.data.models.query import Query, TimeRangeType
from app.integrations.graylog.client import GraylogClient

PLACEHOLDER = "{Plaka}"


@dataclass
class ExecutionResult:
    fields: list[str]
    rows: list[dict[str, str]]


def _build_query_string(query: Query, customer: Customer | None) -> str:
    if not query.UsesCustomerParameter:
        return query.QueryTemplate

    if customer is None:
        raise QueryValidationError("Bu sorgu için önce bir müşteri/şehir seçin.")
    # NetworkId is an integer from the DB, so injecting it carries no free-text risk
    # (CLAUDE.md §6). Guard defensively regardless.
    if not isinstance(customer.NetworkId, int):
        raise QueryValidationError("Geçersiz müşteri (NetworkId).")
    return query.QueryTemplate.replace(PLACEHOLDER, str(customer.NetworkId))


def _build_timerange(query: Query) -> dict:
    if query.TimeRangeType is TimeRangeType.RELATIVE:
        return {"type": "relative", "range": query.TimeRangeRangeSeconds or 0}
    if query.TimeRangeType is TimeRangeType.ABSOLUTE:
        return {
            "type": "absolute",
            "from": query.TimeRangeFrom.isoformat() if query.TimeRangeFrom else None,
            "to": query.TimeRangeTo.isoformat() if query.TimeRangeTo else None,
        }
    return {"type": "keyword", "keyword": query.TimeRangeKeyword or ""}


def execute_query(
    profile: GraylogProfile,
    query: Query,
    stream_ids: list[str],
    customer: Customer | None,
) -> ExecutionResult:
    """Run ``query`` for an optional ``customer`` and return the result rows."""
    query_string = _build_query_string(query, customer)
    timerange = _build_timerange(query)
    fields = json.loads(query.FieldsJson) if query.FieldsJson else []

    token = decrypt_token(profile.TokenEncrypted)
    client = GraylogClient(profile.BaseUrl, token)
    rows = client.execute_search(
        query_string=query_string,
        streams=stream_ids,
        timerange=timerange,
        fields=fields,
        size=query.ResultSize,
    )
    return ExecutionResult(fields=fields, rows=rows)
