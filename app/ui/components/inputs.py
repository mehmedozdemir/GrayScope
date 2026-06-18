"""Input components: search box and a helper for labeled form fields."""
from __future__ import annotations

from PySide6.QtWidgets import QLabel, QLineEdit, QVBoxLayout, QWidget

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
