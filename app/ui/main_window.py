"""Application shell: sidebar + stacked content pages (DESIGN_SYSTEM.md §2)."""
from __future__ import annotations

import sqlite3

from PySide6.QtWidgets import QHBoxLayout, QStackedWidget, QWidget

from app.ui.components.feedback import EmptyState
from app.ui.components.navigation import Sidebar
from app.ui.pages.customers_page import CustomersPage
from app.ui.pages.graylog_profiles_page import GraylogProfilesPage

# (glyph, label) in fixed display order (DESIGN_SYSTEM.md §2).
_NAV_ITEMS = [
    ("\U0001F50E", "Sorgular"),
    ("\U0001F465", "Müşteriler"),
    ("\U0001F5A5", "Graylog Profilleri"),
]


class MainWindow(QWidget):
    def __init__(self, conn: sqlite3.Connection) -> None:
        super().__init__()
        self._conn = conn
        self.setWindowTitle("GrayScope")
        self.setMinimumSize(1280, 720)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._sidebar = Sidebar(_NAV_ITEMS)
        self._stack = QStackedWidget()

        # Index 0: Sorgular — built in the next increment.
        self._stack.addWidget(
            EmptyState(
                "\U0001F50E",
                "Sorgular",
                "Bu ekran bir sonraki adımda eklenecek.",
            )
        )
        # Index 1: Müşteriler
        self._stack.addWidget(CustomersPage(self._conn))
        # Index 2: Graylog Profilleri
        self._stack.addWidget(GraylogProfilesPage(self._conn))

        layout.addWidget(self._sidebar)
        layout.addWidget(self._stack, 1)

        self._sidebar.navigation_changed.connect(self._stack.setCurrentIndex)
        self._sidebar.set_active(0)
