"""
Lockout, onboarding, and activity log tests.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from services.auth_service import AuthError, AuthService
from services.lockout_service import LockoutService
from services.onboarding_service import OnboardingService
from services.activity_service import ActivityService


def test_lockout_blocks_after_max_attempts(tmp_path, monkeypatch):
    monkeypatch.setattr("config.use_database", lambda: False)
    monkeypatch.setattr("services.lockout_service.LockoutService._JSON_PATH", tmp_path / "lockouts.json")
    monkeypatch.setattr("config.LOCKOUT_MAX_ATTEMPTS", 2)

    service = LockoutService()
    service.record_failure("user@example.com")
    service.record_failure("user@example.com")

    with pytest.raises(AuthError, match="Too many failed sign-in attempts"):
        service.check_allowed("user@example.com")


def test_lockout_resets_after_success(tmp_path, monkeypatch):
    monkeypatch.setattr("config.use_database", lambda: False)
    monkeypatch.setattr("services.lockout_service.LockoutService._JSON_PATH", tmp_path / "lockouts.json")

    service = LockoutService()
    service.record_failure("user@example.com")
    service.record_success("user@example.com")

    service.check_allowed("user@example.com")


def test_sign_in_records_lockout_failure(monkeypatch):
    monkeypatch.setattr("services.auth_service.AUTH_DEV_BYPASS", False)
    monkeypatch.setattr("services.auth_service.is_supabase_configured", lambda: False)

    failures: list[str] = []

    class FakeLockout:
        def check_allowed(self, email):
            return None

        def record_failure(self, email):
            failures.append(email)

        def record_success(self, email):
            pass

    monkeypatch.setattr("services.lockout_service.LockoutService", lambda: FakeLockout())

    class FakeAuth:
        def sign_in_with_password(self, _credentials):
            class Response:
                session = None
                user = None

            return Response()

    service = AuthService()
    service._client = type("Client", (), {"auth": FakeAuth()})()

    with pytest.raises(AuthError, match="Invalid email or password"):
        service.sign_in("user@example.com", "wrong-password")

    assert failures == ["user@example.com"]


def test_onboarding_detects_project_creation(tmp_path, monkeypatch, isolated_env):
    monkeypatch.setattr("config.use_database", lambda: False)
    user_id = "00000000-0000-4000-8000-000000000010"
    base = tmp_path / "users"

    monkeypatch.setattr("core.user_paths.get_user_data_root", lambda uid: base / uid)
    monkeypatch.setattr("core.user_paths.get_user_profile_json", lambda uid: base / uid / "profile.json")
    monkeypatch.setattr("core.user_paths.get_user_usage_json", lambda uid: base / uid / "usage.json")
    monkeypatch.setattr("core.user_paths.get_user_projects_json", lambda uid: base / uid / "projects.json")
    monkeypatch.setattr("core.user_paths.get_user_projects_root", lambda uid: base / uid / "projects")

    from core.current_user import current_user_scope
    from models.user import User
    from services.project_service import ProjectService

    user = User(id=user_id, email="onboarding@example.com", email_verified=True)

    with current_user_scope(user):
        onboarding = OnboardingService()
        assert onboarding.needs_onboarding() is True

        ProjectService().create_project("First Project")

        completed = onboarding._detect_completed_steps()
        assert completed[1] is True


def test_activity_service_persists_json_entries(tmp_path, monkeypatch, isolated_env):
    monkeypatch.setattr("config.use_database", lambda: False)
    user_id = "00000000-0000-4000-8000-000000000011"
    base = tmp_path / "users"

    monkeypatch.setattr("core.user_paths.get_user_data_root", lambda uid: base / uid)

    service = ActivityService()
    service.log("user.signed_in", "Signed in")

    logs = service.list_recent()
    assert len(logs) == 1
    assert logs[0]["message"] == "Signed in"
