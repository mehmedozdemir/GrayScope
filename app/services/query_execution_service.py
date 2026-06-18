"""Query execution orchestration (CLAUDE.md §5).

Owns the business rules: named ``{parameter}`` substitution, time-range
computation, and the Graylog call. The UI passes data in and gets a result back;
it never builds queries or talks to the client directly.

Any ``{name}`` token in the query template (name = identifier) is a parameter the
user fills in at run time; the run screen renders one input per distinct parameter.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from app.core.encryption import decrypt_token
from app.core.exceptions import QueryValidationError
from app.data.models.graylog_profile import GraylogProfile
from app.data.models.query import Query, TimeRangeType
from app.integrations.graylog.client import GraylogClient

# A parameter is {Identifier}; restricted to identifier chars so Lucene ranges
# like {1 TO 5} are not mistaken for parameters.
PARAM_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


@dataclass
class ExecutionResult:
    fields: list[str]
    rows: list[dict[str, str]]


def extract_parameters(template: str) -> list[str]:
    """Distinct parameter names found in ``template``, in order of first appearance."""
    seen: list[str] = []
    for match in PARAM_RE.finditer(template or ""):
        name = match.group(1)
        if name not in seen:
            seen.append(name)
    return seen


def _build_query_string(template: str, params: dict[str, str]) -> str:
    def replace(match: re.Match) -> str:
        name = match.group(1)
        value = params.get(name, "")
        if value == "" or value is None:
            raise QueryValidationError(f"'{name}' parametresi için bir değer girin.")
        return str(value)

    return PARAM_RE.sub(replace, template)


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
    params: dict[str, str],
) -> ExecutionResult:
    """Run ``query`` with the given parameter values and return the result rows."""
    query_string = _build_query_string(query.QueryTemplate, params)
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
