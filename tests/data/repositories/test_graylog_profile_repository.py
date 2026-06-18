"""Happy-path tests for GraylogProfileRepository."""
from __future__ import annotations

from app.data.models.graylog_profile import GraylogProfile
from app.data.repositories.graylog_profile_repository import GraylogProfileRepository


def test_create_and_get_profile(conn):
    repo = GraylogProfileRepository(conn)

    created = repo.create(
        GraylogProfile(
            Name="Ana Sunucu",
            BaseUrl="https://graylog.example.com:9000/api",
            TokenEncrypted="encrypted-token",
            IsDefault=True,
        )
    )

    assert created.Id is not None
    assert created.CreatedAt is not None

    fetched = repo.get_by_id(created.Id)
    assert fetched is not None
    assert fetched.Name == "Ana Sunucu"
    assert fetched.IsDefault is True
    assert fetched.IsActive is True
