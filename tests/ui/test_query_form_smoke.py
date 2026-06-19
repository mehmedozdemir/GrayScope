"""Offscreen construction smoke test for QueryFormDialog.

Guards against regressions where the dialog fails to open (e.g. a NameError in
``_build_fields``). Uses a stub stream service so no network/encryption is needed.
"""
from __future__ import annotations

import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from app.data.models.graylog_profile import GraylogProfile
from app.data.models.query import Query, TimeRangeType
from app.data.models.query_folder import QueryFolder
from app.ui.pages.query_form_dialog import QueryFormDialog


class _StubStreamService:
    def get_streams(self, profile, force_refresh=False):
        return []


@pytest.fixture(scope="module")
def qapp():
    from app.ui.stylesheets import apply_theme

    app = QApplication.instance() or QApplication([])
    apply_theme(app, "dark")
    return app


def _profile() -> GraylogProfile:
    return GraylogProfile(Id=1, Name="Ana", BaseUrl="https://x/api", TokenEncrypted="enc")


def _wait(dialog) -> None:
    if dialog._worker is not None:
        dialog._worker.wait(5000)


def test_new_query_form_opens(qapp):
    folders = [QueryFolder(Id=1, Name="Şehir"), QueryFolder(Id=2, Name="HTTP", ParentId=1)]
    dialog = QueryFormDialog(
        None, [_profile()], _StubStreamService(), folders=folders, default_folder_id=2
    )
    assert dialog._folder_combo.currentData() == 2  # default folder preselected
    _wait(dialog)


def test_edit_query_form_opens_with_folder(qapp):
    folders = [QueryFolder(Id=1, Name="Şehir")]
    query = Query(
        Id=9,
        Name="Q",
        GraylogProfileId=1,
        QueryTemplate="*",
        TimeRangeType=TimeRangeType.RELATIVE,
        TimeRangeRangeSeconds=60,
        FieldsJson=json.dumps(["timestamp"]),
        FolderId=1,
    )
    dialog = QueryFormDialog(None, [_profile()], _StubStreamService(), query=query, folders=folders)
    assert dialog.result_query().FolderId == 1
    _wait(dialog)
