"""Graylog Profilleri page — profile CRUD + connection test
(DESIGN_SYSTEM.md §5, PROJECT_PLAN.md §5.2)."""
from __future__ import annotations

import sqlite3

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.encryption import encrypt_token
from app.core.exceptions import DuplicateRecordError, ProfileInUseError
from app.data.models.graylog_profile import GraylogProfile
from app.data.repositories.graylog_profile_repository import GraylogProfileRepository
from app.integrations.graylog.exceptions import GraylogError
from app.services.connection_test_service import test_profile_connection
from app.ui.components.buttons import icon_button, primary_button, secondary_button
from app.ui.components.dialogs import ConfirmDialog
from app.ui.components.feedback import badge, show_toast
from app.ui.components.inputs import labeled_field
from app.ui.components.tables import TablePanel
from app.ui.theme import Spacing

_HEADERS = ["Ad", "Sunucu Adresi", "Varsayılan", "Aktif", ""]


class _ConnectionTestWorker(QThread):
    """Runs a connection test off the UI thread (loading state required by CLAUDE.md §8)."""

    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(self, profile: GraylogProfile, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._profile = profile

    def run(self) -> None:
        try:
            result = test_profile_connection(self._profile)
        except GraylogError as exc:
            self.failed.emit(str(exc))
            return
        except Exception:  # noqa: BLE001 — surface as generic failure, never crash UI
            self.failed.emit("Bağlantı testi sırasında beklenmeyen bir hata oluştu.")
            return
        version = f" (v{result.version})" if result.version else ""
        self.succeeded.emit(f"Bağlantı başarılı{version}.")


class GraylogProfileFormDialog(QDialog):
    """Add / edit a Graylog profile. Token is always masked (DESIGN_SYSTEM.md §5)."""

    def __init__(self, parent: QWidget, profile: GraylogProfile | None = None) -> None:
        super().__init__(parent)
        self._profile = profile
        self.setWindowTitle("Profili Düzenle" if profile else "Yeni Graylog Profili")
        self.setModal(True)
        self.setMinimumWidth(480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)

        self._name = QLineEdit()
        self._name.setPlaceholderText("Örn. Ana Sunucu")
        self._base_url = QLineEdit()
        self._base_url.setPlaceholderText("https://graylog.sirket.com:9000/api")

        self._token = QLineEdit()
        self._token.setEchoMode(QLineEdit.EchoMode.Password)
        self._token.setPlaceholderText(
            "Değiştirmek için yeni token girin" if profile else "Graylog API token'ı"
        )
        self._show_token = icon_button("👁", "Token'ı göster")
        self._show_token.setCheckable(True)
        token_row = QWidget()
        token_layout = QHBoxLayout(token_row)
        token_layout.setContentsMargins(0, 0, 0, 0)
        token_layout.setSpacing(Spacing.XS)
        token_layout.addWidget(self._token, 1)
        token_layout.addWidget(self._show_token)

        self._is_default = QCheckBox("Varsayılan profil")
        self._is_active = QCheckBox("Aktif")
        self._is_active.setChecked(True)

        if profile:
            self._name.setText(profile.Name)
            self._base_url.setText(profile.BaseUrl)
            self._is_default.setChecked(profile.IsDefault)
            self._is_active.setChecked(profile.IsActive)

        layout.addWidget(labeled_field("Ad", self._name, required=True))
        layout.addWidget(labeled_field("Sunucu Adresi (BaseUrl)", self._base_url, required=True))
        layout.addWidget(labeled_field("Token", token_row, required=not profile))
        layout.addWidget(self._is_default)
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

        self._show_token.toggled.connect(self._toggle_token_visibility)

    def _toggle_token_visibility(self, shown: bool) -> None:
        self._token.setEchoMode(
            QLineEdit.EchoMode.Normal if shown else QLineEdit.EchoMode.Password
        )

    def _on_save(self) -> None:
        if not self._name.text().strip():
            self._show_error("Ad boş olamaz.")
            return
        if not self._base_url.text().strip():
            self._show_error("Sunucu adresi boş olamaz.")
            return
        if not self._profile and not self._token.text():
            self._show_error("Yeni profil için token zorunludur.")
            return
        self.accept()

    def _show_error(self, message: str) -> None:
        self._error.setText(message)
        self._error.setVisible(True)

    def result_profile(self) -> GraylogProfile:
        """Build the profile to persist. Token is encrypted here; a blank token on
        edit keeps the existing ciphertext."""
        new_token = self._token.text()
        if new_token:
            token_encrypted = encrypt_token(new_token)
        else:
            token_encrypted = self._profile.TokenEncrypted  # edit, unchanged

        return GraylogProfile(
            Id=self._profile.Id if self._profile else None,
            Name=self._name.text().strip(),
            BaseUrl=self._base_url.text().strip(),
            TokenEncrypted=token_encrypted,
            IsDefault=self._is_default.isChecked(),
            IsActive=self._is_active.isChecked(),
        )


class GraylogProfilesPage(QWidget):
    def __init__(self, conn: sqlite3.Connection) -> None:
        super().__init__()
        self._repo = GraylogProfileRepository(conn)
        self._profiles: list[GraylogProfile] = []
        self._active_worker: _ConnectionTestWorker | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        layout.setSpacing(Spacing.MD)

        layout.addWidget(self._build_header())
        self._panel = TablePanel(
            _HEADERS,
            "\U0001F5A5",
            "Henüz Graylog sunucusu tanımlanmadı",
            "Bir profil ekleyerek sorguları bu sunucuda çalıştırabilirsiniz.",
        )
        layout.addWidget(self._panel, 1)

        self._add_button.clicked.connect(self._on_add)
        self.load_data()

    def _build_header(self) -> QWidget:
        header = QWidget()
        row = QHBoxLayout(header)
        row.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Graylog Profilleri")
        title.setProperty("class", "page-title")
        self._add_button = primary_button("+ Yeni Profil")

        row.addWidget(title)
        row.addStretch()
        row.addWidget(self._add_button)
        return header

    def load_data(self) -> None:
        self._profiles = self._repo.get_all()
        self._render()

    def _render(self) -> None:
        self._panel.set_empty(not self._profiles)

        table = self._panel.table
        table.setSortingEnabled(False)
        table.setRowCount(len(self._profiles))
        for index, profile in enumerate(self._profiles):
            table.setItem(index, 0, QTableWidgetItem(profile.Name))
            table.setItem(index, 1, QTableWidgetItem(profile.BaseUrl))
            table.setCellWidget(
                index, 2, self._badge_cell(badge("Varsayılan", "accent")) if profile.IsDefault else QWidget()
            )
            table.setCellWidget(
                index,
                3,
                self._badge_cell(
                    badge("Aktif", "success") if profile.IsActive else badge("Pasif", "muted")
                ),
            )
            table.setCellWidget(index, 4, self._action_cell(profile))
        table.setSortingEnabled(True)

    def _badge_cell(self, widget: QWidget) -> QWidget:
        wrapper = QWidget()
        box = QHBoxLayout(wrapper)
        box.setContentsMargins(Spacing.SM, 0, Spacing.SM, 0)
        box.addWidget(widget)
        box.addStretch()
        return wrapper

    def _action_cell(self, profile: GraylogProfile) -> QWidget:
        wrapper = QWidget()
        box = QHBoxLayout(wrapper)
        box.setContentsMargins(0, 0, Spacing.SM, 0)
        box.setSpacing(Spacing.XS)
        box.addStretch()

        test = icon_button("🔌", "Bağlantıyı Test Et")
        edit = icon_button("✎", "Düzenle")
        delete = icon_button("🗑", "Sil")
        test.clicked.connect(lambda: self._on_test(profile, test))
        edit.clicked.connect(lambda: self._on_edit(profile))
        delete.clicked.connect(lambda: self._on_delete(profile))
        box.addWidget(test)
        box.addWidget(edit)
        box.addWidget(delete)
        return wrapper

    def _persist_default(self, profile: GraylogProfile) -> None:
        if profile.IsDefault and profile.Id is not None:
            self._repo.clear_default_except(profile.Id)

    def _on_add(self) -> None:
        dialog = GraylogProfileFormDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            created = self._repo.create(dialog.result_profile())
        except DuplicateRecordError as exc:
            show_toast(self, str(exc), "error")
            return
        self._persist_default(created)
        show_toast(self, "Profil kaydedildi.", "success")
        self.load_data()

    def _on_edit(self, profile: GraylogProfile) -> None:
        dialog = GraylogProfileFormDialog(self, profile)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            updated = self._repo.update(dialog.result_profile())
        except DuplicateRecordError as exc:
            show_toast(self, str(exc), "error")
            return
        self._persist_default(updated)
        show_toast(self, "Profil kaydedildi.", "success")
        self.load_data()

    def _on_delete(self, profile: GraylogProfile) -> None:
        if not ConfirmDialog.confirm(
            self,
            "Profili sil",
            f"'{profile.Name}' profilini silmek istediğinize emin misiniz?",
            confirm_text="Sil",
            danger=True,
        ):
            return
        try:
            self._repo.delete(profile.Id)
        except ProfileInUseError as exc:
            show_toast(self, str(exc), "warning")
            return
        show_toast(self, "Profil silindi.", "success")
        self.load_data()

    def _on_test(self, profile: GraylogProfile, button) -> None:
        if self._active_worker is not None:
            return  # a test is already running
        button.setEnabled(False)
        button.setText("…")

        worker = _ConnectionTestWorker(profile, self)
        self._active_worker = worker

        def finish(message: str, tone: str) -> None:
            show_toast(self, message, tone)
            button.setEnabled(True)
            button.setText("🔌")
            self._active_worker = None
            worker.deleteLater()

        worker.succeeded.connect(lambda msg: finish(msg, "success"))
        worker.failed.connect(lambda msg: finish(msg, "error"))
        worker.start()
