"""
Regression tests for Quick Report workspace mode.
"""

from __future__ import annotations

import uuid

import pytest

from core.project_access import ProjectAccessError, require_real_project_uuid
from core.workspace_context import (
    QUICK_REPORT_JSON_FOLDER,
    QUICK_REPORT_PROJECT_ID,
    QUICK_REPORT_STORAGE_SCOPE,
    is_quick_report,
    quick_report_storage_scope,
    resolve_storage_scope,
)
from core.current_user import CurrentUser
from repositories.supabase_timeline_repository import SupabaseTimelineRepository
from repositories.timeline_repository import TimelineRepository
from services.auth_service import AuthService
from services.document_service import DocumentService
from services.export_service import ExportService
from services.report_service import ReportService
from services.timeline_service import TimelineService
from services.workspace_service import WorkspaceService
from storage.file_store import FileStore
from tests.conftest import MockUpload, TEST_USER, TEST_USER_ID


class TrackingQuery:
    def __init__(self, tracker: "TrackingSupabaseClient", table_name: str) -> None:
        self._tracker = tracker
        self._table_name = table_name
        self._pending: dict[str, object] = {}

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, column: str, value: object):
        self._pending[column] = value
        return self

    def order(self, *_args, **_kwargs):
        return self

    def maybe_single(self):
        return self

    def insert(self, _row):
        return self

    def upsert(self, _row, **_kwargs):
        return self

    def delete(self):
        return self

    def execute(self):
        if self._table_name == "timeline_events" and "project_id" in self._pending:
            self._tracker.project_id_filters.append(self._pending["project_id"])
        if self._table_name == "quick_report_timeline_events":
            self._tracker.quick_report_timeline_queries += 1

        class Response:
            data: list[dict] = []
            error = None

        return Response()


class FakeStorageBucket:
    def list(self, _prefix: str):
        return []

    def upload(self, *_args, **_kwargs):
        return None

    def download(self, _key: str) -> bytes:
        return b""

    def remove(self, _keys):
        return None


class FakeStorageAPI:
    def from_(self, _bucket: str) -> FakeStorageBucket:
        return FakeStorageBucket()


class TrackingSupabaseClient:
    def __init__(self) -> None:
        self.project_id_filters: list[object] = []
        self.quick_report_timeline_queries = 0
        self.storage = FakeStorageAPI()

    def table(self, name: str) -> TrackingQuery:
        return TrackingQuery(self, name)


def _enable_supabase_backends(monkeypatch, client: TrackingSupabaseClient) -> None:
    monkeypatch.setattr("config.use_database", lambda: True)
    monkeypatch.setattr("config.use_supabase_storage", lambda: True)
    monkeypatch.setattr("config.is_supabase_configured", lambda: True)
    for target in (
        "core.database.get_database_client",
        "repositories.supabase_quick_report_timeline_repository.get_database_client",
        "repositories.supabase_timeline_repository.get_database_client",
        "repositories.supabase_project_repository.get_database_client",
    ):
        monkeypatch.setattr(target, lambda *, access_token=None: client)


def test_is_quick_report_recognizes_workspace_sentinel():
    assert is_quick_report(QUICK_REPORT_PROJECT_ID) is True
    assert is_quick_report(str(uuid.uuid4())) is False
    assert is_quick_report(None) is False


def test_quick_report_storage_scope_uses_legacy_folder_in_json_mode(monkeypatch):
    monkeypatch.setattr("config.use_supabase_storage", lambda: False)

    assert quick_report_storage_scope() == QUICK_REPORT_JSON_FOLDER
    assert resolve_storage_scope(QUICK_REPORT_PROJECT_ID) == QUICK_REPORT_JSON_FOLDER


def test_quick_report_storage_scope_uses_dedicated_scope_in_supabase_mode(monkeypatch):
    monkeypatch.setattr("config.use_supabase_storage", lambda: True)

    assert quick_report_storage_scope() == QUICK_REPORT_STORAGE_SCOPE
    assert resolve_storage_scope(QUICK_REPORT_PROJECT_ID) == QUICK_REPORT_STORAGE_SCOPE


def test_require_real_project_uuid_rejects_quick_report():
    with pytest.raises(ProjectAccessError, match="not a database project"):
        require_real_project_uuid(QUICK_REPORT_PROJECT_ID)


def test_supabase_timeline_repository_rejects_quick_report(monkeypatch):
    client = TrackingSupabaseClient()
    monkeypatch.setattr(
        "repositories.supabase_timeline_repository.get_database_client",
        lambda *, access_token=None: client,
    )

    with pytest.raises(ProjectAccessError, match="not a database project"):
        SupabaseTimelineRepository(QUICK_REPORT_PROJECT_ID, user_id=TEST_USER_ID)


def test_json_quick_report_workspace_round_trip(isolated_env, tmp_path, monkeypatch):
    monkeypatch.setattr("config.use_database", lambda: False)
    monkeypatch.setattr("config.use_supabase_storage", lambda: False)
    monkeypatch.setattr(
        "services.lockout_service.LockoutService._JSON_PATH",
        tmp_path / "lockouts.json",
    )

    document_service = DocumentService()
    document_service.save_document(
        QUICK_REPORT_PROJECT_ID,
        MockUpload("notes.txt", b"Quick report notes."),
    )
    ReportService.save_report(
        QUICK_REPORT_PROJECT_ID,
        "Quick Status",
        "# Quick Status\n\nAll good.",
    )

    workspace = WorkspaceService().load_workspace(QUICK_REPORT_PROJECT_ID)

    assert workspace.id == QUICK_REPORT_PROJECT_ID
    assert workspace.name == "Quick Report"
    assert len(workspace.documents) == 1
    assert len(workspace.reports) == 1
    assert isinstance(workspace.timeline, list)
    assert len(workspace.exports) == 0

    quick_root = isolated_env["user_root"].parent / TEST_USER_ID / "projects" / QUICK_REPORT_JSON_FOLDER
    assert (quick_root / "documents" / "notes.txt").is_file()


def test_supabase_quick_report_workspace_never_queries_project_uuid(
    isolated_env,
    monkeypatch,
):
    client = TrackingSupabaseClient()
    _enable_supabase_backends(monkeypatch, client)

    workspace = WorkspaceService().load_workspace(QUICK_REPORT_PROJECT_ID)

    assert workspace.id == QUICK_REPORT_PROJECT_ID
    assert workspace.documents == []
    assert workspace.reports == []
    assert workspace.exports == []
    assert client.quick_report_timeline_queries >= 1
    assert QUICK_REPORT_PROJECT_ID not in client.project_id_filters
    assert QUICK_REPORT_STORAGE_SCOPE not in client.project_id_filters


def test_supabase_timeline_service_routes_quick_report_to_user_scoped_table(monkeypatch):
    client = TrackingSupabaseClient()
    _enable_supabase_backends(monkeypatch, client)

    events = TimelineService().get_timeline(QUICK_REPORT_PROJECT_ID)

    assert events == []
    assert client.quick_report_timeline_queries >= 1
    assert client.project_id_filters == []


def test_supabase_file_store_uses_quick_report_scope_not_sentinel(monkeypatch):
    monkeypatch.setattr("config.use_supabase_storage", lambda: True)
    monkeypatch.setattr("config.is_supabase_configured", lambda: True)

    captured_prefixes: list[str] = []

    class FakeBucket:
        def list(self, prefix: str):
            captured_prefixes.append(prefix)
            return []

        def upload(self, *_args, **_kwargs):
            return None

    class FakeStorage:
        def from_(self, _bucket: str) -> FakeBucket:
            return FakeBucket()

    class FakeClient:
        storage = FakeStorage()

    monkeypatch.setattr(
        "core.database.get_database_client",
        lambda *, access_token=None: FakeClient(),
    )

    store = FileStore(CurrentUser.from_user(TEST_USER))
    store.list_files(QUICK_REPORT_PROJECT_ID, "documents")

    assert captured_prefixes == [f"{TEST_USER_ID}/{QUICK_REPORT_STORAGE_SCOPE}/documents/"]


def test_local_file_store_keeps_legacy_quick_report_folder(isolated_env):
    store = FileStore(CurrentUser.from_user(TEST_USER))
    storage_path = store.write(
        QUICK_REPORT_PROJECT_ID,
        "documents",
        "legacy.txt",
        b"legacy quick report",
    )

    quick_root = isolated_env["user_root"].parent / TEST_USER_ID / "projects" / QUICK_REPORT_JSON_FOLDER
    assert (quick_root / "documents" / "legacy.txt").is_file()
    assert QUICK_REPORT_JSON_FOLDER in storage_path.replace("\\", "/")


def test_supabase_quick_report_documents_reports_exports_use_storage_scope(
    isolated_env,
    monkeypatch,
):
    monkeypatch.setattr("config.use_supabase_storage", lambda: True)
    monkeypatch.setattr("config.is_supabase_configured", lambda: True)
    monkeypatch.setattr("config.use_database", lambda: False)

    uploaded_keys: list[str] = []

    class FakeBucket:
        def list(self, prefix: str):
            if prefix.endswith("/reports/"):
                return [{"name": "quick_export.md"}]
            if prefix.endswith("/exports/"):
                return [{"name": "quick_export.md"}]
            return []

        def upload(self, key, _content, **_kwargs):
            uploaded_keys.append(key)

        def download(self, key: str) -> bytes:
            return b"# Report\n"

        def remove(self, _keys):
            return None

    class FakeStorage:
        def from_(self, _bucket: str) -> FakeBucket:
            return FakeBucket()

    class FakeClient:
        storage = FakeStorage()

    monkeypatch.setattr(
        "core.database.get_database_client",
        lambda *, access_token=None: FakeClient(),
    )

    document_service = DocumentService()
    document_service.save_document(
        QUICK_REPORT_PROJECT_ID,
        MockUpload("input.txt", b"input"),
    )
    ReportService.save_report(
        QUICK_REPORT_PROJECT_ID,
        "Quick Export",
        "# Quick Export\n",
    )
    ExportService().export_markdown(
        project_id=QUICK_REPORT_PROJECT_ID,
        report_name="Quick Export",
        report_text="# Quick Export\n",
    )

    reports = ReportService.get_reports(QUICK_REPORT_PROJECT_ID)
    exports = ExportService().get_exports(QUICK_REPORT_PROJECT_ID)

    assert reports
    assert exports
    assert all(
        f"/{QUICK_REPORT_STORAGE_SCOPE}/" in key.replace("\\", "/")
        for key in uploaded_keys
    )
    assert all(
        QUICK_REPORT_PROJECT_ID not in key
        for key in uploaded_keys
    )


def test_post_login_workspace_load_with_supabase_quick_report(monkeypatch, isolated_env):
    client = TrackingSupabaseClient()
    _enable_supabase_backends(monkeypatch, client)
    monkeypatch.setattr("config.auth_dev_bypass_enabled", lambda: False)
    monkeypatch.setattr("services.auth_service.is_supabase_configured", lambda: True)

    class FakeUser:
        def model_dump(self):
            return {
                "id": TEST_USER_ID,
                "email": TEST_USER.email,
                "email_confirmed_at": "2026-01-01T00:00:00Z",
                "user_metadata": {"full_name": TEST_USER.full_name},
            }

    class FakeSession:
        access_token = "access"
        refresh_token = "refresh"

    class FakeResponse:
        session = FakeSession()
        user = FakeUser()

    class FakeAuth:
        def sign_in_with_password(self, _credentials):
            return FakeResponse()

    class FakeLockout:
        def check_allowed(self, _email):
            return None

        def record_failure(self, _email):
            return None

        def record_success(self, _email):
            return None

    monkeypatch.setattr("services.lockout_service.LockoutService", lambda: FakeLockout())
    monkeypatch.setattr(
        "core.database.get_service_role_client",
        lambda: TrackingSupabaseClient(),
    )

    auth_service = object.__new__(AuthService)
    auth_service._client = type("Client", (), {"auth": FakeAuth()})()

    session = auth_service.sign_in(TEST_USER.email, "correct-password")
    assert session.user.id == TEST_USER_ID

    workspace = WorkspaceService().load_workspace(QUICK_REPORT_PROJECT_ID)
    assert workspace.name == "Quick Report"
    assert QUICK_REPORT_PROJECT_ID not in client.project_id_filters


def test_timeline_repository_selects_quick_report_backend(monkeypatch):
    client = TrackingSupabaseClient()
    _enable_supabase_backends(monkeypatch, client)

    repository = TimelineRepository(QUICK_REPORT_PROJECT_ID)

    repository.load()

    assert client.quick_report_timeline_queries == 1
    assert client.project_id_filters == []
