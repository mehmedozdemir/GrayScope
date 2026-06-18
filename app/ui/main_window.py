"""Application shell — hosts the Sorgular page full-window.

The old sidebar navigation is gone: the query tree lives on the left of the
Sorgular page, and profiles/customers moved into the Settings dialog reachable
from the bottom-left of that page.
"""
from __future__ import annotations

import sqlite3

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QVBoxLayout, QWidget

from app.services.stream_catalog_service import StreamCatalogService
from app.ui.pages.queries_page import QueriesPage


class MainWindow(QWidget):
    def __init__(self, conn: sqlite3.Connection) -> None:
        super().__init__()
        self._conn = conn
        self.setWindowTitle("GrayScope")
        self.setMinimumSize(1280, 720)

        self._stream_service = StreamCatalogService()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(QueriesPage(self._conn, self._stream_service))

    def closeEvent(self, event) -> None:
        # Wait for any in-flight worker threads so they are not destroyed mid-run.
        for thread in self.findChildren(QThread):
            if thread.isRunning():
                thread.wait(12000)
        super().closeEvent(event)
