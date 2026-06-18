"""Sorgular page — master-detail list + query execution
(DESIGN_SYSTEM.md §3, PROJECT_PLAN.md §5.4)."""
from __future__ import annotations

import re
import sqlite3
from dataclasses import replace

from PySide6.QtCore import QSize, QSortFilterProxyModel, Qt, QThread, Signal
from PySide6.QtGui import QColor, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QStyledItemDelegate,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.core.exceptions import GrayScopeError
from app.data.models.customer import Customer
from app.data.models.query import Query
from app.data.repositories.customer_repository import CustomerRepository
from app.data.repositories.graylog_profile_repository import GraylogProfileRepository
from app.data.repositories.query_repository import QueryRepository
from app.data.repositories.query_stream_repository import QueryStreamRepository
from app.integrations.graylog.exceptions import GraylogError
from app.services.query_execution_service import ExecutionResult, execute_query
from app.services.stream_catalog_service import StreamCatalogService
from app.ui.components.buttons import icon_button, primary_button
from app.ui.components.dialogs import ConfirmDialog
from app.ui.components.feedback import EmptyState, badge, show_toast
from app.ui.components.inputs import SearchInput
from app.ui.pages.query_form_dialog import QueryFormDialog
from app.ui.theme import Colors, Spacing

# Result stack indices.
_RESULT_IDLE, _RESULT_LOADING, _RESULT_GRID, _RESULT_EMPTY, _RESULT_ERROR = range(5)


class _ExecutionWorker(QThread):
    succeeded = Signal(object)  # ExecutionResult
    failed = Signal(str)

    def __init__(self, profile, query, stream_ids, customer, parent=None) -> None:
        super().__init__(parent)
        self._args = (profile, query, stream_ids, customer)

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
        self._bg = QColor(Colors.WARNING)
        self._fg = QColor(Colors.BG_BASE)

    def set_pattern(self, pattern) -> None:
        self._pattern = pattern

    def paint(self, painter, option, index) -> None:
        text = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
        if self._pattern is not None and self._pattern.search(text):
            painter.save()
            painter.fillRect(option.rect, self._bg)
            painter.setPen(self._fg)
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
        self._queries_repo = QueryRepository(conn)
        self._profiles_repo = GraylogProfileRepository(conn)
        self._streams_repo = QueryStreamRepository(conn)
        self._customers_repo = CustomerRepository(conn)
        self._stream_service = stream_service

        self._queries: list[Query] = []
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
        panel = QWidget()
        panel.setMinimumWidth(340)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        layout.setSpacing(Spacing.SM)

        self._search = SearchInput("Sorgu ara")
        self._new_button = primary_button("+ Yeni Sorgu")
        layout.addWidget(self._search)
        layout.addWidget(self._new_button)

        self._list_stack = QStackedWidget()
        self._list = QListWidget()
        self._list_empty = EmptyState(
            "\U0001F50E", "Henüz sorgu yok", "Yeni bir sorgu oluşturarak başlayın."
        )
        self._list_stack.addWidget(self._list)
        self._list_stack.addWidget(self._list_empty)
        layout.addWidget(self._list_stack, 1)
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
        layout.setContentsMargins(Spacing.XL, Spacing.XL, Spacing.XL, Spacing.XL)
        layout.setSpacing(Spacing.LG)

        header = QHBoxLayout()
        self._title = QLabel()
        self._title.setProperty("class", "page-title")
        self._edit_button = icon_button("✎", "Düzenle")
        self._delete_button = icon_button("🗑", "Sil")
        header.addWidget(self._title)
        header.addStretch()
        header.addWidget(self._edit_button)
        header.addWidget(self._delete_button)
        layout.addLayout(header)

        # Run panel — a single card grouping parameters + run controls, set apart
        # from the result grid below. A thin separator divides the (optional)
        # parameter area from the query/run row.
        self._run_panel = QFrame()
        self._run_panel.setProperty("class", "card")
        panel_layout = QVBoxLayout(self._run_panel)
        panel_layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        panel_layout.setSpacing(Spacing.MD)

        # Parameters area — shown only for parametric queries.
        self._customer_row = QWidget()
        customer_layout = QHBoxLayout(self._customer_row)
        customer_layout.setContentsMargins(0, 0, 0, 0)
        customer_layout.setSpacing(Spacing.SM)
        params_label = QLabel("Parametreler")
        params_label.setProperty("class", "section-header")
        self._customer_label = QLabel("Şehir / Müşteri:")
        self._customer_label.setProperty("class", "field-label")
        self._customer_combo = QComboBox()
        self._customer_combo.setMinimumWidth(240)
        # Non-editable: clicking opens the full city list; typing jumps to a match.
        customer_layout.addWidget(params_label)
        customer_layout.addSpacing(Spacing.MD)
        customer_layout.addWidget(self._customer_label)
        customer_layout.addWidget(self._customer_combo)
        customer_layout.addStretch()
        panel_layout.addWidget(self._customer_row)

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
        self._search.textChanged.connect(self._render_list)
        self._new_button.clicked.connect(self._on_new)
        self._list.currentItemChanged.connect(self._on_select)
        self._edit_button.clicked.connect(self._on_edit)
        self._delete_button.clicked.connect(self._on_delete)
        self._customer_combo.currentIndexChanged.connect(self._update_run_enabled)
        self._run_button.clicked.connect(self._on_run)

    def load_data(self) -> None:
        self._queries = self._queries_repo.get_all()
        self._profiles_by_id = {p.Id: p for p in self._profiles_repo.get_all()}
        self._render_list()

    def _render_list(self) -> None:
        term = self._search.text().strip().lower()
        visible = [q for q in self._queries if term in q.Name.lower()] if term else self._queries
        self._list_stack.setCurrentIndex(1 if not self._queries else 0)

        self._list.blockSignals(True)
        self._list.clear()
        for query in visible:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, query.Id)
            self._list.addItem(item)
            row = self._list_row(query)
            self._list.setItemWidget(item, row)
            # Allow up to ~2 wrapped lines; longer names clip and reveal via tooltip.
            hint = row.sizeHint()
            item.setSizeHint(QSize(hint.width(), min(hint.height(), 72)))
        self._list.blockSignals(False)

    def _list_row(self, query: Query) -> QWidget:
        row = QWidget()
        row.setProperty("class", "list-row")
        layout = QVBoxLayout(row)
        layout.setContentsMargins(Spacing.SM, Spacing.SM, Spacing.SM, Spacing.SM)
        layout.setSpacing(Spacing.XS)
        name = QLabel(query.Name)
        name.setProperty("class", "query-name")
        name.setWordWrap(True)
        name.setToolTip(query.Name)
        profile = self._profiles_by_id.get(query.GraylogProfileId)
        profile_badge = badge(profile.Name if profile else "—", "muted")
        badge_row = QHBoxLayout()
        badge_row.setContentsMargins(0, 0, 0, 0)
        badge_row.addWidget(profile_badge)
        badge_row.addStretch()
        layout.addWidget(name)
        layout.addLayout(badge_row)
        return row

    def _on_select(self, current: QListWidgetItem | None, _previous=None) -> None:
        if current is None:
            self._selected = None
            self._detail_stack.setCurrentIndex(0)
            return
        query_id = current.data(Qt.ItemDataRole.UserRole)
        self._selected = next((q for q in self._queries if q.Id == query_id), None)
        if self._selected is None:
            self._detail_stack.setCurrentIndex(0)
            return
        self._show_detail(self._selected)

    def _show_detail(self, query: Query) -> None:
        self._detail_stack.setCurrentIndex(1)
        self._title.setText(query.Name)

        # Pre-fill the editable run controls from the saved query (single-line view).
        self._query_input.setText(query.QueryTemplate.replace("\n", " "))
        self._count_spin.setValue(query.ResultSize)

        parametric = query.UsesCustomerParameter
        self._customer_row.setVisible(parametric)
        self._param_separator.setVisible(parametric)
        if parametric:
            self._populate_customers()
        self._results.setCurrentIndex(_RESULT_IDLE)
        self._set_grid_search_visible(False)
        self._update_run_enabled()

    def _populate_customers(self) -> None:
        self._customer_combo.blockSignals(True)
        self._customer_combo.clear()
        self._customer_combo.addItem("Seç…", None)
        for customer in self._customers_repo.get_all(only_active=True):
            self._customer_combo.addItem(f"{customer.NetworkId} — {customer.Name}", customer)
        self._customer_combo.setCurrentIndex(0)
        self._customer_combo.blockSignals(False)

    def _update_run_enabled(self) -> None:
        if self._selected is None:
            return
        if self._selected.UsesCustomerParameter and self._customer_combo.currentData() is None:
            self._run_button.setEnabled(False)
            self._run_button.setToolTip("Önce bir müşteri/şehir seçin")
        else:
            self._run_button.setEnabled(True)
            self._run_button.setToolTip("")

    # ── CRUD ─────────────────────────────────────────────────────────────
    def _active_profiles(self):
        return self._profiles_repo.get_all(only_active=True)

    def _on_new(self) -> None:
        profiles = self._active_profiles()
        if not profiles:
            show_toast(self, "Önce bir Graylog profili ekleyin.", "warning")
            return
        dialog = QueryFormDialog(self, profiles, self._stream_service)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        created = self._queries_repo.create(dialog.result_query())
        self._streams_repo.replace_for_query(created.Id, dialog.selected_streams())
        show_toast(self, "Sorgu kaydedildi.", "success")
        self.load_data()

    def _on_edit(self) -> None:
        if self._selected is None:
            return
        profiles = self._active_profiles()
        existing = self._streams_repo.get_by_query(self._selected.Id)
        dialog = QueryFormDialog(self, profiles, self._stream_service, self._selected, existing)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        updated = self._queries_repo.update(dialog.result_query())
        self._streams_repo.replace_for_query(updated.Id, dialog.selected_streams())
        show_toast(self, "Sorgu güncellendi.", "success")
        self.load_data()
        self._reselect(updated.Id)

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
        for i in range(self._list.count()):
            if self._list.item(i).data(Qt.ItemDataRole.UserRole) == query_id:
                self._list.setCurrentRow(i)
                return

    # ── execution ─────────────────────────────────────────────────────────
    def _on_run(self) -> None:
        if self._selected is None or self._worker is not None:
            return
        profile = self._profiles_by_id.get(self._selected.GraylogProfileId)
        if profile is None:
            show_toast(self, "Bu sorgunun profili bulunamadı.", "error")
            return
        stream_ids = [qs.StreamId for qs in self._streams_repo.get_by_query(self._selected.Id)]
        customer: Customer | None = self._customer_combo.currentData()

        # Ad-hoc overrides from the run row (not persisted): edited query text and
        # record count (0 = all). Empty text falls back to "*" (match all).
        effective = replace(
            self._selected,
            QueryTemplate=self._query_input.text().strip() or "*",
            ResultSize=self._count_spin.value(),
        )

        self._results.setCurrentIndex(_RESULT_LOADING)
        self._run_button.setEnabled(False)

        worker = _ExecutionWorker(profile, effective, stream_ids, customer, self)
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
