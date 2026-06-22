"""GrayScope application entry point."""
from __future__ import annotations

import logging
import sqlite3
import sys
from pathlib import Path

from app.data.database import connect, init_schema


def _setup_logging() -> None:
    log_dir = Path.home() / ".grayscope"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "grayscope.log"
    logging.basicConfig(
        level=logging.ERROR,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stderr),
        ],
    )


def bootstrap() -> sqlite3.Connection:
    conn = connect()
    init_schema(conn)
    return conn


def main() -> None:
    _setup_logging()
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
