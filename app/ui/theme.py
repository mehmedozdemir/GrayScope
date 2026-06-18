"""Design tokens — single source of truth for colors, spacing, typography, radii.

Import these everywhere; never hardcode values in widget files (CLAUDE.md §8,
pyside6-ui-ux skill). GrayScope ships dark theme only in Faz 1 (DESIGN_SYSTEM.md §1).
"""
from __future__ import annotations


class Colors:
    # Backgrounds
    BG_BASE = "#0F1117"
    BG_SURFACE = "#1A1D27"
    BG_ELEVATED = "#22263A"
    BG_OVERLAY = "#2A2F47"

    # Brand / accent
    ACCENT = "#5B8AF0"
    ACCENT_HOVER = "#7BA3FF"
    ACCENT_PRESSED = "#4A76D8"
    ACCENT_MUTED = "#1E2D5A"

    # Text
    TEXT_PRIMARY = "#F0F2FF"
    TEXT_SECONDARY = "#8B90A8"
    TEXT_DISABLED = "#4A4F6A"

    # Borders
    BORDER = "#2E3248"
    BORDER_STRONG = "#3D4260"
    BORDER_FOCUS = "#5B8AF0"

    # Semantic
    SUCCESS = "#4CAF80"
    SUCCESS_MUTED = "#1A3D2B"
    WARNING = "#F0A84A"
    WARNING_MUTED = "#3D2D10"
    ERROR = "#E05C6A"
    ERROR_MUTED = "#3D1520"
    INFO = "#5B8AF0"
    INFO_MUTED = "#1E2D5A"


class Spacing:
    """4px grid. All padding/margin must use these constants."""

    XS = 4
    SM = 8
    MD = 16
    LG = 24
    XL = 32
    XXL = 48


class Typography:
    FONT_FAMILY = "JetBrains Mono"  # Whole-UI font; falls back to system default if absent.
    FONT_MONO = "JetBrains Mono"  # Query text / monospace contexts (DESIGN_SYSTEM.md §4).

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
    font.setWeight(weight)
    return font
