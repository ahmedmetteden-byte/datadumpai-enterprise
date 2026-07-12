"""
Authentication and per-user storage tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.user_paths import get_user_projects_json, get_user_projects_root
from services.project_service import ProjectService
from services.auth_service import AuthError, AuthService
from tests.conftest import TEST_USER_ID


def test_dev_sign_in_returns_stable_user(monkeypatch):
    monkeypatch.setattr("services.auth_service.AUTH_DEV_BYPASS", True)

    session = AuthService().dev_sign_in()

    assert session.user.id
    assert session.user.email
    assert session.access_token


def test_sign_in_uses_dev_bypass(monkeypatch):
    monkeypatch.setattr("services.auth_service.AUTH_DEV_BYPASS", True)

    session = AuthService().sign_in("anyone@example.com", "any-password")

    assert session.user.email_verified is True


def test_sign_up_uses_dev_bypass(monkeypatch, isolated_env, tmp_path):
    monkeypatch.setattr("services.auth_service.AUTH_DEV_BYPASS", True)
    monkeypatch.setattr(
        "services.email_uniqueness.EmailUniquenessService._registry_path",
        lambda self: tmp_path / "auth_email_registry_signup.json",
    )

    session = AuthService().sign_up(
        "new.user.signup@example.com",
        "password123",
        full_name="Ada Lovelace",
    )

    assert session is not None
    assert session.user.email == "new.user.signup@example.com"
    assert session.user.full_name == "Ada Lovelace"
    assert session.user.email_verified is True


def test_sign_in_rejects_unverified_email(monkeypatch):
    monkeypatch.setattr("services.auth_service.AUTH_DEV_BYPASS", False)
    monkeypatch.setattr("services.auth_service.is_supabase_configured", lambda: False)

    class FakeUser:
        def model_dump(self):
            return {
                "id": "user-123",
                "email": "unverified.user@example.com",
                "email_confirmed_at": None,
                "user_metadata": {},
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

    class FakeClient:
        auth = FakeAuth()

    service = AuthService()
    service._client = FakeClient()

    with pytest.raises(AuthError, match="verify your email"):
        service.sign_in("unverified.user@example.com", "password123")


def test_bootstrap_user_account_creates_profile(tmp_path, monkeypatch, isolated_env):
    monkeypatch.setattr("config.use_database", lambda: False)

    user_id = "00000000-0000-4000-8000-000000000099"
    base = tmp_path / "users"

    monkeypatch.setattr(
        "core.user_paths.get_user_data_root",
        lambda uid: base / uid,
    )
    monkeypatch.setattr(
        "core.user_paths.get_user_profile_json",
        lambda uid: base / uid / "profile.json",
    )
    monkeypatch.setattr(
        "core.user_paths.get_user_usage_json",
        lambda uid: base / uid / "usage.json",
    )

    from models.user import User
    from services.user_bootstrap import bootstrap_user_account

    user = User(
        id=user_id,
        email="ada@example.com",
        full_name="Ada Lovelace",
        email_verified=True,
    )
    bootstrap_user_account(user)

    from core.current_user import current_user_scope
    from services.profile_service import ProfileService

    with current_user_scope(user):
        profile = ProfileService().load()
    assert profile["email"] == "ada@example.com"
    assert profile["full_name"] == "Ada Lovelace"
    assert profile["last_login"] is not None


def test_projects_are_isolated_per_user(tmp_path, monkeypatch, isolated_env):
    monkeypatch.setattr("config.use_database", lambda: False)
    other_user_id = "00000000-0000-4000-8000-000000000003"
    base = tmp_path / "users"

    def projects_json_for(user_id: str) -> Path:
        path = base / user_id / "projects.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def projects_root_for(user_id: str) -> Path:
        path = base / user_id / "projects"
        path.mkdir(parents=True, exist_ok=True)
        return path

    monkeypatch.setattr(
        "core.user_paths.get_user_projects_json",
        projects_json_for,
    )
    monkeypatch.setattr(
        "core.user_paths.get_user_projects_root",
        projects_root_for,
    )

    from core.current_user import current_user_scope
    from models.user import User
    from tests.conftest import TEST_USER

    other_user = User(
        id=other_user_id,
        email="other@example.com",
        email_verified=True,
    )

    with current_user_scope(TEST_USER):
        first_service = ProjectService()
        first = first_service.create_project("User One Project")

    with current_user_scope(other_user):
        second_service = ProjectService()
        second = second_service.create_project("User Two Project")

    with current_user_scope(TEST_USER):
        first_service = ProjectService()
        assert first_service.get_project(first["id"])["name"] == "User One Project"
        with pytest.raises(ValueError, match="Project not found"):
            first_service.get_project(second["id"])


def test_user_paths_create_directories(tmp_path, monkeypatch):
    user_id = "path-test-user"
    base = tmp_path / "users"

    monkeypatch.setattr(
        "core.user_paths.get_user_data_root",
        lambda uid: base / uid,
    )
    monkeypatch.setattr(
        "core.user_paths.get_user_projects_json",
        lambda uid: base / uid / "projects.json",
    )
    monkeypatch.setattr(
        "core.user_paths.get_user_projects_root",
        lambda uid: base / uid / "projects",
    )

    projects_json = get_user_projects_json(user_id)
    projects_root = get_user_projects_root(user_id)

    assert projects_json.parent == Path(base / user_id)
    assert projects_root.is_dir()
