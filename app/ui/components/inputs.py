"""Input components: search box, labeled-field helper, and a chip/tag input."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ui.theme import Spacing


class SearchInput(QLineEdit):
    """A line edit pre-styled as a search box with a magnifier placeholder."""

    def __init__(self, placeholder: str = "Ara...", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setPlaceholderText(f"\U0001F50D  {placeholder}")
        self.setClearButtonEnabled(True)


def labeled_field(label_text: str, field: QWidget, required: bool = False) -> QWidget:
    """Wrap a widget with a visible label above it (labels always visible — skill rule)."""
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(Spacing.XS)

    label = QLabel(f"{label_text} *" if required else label_text)
    label.setProperty("class", "field-label")
    label.setBuddy(field)

    layout.addWidget(label)
    layout.addWidget(field)
    return container


class ChipInput(QWidget):
    """Tag input: type a value + Enter to add a chip, click ✕ to remove it
    (DESIGN_SYSTEM.md §4 item 7). Emits ``changed`` when the value set changes."""

    changed = Signal()

    def __init__(self, placeholder: str = "Alan adı yazıp Enter'a basın", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._values: list[str] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.SM)

        self._chips_host = QWidget()
        self._chips_layout = QHBoxLayout(self._chips_host)
        self._chips_layout.setContentsMargins(0, 0, 0, 0)
        self._chips_layout.setSpacing(Spacing.XS)
        self._chips_layout.addStretch()

        self._entry = QLineEdit()
        self._entry.setPlaceholderText(placeholder)
        self._entry.returnPressed.connect(self._on_enter)

        layout.addWidget(self._chips_host)
        layout.addWidget(self._entry)

    def _on_enter(self) -> None:
        value = self._entry.text().strip()
        self._entry.clear()
        if value and value not in self._values:
            self._values.append(value)
            self._rebuild()
            self.changed.emit()

    def _remove(self, value: str) -> None:
        self._values.remove(value)
        self._rebuild()
        self.changed.emit()

    def _rebuild(self) -> None:
        while self._chips_layout.count() > 1:  # keep the trailing stretch
            item = self._chips_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for value in self._values:
            self._chips_layout.insertWidget(self._chips_layout.count() - 1, self._make_chip(value))

    def _make_chip(self, value: str) -> QWidget:
        chip = QFrame()
        chip.setProperty("class", "chip")
        row = QHBoxLayout(chip)
        row.setContentsMargins(Spacing.SM, 2, Spacing.XS, 2)
        row.setSpacing(Spacing.XS)
        row.addWidget(QLabel(value))
        remove = QPushButton("✕")
        remove.setProperty("variant", "ghost")
        remove.setFixedSize(18, 18)
        remove.setToolTip("Kaldır")
        remove.clicked.connect(lambda: self._remove(value))
        row.addWidget(remove)
        return chip

    def values(self) -> list[str]:
        return list(self._values)

    def set_values(self, values: list[str]) -> None:
        self._values = list(dict.fromkeys(values))
        self._rebuild()
        self.changed.emit()
