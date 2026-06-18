"""Stream catalog with per-profile caching (PROJECT_PLAN.md §3.6, CLAUDE.md §5)."""
from __future__ import annotations

from app.core.encryption import decrypt_token
from app.data.models.graylog_profile import GraylogProfile
from app.integrations.graylog.client import GraylogClient
from app.integrations.graylog.schemas import StreamInfo


class StreamCatalogService:
    """Fetches and caches a profile's stream list. One instance is shared across the UI."""

    def __init__(self) -> None:
        self._cache: dict[int, list[StreamInfo]] = {}

    def get_streams(self, profile: GraylogProfile, force_refresh: bool = False) -> list[StreamInfo]:
        if not force_refresh and profile.Id in self._cache:
            return self._cache[profile.Id]

        token = decrypt_token(profile.TokenEncrypted)
        streams = GraylogClient(profile.BaseUrl, token).get_streams()
        if profile.Id is not None:
            self._cache[profile.Id] = streams
        return streams

    def invalidate(self, profile_id: int) -> None:
        self._cache.pop(profile_id, None)
