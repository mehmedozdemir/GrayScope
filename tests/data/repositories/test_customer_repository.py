"""Happy-path tests for CustomerRepository."""
from __future__ import annotations

from app.data.models.customer import Customer
from app.data.repositories.customer_repository import CustomerRepository


def test_create_and_get_by_network_id(conn):
    repo = CustomerRepository(conn)

    created = repo.create(Customer(NetworkId=34, Name="İstanbul"))

    assert created.Id is not None

    fetched = repo.get_by_network_id(34)
    assert fetched is not None
    assert fetched.Name == "İstanbul"
    assert fetched.IsActive is True
