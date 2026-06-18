"""Müşteriler (city / plate-code) page — CRUD over the Customer table
(DESIGN_SYSTEM.md §6, PROJECT_PLAN.md §5.3)."""
from __future__ import annotations

import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.exceptions import DuplicateRecordError
from app.data.models.customer import Customer
from app.data.repositories.customer_repository import CustomerRepository
from app.ui.components.buttons import icon_button, primary_button, secondary_button
from app.ui.components.dialogs import ConfirmDialog
from app.ui.components.feedback import badge, show_toast
from app.ui.components.inputs import SearchInput, labeled_field
from app.ui.components.tables import TablePanel
from app.ui.theme import Colors, Spacing

_HEADERS = ["Plaka Kodu", "Şehir", "Aktif", "Açıklama", ""]


class _NumericItem(QTableWidgetItem):
    """Table item that sorts by a numeric value rather than its display text."""

    def __init__(self, value: int) -> None:
        super().__init__(str(value))
        self._value = value
        self.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

    def __lt__(self, other: "QTableWidgetItem") -> bool:
        if isinstance(other, _NumericItem):
            return self._value < other._value
        return super().__lt__(other)


class CustomerFormDialog(QDialog):
    """Add / edit a single customer."""

    def __init__(self, parent: QWidget, customer: Customer | None = None) -> None:
        super().__init__(parent)
        self._customer = customer
        self.setWindowTitle("Müşteri Düzenle" if customer else "Yeni Müşteri")
        self.setModal(True)
        self.setMinimumWidth(440)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)

        self._network_id = QSpinBox()
        self._network_id.setRange(1, 9999)
        self._name = QLineEdit()
        self._name.setPlaceholderText("Şehir / müşteri adı")
        self._description = QLineEdit()
        self._description.setPlaceholderText("Opsiyonel not")
        self._is_active = QCheckBox("Aktif")
        self._is_active.setChecked(True)

        if customer:
            self._network_id.setValue(customer.NetworkId)
            self._name.setText(customer.Name)
            self._description.setText(customer.Description or "")
            self._is_active.setChecked(customer.IsActive)

        layout.addWidget(labeled_field("Plaka Kodu (NetworkId)", self._network_id, required=True))
        layout.addWidget(labeled_field("Şehir / Ad", self._name, required=True))
        layout.addWidget(labeled_field("Açıklama", self._description))
        layout.addWidget(self._is_active)

        self._error = QLabel()
        self._error.setProperty("class", "error-text")
        self._error.setVisible(False)
        layout.addWidget(self._error)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = secondary_button("Vazgeç")
        save = primary_button("Kaydet")
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self._on_save)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)

    def _on_save(self) -> None:
        if not self._name.text().strip():
            self._show_error("Şehir / Ad boş olamaz.")
            return
        self.accept()

    def _show_error(self, message: str) -> None:
        self._error.setText(message)
        self._error.setVisible(True)

    def result_customer(self) -> Customer:
        return Customer(
            Id=self._customer.Id if self._customer else None,
            NetworkId=self._network_id.value(),
            Name=self._name.text().strip(),
            IsActive=self._is_active.isChecked(),
            Description=self._description.text().strip() or None,
        )


class CustomersPage(QWidget):
    def __init__(self, conn: sqlite3.Connection) -> None:
        super().__init__()
        self._repo = CustomerRepository(conn)
        self._customers: list[Customer] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.XL, Spacing.XL, Spacing.XL, Spacing.XL)
        layout.setSpacing(Spacing.LG)

        layout.addWidget(self._build_header())
        self._panel = TablePanel(
            _HEADERS,
            "\U0001F4ED",
            "Aramanızla eşleşen kayıt yok",
            "Farklı bir plaka kodu veya şehir adı deneyin.",
        )
        layout.addWidget(self._panel, 1)

        self._connect_signals()
        self.load_data()

    def _build_header(self) -> QWidget:
        header = QWidget()
        row = QHBoxLayout(header)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(Spacing.MD)

        title = QLabel("Müşteriler")
        title.setProperty("class", "page-title")
        self._search = SearchInput("Plaka kodu veya şehir ara")
        self._search.setFixedWidth(280)
        self._add_button = primary_button("+ Yeni Kayıt")

        row.addWidget(title)
        row.addStretch()
        row.addWidget(self._search)
        row.addWidget(self._add_button)
        return header

    def _connect_signals(self) -> None:
        self._search.textChanged.connect(self._render)
        self._add_button.clicked.connect(self._on_add)

    def load_data(self) -> None:
        self._customers = self._repo.get_all()
        self._render()

    def _filtered(self) -> list[Customer]:
        term = self._search.text().strip().lower()
        if not term:
            return self._customers
        return [
            c
            for c in self._customers
            if term in c.Name.lower() or term in str(c.NetworkId)
        ]

    def _render(self) -> None:
        rows = self._filtered()
        self._panel.set_empty(not rows)

        table = self._panel.table
        table.setSortingEnabled(False)
        table.setRowCount(len(rows))
        for index, customer in enumerate(rows):
            table.setItem(index, 0, _NumericItem(customer.NetworkId))
            table.setItem(index, 1, QTableWidgetItem(customer.Name))
            table.setCellWidget(index, 2, self._active_cell(customer.IsActive))
            table.setItem(index, 3, QTableWidgetItem(customer.Description or "—"))
            table.setCellWidget(index, 4, self._action_cell(customer))

            if not customer.IsActive:
                for col in (0, 1, 3):
                    item = table.item(index, col)
                    if item:
                        item.setForeground(Qt.GlobalColor.gray)
        table.setSortingEnabled(True)

    def _active_cell(self, is_active: bool) -> QWidget:
        wrapper = QWidget()
        box = QHBoxLayout(wrapper)
        box.setContentsMargins(Spacing.SM, 0, Spacing.SM, 0)
        box.addWidget(
            badge("Aktif", "success") if is_active else badge("Pasif", "muted")
        )
        box.addStretch()
        return wrapper

    def _action_cell(self, customer: Customer) -> QWidget:
        wrapper = QWidget()
        box = QHBoxLayout(wrapper)
        box.setContentsMargins(0, 0, Spacing.SM, 0)
        box.setSpacing(Spacing.XS)
        box.addStretch()

        edit = icon_button("✎", "Düzenle")
        delete = icon_button("🗑", "Sil")
        edit.clicked.connect(lambda: self._on_edit(customer))
        delete.clicked.connect(lambda: self._on_delete(customer))
        box.addWidget(edit)
        box.addWidget(delete)
        return wrapper

    def _on_add(self) -> None:
        dialog = CustomerFormDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                self._repo.create(dialog.result_customer())
            except DuplicateRecordError as exc:
                show_toast(self, str(exc), "error")
                return
            show_toast(self, "Müşteri eklendi.", "success")
            self.load_data()

    def _on_edit(self, customer: Customer) -> None:
        dialog = CustomerFormDialog(self, customer)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                self._repo.update(dialog.result_customer())
            except DuplicateRecordError as exc:
                show_toast(self, str(exc), "error")
                return
            show_toast(self, "Müşteri güncellendi.", "success")
            self.load_data()

    def _on_delete(self, customer: Customer) -> None:
        if ConfirmDialog.confirm(
            self,
            "Müşteriyi sil",
            f"'{customer.Name}' kaydını silmek istediğinize emin misiniz?",
            confirm_text="Sil",
            danger=True,
        ):
            self._repo.delete(customer.Id)
            show_toast(self, "Müşteri silindi.", "success")
            self.load_data()
