"""Table components: a configured table plus an empty-state-aware panel."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QStackedWidget,
    QTableWidget,
    QWidget,
)

from app.ui.components.feedback import EmptyState


def make_table(headers: list[str]) -> QTableWidget:
    """A read-optimized table: row selection, no inline edit, client-side sorting."""
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setAlternatingRowColors(True)
    table.setSortingEnabled(True)
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    table.horizontalHeader().setHighlightSections(False)
    return table


class TablePanel(QStackedWidget):
    """Stacks a table with a designed empty state, toggled via :meth:`set_empty`."""

    def __init__(
        self,
        headers: list[str],
        empty_icon: str,
        empty_title: str,
        empty_subtitle: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.table = make_table(headers)
        self._empty = EmptyState(empty_icon, empty_title, empty_subtitle)
        self.addWidget(self.table)   # index 0
        self.addWidget(self._empty)  # index 1

    def set_empty(self, is_empty: bool) -> None:
        self.setCurrentIndex(1 if is_empty else 0)
