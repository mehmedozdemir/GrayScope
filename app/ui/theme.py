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
    "BG_BASE": "#E8ECF5",
    "BG_SURFACE": "#F0F3FA",
    "BG_ELEVATED": "#E0E6F0",
    "BG_OVERLAY": "#F0F3FA",
    "ACCENT": "#2B5ED4",
    "ACCENT_HOVER": "#1F4FC0",
    "ACCENT_PRESSED": "#1640A8",
    "ACCENT_MUTED": "#CCDAFF",
    "TEXT_PRIMARY": "#0D1117",
    "TEXT_SECONDARY": "#363B55",
    "TEXT_DISABLED": "#8890AA",
    "BORDER": "#B8C2D8",
    "BORDER_STRONG": "#9AA8C4",
    "BORDER_FOCUS": "#2B5ED4",
    "SUCCESS": "#1E8A4E",
    "SUCCESS_MUTED": "#C4EDD8",
    "WARNING": "#A86200",
    "WARNING_MUTED": "#F5DFB0",
    "ERROR": "#B02838",
    "ERROR_MUTED": "#F2C8CC",
    "INFO": "#2B5ED4",
    "INFO_MUTED": "#CCDAFF",
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
    SIZE_SM = 11
    SIZE_MD = 13
    SIZE_LG = 14
    SIZE_XL = 17
    SIZE_2XL = 22
    SIZE_3XL = 30

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
