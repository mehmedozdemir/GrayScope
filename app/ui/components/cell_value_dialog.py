"""Cell value viewer — opens a window showing a grid cell's value, optionally
pretty-formatted (JSON / XML / YAML / Markdown), with a copy button."""
from __future__ import annotations

import json
import xml.dom.minidom as minidom

from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.ui.components.buttons import primary_button, secondary_button
from app.ui.components.feedback import show_toast
from app.ui.components.inputs import labeled_field
from app.ui.theme import Spacing, Typography, make_font

# Format options shown in the combo (label → internal key).
_FORMATS = ["Otomatik", "JSON", "XML", "YAML", "Markdown", "Düz metin"]


def format_json(text: str) -> str | None:
    try:
        return json.dumps(json.loads(text), indent=2, ensure_ascii=False)
    except (ValueError, TypeError):
        return None


def format_xml(text: str) -> str | None:
    try:
        pretty = minidom.parseString(text.strip()).toprettyxml(indent="  ")
    except Exception:  # noqa: BLE001 — any parse error means "not XML"
        return None
    # minidom inserts blank lines; drop them.
    return "\n".join(line for line in pretty.splitlines() if line.strip())


def format_yaml(text: str) -> str | None:
    try:
        import yaml
    except ImportError:
        return None
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        return None
    if not isinstance(data, (dict, list)):
        return None  # scalars/plain strings aren't worth reformatting
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False).rstrip()


def auto_format(text: str) -> tuple[str, str]:
    """Best-effort detection for unambiguous formats. Returns (kind, formatted_text)."""
    stripped = text.strip()
    if stripped[:1] in "{[":
        formatted = format_json(text)
        if formatted is not None:
            return "JSON", formatted
    if stripped.startswith("<"):
        formatted = format_xml(text)
        if formatted is not None:
            return "XML", formatted
    return "Düz metin", text


class CellValueDialog(QDialog):
    def __init__(self, field_name: str, value: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._value = value
        self.setWindowTitle(f"{field_name or 'Değer'}")
        self.setMinimumSize(560, 460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        layout.setSpacing(Spacing.SM)

        self._format_combo = QComboBox()
        self._format_combo.addItems(_FORMATS)
        layout.addWidget(labeled_field("Biçim", self._format_combo))

        self._editor = QTextEdit()
        self._editor.setReadOnly(True)
        self._editor.setFont(make_font(Typography.SIZE_SM, family=Typography.FONT_MONO))
        layout.addWidget(self._editor, 1)

        footer = QHBoxLayout()
        footer.addStretch()
        copy_button = primary_button("Kopyala")
        close_button = secondary_button("Kapat")
        footer.addWidget(close_button)
        footer.addWidget(copy_button)
        layout.addLayout(footer)

        self._format_combo.currentTextChanged.connect(self._render)
        copy_button.clicked.connect(self._copy)
        close_button.clicked.connect(self.close)

        self._render("Otomatik")

    def _render(self, fmt: str) -> None:
        if fmt == "Otomatik":
            _, text = auto_format(self._value)
            self._set_plain(text)
            return
        if fmt == "Markdown":
            self._editor.setMarkdown(self._value)
            return
        formatter = {"JSON": format_json, "XML": format_xml, "YAML": format_yaml}.get(fmt)
        if formatter is not None:
            formatted = formatter(self._value)
            self._set_plain(formatted if formatted is not None else self._value)
        else:
            self._set_plain(self._value)

    def _set_plain(self, text: str) -> None:
        self._editor.setFont(make_font(Typography.SIZE_SM, family=Typography.FONT_MONO))
        self._editor.setPlainText(text)

    def _copy(self) -> None:
        QApplication.clipboard().setText(self._editor.toPlainText())
        show_toast(self, "Panoya kopyalandı.", "success")
