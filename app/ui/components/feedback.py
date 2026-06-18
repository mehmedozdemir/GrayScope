"""Feedback components: Badge, EmptyState, and Toast notifications."""
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.ui.theme import Spacing

_TONE_ICONS = {"success": "✓", "error": "✕", "warning": "⚠", "info": "ℹ"}


def badge(text: str, tone: str = "muted") -> QLabel:
    """A small pill label. ``tone`` ∈ {muted, accent, success}."""
    label = QLabel(text)
    label.setProperty("class", "badge")
    label.setProperty("tone", tone)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return label


class EmptyState(QWidget):
    """Designed empty state: icon + title + subtitle, centered."""

    def __init__(self, icon: str, title: str, subtitle: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(Spacing.SM)

        icon_label = QLabel(icon)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("font-size: 48px;")

        title_label = QLabel(title)
        title_label.setProperty("class", "empty-state-title")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(icon_label)
        layout.addWidget(title_label)

        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setProperty("class", "empty-state-subtitle")
            subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            subtitle_label.setWordWrap(True)
            layout.addWidget(subtitle_label)


class Toast(QFrame):
    """Non-blocking notification, bottom-right, auto-dismiss after 4s with fade."""

    _MARGIN = 24
    _DURATION_MS = 4000

    def __init__(self, parent: QWidget, message: str, tone: str = "info") -> None:
        super().__init__(parent)
        self.setProperty("class", "toast")
        self.setProperty("tone", tone)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(Spacing.MD, Spacing.SM, Spacing.MD, Spacing.SM)
        layout.setSpacing(Spacing.SM)

        icon = QLabel(_TONE_ICONS.get(tone, _TONE_ICONS["info"]))
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setMaximumWidth(320)
        layout.addWidget(icon)
        layout.addWidget(message_label)

        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)
        self._effect.setOpacity(0.0)

    def show_animated(self) -> None:
        self.adjustSize()
        self._reposition()
        self.show()
        self.raise_()

        self._fade_in = QPropertyAnimation(self._effect, b"opacity", self)
        self._fade_in.setDuration(150)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.start()

        QTimer.singleShot(self._DURATION_MS, self._fade_out)

    def _reposition(self) -> None:
        parent = self.parentWidget()
        if not parent:
            return
        x = parent.width() - self.width() - self._MARGIN
        y = parent.height() - self.height() - self._MARGIN
        self.move(max(x, self._MARGIN), max(y, self._MARGIN))

    def _fade_out(self) -> None:
        self._fade = QPropertyAnimation(self._effect, b"opacity", self)
        self._fade.setDuration(200)
        self._fade.setStartValue(1.0)
        self._fade.setEndValue(0.0)
        self._fade.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._fade.finished.connect(self.deleteLater)
        self._fade.start()


def show_toast(parent: QWidget, message: str, tone: str = "info") -> Toast:
    """Create and display a toast over the given (usually top-level) widget."""
    window = parent.window()
    toast = Toast(window, message, tone)
    toast.show_animated()
    return toast
