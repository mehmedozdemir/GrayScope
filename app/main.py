"""GrayScope application entry point."""
from __future__ import annotations

import sqlite3
import sys

from app.data.database import connect, init_schema


def bootstrap() -> sqlite3.Connection:
    conn = connect()
    init_schema(conn)
    return conn


def main() -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication

    from app.ui.main_window import MainWindow
    from app.ui.stylesheets import apply_theme
    from app.ui.theme import DEFAULT_THEME

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("GrayScope")
    app.setOrganizationName("GrayScope")

    mode = QSettings("GrayScope", "GrayScope").value("theme", DEFAULT_THEME)
    apply_theme(app, mode)

    conn = bootstrap()
    window = MainWindow(conn)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
