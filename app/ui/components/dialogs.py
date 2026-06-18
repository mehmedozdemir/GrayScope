"""Reusable dialogs."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.ui.components.buttons import danger_button, primary_button, secondary_button
from app.ui.theme import Spacing


class ConfirmDialog(QDialog):
    """Modal confirmation for destructive or important actions."""

    def __init__(
        self,
        title: str,
        message: str,
        confirm_text: str = "Onayla",
        danger: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.LG)

        heading = QLabel(title)
        heading.setProperty("class", "page-title")
        body = QLabel(message)
        body.setWordWrap(True)
        body.setProperty("class", "caption")
        layout.addWidget(heading)
        layout.addWidget(body)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = secondary_button("Vazgeç")
        confirm = danger_button(confirm_text) if danger else primary_button(confirm_text)
        cancel.clicked.connect(self.reject)
        confirm.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(confirm)
        layout.addLayout(buttons)

    @staticmethod
    def confirm(
        parent: QWidget,
        title: str,
        message: str,
        confirm_text: str = "Onayla",
        danger: bool = False,
    ) -> bool:
        dialog = ConfirmDialog(title, message, confirm_text, danger, parent)
        return dialog.exec() == QDialog.DialogCode.Accepted
