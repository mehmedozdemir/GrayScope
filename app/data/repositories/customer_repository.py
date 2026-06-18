"""CRUD for the Customer (city / plate-code) table."""
from __future__ import annotations

import sqlite3

from app.core.exceptions import DuplicateRecordError
from app.data.models.customer import Customer


def _row_to_model(row: sqlite3.Row) -> Customer:
    return Customer(
        Id=row["Id"],
        NetworkId=row["NetworkId"],
        Name=row["Name"],
        IsActive=bool(row["IsActive"]),
        Description=row["Description"],
    )


class CustomerRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(self, customer: Customer) -> Customer:
        try:
            cursor = self._conn.execute(
                """
                INSERT INTO Customer (NetworkId, Name, IsActive, Description)
                VALUES (?, ?, ?, ?)
                """,
                (
                    customer.NetworkId,
                    customer.Name,
                    int(customer.IsActive),
                    customer.Description,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise DuplicateRecordError(
                f"NetworkId {customer.NetworkId} zaten kayıtlı."
            ) from exc
        self._conn.commit()
        customer.Id = cursor.lastrowid
        return customer

    def bulk_create(self, customers: list[Customer]) -> int:
        """Insert many customers in one transaction, ignoring duplicates by NetworkId.

        Returns the number of rows actually inserted. Used by city seeding so that
        re-running seed is idempotent.
        """
        before = self._conn.total_changes
        self._conn.executemany(
            """
            INSERT OR IGNORE INTO Customer (NetworkId, Name, IsActive, Description)
            VALUES (?, ?, ?, ?)
            """,
            [
                (c.NetworkId, c.Name, int(c.IsActive), c.Description)
                for c in customers
            ],
        )
        self._conn.commit()
        return self._conn.total_changes - before

    def get_by_id(self, customer_id: int) -> Customer | None:
        row = self._conn.execute(
            "SELECT * FROM Customer WHERE Id = ?", (customer_id,)
        ).fetchone()
        return _row_to_model(row) if row else None

    def get_by_network_id(self, network_id: int) -> Customer | None:
        row = self._conn.execute(
            "SELECT * FROM Customer WHERE NetworkId = ?", (network_id,)
        ).fetchone()
        return _row_to_model(row) if row else None

    def get_all(self, only_active: bool = False) -> list[Customer]:
        sql = "SELECT * FROM Customer"
        if only_active:
            sql += " WHERE IsActive = 1"
        sql += " ORDER BY NetworkId"
        return [_row_to_model(r) for r in self._conn.execute(sql).fetchall()]

    def update(self, customer: Customer) -> Customer:
        try:
            self._conn.execute(
                """
                UPDATE Customer
                   SET NetworkId = ?, Name = ?, IsActive = ?, Description = ?
                 WHERE Id = ?
                """,
                (
                    customer.NetworkId,
                    customer.Name,
                    int(customer.IsActive),
                    customer.Description,
                    customer.Id,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise DuplicateRecordError(
                f"NetworkId {customer.NetworkId} zaten kayıtlı."
            ) from exc
        self._conn.commit()
        return customer

    def delete(self, customer_id: int) -> None:
        self._conn.execute("DELETE FROM Customer WHERE Id = ?", (customer_id,))
        self._conn.commit()
