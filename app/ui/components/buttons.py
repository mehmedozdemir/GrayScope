"""Button factories. Variants are styled via the ``variant`` dynamic property
(see stylesheets.py) — never subclassed for style alone."""
from __future__ import annotations

from PySide6.QtWidgets import QPushButton, QWidget


def refresh_style(widget: QWidget) -> None:
    """Re-evaluate QSS after a dynamic property changes."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def _button(text: str, variant: str) -> QPushButton:
    button = QPushButton(text)
    button.setProperty("variant", variant)
    button.setCursor(button.cursor())
    return button


def primary_button(text: str) -> QPushButton:
    return _button(text, "primary")


def secondary_button(text: str) -> QPushButton:
    return _button(text, "secondary")


def ghost_button(text: str) -> QPushButton:
    return _button(text, "ghost")


def danger_button(text: str) -> QPushButton:
    return _button(text, "danger")


def icon_button(glyph: str, tooltip: str) -> QPushButton:
    """A 36x36 icon-only button. ``glyph`` is a short text/emoji icon.

    Tooltip is mandatory for icon-only controls (accessibility / skill rule).
    """
    button = QPushButton(glyph)
    button.setProperty("variant", "icon")
    button.setToolTip(tooltip)
    button.setAccessibleName(tooltip)
    return button
