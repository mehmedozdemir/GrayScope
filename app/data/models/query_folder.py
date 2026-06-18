"""QueryFolder model — tree of folders for organizing queries."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class QueryFolder:
    Name: str
    ParentId: int | None = None  # None = root-level folder
    Id: int | None = None
