"""Global QSS built from design tokens.

Applied once via ``apply_theme(app)``. Widget files never contain QSS strings
(pyside6-ui-ux skill rule). Variants are selected with the ``variant`` / ``class``
dynamic properties.
"""
from __future__ import annotations

from app.ui.theme import Colors as C
from app.ui.theme import Radius as R
from app.ui.theme import Spacing as S
from app.ui.theme import Typography as T


def get_global_stylesheet() -> str:
    return f"""
/* ── Base ──────────────────────────────────────────────────────────────── */
QWidget {{
    background-color: {C.BG_BASE};
    color: {C.TEXT_PRIMARY};
    font-family: '{T.FONT_FAMILY}', 'Segoe UI', sans-serif;
    font-size: {T.SIZE_MD}px;
    selection-background-color: {C.ACCENT_MUTED};
    selection-color: {C.TEXT_PRIMARY};
    border: none;
    outline: none;
}}
QMainWindow, QDialog {{ background-color: {C.BG_BASE}; }}

/* ── Typography helpers ────────────────────────────────────────────────── */
QLabel[class="page-title"] {{
    font-size: {T.SIZE_2XL}px; font-weight: {T.WEIGHT_BOLD}; color: {C.TEXT_PRIMARY};
}}
QLabel[class="section-header"] {{
    font-size: {T.SIZE_SM}px; font-weight: {T.WEIGHT_SEMIBOLD};
    color: {C.TEXT_SECONDARY}; letter-spacing: 0.8px;
}}
QLabel[class="field-label"] {{
    font-size: {T.SIZE_SM}px; font-weight: {T.WEIGHT_MEDIUM}; color: {C.TEXT_SECONDARY};
}}
QLabel[class="caption"] {{ font-size: {T.SIZE_SM}px; color: {C.TEXT_SECONDARY}; }}
QLabel[class="query-name"] {{
    font-size: {T.SIZE_MD}px; font-weight: {T.WEIGHT_MEDIUM}; color: {C.TEXT_PRIMARY};
}}
QLabel[class="hint"] {{ font-size: {T.SIZE_SM}px; color: {C.TEXT_SECONDARY}; }}
QLabel[class="empty-state-title"] {{
    font-size: {T.SIZE_LG}px; font-weight: {T.WEIGHT_SEMIBOLD}; color: {C.TEXT_SECONDARY};
}}
QLabel[class="empty-state-subtitle"] {{
    font-size: {T.SIZE_MD}px; color: {C.TEXT_DISABLED};
}}
QLabel[class="error-text"] {{ font-size: {T.SIZE_SM}px; color: {C.ERROR}; }}

/* ── Buttons ───────────────────────────────────────────────────────────── */
QPushButton {{
    font-size: {T.SIZE_SM}px; font-weight: {T.WEIGHT_MEDIUM};
    border: none; border-radius: {R.MD}px;
    padding: {S.XS}px {S.MD}px; min-height: 28px;
}}
QPushButton[variant="primary"] {{ background-color: {C.ACCENT}; color: white; }}
QPushButton[variant="primary"]:hover {{ background-color: {C.ACCENT_HOVER}; }}
QPushButton[variant="primary"]:pressed {{ background-color: {C.ACCENT_PRESSED}; }}
QPushButton[variant="primary"]:disabled {{
    background-color: {C.BG_ELEVATED}; color: {C.TEXT_DISABLED};
}}

QPushButton[variant="secondary"] {{
    background-color: transparent; color: {C.TEXT_PRIMARY}; border: 1px solid {C.BORDER};
}}
QPushButton[variant="secondary"]:hover {{
    background-color: {C.BG_ELEVATED}; border-color: {C.BORDER_STRONG};
}}
QPushButton[variant="secondary"]:pressed {{ background-color: {C.BG_OVERLAY}; }}
QPushButton[variant="secondary"]:disabled {{
    color: {C.TEXT_DISABLED}; border-color: {C.BORDER};
}}

QPushButton[variant="ghost"] {{ background-color: transparent; color: {C.TEXT_SECONDARY}; }}
QPushButton[variant="ghost"]:hover {{ background-color: {C.BG_ELEVATED}; color: {C.TEXT_PRIMARY}; }}
QPushButton[variant="ghost"]:pressed {{ background-color: {C.BG_OVERLAY}; }}

QPushButton[variant="danger"] {{ background-color: {C.ERROR}; color: white; }}
QPushButton[variant="danger"]:hover {{ background-color: #E86878; }}
QPushButton[variant="danger"]:pressed {{ background-color: #C04458; }}

QPushButton[variant="icon"] {{
    background-color: transparent; border-radius: {R.MD}px; padding: {S.XS}px;
    min-width: 30px; max-width: 30px; min-height: 30px; max-height: 30px;
    color: {C.TEXT_SECONDARY}; font-size: {T.SIZE_MD}px;
}}
QPushButton[variant="icon"]:hover {{ background-color: {C.BG_ELEVATED}; color: {C.TEXT_PRIMARY}; }}
QPushButton[variant="icon"]:pressed {{ background-color: {C.BG_OVERLAY}; }}
QPushButton[variant="icon"]:disabled {{ color: {C.TEXT_DISABLED}; }}

/* ── Inputs ────────────────────────────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox {{
    background-color: {C.BG_ELEVATED}; color: {C.TEXT_PRIMARY};
    border: 1px solid {C.BORDER}; border-radius: {R.MD}px;
    padding: {S.XS}px {S.SM}px; min-height: 28px;
    selection-background-color: {C.ACCENT_MUTED};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus {{
    border-color: {C.BORDER_FOCUS};
}}
QLineEdit:disabled, QTextEdit:disabled, QSpinBox:disabled {{
    background-color: {C.BG_SURFACE}; color: {C.TEXT_DISABLED};
}}
QLineEdit[state="error"] {{ border-color: {C.ERROR}; }}
QPlainTextEdit[mono="true"] {{ font-family: '{T.FONT_MONO}', 'Consolas', monospace; }}

/* ── ComboBox ──────────────────────────────────────────────────────────── */
QComboBox {{
    background-color: {C.BG_ELEVATED}; color: {C.TEXT_PRIMARY};
    border: 1px solid {C.BORDER}; border-radius: {R.MD}px;
    padding: {S.XS}px {S.SM}px; min-height: 28px;
}}
QComboBox:focus {{ border-color: {C.BORDER_FOCUS}; }}
QComboBox:hover {{ border-color: {C.BORDER_STRONG}; }}
QComboBox::drop-down {{ border: none; width: 28px; }}
QComboBox QAbstractItemView {{
    background-color: {C.BG_OVERLAY}; color: {C.TEXT_PRIMARY};
    border: 1px solid {C.BORDER}; border-radius: {R.MD}px; padding: {S.XS}px;
    selection-background-color: {C.ACCENT_MUTED}; selection-color: {C.TEXT_PRIMARY};
    outline: none;
}}
QComboBox QAbstractItemView::item {{ min-height: 28px; padding: 0 {S.SM}px; }}

/* ── Tables ────────────────────────────────────────────────────────────── */
QTableView {{
    background-color: {C.BG_SURFACE}; alternate-background-color: {C.BG_BASE};
    gridline-color: {C.BORDER}; border: 1px solid {C.BORDER}; border-radius: {R.LG}px;
    selection-background-color: {C.ACCENT_MUTED}; selection-color: {C.TEXT_PRIMARY};
    outline: none;
}}
QTableView::item {{ padding: {S.SM}px {S.MD}px; border: none; }}
QTableView::item:hover {{ background-color: {C.BG_ELEVATED}; }}
QTableView::item:selected {{ background-color: {C.ACCENT_MUTED}; color: {C.TEXT_PRIMARY}; }}
QHeaderView {{ background-color: transparent; }}
QHeaderView::section {{
    background-color: {C.BG_SURFACE}; color: {C.TEXT_SECONDARY};
    font-size: {T.SIZE_SM}px; font-weight: {T.WEIGHT_SEMIBOLD}; letter-spacing: 0.5px;
    padding: {S.SM}px {S.MD}px; border: none; border-bottom: 1px solid {C.BORDER};
}}
QHeaderView::section:hover {{ background-color: {C.BG_ELEVATED}; color: {C.TEXT_PRIMARY}; }}
QTableCornerButton::section {{ background-color: {C.BG_SURFACE}; border: none; }}

/* ── Frames / cards / sidebar ──────────────────────────────────────────── */
QFrame[class="card"] {{
    background-color: {C.BG_SURFACE}; border: 1px solid {C.BORDER}; border-radius: {R.LG}px;
}}
QFrame[class="sidebar"] {{
    background-color: {C.BG_SURFACE}; border-right: 1px solid {C.BORDER}; border-radius: 0;
}}
QFrame[class="separator"] {{ background-color: {C.BORDER}; max-height: 1px; border: none; }}

/* ── Sidebar nav items ─────────────────────────────────────────────────── */
QPushButton[class="nav-item"] {{
    background-color: transparent; color: {C.TEXT_SECONDARY}; text-align: left;
    padding: 0 {S.MD}px; border-radius: {R.MD}px;
    font-size: {T.SIZE_MD}px; font-weight: {T.WEIGHT_MEDIUM};
    min-height: 38px; border-left: 3px solid transparent;
}}
QPushButton[class="nav-item"]:hover {{ background-color: {C.BG_ELEVATED}; color: {C.TEXT_PRIMARY}; }}
QPushButton[class="nav-item"][active="true"] {{
    background-color: {C.ACCENT_MUTED}; color: {C.ACCENT};
    font-weight: {T.WEIGHT_SEMIBOLD}; border-left: 3px solid {C.ACCENT};
}}

/* ── Badges ────────────────────────────────────────────────────────────── */
QLabel[class="badge"] {{
    background-color: {C.BG_ELEVATED}; color: {C.TEXT_SECONDARY};
    font-size: {T.SIZE_XS}px; font-weight: {T.WEIGHT_MEDIUM};
    padding: 2px {S.SM}px; border-radius: {R.FULL}px;
}}
QLabel[class="badge"][tone="accent"] {{ background-color: {C.ACCENT_MUTED}; color: {C.ACCENT}; }}
QLabel[class="badge"][tone="success"] {{ background-color: {C.SUCCESS_MUTED}; color: {C.SUCCESS}; }}
QLabel[class="badge"][tone="muted"] {{ background-color: {C.BG_ELEVATED}; color: {C.TEXT_DISABLED}; }}

/* ── Chip (tag input) ──────────────────────────────────────────────────── */
QFrame[class="chip"] {{
    background-color: {C.ACCENT_MUTED}; border-radius: {R.FULL}px;
}}
QFrame[class="chip"] QLabel {{ color: {C.ACCENT}; font-size: {T.SIZE_SM}px; background: transparent; }}
QFrame[class="chip"] QPushButton {{ color: {C.ACCENT}; font-size: {T.SIZE_XS}px; }}
QFrame[class="chip"] QPushButton:hover {{ color: {C.TEXT_PRIMARY}; }}

/* ── Toast ─────────────────────────────────────────────────────────────── */
QFrame[class="toast"] {{
    background-color: {C.BG_OVERLAY}; border: 1px solid {C.BORDER_STRONG};
    border-radius: {R.MD}px;
}}
QFrame[class="toast"][tone="success"] {{ border-left: 4px solid {C.SUCCESS}; }}
QFrame[class="toast"][tone="error"] {{ border-left: 4px solid {C.ERROR}; }}
QFrame[class="toast"][tone="warning"] {{ border-left: 4px solid {C.WARNING}; }}
QFrame[class="toast"][tone="info"] {{ border-left: 4px solid {C.INFO}; }}

/* ── CheckBox & RadioButton ────────────────────────────────────────────── */
QCheckBox, QRadioButton {{ color: {C.TEXT_PRIMARY}; spacing: {S.SM}px; }}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 18px; height: 18px; border: 1.5px solid {C.BORDER_STRONG};
    border-radius: {R.SM}px; background-color: {C.BG_ELEVATED};
}}
QCheckBox::indicator:checked {{ background-color: {C.ACCENT}; border-color: {C.ACCENT}; }}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{ border-color: {C.ACCENT}; }}
QRadioButton::indicator {{ border-radius: 9px; }}
QRadioButton::indicator:checked {{ background-color: {C.ACCENT}; border-color: {C.ACCENT}; }}

/* ── Tabs ──────────────────────────────────────────────────────────────── */
QTabWidget::pane {{
    background-color: {C.BG_SURFACE}; border: 1px solid {C.BORDER};
    border-radius: {R.LG}px; border-top-left-radius: 0;
}}
QTabBar::tab {{
    background-color: transparent; color: {C.TEXT_SECONDARY};
    padding: {S.SM}px {S.LG}px; border: none; border-bottom: 2px solid transparent;
}}
QTabBar::tab:hover {{ color: {C.TEXT_PRIMARY}; }}
QTabBar::tab:selected {{
    color: {C.ACCENT}; border-bottom: 2px solid {C.ACCENT}; font-weight: {T.WEIGHT_SEMIBOLD};
}}

/* ── Scrollbars ────────────────────────────────────────────────────────── */
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {C.BORDER_STRONG}; border-radius: 4px; min-height: 32px; }}
QScrollBar::handle:vertical:hover {{ background: {C.TEXT_SECONDARY}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; background: transparent; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QScrollBar:horizontal {{ background: transparent; height: 8px; margin: 0; }}
QScrollBar::handle:horizontal {{ background: {C.BORDER_STRONG}; border-radius: 4px; min-width: 32px; }}
QScrollBar::handle:horizontal:hover {{ background: {C.TEXT_SECONDARY}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; background: transparent; }}

/* ── Splitter ──────────────────────────────────────────────────────────── */
QSplitter::handle {{ background-color: {C.BORDER}; }}
QSplitter::handle:horizontal {{ width: 1px; }}
QSplitter::handle:hover {{ background-color: {C.ACCENT}; }}

/* ── Tooltip ───────────────────────────────────────────────────────────── */
QToolTip {{
    background-color: {C.BG_OVERLAY}; color: {C.TEXT_PRIMARY};
    border: 1px solid {C.BORDER_STRONG}; border-radius: {R.SM}px;
    padding: {S.XS}px {S.SM}px; font-size: {T.SIZE_SM}px;
}}
"""


def apply_theme(app) -> None:
    """Apply the global stylesheet and default font. Call once after QApplication()."""
    from app.ui.theme import Typography as Typo

    app.setStyleSheet(get_global_stylesheet())
    font = make_font_default(Typo)
    app.setFont(font)


def make_font_default(typo):
    from PySide6.QtGui import QFont, QFontDatabase

    # Use JetBrains Mono if installed; otherwise keep the system default family.
    if typo.FONT_FAMILY in QFontDatabase.families():
        font = QFont(typo.FONT_FAMILY)
    else:
        font = QFont()
    font.setPixelSize(typo.SIZE_MD)
    return font
