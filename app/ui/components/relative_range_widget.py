"""Compact «N <birim>» widget for editing a relative time range.

Converts between a human «5 dakika», «2 saat» choice and the raw seconds value
stored on the Query model.  Exposed API is intentionally minimal:

    widget.seconds()        → int   (current value in seconds)
    widget.set_seconds(n)   → None  (round-trip from stored seconds)
    widget.changed          → Signal()
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QSpinBox, QWidget

from app.ui.theme import Spacing

_UNITS: list[tuple[str, int]] = [
    ("dakika", 60),
    ("saat", 3_600),
    ("gün", 86_400),
    ("hafta", 604_800),
    ("ay", 2_592_000),
    ("yıl", 31_536_000),
]

_UNIT_LABELS = [u for u, _ in _UNITS]
_UNIT_SECONDS = [s for _, s in _UNITS]


def _best_unit(seconds: int) -> tuple[int, int]:
    """Return (amount, unit_index) that most cleanly represents *seconds*."""
    best_idx = 0
    for i, multiplier in enumerate(_UNIT_SECONDS):
        if seconds % multiplier == 0:
            best_idx = i
    amount = seconds // _UNIT_SECONDS[best_idx]
    return max(1, amount), best_idx


class RelativeRangeWidget(QWidget):
    changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.SM)

        self._spin = QSpinBox()
        self._spin.setRange(1, 9_999)
        self._spin.setValue(1)
        self._spin.setFixedWidth(72)

        self._unit = QComboBox()
        self._unit.addItems(_UNIT_LABELS)
        self._unit.setCurrentIndex(1)  # default: saat

        layout.addWidget(self._spin)
        layout.addWidget(self._unit)
        layout.addStretch()

        self._spin.valueChanged.connect(self.changed)
        self._unit.currentIndexChanged.connect(self.changed)

    def seconds(self) -> int:
        return self._spin.value() * _UNIT_SECONDS[self._unit.currentIndex()]

    def set_seconds(self, value: int) -> None:
        amount, unit_idx = _best_unit(max(1, value))
        self._spin.blockSignals(True)
        self._unit.blockSignals(True)
        self._spin.setValue(amount)
        self._unit.setCurrentIndex(unit_idx)
        self._spin.blockSignals(False)
        self._unit.blockSignals(False)

    def display_text(self) -> str:
        """Short human-readable label, e.g. «Son 5 dakika»."""
        return f"Son {self._spin.value()} {_UNIT_LABELS[self._unit.currentIndex()]}"
