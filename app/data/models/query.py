"""Query model (PROJECT_PLAN.md §4.3)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from app.core.config import DEFAULT_RESULT_SIZE


class TimeRangeType(str, Enum):
    RELATIVE = "Relative"
    ABSOLUTE = "Absolute"
    KEYWORD = "Keyword"


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


@dataclass
class Query:
    Name: str
    GraylogProfileId: int
    UsesCustomerParameter: bool
    QueryTemplate: str
    TimeRangeType: TimeRangeType
    FieldsJson: str
    ResultSize: int = DEFAULT_RESULT_SIZE
    TimeRangeRangeSeconds: int | None = None
    TimeRangeFrom: datetime | None = None
    TimeRangeTo: datetime | None = None
    TimeRangeKeyword: str | None = None
    DefaultSortField: str | None = None
    DefaultSortOrder: SortOrder | None = None
    Id: int | None = None
    CreatedAt: datetime | None = None
    UpdatedAt: datetime | None = None
