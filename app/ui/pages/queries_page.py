"""Sorgular page — master-detail list + query execution
(DESIGN_SYSTEM.md §3, PROJECT_PLAN.md §5.4)."""
from __future__ import annotations

import re
import sqlite3
from dataclasses import replace

from PySide6.QtCore import QSortFilterProxyModel, Qt, QThread, Signal
from PySide6.QtGui import QColor, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QStyledItemDelegate,
    QTableView,
    QTreeWidget,
    QTreeWidgetItem,
    QTreeWidgetItemIterator,
    QVBoxLayout,
    QWidget,
)

from app.core.exceptions import GrayScopeError
from app.data.models.query import Query
from app.data.models.query_folder import QueryFolder
from app.data.repositories.graylog_profile_repository import GraylogProfileRepository
from app.data.repositories.query_folder_repository import QueryFolderRepository
from app.data.repositories.query_repository import QueryRepository
from app.data.repositories.query_stream_repository import QueryStreamRepository
from app.integrations.graylog.exceptions import GraylogError
from app.services.query_execution_service import (
    ExecutionResult,
    execute_query,
    extract_parameters,
)
from app.services.stream_catalog_service import StreamCatalogService
from app.ui.components.buttons import ghost_button, icon_button, primary_button
from app.ui.components.cell_value_dialog import CellValueDialog
from app.ui.components.dialogs import ConfirmDialog
from app.ui.components.feedback import EmptyState, badge, show_toast
from app.ui.components.inputs import SearchInput, labeled_field
from app.ui.pages.query_form_dialog import QueryFormDialog
from app.ui.pages.settings_dialog import SettingsDialog
from app.ui.theme import Colors, Spacing
from app.ui import theme as _theme
from app.ui.stylesheets import apply_theme as _apply_theme

# Tree item roles: (kind, id) where kind is "folder" or "query".
_ROLE = Qt.ItemDataRole.UserRole

# Result stack indices.
_RESULT_IDLE, _RESULT_LOADING, _RESULT_GRID, _RESULT_EMPTY, _RESULT_ERROR = range(5)


class _ExecutionWorker(QThread):
    succeeded = Signal(object)  # ExecutionResult
    failed = Signal(str)

    def __init__(self, profile, query, stream_ids, params, parent=None) -> None:
        super().__init__(parent)
        self._args = (profile, query, stream_ids, params)

    def run(self) -> None:
        try:
            result = execute_query(*self._args)
        except (GraylogError, GrayScopeError) as exc:
            self.failed.emit(str(exc))
            return
        except Exception:  # noqa: BLE001
            self.failed.emit("Sorgu çalıştırılırken beklenmeyen bir hata oluştu.")
            return
        self.succeeded.emit(result)


def compile_search(term: str) -> "re.Pattern | None":
    """Compile a result-search term into a case-insensitive 'contains' matcher.

    Plain text matches as a substring; ``*`` and ``?`` act as wildcards
    (``*`` = any run of chars, ``?`` = one char). Returns None for empty input.
    """
    term = term.strip()
    if not term:
        return None
    pattern = re.escape(term).replace(r"\*", ".*").replace(r"\?", ".")
    try:
        return re.compile(pattern, re.IGNORECASE)
    except re.error:
        return None


class _HighlightDelegate(QStyledItemDelegate):
    """Paints cells matching the search term with a highlight background.

    Done in a delegate (not via the model's BackgroundRole) because the table's
    stylesheet overrides item BackgroundRole, so model-set colors never render.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._pattern: "re.Pattern | None" = None

    def set_pattern(self, pattern) -> None:
        self._pattern = pattern

    def paint(self, painter, option, index) -> None:
        text = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
        if self._pattern is not None and self._pattern.search(text):
            # Read colors live so the highlight follows the active theme.
            painter.save()
            painter.fillRect(option.rect, QColor(Colors.WARNING))
            painter.setPen(QColor(Colors.BG_BASE))
            rect = option.rect.adjusted(Spacing.MD, 0, -Spacing.SM, 0)
            painter.drawText(
                rect,
                int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
                text,
            )
            painter.restore()
        else:
            super().paint(painter, option, index)


class QueriesPage(QWidget):
    def __init__(self, conn: sqlite3.Connection, stream_service: StreamCatalogService) -> None:
        super().__init__()
        self._conn = conn
        self._queries_repo = QueryRepository(conn)
        self._profiles_repo = GraylogProfileRepository(conn)
        self._streams_repo = QueryStreamRepository(conn)
        self._folders_repo = QueryFolderRepository(conn)
        self._stream_service = stream_service

        self._queries: list[Query] = []
        self._folders: list[QueryFolder] = []
        self._selected: Query | None = None
        self._worker: _ExecutionWorker | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_master())
        splitter.addWidget(self._build_detail())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([400, 880])
        layout.addWidget(splitter)

        self._connect_signals()
        self.load_data()

    # ── master (left) ───────────────────────────────────────────────────
    def _build_master(self) -> QWidget:
        panel = QFrame()
        panel.setProperty("class", "master-panel")
        panel.setMinimumWidth(300)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        layout.setSpacing(Spacing.SM)

        self._search = SearchInput("Sorgu ara")
        self._new_button = primary_button("+ Yeni Sorgu")
        layout.addWidget(self._search)
        layout.addWidget(self._new_button)

        self._tree_stack = QStackedWidget()
        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree_empty = EmptyState(
            "\U0001F50E", "Henüz sorgu yok", "Yeni bir sorgu oluşturarak başlayın."
        )
        self._tree_stack.addWidget(self._tree)
        self._tree_stack.addWidget(self._tree_empty)
        layout.addWidget(self._tree_stack, 1)

        # Bottom corner: settings + theme toggle.
        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 0, 0, 0)
        self._settings_button = ghost_button("⚙  Ayarlar")
        is_dark = _theme.current_theme() == "dark"
        self._theme_button = icon_button(
            "☀" if is_dark else "🌙",
            "Açık temaya geç" if is_dark else "Koyu temaya geç",
        )
        bottom.addWidget(self._settings_button)
        bottom.addStretch()
        bottom.addWidget(self._theme_button)
        layout.addLayout(bottom)
        return panel

    # ── detail (right) ──────────────────────────────────────────────────
    def _build_detail(self) -> QWidget:
        self._detail_stack = QStackedWidget()
        self._detail_stack.addWidget(
            EmptyState(
                "\U0001F446",
                "Bir sorgu seçin",
                "Soldan bir sorgu seçin ya da yeni bir sorgu oluşturun.",
            )
        )
        self._detail_stack.addWidget(self._build_detail_content())
        return self._detail_stack

    def _build_detail_content(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(Spacing.LG, Spacing.MD, Spacing.LG, Spacing.MD)
        layout.setSpacing(Spacing.SM)

        header = QHBoxLayout()
        self._title = QLabel()
        self._title.setProperty("class", "detail-title")
        self._edit_button = icon_button("✎", "Düzenle")
        self._copy_button = icon_button("⧉", "Kopyala (çoğalt)")
        self._delete_button = icon_button("🗑", "Sil")
        header.addWidget(self._title)
        header.addStretch()
        header.addWidget(self._edit_button)
        header.addWidget(self._copy_button)
        header.addWidget(self._delete_button)
        layout.addLayout(header)

        # Selected streams shown as small badges under the title.
        self._streams_row = QWidget()
        self._streams_layout = QHBoxLayout(self._streams_row)
        self._streams_layout.setContentsMargins(0, 0, 0, 0)
        self._streams_layout.setSpacing(Spacing.XS)
        layout.addWidget(self._streams_row)

        # Run panel — a single card grouping parameters + run controls, set apart
        # from the result grid below. A thin separator divides the (optional)
        # parameter area from the query/run row.
        self._run_panel = QFrame()
        self._run_panel.setProperty("class", "run-panel")
        panel_layout = QVBoxLayout(self._run_panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(Spacing.SM)

        # Parameters area — one labeled input per {param} in the query text,
        # laid out side by side (label above each field). Built dynamically.
        self._params_row = QWidget()
        self._params_layout = QHBoxLayout(self._params_row)
        self._params_layout.setContentsMargins(0, 0, 0, 0)
        self._params_layout.setSpacing(Spacing.MD)
        self._param_fields: dict[str, QLineEdit] = {}
        panel_layout.addWidget(self._params_row)

        self._param_separator = QFrame()
        self._param_separator.setProperty("class", "separator")
        self._param_separator.setFixedHeight(1)
        panel_layout.addWidget(self._param_separator)

        # Run row: editable query text (widest) + record count + run button.
        self._run_row = QWidget()
        run_layout = QHBoxLayout(self._run_row)
        run_layout.setContentsMargins(0, 0, 0, 0)
        run_layout.setSpacing(Spacing.SM)

        self._query_input = QLineEdit()
        self._query_input.setProperty("class", "plain-input")
        self._query_input.setPlaceholderText("Sorgu metni")
        self._query_input.setToolTip("Çalıştırmadan önce sorgu metnini geçici olarak düzenleyebilirsiniz")

        count_label = QLabel("Adet:")
        count_label.setProperty("class", "field-label")
        self._count_spin = QSpinBox()
        self._count_spin.setRange(0, 1_000_000)
        self._count_spin.setSpecialValueText("Tümü")  # 0 → all records
        self._count_spin.setToolTip("Çekilecek kayıt sayısı (0 = tüm kayıtlar)")
        self._count_spin.setFixedWidth(96)

        self._run_button = primary_button("Çalıştır")

        run_layout.addWidget(self._query_input, 1)
        run_layout.addWidget(count_label)
        run_layout.addWidget(self._count_spin)
        run_layout.addWidget(self._run_button)
        panel_layout.addWidget(self._run_row)

        layout.addWidget(self._run_panel)

        layout.addWidget(self._build_results(), 1)

        # Full-text search over the result grid, fixed at the bottom (grid-wide).
        self._grid_search = QLineEdit()
        self._grid_search.setPlaceholderText("\U0001F50D  Sonuçlarda ara (eşleşenler vurgulanır)…")
        self._grid_search.setClearButtonEnabled(True)
        self._grid_search.setVisible(False)
        self._grid_search.textChanged.connect(self._highlight_matches)
        layout.addWidget(self._grid_search)
        return content

    def _build_results(self) -> QWidget:
        self._results = QStackedWidget()

        self._results.insertWidget(
            _RESULT_IDLE,
            EmptyState("▶", "Çalıştırmaya hazır", "Sonuçları görmek için Çalıştır'a basın."),
        )
        self._results.insertWidget(
            _RESULT_LOADING, EmptyState("⏳", "Çalıştırılıyor…", "Graylog'dan sonuçlar alınıyor.")
        )

        self._table = QTableView()
        self._table.setSortingEnabled(True)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._proxy = QSortFilterProxyModel(self)
        self._table.setModel(self._proxy)
        self._highlight_delegate = _HighlightDelegate(self._table)
        self._table.setItemDelegate(self._highlight_delegate)
        self._results.insertWidget(_RESULT_GRID, self._table)

        self._results.insertWidget(
            _RESULT_EMPTY, EmptyState("\U0001F4ED", "Bu sorgu için kayıt bulunamadı")
        )
        self._error_state = EmptyState("⚠", "Sorgu çalıştırılamadı", "")
        self._results.insertWidget(_RESULT_ERROR, self._error_state)
        return self._results

    # ── data / behaviour ────────────────────────────────────────────────
    def _connect_signals(self) -> None:
        self._search.textChanged.connect(self._render_tree)
        self._new_button.clicked.connect(self._on_new)
        self._tree.currentItemChanged.connect(self._on_select)
        self._tree.customContextMenuRequested.connect(self._on_tree_menu)
        self._settings_button.clicked.connect(self._open_settings)
        self._theme_button.clicked.connect(self._toggle_theme)
        self._edit_button.clicked.connect(self._on_edit)
        self._copy_button.clicked.connect(self._on_copy)
        self._delete_button.clicked.connect(self._on_delete)
        self._query_input.textChanged.connect(self._rebuild_params)
        self._run_button.clicked.connect(self._on_run)
        self._table.doubleClicked.connect(self._on_cell_double_clicked)

    def _on_cell_double_clicked(self, index) -> None:
        if not index.isValid():
            return
        value = str(index.data() or "")
        field = self._proxy.headerData(index.column(), Qt.Orientation.Horizontal) or ""
        dialog = CellValueDialog(str(field), value, self.window())
        dialog.show()

    def load_data(self) -> None:
        self._queries = self._queries_repo.get_all()
        self._folders = self._folders_repo.get_all()
        self._profiles_by_id = {p.Id: p for p in self._profiles_repo.get_all()}
        self._render_tree()

    # ── tree ─────────────────────────────────────────────────────────────
    def _render_tree(self) -> None:
        term = self._search.text().strip().lower()
        self._tree_stack.setCurrentIndex(
            1 if (not self._queries and not self._folders) else 0
        )

        self._tree.blockSignals(True)
        self._tree.clear()
        root = self._tree.invisibleRootItem()

        by_parent: dict[int | None, list[QueryFolder]] = {}
        for folder in self._folders:
            by_parent.setdefault(folder.ParentId, []).append(folder)

        folder_items: dict[int, QTreeWidgetItem] = {}

        def add_folders(parent_id: int | None, parent_item: QTreeWidgetItem) -> None:
            for folder in sorted(by_parent.get(parent_id, []), key=lambda f: f.Name.lower()):
                item = QTreeWidgetItem(parent_item, [f"\U0001F4C1  {folder.Name}"])
                item.setData(0, _ROLE, ("folder", folder.Id))
                folder_items[folder.Id] = item
                add_folders(folder.Id, item)

        add_folders(None, root)

        for query in self._queries:
            if term and term not in query.Name.lower():
                continue
            parent_item = folder_items.get(query.FolderId, root)
            item = QTreeWidgetItem(parent_item, [f"\U0001F50E  {query.Name}"])
            item.setData(0, _ROLE, ("query", query.Id))
            item.setToolTip(0, query.Name)

        if term:
            self._prune_empty_folders(folder_items, root)
        self._tree.expandAll()
        self._tree.blockSignals(False)

    def _prune_empty_folders(self, folder_items, root) -> None:
        changed = True
        while changed:
            changed = False
            for fid, item in list(folder_items.items()):
                if item.childCount() == 0:
                    (item.parent() or root).removeChild(item)
                    del folder_items[fid]
                    changed = True

    def _selected_kind_id(self):
        item = self._tree.currentItem()
        return item.data(0, _ROLE) if item else (None, None)

    def _on_select(self, current: QTreeWidgetItem | None, _previous=None) -> None:
        kind, ident = current.data(0, _ROLE) if current else (None, None)
        if kind == "query":
            self._selected = next((q for q in self._queries if q.Id == ident), None)
            if self._selected:
                self._show_detail(self._selected)
                return
        self._selected = None
        self._detail_stack.setCurrentIndex(0)

    # ── folders (context menu) ───────────────────────────────────────────
    def _folder_name(self, folder_id: int) -> str:
        return next((f.Name for f in self._folders if f.Id == folder_id), "")

    def _on_tree_menu(self, pos) -> None:
        item = self._tree.itemAt(pos)
        menu = QMenu(self)
        if item is None:
            menu.addAction("Yeni Klasör", lambda: self._new_folder(None))
        else:
            kind, ident = item.data(0, _ROLE)
            if kind == "folder":
                menu.addAction("Yeni Alt Klasör", lambda: self._new_folder(ident))
                menu.addAction("Yeniden Adlandır", lambda: self._rename_folder(ident))
                menu.addSeparator()
                menu.addAction("Sil", lambda: self._delete_folder(ident))
            else:
                menu.addAction("Düzenle", self._on_edit)
                menu.addAction("Kopyala", lambda qid=ident: self._copy_query(qid))
                menu.addSeparator()
                menu.addAction("Sil", self._on_delete)
        menu.exec(self._tree.viewport().mapToGlobal(pos))

    def _new_folder(self, parent_id: int | None) -> None:
        name, ok = QInputDialog.getText(self, "Yeni Klasör", "Klasör adı:")
        if ok and name.strip():
            self._folders_repo.create(QueryFolder(Name=name.strip(), ParentId=parent_id))
            self.load_data()

    def _rename_folder(self, folder_id: int) -> None:
        name, ok = QInputDialog.getText(
            self, "Yeniden Adlandır", "Klasör adı:", text=self._folder_name(folder_id)
        )
        if ok and name.strip():
            self._folders_repo.rename(folder_id, name.strip())
            self.load_data()

    def _delete_folder(self, folder_id: int) -> None:
        if ConfirmDialog.confirm(
            self,
            "Klasörü sil",
            f"'{self._folder_name(folder_id)}' klasörünü silmek istediğinize emin misiniz? "
            "İçindeki sorgular kök seviyeye taşınır.",
            confirm_text="Sil",
            danger=True,
        ):
            self._folders_repo.delete(folder_id)
            self.load_data()

    # ── settings & theme ─────────────────────────────────────────────────
    def _open_settings(self) -> None:
        SettingsDialog(self._conn, self).exec()
        self.load_data()  # profiles/customers may have changed

    def _toggle_theme(self) -> None:
        from PySide6.QtCore import QSettings

        new_mode = "light" if _theme.current_theme() == "dark" else "dark"
        _apply_theme(QApplication.instance(), new_mode)
        QSettings("GrayScope", "GrayScope").setValue("theme", new_mode)
        is_dark = new_mode == "dark"
        self._theme_button.setText("☀" if is_dark else "🌙")
        self._theme_button.setToolTip("Açık temaya geç" if is_dark else "Koyu temaya geç")
        self._table.viewport().update()

    def _populate_stream_badges(self, query: Query) -> None:
        while self._streams_layout.count():
            item = self._streams_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        streams = self._streams_repo.get_by_query(query.Id)
        if not streams:
            self._streams_row.setVisible(False)
            return
        for stream in streams:
            self._streams_layout.addWidget(badge(stream.StreamName, "muted"))
        self._streams_layout.addStretch()
        self._streams_row.setVisible(True)

    def _show_detail(self, query: Query) -> None:
        self._detail_stack.setCurrentIndex(1)
        self._title.setText(query.Name)
        self._populate_stream_badges(query)

        # Pre-fill the editable run controls from the saved query (single-line view).
        self._query_input.setText(query.QueryTemplate.replace("\n", " "))
        self._count_spin.setValue(query.ResultSize)

        self._rebuild_params()
        self._results.setCurrentIndex(_RESULT_IDLE)
        self._set_grid_search_visible(False)
        self._update_run_enabled()

    def _rebuild_params(self) -> None:
        """Render one labeled input per {param} in the current query text.

        Preserves already-entered values for parameters that still exist.
        """
        names = extract_parameters(self._query_input.text())
        previous = {name: field.text() for name, field in self._param_fields.items()}

        while self._params_layout.count():
            item = self._params_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._param_fields = {}

        for name in names:
            field = QLineEdit()
            field.setMinimumWidth(140)
            field.setText(previous.get(name, ""))
            field.textChanged.connect(self._update_run_enabled)
            self._param_fields[name] = field
            self._params_layout.addWidget(labeled_field(name, field))
        self._params_layout.addStretch()

        has_params = bool(names)
        self._params_row.setVisible(has_params)
        self._param_separator.setVisible(has_params)
        self._update_run_enabled()

    def _update_run_enabled(self) -> None:
        if self._selected is None:
            return
        all_filled = all(field.text().strip() for field in self._param_fields.values())
        self._run_button.setEnabled(all_filled)
        self._run_button.setToolTip("" if all_filled else "Önce tüm parametreleri doldurun")

    # ── CRUD ─────────────────────────────────────────────────────────────
    def _active_profiles(self):
        return self._profiles_repo.get_all(only_active=True)

    def _on_new(self) -> None:
        profiles = self._active_profiles()
        if not profiles:
            show_toast(self, "Önce bir Graylog profili ekleyin.", "warning")
            return
        kind, ident = self._selected_kind_id()
        if kind == "folder":
            default_folder = ident
        elif kind == "query" and self._selected:
            default_folder = self._selected.FolderId
        else:
            default_folder = None
        dialog = QueryFormDialog(
            self, profiles, self._stream_service,
            folders=self._folders, default_folder_id=default_folder,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        created = self._queries_repo.create(dialog.result_query())
        self._streams_repo.replace_for_query(created.Id, dialog.selected_streams())
        show_toast(self, "Sorgu kaydedildi.", "success")
        self.load_data()
        self._reselect(created.Id)

    def _on_edit(self) -> None:
        if self._selected is None:
            return
        profiles = self._active_profiles()
        existing = self._streams_repo.get_by_query(self._selected.Id)
        dialog = QueryFormDialog(
            self, profiles, self._stream_service, self._selected, existing,
            folders=self._folders,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        updated = self._queries_repo.update(dialog.result_query())
        self._streams_repo.replace_for_query(updated.Id, dialog.selected_streams())
        show_toast(self, "Sorgu güncellendi.", "success")
        self.load_data()
        self._reselect(updated.Id)

    def _on_copy(self) -> None:
        if self._selected is not None:
            self._copy_query(self._selected.Id)

    def _unique_copy_name(self, base: str) -> str:
        existing = {q.Name for q in self._queries}
        candidate = f"{base} (kopya)"
        index = 2
        while candidate in existing:
            candidate = f"{base} (kopya {index})"
            index += 1
        return candidate

    def _copy_query(self, query_id: int) -> None:
        """Duplicate a query (with its streams and folder) under a new unique name."""
        original = next((q for q in self._queries if q.Id == query_id), None)
        if original is None:
            return
        new_query = replace(original, Id=None, Name=self._unique_copy_name(original.Name))
        created = self._queries_repo.create(new_query)
        self._streams_repo.replace_for_query(
            created.Id, self._streams_repo.get_by_query(original.Id)
        )
        show_toast(self, "Sorgu kopyalandı.", "success")
        self.load_data()
        self._reselect(created.Id)

    def _on_delete(self) -> None:
        if self._selected is None:
            return
        if not ConfirmDialog.confirm(
            self,
            "Sorguyu sil",
            f"'{self._selected.Name}' sorgusunu silmek istediğinize emin misiniz?",
            confirm_text="Sil",
            danger=True,
        ):
            return
        self._queries_repo.delete(self._selected.Id)
        show_toast(self, "Sorgu silindi.", "success")
        self._selected = None
        self._detail_stack.setCurrentIndex(0)
        self.load_data()

    def _reselect(self, query_id: int) -> None:
        iterator = QTreeWidgetItemIterator(self._tree)
        while iterator.value():
            item = iterator.value()
            if item.data(0, _ROLE) == ("query", query_id):
                self._tree.setCurrentItem(item)
                return
            iterator += 1

    # ── execution ─────────────────────────────────────────────────────────
    def _on_run(self) -> None:
        if self._selected is None or self._worker is not None:
            return
        profile = self._profiles_by_id.get(self._selected.GraylogProfileId)
        if profile is None:
            show_toast(self, "Bu sorgunun profili bulunamadı.", "error")
            return
        stream_ids = [qs.StreamId for qs in self._streams_repo.get_by_query(self._selected.Id)]
        params = {name: field.text().strip() for name, field in self._param_fields.items()}

        # Ad-hoc overrides from the run row (not persisted): edited query text and
        # record count (0 = all). Empty text falls back to "*" (match all).
        effective = replace(
            self._selected,
            QueryTemplate=self._query_input.text().strip() or "*",
            ResultSize=self._count_spin.value(),
        )

        self._results.setCurrentIndex(_RESULT_LOADING)
        self._run_button.setEnabled(False)

        worker = _ExecutionWorker(profile, effective, stream_ids, params, self)
        self._worker = worker
        worker.succeeded.connect(self._on_run_succeeded)
        worker.failed.connect(self._on_run_failed)
        worker.finished.connect(self._on_run_finished)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def _on_run_succeeded(self, result: ExecutionResult) -> None:
        if not result.rows:
            self._set_grid_search_visible(False)
            self._results.setCurrentIndex(_RESULT_EMPTY)
            return
        model = QStandardItemModel(len(result.rows), len(result.fields), self)
        model.setHorizontalHeaderLabels(result.fields)
        for r, row in enumerate(result.rows):
            for c, field in enumerate(result.fields):
                item = QStandardItem(str(row.get(field, "")))
                item.setEditable(False)
                model.setItem(r, c, item)
        self._proxy.setSourceModel(model)  # replaces previous result (FR-Query-Run-02)

        sort_field = self._selected.DefaultSortField if self._selected else None
        if sort_field and sort_field in result.fields:
            from app.data.models.query import SortOrder

            order = (
                Qt.SortOrder.DescendingOrder
                if self._selected.DefaultSortOrder is SortOrder.DESC
                else Qt.SortOrder.AscendingOrder
            )
            self._table.sortByColumn(result.fields.index(sort_field), order)
        self._results.setCurrentIndex(_RESULT_GRID)
        self._set_grid_search_visible(True)

    def _on_run_failed(self, message: str) -> None:
        self._set_grid_search_visible(False)
        # Rebuild the error empty-state with the actual message.
        self._results.removeWidget(self._error_state)
        self._error_state = EmptyState("⚠", "Sorgu çalıştırılamadı", message)
        self._results.insertWidget(_RESULT_ERROR, self._error_state)
        self._results.setCurrentIndex(_RESULT_ERROR)

    def _set_grid_search_visible(self, visible: bool) -> None:
        self._grid_search.blockSignals(True)
        self._grid_search.clear()
        self._grid_search.blockSignals(False)
        self._highlight_delegate.set_pattern(None)
        self._grid_search.setVisible(visible)

    def _highlight_matches(self) -> None:
        """Update the highlight pattern as the user types (substring + wildcards)."""
        self._highlight_delegate.set_pattern(compile_search(self._grid_search.text()))
        self._table.viewport().update()

    def _on_run_finished(self) -> None:
        self._worker = None
        self._update_run_enabled()
