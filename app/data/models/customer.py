"""Customer (city / plate-code) model (PROJECT_PLAN.md §4.2)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Customer:
    NetworkId: int
    Name: str
    IsActive: bool = True
    Description: str | None = None
    Id: int | None = None
