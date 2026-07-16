"""Tests for reclaiming orphaned profile rows during signup."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from models.user import User as AppUser
from services.auth_service import AuthError, AuthService, AuthSession


class _FakeTable:
    def __init__(self, name: str, store: dict[str, list[dict]]):
        self.name = name
        self.store = store
        self._filters: list[tuple[str, str, str]] = []
        self._action = "select"
        self._payload = None

    def select(self, *_cols):
        self._action = "select"
        return self

    def delete(self):
        self._action = "delete"
        return self

    def eq(self, column: str, value: str):
        self._filters.append(("eq", column, value))
        return self

    def ilike(self, column: str, value: str):
        self._filters.append(("ilike", column, value))
        return self

    def execute(self):
        rows = list(self.store.get(self.name, []))
        matched = []
        for row in rows:
            ok = True
            for op, column, value in self._filters:
                current = str(row.get(column, ""))
                if op == "eq" and current != value:
                    ok = False
                if op == "ilike" and current.lower() != value.lower():
                    ok = False
            if ok:
                matched.append(row)

        if self._action == "delete":
            remaining = [row for row in rows if row not in matched]
            self.store[self.name] = remaining
            return SimpleNamespace(data=matched)

        return SimpleNamespace(data=matched)


class _FakeClient:
    def __init__(self, store: dict[str, list[dict]]):
        self.store = store
        self.auth = SimpleNamespace(
            sign_up=lambda payload: (_ for _ in ()).throw(
                Exception("Database error saving new user")
            )
        )

    def table(self, name: str):
        return _FakeTable(name, self.store)


def test_delete_orphaned_account_rows_removes_profile_without_auth(monkeypatch):
    store = {
        "user_profiles": [
            {"user_id": "orphan-1", "email": "saada@example.com"},
        ],
        "user_usage": [
            {"user_id": "orphan-1", "plan": "free"},
        ],
    }
    client = _FakeClient(store)
    service = AuthService()

    monkeypatch.setattr(service, "_lookup_auth_user_by_email", lambda email: None)
    monkeypatch.setattr("config.use_database", lambda: True)
    monkeypatch.setattr("config.is_supabase_configured", lambda: True)
    monkeypatch.setattr(
        "core.database.create_service_role_client",
        lambda: client,
    )
    monkeypatch.setattr(
        "core.database.get_service_role_client",
        lambda: client,
    )
    monkeypatch.setattr(
        "core.database.handle_response",
        lambda response, action="": response,
    )

    removed = service._delete_orphaned_account_rows("saada@example.com")

    assert removed is True
    assert store["user_profiles"] == []
    assert store["user_usage"] == []


def test_sign_up_requires_admin_configuration(monkeypatch):
    service = AuthService()
    monkeypatch.setattr("config.auth_dev_bypass_enabled", lambda: False)
    monkeypatch.setattr(AuthService, "_admin_sign_up_available", staticmethod(lambda: False))

    with pytest.raises(AuthError, match="SUPABASE_SERVICE_ROLE_KEY"):
        service.sign_up("new@example.com", "password123")


def test_sign_up_uses_admin_path_without_verification_email(monkeypatch):
    service = AuthService()
    created = {}

    expected = AuthSession(
        access_token="a",
        refresh_token="r",
        user=AppUser(
            id="new-user",
            email="new@example.com",
            full_name="Ada",
            email_verified=True,
        ),
    )

    monkeypatch.setattr("config.auth_dev_bypass_enabled", lambda: False)
    monkeypatch.setattr(AuthService, "_admin_sign_up_available", staticmethod(lambda: True))
    monkeypatch.setattr(service, "_lookup_auth_user_by_email", lambda email: None)
    monkeypatch.setattr(service, "_delete_orphaned_account_rows", lambda email: None)

    class AdminAuth:
        def create_user(self, payload):
            created["payload"] = payload
            return SimpleNamespace(
                user=SimpleNamespace(id="new-user", email=payload["email"])
            )

    monkeypatch.setattr(
        "core.database.create_service_role_client",
        lambda: SimpleNamespace(auth=SimpleNamespace(admin=AdminAuth())),
    )
    monkeypatch.setattr(
        "core.database.get_service_role_client",
        lambda: SimpleNamespace(auth=SimpleNamespace(admin=AdminAuth())),
    )
    monkeypatch.setattr(
        service,
        "_session_after_password_sign_in",
        lambda email, password: expected,
    )

    result = service.sign_up("new@example.com", "password123", full_name="Ada")

    assert result is expected
    assert created["payload"]["email_confirm"] is True
    assert created["payload"]["user_metadata"]["full_name"] == "Ada"


def test_sign_up_never_surfaces_verification_email_rate_limit(monkeypatch):
    """Signup must not raise the old 'Too many verification emails' message."""

    service = AuthService()
    expected = AuthSession(
        access_token="a",
        refresh_token="r",
        user=AppUser(
            id="u1",
            email="new@example.com",
            full_name="Ada",
            email_verified=True,
        ),
    )

    monkeypatch.setattr("config.auth_dev_bypass_enabled", lambda: False)
    monkeypatch.setattr(AuthService, "_admin_sign_up_available", staticmethod(lambda: True))
    monkeypatch.setattr(service, "_sign_up_with_admin", lambda *a, **k: expected)

    result = service.sign_up("new@example.com", "password123", full_name="Ada")

    assert result is expected


def test_resend_verification_confirms_without_email_when_rate_limited(monkeypatch):
    service = AuthService()
    updates = {}

    existing = SimpleNamespace(
        id="user-1",
        email_confirmed_at=None,
        confirmed_at=None,
    )

    class AdminAuth:
        def update_user_by_id(self, user_id, payload):
            updates["user_id"] = user_id
            updates["payload"] = payload
            return SimpleNamespace(user=SimpleNamespace(id=user_id))

    monkeypatch.setattr(service, "_lookup_auth_user_by_email", lambda email: existing)
    monkeypatch.setattr(AuthService, "_admin_sign_up_available", staticmethod(lambda: True))
    monkeypatch.setattr(
        "core.database.create_service_role_client",
        lambda: SimpleNamespace(auth=SimpleNamespace(admin=AdminAuth())),
    )
    monkeypatch.setattr(
        "core.database.get_service_role_client",
        lambda: SimpleNamespace(auth=SimpleNamespace(admin=AdminAuth())),
    )

    service.resend_verification("new@example.com")

    assert updates["user_id"] == "user-1"
    assert updates["payload"]["email_confirm"] is True
