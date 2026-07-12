"""
Multi-tenant isolation security tests.

Creates two users (A and B) with separate workspaces and verifies that
User B cannot read, list, search, export, or infer any of User A's data.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest

from core.current_user import CurrentUser, bind_current_user
from core.tenant_session import (
    TENANT_DATA_KEYS,
    TENANT_USER_KEY,
    clear_tenant_session,
    ensure_tenant_context,
)
from models.user import User
from repositories.project_repository import ProjectRepository
from services.document_service import DocumentService
from services.export_service import ExportService
from services.project_service import ProjectService
from services.report_service import ReportService
from services.search_service import SearchService
from services.workspace_service import WorkspaceService
from storage.file_store import FileStore
from tests.conftest import MockUpload

USER_A_ID = "00000000-0000-4000-8000-000000000010"
USER_B_ID = "00000000-0000-4000-8000-000000000011"

USER_A = User(
    id=USER_A_ID,
    email="user-a@example.com",
    full_name="User A",
    email_verified=True,
)
USER_B = User(
    id=USER_B_ID,
    email="user-b@example.com",
    full_name="User B",
    email_verified=True,
)


class _SessionState(dict):
    """Minimal Streamlit session_state stand-in for unit tests."""

    def get(self, key, default=None):
        return super().get(key, default)

    def pop(self, key, default=None):
        return super().pop(key, default)


@pytest.fixture
def two_user_env(tmp_path, monkeypatch):
    """Isolate per-user storage for User A and User B under tmp_path."""

    monkeypatch.setattr("config.use_database", lambda: False)

    def user_data_root(user_id: str) -> Path:
        return tmp_path / "users" / user_id

    monkeypatch.setattr(
        "core.user_paths.get_user_data_root",
        lambda user_id: user_data_root(user_id),
    )
    monkeypatch.setattr(
        "core.user_paths.get_user_projects_json",
        lambda user_id: user_data_root(user_id) / "projects.json",
    )
    monkeypatch.setattr(
        "core.user_paths.get_user_projects_root",
        lambda user_id: user_data_root(user_id) / "projects",
    )
    monkeypatch.setattr(
        "core.user_paths.get_users_root",
        lambda: tmp_path / "users",
    )

    return {"root": tmp_path / "users"}


@pytest.fixture
def user_a_data(two_user_env, monkeypatch):
    """Seed User A with a project, document, and report."""

    _as_user(monkeypatch, USER_A)

    project_service = ProjectService()
    document_service = DocumentService()

    project = project_service.create_project("User A Confidential")
    project_id = project["id"]

    document_service.save_document(
        project_id,
        MockUpload("secret_board_pack.txt", b"User A secret revenue figure: 42M"),
    )

    report = ReportService.save_report(
        project_id,
        "Executive Summary",
        report_text="# User A Secret Report\nConfidential findings.",
        source_documents=["secret_board_pack.txt"],
    )

    return {
        "project_id": project_id,
        "project_name": project["name"],
        "document_name": "secret_board_pack.txt",
        "report": report,
    }


def _as_user(monkeypatch, user: User) -> None:
    bind_current_user(user)
    monkeypatch.setattr("core.auth.get_current_user", lambda: user)


@pytest.fixture
def as_user_a(monkeypatch):
    _as_user(monkeypatch, USER_A)
    return USER_A


@pytest.fixture
def as_user_b(monkeypatch):
    _as_user(monkeypatch, USER_B)
    return USER_B


def test_user_b_cannot_list_user_a_projects(
    two_user_env,
    user_a_data,
    as_user_b,
):
    service = ProjectService()
    projects = service.get_projects()

    assert projects == []
    assert service.project_exists(user_a_data["project_id"]) is False

    with pytest.raises(ValueError, match="Project not found"):
        service.get_project(user_a_data["project_id"])


def test_user_b_cannot_read_user_a_documents(
    two_user_env,
    user_a_data,
    as_user_b,
):
    documents = DocumentService().get_documents(
        user_a_data["project_id"],
    )

    assert documents == []


def test_user_b_cannot_read_user_a_reports(
    two_user_env,
    user_a_data,
    as_user_b,
):
    reports = ReportService.get_reports(user_a_data["project_id"])

    assert reports == []


def test_user_b_cannot_load_user_a_report_by_path(
    two_user_env,
    user_a_data,
    as_user_b,
):
    foreign_path = user_a_data["report"]["path"]

    with pytest.raises(PermissionError):
        FileStore(CurrentUser.from_user(USER_B)).read_text(foreign_path)

    with pytest.raises(PermissionError):
        ReportService.load_report(foreign_path)


def test_user_b_cannot_load_user_a_report_data(
    two_user_env,
    user_a_data,
    as_user_b,
):
    with pytest.raises((FileNotFoundError, PermissionError)):
        ReportService.load_report_data(
            user_a_data["project_id"],
            user_a_data["report"]["filename"],
        )


def test_file_store_rejects_foreign_storage_key(two_user_env, as_user_b):
    foreign_key = f"{USER_A_ID}/proj-1/reports/secret.md"

    with pytest.raises(PermissionError):
        FileStore(CurrentUser.from_user(USER_B)).read_bytes(foreign_key)


def test_file_store_rejects_foreign_local_path(
    two_user_env,
    user_a_data,
    as_user_b,
):
    foreign_path = user_a_data["report"]["path"]

    with pytest.raises(PermissionError):
        FileStore(CurrentUser.from_user(USER_B)).read_bytes(foreign_path)


def test_search_does_not_find_other_user_data(
    two_user_env,
    user_a_data,
    as_user_b,
):
    search = SearchService(
        project_repository=ProjectRepository(),
    )

    for query in ("Confidential", "secret_board_pack", "User A", "42M"):
        results = search.enterprise_search(query)
        assert results == [], f"User B should not find hits for {query!r}"

    scoped = search.enterprise_search(
        "Confidential",
        project_id=user_a_data["project_id"],
    )
    assert scoped == []


def test_workspace_service_rejects_other_users_project(
    two_user_env,
    user_a_data,
    as_user_b,
):
    with pytest.raises(ValueError, match="Project not found"):
        WorkspaceService().load_workspace(user_a_data["project_id"])


def test_user_b_exports_empty_for_user_a_project(
    two_user_env,
    user_a_data,
    as_user_b,
):
    exports = ExportService().get_exports(user_a_data["project_id"])
    assert exports == []


def test_user_a_data_not_visible_in_user_b_project_list(
    two_user_env,
    user_a_data,
    as_user_b,
):
    own_project = ProjectService().create_project("User B Workspace")
    projects = ProjectService().get_projects()

    assert len(projects) == 1
    assert projects[0]["id"] == own_project["id"]
    assert all(project["id"] != user_a_data["project_id"] for project in projects)


def test_user_a_can_access_own_data(two_user_env, user_a_data, as_user_a):
    project_service = ProjectService()
    project = project_service.get_project(user_a_data["project_id"])

    assert project["name"] == user_a_data["project_name"]

    documents = DocumentService().get_documents(
        user_a_data["project_id"],
    )
    assert len(documents) == 1
    assert documents[0]["filename"] == user_a_data["document_name"]

    reports = ReportService.get_reports(user_a_data["project_id"])
    assert len(reports) == 1

    text = ReportService.load_report_for_project(
        user_a_data["project_id"],
        user_a_data["report"]["filename"],
    )
    assert "User A Secret Report" in text


def test_tenant_session_clears_on_user_switch(monkeypatch):
    state = _SessionState(
        {
            TENANT_USER_KEY: USER_A_ID,
            "projects": [{"id": "leaked-project", "name": "Leaked"}],
            "selected_report": {"path": "/tmp/leaked.md", "name": "Leaked"},
            "draft_report": {"content": "secret"},
            "project_report_documents_abc": ["doc.pdf"],
        }
    )
    monkeypatch.setattr("streamlit.session_state", state)

    ensure_tenant_context(USER_B_ID)

    assert state[TENANT_USER_KEY] == USER_B_ID
    assert "projects" not in state
    assert "selected_report" not in state
    assert "draft_report" not in state
    assert "project_report_documents_abc" not in state


def test_clear_tenant_session_removes_workspace_keys(monkeypatch):
    state = _SessionState({key: f"value-{key}" for key in TENANT_DATA_KEYS})
    state[TENANT_USER_KEY] = USER_A_ID
    state["project_report_documents_xyz"] = ["a.pdf"]
    monkeypatch.setattr("streamlit.session_state", state)

    clear_tenant_session()

    for key in TENANT_DATA_KEYS:
        assert key not in state
    assert TENANT_USER_KEY not in state
    assert "project_report_documents_xyz" not in state


def test_set_active_workspace_rejects_foreign_project(
    two_user_env,
    user_a_data,
    as_user_b,
    monkeypatch,
):
    state = _SessionState()
    monkeypatch.setattr("streamlit.session_state", state)

    from ui.projects import set_active_workspace

    with pytest.raises(ValueError, match="Workspace not found"):
        set_active_workspace(user_a_data["project_id"])
