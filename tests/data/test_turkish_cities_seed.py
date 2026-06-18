"""Tests for the Turkish cities seed."""
from __future__ import annotations

from app.data.repositories.customer_repository import CustomerRepository
from app.data.seed.turkish_cities import TURKISH_CITIES, seed_customers


def test_seed_inserts_all_81_provinces(conn):
    repo = CustomerRepository(conn)

    inserted = seed_customers(repo)

    assert inserted == 81
    assert len(TURKISH_CITIES) == 81
    assert repo.get_by_network_id(34).Name == "İstanbul"


def test_seed_is_idempotent(conn):
    repo = CustomerRepository(conn)

    seed_customers(repo)
    second_run = seed_customers(repo)

    assert second_run == 0
    assert len(repo.get_all()) == 81
