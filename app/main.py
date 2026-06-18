"""GrayScope application entry point.

Bootstraps the database (schema + city seed), then launches the PySide6 UI.
"""
from __future__ import annotations

import sqlite3
import sys

from app.data.database import connect, init_schema
from app.data.repositories.customer_repository import CustomerRepository
from app.data.seed.turkish_cities import seed_customers


def bootstrap() -> sqlite3.Connection:
    """Create the schema and seed reference data, returning the shared connection."""
    conn = connect()
    init_schema(conn)
    seed_customers(CustomerRepository(conn))
    return conn


def main() -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    from app.ui.main_window import MainWindow
    from app.ui.stylesheets import apply_theme

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("GrayScope")
    apply_theme(app)

    conn = bootstrap()
    window = MainWindow(conn)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
