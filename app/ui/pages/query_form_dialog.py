"""New/Edit query dialog (DESIGN_SYSTEM.md §4, PROJECT_PLAN.md §5.5)."""
from __future__ import annotations

import json

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.config import DEFAULT_RESULT_SIZE
from app.data.models.graylog_profile import GraylogProfile
from app.data.models.query import Query, SortOrder, TimeRangeType
from app.data.models.query_folder import QueryFolder
from app.data.models.query_stream import QueryStream
from app.integrations.graylog.exceptions import GraylogError
from app.services.stream_catalog_service import StreamCatalogService
from app.ui.components.buttons import icon_button, primary_button, secondary_button
from app.ui.components.inputs import ChipInput, SearchInput, labeled_field
from app.ui.components.relative_range_widget import RelativeRangeWidget
from app.ui.theme import Spacing


class _StreamLoadWorker(QThread):
    succeeded = Signal(list)  # list[StreamInfo]
    failed = Signal(str)

    def __init__(self, service: StreamCatalogService, profile: GraylogProfile, parent=None) -> None:
        super().__init__(parent)
        self._service = service
        self._profile = profile

    def run(self) -> None:
        try:
            streams = self._service.get_streams(self._profile, force_refresh=True)
        except GraylogError as exc:
            self.failed.emit(str(exc))
            return
        except Exception:  # noqa: BLE001
            self.failed.emit("Stream listesi alınamadı, bağlantıyı kontrol edin.")
            return
        self.succeeded.emit(streams)


class QueryFormDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        profiles: list[GraylogProfile],
        stream_service: StreamCatalogService,
        query: Query | None = None,
        existing_streams: list[QueryStream] | None = None,
        folders: list[QueryFolder] | None = None,
        default_folder_id: int | None = None,
    ) -> None:
        super().__init__(parent)
        self._profiles = profiles
        self._stream_service = stream_service
        self._query = query
        self._existing_streams = existing_streams or []
        self._folders = folders or []
        self._default_folder_id = default_folder_id
        self._worker: _StreamLoadWorker | None = None

        self.setWindowTitle("Sorguyu Düzenle" if query else "Yeni Sorgu")
        self.setModal(True)
        self.setMinimumSize(640, 720)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        form = QVBoxLayout(content)
        form.setContentsMargins(Spacing.LG, Spacing.MD, Spacing.LG, Spacing.MD)
        form.setSpacing(Spacing.SM)

        self._build_fields(form)
        outer.addWidget(self._build_footer())

        if query:
            self._populate(query)
        self._connect_signals()
        self._reload_streams()

    def _ordered_folders(self) -> list[tuple[QueryFolder, int]]:
        """Folders in hierarchical order with their depth (for indented display)."""
        by_parent: dict[int | None, list[QueryFolder]] = {}
        for folder in self._folders:
            by_parent.setdefault(folder.ParentId, []).append(folder)
        ordered: list[tuple[QueryFolder, int]] = []

        def walk(parent_id: int | None, depth: int) -> None:
            for folder in sorted(by_parent.get(parent_id, []), key=lambda f: f.Name.lower()):
                ordered.append((folder, depth))
                walk(folder.Id, depth + 1)

        walk(None, 0)
        return ordered

    # ── construction ────────────────────────────────────────────────────
    def _build_fields(self, form: QVBoxLayout) -> None:
        self._name = QLineEdit()
        self._name.setPlaceholderText("Sorgu adı")
        form.addWidget(labeled_field("Ad", self._name, required=True))

        self._profile_combo = QComboBox()
        for profile in self._profiles:
            self._profile_combo.addItem(profile.Name, profile.Id)
        form.addWidget(labeled_field("Graylog Profili", self._profile_combo, required=True))

        self._folder_combo = QComboBox()
        self._folder_combo.addItem("(Kök)", None)
        for folder, depth in self._ordered_folders():
            self._folder_combo.addItem("    " * depth + folder.Name, folder.Id)
        default = self._default_folder_id if self._query is None else None
        if default is not None:
            idx = self._folder_combo.findData(default)
            if idx >= 0:
                self._folder_combo.setCurrentIndex(idx)
        form.addWidget(labeled_field("Klasör", self._folder_combo))

        self._query_text = QPlainTextEdit()
        self._query_text.setProperty("mono", "true")
        self._query_text.setPlaceholderText("NetworkId:{NetworkId} AND NOT StatusCode:200")
        self._query_text.setFixedHeight(96)
        form.addWidget(labeled_field("Sorgu metni", self._query_text, required=True))
        param_hint = QLabel(
            "Parametre eklemek için sorgu metninde {parametreAdı} kullanın "
            "(örn. {NetworkId}). Çalıştırma ekranında her parametre için bir giriş alanı çıkar."
        )
        param_hint.setProperty("class", "hint")
        param_hint.setWordWrap(True)
        form.addWidget(param_hint)

        form.addWidget(self._build_streams_section())
        form.addWidget(self._build_timerange_section())

        self._fields = ChipInput()
        form.addWidget(labeled_field("Gösterilecek alanlar", self._fields, required=True))

        form.addWidget(self._build_sort_section())

        self._result_size = QSpinBox()
        self._result_size.setRange(10, 1000)
        self._result_size.setValue(DEFAULT_RESULT_SIZE)
        form.addWidget(labeled_field("Sonuç limiti", self._result_size))

        self._error = QLabel()
        self._error.setProperty("class", "error-text")
        self._error.setVisible(False)
        form.addWidget(self._error)

    def _build_streams_section(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.XS)

        header = QHBoxLayout()
        label = QLabel("Stream seçimi")
        label.setProperty("class", "field-label")
        self._stream_refresh = icon_button("⟳", "Stream listesini yenile")
        header.addWidget(label)
        header.addStretch()
        header.addWidget(self._stream_refresh)
        layout.addLayout(header)

        self._stream_search = SearchInput("Stream ara")
        layout.addWidget(self._stream_search)

        self._stream_status = QLabel("Stream listesi yükleniyor…")
        self._stream_status.setProperty("class", "caption")
        layout.addWidget(self._stream_status)

        self._stream_list = QListWidget()
        self._stream_list.setFixedHeight(140)
        layout.addWidget(self._stream_list)
        return container

    def _build_timerange_section(self) -> QWidget:
        self._timerange_tabs = QTabWidget()

        relative = QWidget()
        rl = QVBoxLayout(relative)
        self._relative_range = RelativeRangeWidget()
        rl.addWidget(labeled_field("Tarih aralığı", self._relative_range))
        self._timerange_tabs.addTab(relative, "Relative")

        absolute = QWidget()
        al = QHBoxLayout(absolute)
        self._absolute_from = QDateTimeEdit()
        self._absolute_from.setCalendarPopup(True)
        self._absolute_to = QDateTimeEdit()
        self._absolute_to.setCalendarPopup(True)
        al.addWidget(labeled_field("Başlangıç", self._absolute_from))
        al.addWidget(labeled_field("Bitiş", self._absolute_to))
        self._timerange_tabs.addTab(absolute, "Absolute")

        keyword = QWidget()
        kl = QVBoxLayout(keyword)
        self._keyword = QLineEdit()
        self._keyword.setPlaceholderText("örn. yesterday, last 1 day")
        kl.addWidget(labeled_field("Anahtar kelime", self._keyword))
        self._timerange_tabs.addTab(keyword, "Keyword")

        return labeled_field("Tarih aralığı", self._timerange_tabs)

    def _build_sort_section(self) -> QWidget:
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(Spacing.MD)

        self._sort_field = QComboBox()
        self._refresh_sort_options()

        self._sort_asc = QRadioButton("Artan")
        self._sort_desc = QRadioButton("Azalan")
        self._sort_asc.setChecked(True)
        group = QButtonGroup(self)
        group.addButton(self._sort_asc)
        group.addButton(self._sort_desc)

        direction = QWidget()
        dl = QHBoxLayout(direction)
        dl.setContentsMargins(0, 0, 0, 0)
        dl.addWidget(self._sort_asc)
        dl.addWidget(self._sort_desc)

        row.addWidget(labeled_field("Varsayılan sıralama alanı", self._sort_field), 1)
        row.addWidget(labeled_field("Yön", direction))
        return container

    def _build_footer(self) -> QWidget:
        footer = QWidget()
        row = QHBoxLayout(footer)
        row.setContentsMargins(Spacing.LG, Spacing.MD, Spacing.LG, Spacing.MD)
        row.addStretch()
        cancel = secondary_button("Vazgeç")
        save = primary_button("Kaydet")
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self._on_save)
        row.addWidget(cancel)
        row.addWidget(save)
        return footer

    # ── behaviour ───────────────────────────────────────────────────────
    def _connect_signals(self) -> None:
        self._fields.changed.connect(self._refresh_sort_options)
        self._profile_combo.currentIndexChanged.connect(self._reload_streams)
        self._stream_refresh.clicked.connect(self._reload_streams)
        self._stream_search.textChanged.connect(self._filter_streams)

    def _refresh_sort_options(self) -> None:
        current = self._sort_field.currentText() if self._sort_field.count() else ""
        self._sort_field.clear()
        self._sort_field.addItem("(yok)", None)
        for field in self._fields.values():
            self._sort_field.addItem(field, field)
        index = self._sort_field.findText(current)
        if index >= 0:
            self._sort_field.setCurrentIndex(index)

    def _selected_profile(self) -> GraylogProfile | None:
        profile_id = self._profile_combo.currentData()
        return next((p for p in self._profiles if p.Id == profile_id), None)

    def _reload_streams(self) -> None:
        profile = self._selected_profile()
        if profile is None or self._worker is not None:
            return
        self._stream_status.setText("Stream listesi yükleniyor…")
        self._stream_status.setVisible(True)
        self._stream_list.setEnabled(False)

        worker = _StreamLoadWorker(self._stream_service, profile, self)
        self._worker = worker
        worker.succeeded.connect(self._on_streams_loaded)
        worker.failed.connect(self._on_streams_failed)
        worker.finished.connect(self._clear_worker)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def _clear_worker(self) -> None:
        self._worker = None

    def done(self, result: int) -> None:
        # Never let the dialog (and its child QThread) be destroyed while the
        # stream-load thread is still running — that aborts the process.
        if self._worker is not None and self._worker.isRunning():
            self._worker.wait(12000)
        super().done(result)

    def _on_streams_loaded(self, streams: list) -> None:
        selected_ids = {qs.StreamId for qs in self._existing_streams}
        selected_ids |= self._checked_stream_ids()
        self._stream_list.clear()
        for stream in streams:
            item = QListWidgetItem(stream.title)
            item.setData(Qt.ItemDataRole.UserRole, stream.id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if stream.id in selected_ids else Qt.CheckState.Unchecked
            )
            self._stream_list.addItem(item)
        self._stream_status.setVisible(False)
        self._stream_list.setEnabled(True)
        self._filter_streams()

    def _on_streams_failed(self, message: str) -> None:
        # Form stays usable; only the stream area shows the error (FR-Stream-01).
        self._stream_status.setText(f"⚠ {message}  (Yenile ile tekrar deneyin)")
        self._stream_status.setVisible(True)
        self._stream_list.setEnabled(True)

    def _filter_streams(self) -> None:
        term = self._stream_search.text().strip().lower()
        for i in range(self._stream_list.count()):
            item = self._stream_list.item(i)
            item.setHidden(bool(term) and term not in item.text().lower())

    def _checked_stream_ids(self) -> set[str]:
        ids: set[str] = set()
        for i in range(self._stream_list.count()):
            item = self._stream_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                ids.add(item.data(Qt.ItemDataRole.UserRole))
        return ids

    def selected_streams(self) -> list[QueryStream]:
        result: list[QueryStream] = []
        for i in range(self._stream_list.count()):
            item = self._stream_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                result.append(
                    QueryStream(
                        QueryId=0,
                        StreamId=item.data(Qt.ItemDataRole.UserRole),
                        StreamName=item.text(),
                    )
                )
        return result

    # ── populate / collect ──────────────────────────────────────────────
    def _populate(self, query: Query) -> None:
        self._name.setText(query.Name)
        idx = self._profile_combo.findData(query.GraylogProfileId)
        if idx >= 0:
            self._profile_combo.setCurrentIndex(idx)
        self._query_text.setPlainText(query.QueryTemplate)
        self._fields.set_values(json.loads(query.FieldsJson) if query.FieldsJson else [])
        self._result_size.setValue(query.ResultSize)
        folder_idx = self._folder_combo.findData(query.FolderId)
        if folder_idx >= 0:
            self._folder_combo.setCurrentIndex(folder_idx)

        if query.TimeRangeType is TimeRangeType.RELATIVE:
            self._timerange_tabs.setCurrentIndex(0)
            self._relative_range.set_seconds(query.TimeRangeRangeSeconds or 3600)
        elif query.TimeRangeType is TimeRangeType.ABSOLUTE:
            self._timerange_tabs.setCurrentIndex(1)
        else:
            self._timerange_tabs.setCurrentIndex(2)
            self._keyword.setText(query.TimeRangeKeyword or "")

        if query.DefaultSortField:
            self._refresh_sort_options()
            i = self._sort_field.findData(query.DefaultSortField)
            if i >= 0:
                self._sort_field.setCurrentIndex(i)
        if query.DefaultSortOrder is SortOrder.DESC:
            self._sort_desc.setChecked(True)

    def _on_save(self) -> None:
        if not self._name.text().strip():
            self._show_error("Ad boş olamaz.")
            return
        if not self._query_text.toPlainText().strip():
            self._show_error("Sorgu metni boş olamaz.")
            return
        if not self._fields.values():
            self._show_error("En az bir gösterilecek alan ekleyin.")
            return
        self.accept()

    def _show_error(self, message: str) -> None:
        self._error.setText(message)
        self._error.setVisible(True)

    def result_query(self) -> Query:
        tab = self._timerange_tabs.currentIndex()
        time_type = [TimeRangeType.RELATIVE, TimeRangeType.ABSOLUTE, TimeRangeType.KEYWORD][tab]

        sort_field = self._sort_field.currentData()
        sort_order = None
        if sort_field:
            sort_order = SortOrder.DESC if self._sort_desc.isChecked() else SortOrder.ASC

        template = self._query_text.toPlainText().strip()
        return Query(
            Id=self._query.Id if self._query else None,
            Name=self._name.text().strip(),
            GraylogProfileId=self._profile_combo.currentData(),
            QueryTemplate=template,
            TimeRangeType=time_type,
            TimeRangeRangeSeconds=self._relative_range.seconds() if tab == 0 else None,
            TimeRangeFrom=self._absolute_from.dateTime().toPython() if tab == 1 else None,
            TimeRangeTo=self._absolute_to.dateTime().toPython() if tab == 1 else None,
            TimeRangeKeyword=self._keyword.text().strip() if tab == 2 else None,
            FieldsJson=json.dumps(self._fields.values()),
            DefaultSortField=sort_field,
            DefaultSortOrder=sort_order,
            FolderId=self._folder_combo.currentData(),
            ResultSize=self._result_size.value(),
        )
