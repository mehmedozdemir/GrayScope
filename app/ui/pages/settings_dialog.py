"""Ayarlar ve Tanımlamalar — settings/definitions modal."""
from __future__ import annotations

import sqlite3

from PySide6.QtWidgets import QDialog, QTabWidget, QVBoxLayout, QWidget

from app.ui.pages.graylog_profiles_page import GraylogProfilesPage
from app.ui.theme import Spacing


class SettingsDialog(QDialog):
    def __init__(self, conn: sqlite3.Connection, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ayarlar ve Tanımlamalar")
        self.setModal(True)
        self.setMinimumSize(720, 560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        layout.setSpacing(Spacing.MD)

        tabs = QTabWidget()
        tabs.addTab(GraylogProfilesPage(conn), "Graylog Profilleri")
        layout.addWidget(tabs)
