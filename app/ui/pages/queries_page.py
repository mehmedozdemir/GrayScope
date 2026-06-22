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
from app.ui.components.buttons import ghost_button, icon_button, primary_button, secondary_button
from app.ui.components.cell_value_dialog import CellValueDialog
from app.ui.components.relative_range_widget import RelativeRangeWidget
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
    succeeded = Signal(object)           # ExecutionResult
    failed = Signal(str, str)            # (user_message, detail)

    def __init__(self, profile, query, stream_ids, params, parent=None) -> None:
        super().__init__(parent)
        self._args = (profile, query, stream_ids, params)

    def run(self) -> None:
        import traceback
        try:
            result = execute_query(*self._args)
        except (GraylogError, GrayScopeError) as exc:
            self.failed.emit(str(exc), traceback.format_exc())
            return
        except Exception:  # noqa: BLE001
            self.failed.emit(
                "Sorgu çalıştırılırken beklenmeyen bir hata oluştu.",
                traceback.format_exc(),
            )
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


class _WrapHighlightDelegate(QStyledItemDelegate):
    """Cell delegate: word-wrap aware sizing + search-term highlight.

    sizeHint respects the column width so Qt can compute correct row heights
    when word-wrap is enabled. Highlight paint overrides the background for
    cells that match the active search pattern.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._pattern: "re.Pattern | None" = None
        self._wrap: bool = True  # False = single-line (expanded mode)

    def set_pattern(self, pattern) -> None:
        self._pattern = pattern

    def set_wrap(self, wrap: bool) -> None:
        self._wrap = wrap

    def sizeHint(self, option, index) -> "QSize":
        text = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
        if not self._wrap:
            return super().sizeHint(option, index)
        from PySide6.QtCore import QSize
        fm = option.fontMetrics
        padding_h = Spacing.SM * 2
        padding_v = 4 * 2
        col_w = option.rect.width() if option.rect.width() > 0 else 120
        text_w = max(col_w - padding_h, 20)
        bound = fm.boundingRect(
            0, 0, text_w, 0,
            int(Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignLeft),
            text,
        )
        return QSize(col_w, bound.height() + padding_v)

    def paint(self, painter, option, index) -> None:
        text = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
        if self._pattern is not None and self._pattern.search(text):
            painter.save()
            painter.fillRect(option.rect, QColor(Colors.WARNING))
            painter.setPen(QColor(Colors.BG_BASE))
            rect = option.rect.adjusted(Spacing.SM, 4, -Spacing.SM, -4)
            flags = int(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            if self._wrap:
                flags |= int(Qt.TextFlag.TextWordWrap)
            painter.drawText(rect, flags, text)
            painter.restore()
        else:
            if self._wrap:
                # Let Qt draw normally; word wrap is handled via sizeHint + setWordWrap.
                super().paint(painter, option, index)
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

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.addWidget(self._build_master())
        self._splitter.addWidget(self._build_detail())
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setSizes([400, 880])
        self._sidebar_sizes = [400, 880]  # last known open sizes
        layout.addWidget(self._splitter)

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
        self._tree.setIndentation(10)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree_empty = EmptyState(
            "\U0001F50E", "Henüz sorgu yok", "Yeni bir sorgu oluşturarak başlayın."
        )
        self._tree_stack.addWidget(self._tree)
        self._tree_stack.addWidget(self._tree_empty)
        layout.addWidget(self._tree_stack, 1)

        # Bottom corner: settings dropdown + theme toggle.
        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 0, 0, 0)
        self._settings_button = icon_button("⚙", "Ayarlar")
        is_dark = _theme.current_theme() == "dark"
        self._theme_button = icon_button(
            "☀" if is_dark else "🌙",
            "Açık temaya geç" if is_dark else "Koyu temaya geç",
        )

        from PySide6.QtWidgets import QMenu
        settings_menu = QMenu(self)
        self._action_settings = settings_menu.addAction("⚙  Ayarlar")
        settings_menu.addSeparator()
        self._action_backup = settings_menu.addAction("⬆  Sorguları Yedekle")
        self._action_restore = settings_menu.addAction("⬇  Yedeği Yükle")
        self._settings_button.setMenu(settings_menu)
        self._settings_button.clicked.connect(self._settings_button.showMenu)

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
        self._sidebar_toggle_btn = icon_button("☰", "Sol paneli gizle / göster")
        self._title = QLabel()
        self._title.setProperty("class", "detail-title")
        self._edit_button = icon_button("✎", "Düzenle")
        self._copy_button = icon_button("⧉", "Kopyala (çoğalt)")
        self._delete_button = icon_button("🗑", "Sil")
        header.addWidget(self._sidebar_toggle_btn)
        header.addWidget(self._title)
        header.addStretch()
        header.addWidget(self._edit_button)
        header.addWidget(self._copy_button)
        header.addWidget(self._delete_button)
        layout.addLayout(header)

        self._run_history_label = QLabel()
        self._run_history_label.setProperty("class", "caption")
        self._run_history_label.setVisible(False)
        layout.addWidget(self._run_history_label)

        # Info/control row: stream badges (left) + relative range widget (right).
        self._info_row = QWidget()
        info_layout = QHBoxLayout(self._info_row)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(Spacing.SM)

        self._streams_layout = QHBoxLayout()
        self._streams_layout.setContentsMargins(0, 0, 0, 0)
        self._streams_layout.setSpacing(Spacing.XS)
        info_layout.addLayout(self._streams_layout)
        info_layout.addStretch()

        layout.addWidget(self._info_row)

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
        self._count_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)

        self._run_button = primary_button("▶  Çalıştır")

        self._range_widget = RelativeRangeWidget()
        self._range_widget.setToolTip("Sorgu tarih aralığı (geçici, kaydedilmez)")

        run_layout.addWidget(self._range_widget)
        run_layout.addWidget(self._query_input, 1)
        run_layout.addWidget(count_label)
        run_layout.addWidget(self._count_spin)
        run_layout.addWidget(self._run_button)
        panel_layout.addWidget(self._run_row)

        layout.addWidget(self._run_panel)

        layout.addWidget(self._build_results(), 1)

        # Top bar: layout toggle (left) — visible only when grid has results.
        self._top_bar = QWidget()
        self._top_bar.setVisible(False)
        top_layout = QHBoxLayout(self._top_bar)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(Spacing.SM)
        self._layout_toggle_btn = secondary_button("⇔  Genişlet")
        self._layout_toggle_btn.setToolTip(
            "Kolonları yatay kaydırmalı tam genişliğe al (tekrar tıkla: sığdır)"
        )
        self._grid_expanded = False
        self._layout_toggle_btn.clicked.connect(self._toggle_grid_layout)
        top_layout.addWidget(self._layout_toggle_btn)
        top_layout.addStretch()
        layout.addWidget(self._top_bar)

        # Bottom bar: full-text search (left) + export buttons (right).
        bottom_bar = QWidget()
        bottom_bar.setVisible(False)
        self._bottom_bar = bottom_bar
        bar_layout = QHBoxLayout(bottom_bar)
        bar_layout.setContentsMargins(0, 0, 0, 0)
        bar_layout.setSpacing(Spacing.SM)

        self._grid_search = QLineEdit()
        self._grid_search.setPlaceholderText("\U0001F50D  Sonuçlarda ara (eşleşenler vurgulanır)…")
        self._grid_search.setClearButtonEnabled(True)
        self._grid_search.textChanged.connect(self._highlight_matches)

        self._export_csv_btn = secondary_button("CSV")
        self._export_csv_btn.setToolTip("Sonuçları CSV olarak dışa aktar")
        self._export_xlsx_btn = secondary_button("Excel")
        self._export_xlsx_btn.setToolTip("Sonuçları Excel (.xlsx) olarak dışa aktar")
        self._export_csv_btn.clicked.connect(self._on_export_csv)
        self._export_xlsx_btn.clicked.connect(self._on_export_xlsx)

        bar_layout.addWidget(self._grid_search, 1)
        bar_layout.addWidget(self._export_csv_btn)
        bar_layout.addWidget(self._export_xlsx_btn)

        layout.addWidget(bottom_bar)
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
        self._table.setWordWrap(True)
        self._table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._proxy = QSortFilterProxyModel(self)
        self._table.setModel(self._proxy)
        self._highlight_delegate = _WrapHighlightDelegate(self._table)
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
        self._sidebar_toggle_btn.clicked.connect(self._toggle_sidebar)
        self._action_settings.triggered.connect(self._open_settings)
        self._theme_button.clicked.connect(self._toggle_theme)
        self._action_backup.triggered.connect(self._on_backup)
        self._action_restore.triggered.connect(self._on_restore)
        self._edit_button.clicked.connect(self._on_edit)
        self._copy_button.clicked.connect(self._on_copy)
        self._delete_button.clicked.connect(self._on_delete)
        self._query_input.textChanged.connect(self._on_query_text_changed)
        self._run_button.clicked.connect(self._on_run)
        self._table.doubleClicked.connect(self._on_cell_double_clicked)

    def _on_query_text_changed(self, _text: str = "") -> None:
        # Live edit: keep already-entered values, only adding/removing fields.
        self._rebuild_params(preserve=True)

    def _on_cell_double_clicked(self, index) -> None:
        if not index.isValid():
            return
        value = str(index.data() or "")
        field = self._proxy.headerData(index.column(), Qt.Orientation.Horizontal) or ""
        dialog = CellValueDialog(str(field), value, self.window())
        dialog.exec()

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
    # ── backup / restore ────────────────────────────────────────────────────
    def _on_backup(self) -> None:
        from PySide6.QtWidgets import QFileDialog
        from app.services.backup_service import export_backup
        from datetime import datetime
        default_name = f"grayscope_yedek_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        path, _ = QFileDialog.getSaveFileName(
            self, "Sorguları Yedekle", default_name, "JSON Dosyası (*.json)"
        )
        if not path:
            return
        data = export_backup(self._conn)
        import json
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        show_toast(self, f"{len(data['queries'])} sorgu JSON olarak kaydedildi.", "success")

    def _on_restore(self) -> None:
        from PySide6.QtWidgets import QFileDialog
        from app.services.backup_service import import_backup
        path, _ = QFileDialog.getOpenFileName(
            self, "Yedeği Yükle", "", "JSON Dosyası (*.json)"
        )
        if not path:
            return
        import json
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            added, skipped, warnings = import_backup(self._conn, data)
        except Exception as exc:
            show_toast(self, f"Yedek yüklenemedi: {exc}", "error")
            return
        self.load_data()
        msg = f"{added} sorgu eklendi, {skipped} atlandı."
        if warnings:
            msg += "  (" + "; ".join(warnings[:2]) + ("…" if len(warnings) > 2 else "") + ")"
        show_toast(self, msg, "success" if added else "warning")

    def _toggle_sidebar(self) -> None:
        sizes = self._splitter.sizes()
        if sizes[0] > 0:
            # Sidebar visible → hide it.
            self._sidebar_sizes = sizes
            self._splitter.setSizes([0, sizes[0] + sizes[1]])
        else:
            # Sidebar hidden → restore.
            self._splitter.setSizes(self._sidebar_sizes)

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
        for stream in self._streams_repo.get_by_query(query.Id):
            self._streams_layout.addWidget(badge(stream.StreamName, "muted"))

    def _show_detail(self, query: Query) -> None:
        self._detail_stack.setCurrentIndex(1)
        self._title.setText(query.Name)
        self._populate_stream_badges(query)
        self._refresh_run_history_label(query)

        # Pre-fill the editable run controls from the saved query (single-line view).
        # Block signals so the param fields are rebuilt once, with their defaults.
        self._query_input.blockSignals(True)
        self._query_input.setText(query.QueryTemplate.replace("\n", " "))
        self._query_input.blockSignals(False)
        self._count_spin.setValue(query.ResultSize)

        from app.data.models.query import TimeRangeType as _TRT
        is_relative = query.TimeRangeType is _TRT.RELATIVE
        self._range_widget.setVisible(is_relative)
        if is_relative:
            self._range_widget.set_seconds(query.TimeRangeRangeSeconds or 3600)

        self._rebuild_params(preserve=False)  # selection → reset to parameter defaults
        self._results.setCurrentIndex(_RESULT_IDLE)
        self._set_grid_search_visible(False)
        self._update_run_enabled()

    def _rebuild_params(self, preserve: bool = True) -> None:
        """Render one labeled input per {param} in the current query text.

        ``preserve`` keeps already-entered values (live editing); when False the
        fields reset to their parameter defaults (used on query selection).
        """
        specs = extract_parameters(self._query_input.text())
        previous = (
            {name: field.text() for name, field in self._param_fields.items()}
            if preserve
            else {}
        )

        while self._params_layout.count():
            item = self._params_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._param_fields = {}

        for name, default in specs:
            field = QLineEdit()
            field.setMinimumWidth(140)
            field.setText(previous.get(name, default))  # keep value, else use default
            field.textChanged.connect(self._update_run_enabled)
            field.returnPressed.connect(self._run_button.click)  # Enter → Çalıştır
            self._param_fields[name] = field
            self._params_layout.addWidget(labeled_field(name, field))
        self._params_layout.addStretch()

        has_params = bool(specs)
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

        # Ad-hoc overrides from the run row (not persisted): edited query text,
        # record count (0 = all), and relative time range if shown.
        from app.data.models.query import TimeRangeType as _TRT
        overrides: dict = dict(
            QueryTemplate=self._query_input.text().strip() or "*",
            ResultSize=self._count_spin.value(),
        )
        if self._selected.TimeRangeType is _TRT.RELATIVE:
            overrides["TimeRangeRangeSeconds"] = self._range_widget.seconds()
        effective = replace(self._selected, **overrides)

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
        row_count = len(result.rows)

        if not result.rows:
            self._set_grid_search_visible(False)
            self._results.setCurrentIndex(_RESULT_EMPTY)
        else:
            model = QStandardItemModel(row_count, len(result.fields), self)
            model.setHorizontalHeaderLabels(result.fields)
            for r, row in enumerate(result.rows):
                for c, field in enumerate(result.fields):
                    item = QStandardItem(str(row.get(field, "")).replace('\\"', '"'))
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
            # Defer fit-mode so viewport has correct dimensions after layout.
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, self._apply_fit_mode)

        # Persist run stats and refresh the label.
        if self._selected and self._selected.Id:
            self._queries_repo.update_run_stats(self._selected.Id, row_count)
            self._selected.LastRunCount = row_count
            from datetime import datetime, timezone
            self._selected.LastRunAt = datetime.now(timezone.utc)
            self._refresh_run_history_label(self._selected)

    def _refresh_run_history_label(self, query: Query) -> None:
        if query.LastRunAt is None:
            self._run_history_label.setVisible(False)
            return
        from datetime import timezone
        local_dt = query.LastRunAt.astimezone().strftime("%d.%m.%Y %H:%M")
        count = query.LastRunCount if query.LastRunCount is not None else 0
        self._run_history_label.setText(
            f"Son çalıştırma: {local_dt}  •  {count} kayıt"
        )
        self._run_history_label.setVisible(True)

    def _on_run_failed(self, message: str, detail: str = "") -> None:
        import logging
        _log = logging.getLogger(__name__)
        _log.error("Query execution failed: %s\n%s", message, detail)

        self._set_grid_search_visible(False)
        self._results.removeWidget(self._error_state)
        self._error_state = self._build_error_state(message, detail)
        self._results.insertWidget(_RESULT_ERROR, self._error_state)
        self._results.setCurrentIndex(_RESULT_ERROR)

    def _build_error_state(self, message: str, detail: str) -> QWidget:
        from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(Spacing.SM)

        icon = QLabel("⚠")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("font-size: 32px;")

        title = QLabel("Sorgu çalıştırılamadı")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setProperty("class", "empty-state-title")

        msg = QLabel(message)
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setWordWrap(True)
        msg.setProperty("class", "empty-state-subtitle")
        msg.setMaximumWidth(480)

        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addWidget(msg)

        if detail:
            btn_row = QHBoxLayout()
            btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
            detail_btn = secondary_button("Hata Detayı")
            detail_btn.setToolTip("Hatanın teknik detaylarını göster ve kopyala")
            detail_btn.clicked.connect(lambda: self._show_error_detail(message, detail))
            btn_row.addWidget(detail_btn)
            layout.addLayout(btn_row)

        return container

    def _show_error_detail(self, message: str, detail: str) -> None:
        from PySide6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QDialogButtonBox
        )
        from PySide6.QtGui import QClipboard
        dlg = QDialog(self.window())
        dlg.setWindowTitle("Hata Detayı")
        dlg.setMinimumSize(600, 380)
        layout = QVBoxLayout(dlg)
        layout.setSpacing(Spacing.SM)

        summary = QLabel(message)
        summary.setWordWrap(True)
        summary.setProperty("class", "error-text")
        layout.addWidget(summary)

        text_area = QPlainTextEdit()
        text_area.setPlainText(detail)
        text_area.setReadOnly(True)
        text_area.setProperty("mono", "true")
        layout.addWidget(text_area, 1)

        btn_box = QDialogButtonBox()
        copy_btn = btn_box.addButton("Kopyala", QDialogButtonBox.ButtonRole.ActionRole)
        close_btn = btn_box.addButton("Kapat", QDialogButtonBox.ButtonRole.RejectRole)
        copy_btn.clicked.connect(
            lambda: QApplication.clipboard().setText(f"{message}\n\n{detail}")
        )
        close_btn.clicked.connect(dlg.reject)
        layout.addWidget(btn_box)

        dlg.exec()

    def _set_grid_search_visible(self, visible: bool) -> None:
        self._grid_search.blockSignals(True)
        self._grid_search.clear()
        self._grid_search.blockSignals(False)
        self._highlight_delegate.set_pattern(None)
        self._bottom_bar.setVisible(visible)
        self._top_bar.setVisible(visible)
        if visible:
            # Always reset to fit mode when new results arrive.
            self._grid_expanded = False
            self._layout_toggle_btn.setText("⇔  Genişlet")
            self._apply_fit_mode()

    def _apply_fit_mode(self) -> None:
        """Proportional column widths + word wrap + auto row height."""
        hdr = self._table.horizontalHeader()
        src = self._proxy.sourceModel()
        if src is None:
            return
        col_count = src.columnCount()
        if col_count == 0:
            return

        self._highlight_delegate.set_wrap(True)
        self._table.setWordWrap(True)
        self._table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Measure content: header text + sample rows (up to 50) for each column.
        fm = self._table.fontMetrics()
        sample_rows = min(self._proxy.rowCount(), 50)
        widths = []
        for c in range(col_count):
            header_text = src.horizontalHeaderItem(c).text() if src.horizontalHeaderItem(c) else ""
            w = fm.horizontalAdvance(header_text) + Spacing.MD * 2
            for r in range(sample_rows):
                cell = str(self._proxy.index(r, c).data() or "")
                # Cap single-cell contribution so one long value doesn't dominate.
                cw = min(fm.horizontalAdvance(cell) + Spacing.MD * 2, 300)
                w = max(w, cw)
            widths.append(max(w, 60))

        total_content = sum(widths)
        available = self._table.viewport().width()
        if available < 50:
            available = self._table.width() - 20

        for c in range(col_count):
            hdr.setSectionResizeMode(c, hdr.ResizeMode.Fixed)
            col_w = max(60, int(available * widths[c] / total_content))
            hdr.resizeSection(c, col_w)

        hdr.setStretchLastSection(True)
        self._table.resizeRowsToContents()

    def _apply_expand_mode(self) -> None:
        """Content-sized columns + single line + horizontal scroll."""
        hdr = self._table.horizontalHeader()
        src = self._proxy.sourceModel()
        if src is None:
            return

        self._highlight_delegate.set_wrap(False)
        self._table.setWordWrap(False)
        self._table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        hdr.setStretchLastSection(False)

        col_count = src.columnCount()
        for c in range(col_count):
            hdr.setSectionResizeMode(c, hdr.ResizeMode.ResizeToContents)

        self._table.resizeRowsToContents()

    def _toggle_grid_layout(self) -> None:
        self._grid_expanded = not self._grid_expanded
        if self._grid_expanded:
            self._layout_toggle_btn.setText("⊟  Sığdır")
            self._layout_toggle_btn.setToolTip("Kolonları ekrana sığdır ve metni kaydır")
            self._apply_expand_mode()
        else:
            self._layout_toggle_btn.setText("⇔  Genişlet")
            self._layout_toggle_btn.setToolTip("Kolonları yatay kaydırmalı tam genişliğe al")
            self._apply_fit_mode()

    def _highlight_matches(self) -> None:
        """Update the highlight pattern as the user types (substring + wildcards)."""
        self._highlight_delegate.set_pattern(compile_search(self._grid_search.text()))
        self._table.viewport().update()

    # ── export ──────────────────────────────────────────────────────────────
    def _grid_data(self) -> tuple[list[str], list[list[str]]]:
        """Return (headers, rows) from the current proxy model in display order."""
        src = self._proxy.sourceModel()
        if src is None:
            return [], []
        col_count = src.columnCount()
        headers = [src.horizontalHeaderItem(c).text() for c in range(col_count)]
        rows = []
        for pr in range(self._proxy.rowCount()):
            rows.append([
                self._proxy.index(pr, c).data() or "" for c in range(col_count)
            ])
        return headers, rows

    def _export_filename(self, ext: str) -> str | None:
        from PySide6.QtWidgets import QFileDialog
        name = (self._selected.Name if self._selected else "sorgu_sonuclari")
        name = name.replace(" ", "_")
        path, _ = QFileDialog.getSaveFileName(
            self, "Dışa Aktar", f"{name}.{ext}",
            f"{'CSV Dosyası' if ext=='csv' else 'Excel Dosyası'} (*.{ext})"
        )
        return path or None

    def _on_export_csv(self) -> None:
        path = self._export_filename("csv")
        if not path:
            return
        import csv
        headers, rows = self._grid_data()
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(headers)
            w.writerows(rows)
        show_toast(self, f"{len(rows)} kayıt CSV olarak kaydedildi.", "success")

    def _on_export_xlsx(self) -> None:
        path = self._export_filename("xlsx")
        if not path:
            return
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment
        except ImportError:
            show_toast(self, "openpyxl kurulu değil: pip install openpyxl", "error")
            return
        headers, rows = self._grid_data()
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = (self._selected.Name[:31] if self._selected else "Sonuçlar")
        header_font = Font(bold=True, color="F0F2FF")
        header_fill = PatternFill("solid", fgColor="1A1D27")
        for c, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=c, value=h)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")
            ws.column_dimensions[cell.column_letter].width = max(12, len(h) + 4)
        for r, row in enumerate(rows, 2):
            for c, val in enumerate(row, 1):
                ws.cell(row=r, column=c, value=val)
        ws.freeze_panes = "A2"
        wb.save(path)
        show_toast(self, f"{len(rows)} kayıt Excel olarak kaydedildi.", "success")

    def _on_run_finished(self) -> None:
        self._worker = None
        self._update_run_enabled()
