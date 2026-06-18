"""GraylogProfile model (PROJECT_PLAN.md §4.1)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class GraylogProfile:
    Name: str
    BaseUrl: str
    TokenEncrypted: str
    IsDefault: bool = False
    IsActive: bool = True
    Id: int | None = None
    CreatedAt: datetime | None = None
    UpdatedAt: datetime | None = None
