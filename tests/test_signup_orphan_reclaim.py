"""Tests for reclaiming orphaned profile rows during signup."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.auth_service import AuthError, AuthService, SignUpDuplicateError


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


def test_sign_up_reclaims_orphan_then_succeeds(monkeypatch):
    service = AuthService()
    created = {}

    class Session:
        access_token = "a"
        refresh_token = "r"

    class User:
        def model_dump(self):
            return {
                "id": "new-user",
                "email": "saada@example.com",
                "email_confirmed_at": "2026-01-01",
                "user_metadata": {"full_name": "Sa'ada"},
                "identities": [{"id": "1"}],
            }

    class Response:
        user = User()
        session = Session()

    def fake_create(client, email, password, *, full_name):
        if "retried" not in created:
            created["retried"] = True
            raise Exception("Database error saving new user")
        return Response()

    monkeypatch.setattr(service, "_require_client", lambda: object())
    monkeypatch.setattr(service, "_lookup_auth_user_by_email", lambda email: None)
    monkeypatch.setattr(service, "_delete_orphaned_account_rows", lambda email: True)
    monkeypatch.setattr(service, "_create_supabase_user", fake_create)
    monkeypatch.setattr("config.auth_dev_bypass_enabled", lambda: False)

    result = service.sign_up("saada@example.com", "password123", full_name="Sa'ada")

    assert result is not None
    assert result.user.email == "saada@example.com"
    assert result.user.full_name == "Sa'ada"


def test_sign_up_maps_ssl_failures(monkeypatch):
    service = AuthService()

    monkeypatch.setattr(service, "_require_client", lambda: object())
    monkeypatch.setattr(service, "_lookup_auth_user_by_email", lambda email: None)
    monkeypatch.setattr(service, "_delete_orphaned_account_rows", lambda email: False)
    monkeypatch.setattr(
        service,
        "_create_supabase_user",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            Exception(
                "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed"
            )
        ),
    )
    monkeypatch.setattr("config.auth_dev_bypass_enabled", lambda: False)

    with pytest.raises(AuthError, match="authentication service"):
        service.sign_up("new@example.com", "password123")


def test_sign_up_rate_limit_creates_user_without_email(monkeypatch):
    from supabase_auth.errors import AuthApiError

    service = AuthService()
    rate_limit = AuthApiError("email rate limit exceeded", 429, "over_email_send_rate_limit")

    monkeypatch.setattr(service, "_require_client", lambda: object())
    monkeypatch.setattr(service, "_lookup_auth_user_by_email", lambda email: None)
    monkeypatch.setattr(service, "_delete_orphaned_account_rows", lambda email: False)
    monkeypatch.setattr(
        service,
        "_create_supabase_user",
        lambda *args, **kwargs: (_ for _ in ()).throw(rate_limit),
    )
    monkeypatch.setattr(service, "_create_user_without_email", lambda *a, **k: True)
    monkeypatch.setattr("config.auth_dev_bypass_enabled", lambda: False)

    from services.auth_service import SignUpEmailDelayedError

    with pytest.raises(SignUpEmailDelayedError, match="temporarily delayed"):
        service.sign_up("new@example.com", "password123", full_name="Ada")


def test_sign_up_rate_limit_without_fallback_shows_wait_message(monkeypatch):
    from supabase_auth.errors import AuthApiError

    service = AuthService()
    rate_limit = AuthApiError("email rate limit exceeded", 429, "over_email_send_rate_limit")

    monkeypatch.setattr(service, "_require_client", lambda: object())
    monkeypatch.setattr(service, "_lookup_auth_user_by_email", lambda email: None)
    monkeypatch.setattr(service, "_delete_orphaned_account_rows", lambda email: False)
    monkeypatch.setattr(
        service,
        "_create_supabase_user",
        lambda *args, **kwargs: (_ for _ in ()).throw(rate_limit),
    )
    monkeypatch.setattr(service, "_create_user_without_email", lambda *a, **k: False)
    monkeypatch.setattr("config.auth_dev_bypass_enabled", lambda: False)

    with pytest.raises(AuthError, match="Too many verification emails"):
        service.sign_up("new@example.com", "password123")
