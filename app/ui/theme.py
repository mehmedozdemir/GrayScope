"""Design tokens — single source of truth for colors, spacing, typography, radii.

Import these everywhere; never hardcode values in widget files (CLAUDE.md §8,
pyside6-ui-ux skill). GrayScope ships dark + light themes; the active palette is
swapped at runtime via :func:`set_theme`, which reassigns the ``Colors`` attributes
in place so all importers (QSS + code) see the change.
"""
from __future__ import annotations

_DARK = {
    "BG_BASE": "#0F1117",
    "BG_SURFACE": "#1A1D27",
    "BG_ELEVATED": "#22263A",
    "BG_OVERLAY": "#2A2F47",
    "ACCENT": "#5B8AF0",
    "ACCENT_HOVER": "#7BA3FF",
    "ACCENT_PRESSED": "#4A76D8",
    "ACCENT_MUTED": "#1E2D5A",
    "TEXT_PRIMARY": "#F0F2FF",
    "TEXT_SECONDARY": "#8B90A8",
    "TEXT_DISABLED": "#4A4F6A",
    "BORDER": "#2E3248",
    "BORDER_STRONG": "#3D4260",
    "BORDER_FOCUS": "#5B8AF0",
    "SUCCESS": "#4CAF80",
    "SUCCESS_MUTED": "#1A3D2B",
    "WARNING": "#F0A84A",
    "WARNING_MUTED": "#3D2D10",
    "ERROR": "#E05C6A",
    "ERROR_MUTED": "#3D1520",
    "INFO": "#5B8AF0",
    "INFO_MUTED": "#1E2D5A",
}

_LIGHT = {
    "BG_BASE": "#F4F6FB",
    "BG_SURFACE": "#FFFFFF",
    "BG_ELEVATED": "#EDF1F9",
    "BG_OVERLAY": "#FFFFFF",
    "ACCENT": "#3B6FE8",
    "ACCENT_HOVER": "#2A5ED4",
    "ACCENT_PRESSED": "#1F4FC0",
    "ACCENT_MUTED": "#DCE8FF",
    "TEXT_PRIMARY": "#161A24",
    "TEXT_SECONDARY": "#5A6080",
    "TEXT_DISABLED": "#A0A8C0",
    "BORDER": "#DCE1EE",
    "BORDER_STRONG": "#C2CADD",
    "BORDER_FOCUS": "#3B6FE8",
    "SUCCESS": "#2D9B5F",
    "SUCCESS_MUTED": "#D7F0E2",
    "WARNING": "#C47A10",
    "WARNING_MUTED": "#FBEFD6",
    "ERROR": "#C4374A",
    "ERROR_MUTED": "#F7DBDF",
    "INFO": "#3B6FE8",
    "INFO_MUTED": "#DCE8FF",
}

_PALETTES = {"dark": _DARK, "light": _LIGHT}
DEFAULT_THEME = "dark"


class Colors:
    """Active palette. Attributes are (re)assigned by :func:`set_theme`."""


_mode = DEFAULT_THEME


def set_theme(mode: str) -> None:
    """Switch the active palette ('dark' or 'light'), updating ``Colors`` in place."""
    global _mode
    _mode = mode if mode in _PALETTES else DEFAULT_THEME
    for key, value in _PALETTES[_mode].items():
        setattr(Colors, key, value)


def current_theme() -> str:
    return _mode


# Initialize at import so Colors has values before any widget is built.
set_theme(DEFAULT_THEME)


class Spacing:
    """4px grid. All padding/margin must use these constants."""

    XS = 4
    SM = 8
    MD = 16
    LG = 24
    XL = 32
    XXL = 48


class Typography:
    FONT_FAMILY = "Inter"  # Falls back to Segoe UI on Windows.
    FONT_MONO = "Consolas"  # Query text / monospace contexts (DESIGN_SYSTEM.md §4).

    SIZE_XS = 10
    SIZE_SM = 12
    SIZE_MD = 14
    SIZE_LG = 16
    SIZE_XL = 20
    SIZE_2XL = 28
    SIZE_3XL = 36

    WEIGHT_REGULAR = 400
    WEIGHT_MEDIUM = 500
    WEIGHT_SEMIBOLD = 600
    WEIGHT_BOLD = 700


class Radius:
    SM = 4
    MD = 8
    LG = 12
    XL = 16
    FULL = 9999


class Sidebar:
    WIDTH = 240
    ITEM_HEIGHT = 44


def make_font(size: int, weight: int = Typography.WEIGHT_REGULAR,
              family: str = Typography.FONT_FAMILY):
    """Return a configured QFont (uses pixel sizing to match the token scale)."""
    from PySide6.QtGui import QFont

    font = QFont(family)
    font.setPixelSize(size)
    font.setWeight(QFont.Weight(weight))
    return font
