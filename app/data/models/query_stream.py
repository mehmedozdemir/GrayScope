"""QueryStream model (PROJECT_PLAN.md §4.4)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class QueryStream:
    QueryId: int
    StreamId: str
    StreamName: str
    Id: int | None = None
