"""
Release-blocking security isolation tests.

These tests must fail if any code path allows cross-user data access.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest

from core.tenant_session import (
    TENANT_DATA_KEYS,
    TENANT_KEY_PREFIXES,
    TENANT_USER_KEY,
    clear_tenant_session,
    ensure_tenant_context,
)
from core.workspace_context import QUICK_REPORT_PROJECT_ID
from models.user import User
from core.current_user import CurrentUser, bind_current_user, current_user_scope
from services.auth_service import AuthError, AuthService
from services.document_service import DocumentService
from services.email_uniqueness import DUPLICATE_EMAIL_MESSAGE, normalize_email
from services.export_service import ExportService
from services.project_service import ProjectService
from services.report_service import ReportService
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
    def get(self, key, default=None):
        return super().get(key, default)

    def pop(self, key, default=None):
        return super().pop(key, default)


@pytest.fixture
def two_user_env(tmp_path, monkeypatch):
    monkeypatch.setattr("config.use_database", lambda: False)
    monkeypatch.setattr("services.auth_service.AUTH_DEV_BYPASS", False)

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
    monkeypatch.setattr(
        "services.email_uniqueness.EmailUniquenessService._registry_path",
        lambda self: tmp_path / "auth_email_registry.json",
    )

    return {"root": tmp_path / "users"}


def _as_user(monkeypatch, user: User) -> None:
    bind_current_user(user)
    monkeypatch.setattr("core.auth.get_current_user", lambda: user)


@pytest.fixture
def user_a_workspace(two_user_env, monkeypatch):
    _as_user(monkeypatch, USER_A)

    project = ProjectService().create_project("User A Workspace")
    DocumentService().save_document(
        project["id"],
        MockUpload("secret.txt", b"User A secret"),
    )
    report = ReportService.save_report(
        project["id"],
        "Executive Summary",
        report_text="# Secret report",
        source_documents=["secret.txt"],
    )

    quick_doc = DocumentService().save_document(
        QUICK_REPORT_PROJECT_ID,
        MockUpload("quick_secret.txt", b"Quick report secret"),
    )

    return {
        "project_id": project["id"],
        "report": report,
        "quick_document": quick_doc,
    }


@pytest.fixture
def as_user_b(monkeypatch):
    _as_user(monkeypatch, USER_B)
    return USER_B


# --- Authentication ---


def test_duplicate_email_registration_rejected(monkeypatch, isolated_env, tmp_path):
    monkeypatch.setattr("services.auth_service.AUTH_DEV_BYPASS", True)
    monkeypatch.setattr("services.auth_service.is_supabase_configured", lambda: False)
    monkeypatch.setattr(
        "services.email_uniqueness.EmailUniquenessService._registry_path",
        lambda self: tmp_path / "auth_email_registry.json",
    )

    service = AuthService()
    service.dev_sign_up("Ada@Example.com", full_name="Ada")

    with pytest.raises(AuthError, match=DUPLICATE_EMAIL_MESSAGE):
        service.dev_sign_up(" ada@example.com ", full_name="Duplicate")


def test_normalize_email_lowercases_and_trims():
    assert normalize_email("  Ada@Example.COM ") == "ada@example.com"


# --- Session lifecycle ---


def test_session_reset_clears_ai_workspace_and_copilot_state(monkeypatch):
    state = _SessionState(
        {
            TENANT_USER_KEY: USER_A_ID,
            "ai_workspace_messages": [{"role": "user", "content": "secret"}],
            "ai_workspace_prompt_input": "secret prompt",
            "ai_workspace_setting_report_type": "Board Report",
            "ai_workspace_excluded_workspace": ["doc.pdf"],
            "ai_workspace_selected_workspace": ["doc.pdf"],
            "copilot_web_sources": ["https://example.com"],
            "copilot_notice": "secret",
            "draft_report": {"report": {"narrative": "secret"}},
            "selected_report": {"name": "secret"},
            "notifications": [{"title": "secret"}],
            "quick_report_documents": ["doc.pdf"],
            "project_report_documents_abc": ["doc.pdf"],
            "viewer_visual_insights_message": "done",
        }
    )
    monkeypatch.setattr("streamlit.session_state", state)

    ensure_tenant_context(USER_B_ID)

    assert state[TENANT_USER_KEY] == USER_B_ID
    assert "ai_workspace_messages" not in state
    assert "draft_report" not in state
    assert "selected_report" not in state
    assert "copilot_web_sources" not in state
    assert "notifications" not in state
    assert "project_report_documents_abc" not in state
    assert not any(key.startswith(prefix) for key in state for prefix in TENANT_KEY_PREFIXES)


def test_clear_tenant_session_removes_all_tenant_keys(monkeypatch):
    state = _SessionState({key: f"value-{key}" for key in TENANT_DATA_KEYS})
    state[TENANT_USER_KEY] = USER_A_ID
    state["ai_workspace_setting_tone"] = "Formal"
    state["ai_workspace_excluded_workspace"] = ["a.pdf"]
    monkeypatch.setattr("streamlit.session_state", state)

    clear_tenant_session()

    assert TENANT_USER_KEY not in state
    for key in TENANT_DATA_KEYS:
        assert key not in state
    assert "ai_workspace_setting_tone" not in state
    assert "ai_workspace_excluded_workspace" not in state


def test_user_switch_scenario_user_b_starts_clean(
    two_user_env,
    user_a_workspace,
    monkeypatch,
):
    state = _SessionState(
        {
            TENANT_USER_KEY: USER_A_ID,
            "projects": [{"id": user_a_workspace["project_id"]}],
            "ai_workspace_messages": [{"role": "user", "content": "Generate report"}],
            "draft_report": {"report": {"narrative": "secret"}},
            "selected_report": user_a_workspace["report"],
            "quick_report_documents": ["quick_secret.txt"],
        }
    )
    monkeypatch.setattr("streamlit.session_state", state)

    ensure_tenant_context(USER_B_ID)
    _as_user(monkeypatch, USER_B)

    assert ProjectService().get_projects() == []
    assert DocumentService().get_documents(QUICK_REPORT_PROJECT_ID) == []
    assert ReportService.get_reports(QUICK_REPORT_PROJECT_ID) == []
    assert "ai_workspace_messages" not in state
    assert "draft_report" not in state
    assert "selected_report" not in state


def test_user_switch_scenario_user_a_data_restored_after_return(
    two_user_env,
    user_a_workspace,
    monkeypatch,
):
    ensure_tenant_context(USER_A_ID)
    _as_user(monkeypatch, USER_B)
    ensure_tenant_context(USER_B_ID)

    ensure_tenant_context(USER_A_ID)
    _as_user(monkeypatch, USER_A)

    projects = ProjectService().get_projects()
    assert len(projects) == 1
    assert projects[0]["id"] == user_a_workspace["project_id"]

    documents = DocumentService().get_documents(
        user_a_workspace["project_id"],
    )
    assert len(documents) == 1

    quick_docs = DocumentService().get_documents(QUICK_REPORT_PROJECT_ID)
    assert len(quick_docs) == 1


# --- Quick Report isolation ---


def test_quick_report_isolated_between_users(two_user_env, user_a_workspace, as_user_b):
    docs = DocumentService().get_documents(QUICK_REPORT_PROJECT_ID)
    assert docs == []

    with pytest.raises((FileNotFoundError, PermissionError)):
        DocumentService().read_document_text(
            QUICK_REPORT_PROJECT_ID,
            "quick_secret.txt",
        )


# --- Project / report / export isolation ---


def test_project_isolation(two_user_env, user_a_workspace, as_user_b):
    assert ProjectService().get_projects() == []
    assert ProjectService().project_exists(user_a_workspace["project_id"]) is False


def test_report_isolation(two_user_env, user_a_workspace, as_user_b):
    assert ReportService.get_reports(user_a_workspace["project_id"]) == []

    with pytest.raises((FileNotFoundError, PermissionError)):
        ReportService.load_report_data(
            user_a_workspace["project_id"],
            user_a_workspace["report"]["filename"],
        )


def test_export_isolation(two_user_env, user_a_workspace, as_user_b):
    assert ExportService().get_exports(user_a_workspace["project_id"]) == []


def test_filesystem_path_traversal_blocked(two_user_env, user_a_workspace, as_user_b):
    docs = DocumentService().get_documents(f"../{USER_A_ID}")
    assert docs == []


def test_file_store_rejects_traversal_project_id(two_user_env, as_user_b):
    store = FileStore(CurrentUser.from_user(USER_B))

    with pytest.raises(PermissionError):
        store.list_files("../secrets", "documents")


def test_cached_report_session_not_visible_after_user_switch(
    two_user_env,
    user_a_workspace,
    monkeypatch,
):
    state = _SessionState(
        {
            TENANT_USER_KEY: USER_A_ID,
            "draft_report": {
                "report": user_a_workspace["report"],
                "workspace": {"id": user_a_workspace["project_id"]},
            },
            "selected_report": user_a_workspace["report"],
        }
    )
    monkeypatch.setattr("streamlit.session_state", state)

    ensure_tenant_context(USER_B_ID)

    assert "draft_report" not in state
    assert "selected_report" not in state


def test_conversation_state_not_visible_after_user_switch(monkeypatch):
    state = _SessionState(
        {
            TENANT_USER_KEY: USER_A_ID,
            "ai_workspace_messages": [
                {"role": "user", "content": "Summarize my confidential board pack"}
            ],
            "copilot_answer": "User A secret answer",
            "copilot_sources": ["secret.txt"],
        }
    )
    monkeypatch.setattr("streamlit.session_state", state)

    ensure_tenant_context(USER_B_ID)

    assert "ai_workspace_messages" not in state
    assert "copilot_answer" not in state
    assert "copilot_sources" not in state


def test_visualization_cache_cleared_on_user_switch(monkeypatch):
    state = _SessionState(
        {
            TENANT_USER_KEY: USER_A_ID,
            "viewer_visual_insights_message": "charts ready",
            "draft_visual_insights_message": "charts ready",
        }
    )
    monkeypatch.setattr("streamlit.session_state", state)

    clear_tenant_session()

    assert "viewer_visual_insights_message" not in state
    assert "draft_visual_insights_message" not in state


def test_json_backend_isolation(two_user_env, user_a_workspace, as_user_b):
    user_a_root = two_user_env["root"] / USER_A_ID
    user_b_root = two_user_env["root"] / USER_B_ID

    assert user_a_root.exists()
    assert user_b_root.exists() or not any(user_b_root.iterdir()) if user_b_root.exists() else True
    assert (user_a_root / "projects.json").exists()
    assert not (user_b_root / "projects.json").exists() or ProjectService().get_projects() == []


def test_login_after_logout_clears_session(monkeypatch):
    state = _SessionState(
        {
            TENANT_USER_KEY: USER_A_ID,
            "projects": [{"id": "project-a"}],
            "ai_workspace_messages": [{"role": "user", "content": "hello"}],
        }
    )
    monkeypatch.setattr("streamlit.session_state", state)

    clear_tenant_session()

    assert TENANT_USER_KEY not in state
    assert "projects" not in state
    assert "ai_workspace_messages" not in state

    ensure_tenant_context(USER_B_ID)
    assert state[TENANT_USER_KEY] == USER_B_ID


def test_require_current_user_fails_closed_when_unauthenticated(monkeypatch):
    from core.current_user import (
        AuthenticationRequiredError,
        clear_current_user_binding,
        require_current_user,
    )

    clear_current_user_binding()
    monkeypatch.setattr("core.auth.get_current_user", lambda: None)

    with pytest.raises(AuthenticationRequiredError, match="Authentication is required"):
        require_current_user()
