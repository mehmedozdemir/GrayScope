"""Sidebar navigation (DESIGN_SYSTEM.md §2)."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout

from app.ui.components.buttons import refresh_style
from app.ui.theme import Sidebar as SidebarTokens
from app.ui.theme import Spacing


class Sidebar(QFrame):
    """Fixed-width left navigation. Emits ``navigation_changed(index)`` on selection."""

    navigation_changed = Signal(int)

    def __init__(self, items: list[tuple[str, str]]) -> None:
        """``items`` is a list of (glyph, label) pairs in display order."""
        super().__init__()
        self.setProperty("class", "sidebar")
        self.setFixedWidth(SidebarTokens.WIDTH)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.MD, Spacing.LG, Spacing.MD, Spacing.LG)
        layout.setSpacing(Spacing.XS)

        title = QLabel("GrayScope")
        title.setProperty("class", "page-title")
        layout.addWidget(title)
        layout.addSpacing(Spacing.LG)

        self._buttons: list[QPushButton] = []
        for index, (glyph, label) in enumerate(items):
            button = QPushButton(f"  {glyph}   {label}")
            button.setProperty("class", "nav-item")
            button.setCheckable(True)
            button.clicked.connect(lambda _checked, i=index: self.set_active(i))
            layout.addWidget(button)
            self._buttons.append(button)

        layout.addStretch()

    def set_active(self, index: int) -> None:
        for i, button in enumerate(self._buttons):
            is_active = i == index
            button.setChecked(is_active)
            button.setProperty("active", "true" if is_active else "false")
            refresh_style(button)
        self.navigation_changed.emit(index)
