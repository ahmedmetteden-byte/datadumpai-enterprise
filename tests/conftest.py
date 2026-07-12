"""
Shared pytest fixtures for isolated DataDumpAI tests.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest

from core.current_user import bind_current_user, clear_current_user_binding
from models.user import User
from services.document_service import DocumentService
from services.project_service import ProjectService

TEST_USER_ID = "00000000-0000-4000-8000-000000000002"
TEST_USER = User(
    id=TEST_USER_ID,
    email="tester@example.com",
    full_name="Test User",
    email_verified=True,
)


class MockUpload:
    """Minimal Streamlit-like upload object for pipeline tests."""

    def __init__(self, name: str, content: bytes) -> None:
        self.name = name
        self._content = content
        self._pos = 0

    def read(self) -> bytes:
        return self._content

    def seek(self, position: int) -> None:
        self._pos = position


def enable_dev_auth_bypass(monkeypatch) -> None:
    """Enable legacy dev auth only for tests that explicitly exercise it."""

    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("AUTH_DEV_BYPASS", "true")
    monkeypatch.setattr("config.auth_dev_bypass_enabled", lambda: True)


@pytest.fixture(autouse=True)
def auth_context(monkeypatch):
    """Provide a signed-in test user and keep tests on the JSON backend."""

    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("AUTH_DEV_BYPASS", "false")
    monkeypatch.setenv("DATABASE_BACKEND", "json")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setattr("config.auth_dev_bypass_enabled", lambda: False)
    monkeypatch.setattr("config.use_database", lambda: False)
    monkeypatch.setattr("services.auth_service.is_supabase_configured", lambda: False)
    monkeypatch.setattr("core.auth.get_current_user", lambda: TEST_USER)
    monkeypatch.setattr("core.auth.is_authenticated", lambda: True)
    bind_current_user(TEST_USER)
    yield
    clear_current_user_binding()


@pytest.fixture
def isolated_env(tmp_path, monkeypatch):
    """
    Isolate per-user project JSON and on-disk project folders under tmp_path.
    """

    user_root = tmp_path / "users" / TEST_USER_ID
    projects_root = user_root / "projects"
    projects_root.mkdir(parents=True)

    monkeypatch.setattr(
        "core.user_paths.get_user_data_root",
        lambda user_id: tmp_path / "users" / user_id,
    )
    monkeypatch.setattr(
        "core.user_paths.get_user_projects_json",
        lambda user_id: tmp_path / "users" / user_id / "projects.json",
    )
    monkeypatch.setattr(
        "core.user_paths.get_user_projects_root",
        lambda user_id: tmp_path / "users" / user_id / "projects",
    )
    monkeypatch.setattr(
        "core.user_paths.get_user_usage_json",
        lambda user_id: tmp_path / "users" / user_id / "usage.json",
    )
    monkeypatch.setattr(
        "core.user_paths.get_user_profile_json",
        lambda user_id: tmp_path / "users" / user_id / "profile.json",
    )
    monkeypatch.setattr(
        "core.user_paths.get_users_root",
        lambda: tmp_path / "users",
    )

    yield {
        "root": projects_root,
        "projects_json": user_root / "projects.json",
        "usage_json": user_root / "usage.json",
        "user_root": user_root,
    }


@pytest.fixture
def project_service(isolated_env) -> ProjectService:
    return ProjectService()


@pytest.fixture
def document_service(isolated_env) -> DocumentService:
    return DocumentService()


@pytest.fixture
def text_upload() -> MockUpload:
    return MockUpload(
        "board_minutes.txt",
        b"Board meeting minutes.\nRevenue increased 12 percent.\n",
    )
