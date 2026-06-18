"""Request/response data classes for the Graylog REST integration."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ConnectionTestResult:
    """Outcome of a successful connection test (GET /api/system)."""

    cluster_id: str | None
    version: str | None


@dataclass
class StreamInfo:
    """A Graylog stream as needed for selection (GET /api/streams)."""

    id: str
    title: str
