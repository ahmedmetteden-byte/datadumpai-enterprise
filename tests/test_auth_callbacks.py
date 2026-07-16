"""
Password recovery and auth callback tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.auth import (
    AUTH_ACCESS_TOKEN_KEY,
    AUTH_RECOVERY_MODE_KEY,
    AUTH_REFRESH_TOKEN_KEY,
    AUTH_USER_KEY,
    AUTH_VIEW_KEY,
    _store_recovery_session,
    initialize_auth,
    is_authenticated,
    is_password_recovery_pending,
)
from core.auth_callbacks import (
    handle_auth_callback_query_params,
    has_actionable_auth_query_params,
    recovery_failed,
)
from models.user import User
from services.auth_service import AuthError, AuthService, AuthSession
from tests.conftest import TEST_USER_ID


class _SessionState(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as exc:
            raise AttributeError(key) from exc

    def __setattr__(self, key, value):
        self[key] = value

    def get(self, key, default=None):
        return super().get(key, default)

    def pop(self, key, default=None):
        return super().pop(key, default)


class _QueryParams(dict):
    def get(self, key, default=None):
        return super().get(key, default)


def _recovery_session() -> AuthSession:
    return AuthSession(
        access_token="recovery-access",
        refresh_token="recovery-refresh",
        user=User(
            id=TEST_USER_ID,
            email="tester@example.com",
            email_verified=True,
        ),
    )


@pytest.fixture
def auth_state(monkeypatch):
    state = _SessionState(
        {
            AUTH_USER_KEY: None,
            AUTH_ACCESS_TOKEN_KEY: None,
            AUTH_REFRESH_TOKEN_KEY: None,
            AUTH_VIEW_KEY: "sign_in",
            AUTH_RECOVERY_MODE_KEY: False,
            "active_page": "landing",
        }
    )
    query = _QueryParams()
    monkeypatch.setattr("streamlit.session_state", state)
    monkeypatch.setattr("streamlit.query_params", query)
    return state, query


def test_app_has_no_hash_promotion_gate():
    app_source = (Path(__file__).resolve().parents[1] / "app.py").read_text(
        encoding="utf-8"
    )
    assert "resolve_hash_promotion" not in app_source
    assert "promote_auth_hash_to_query_params" not in app_source
    assert "hash_promotion" not in app_source


def test_recovery_callback_with_pkce_code(auth_state, monkeypatch):
    state, query = auth_state
    query["active_page"] = "auth"
    query["type"] = "recovery"
    query["code"] = "pkce-code"

    class _Service:
        def exchange_recovery_code(self, code):
            assert code == "pkce-code"
            return _recovery_session()

    monkeypatch.setattr("core.auth_callbacks.AuthService", _Service)

    assert has_actionable_auth_query_params() is True
    assert handle_auth_callback_query_params() is True
    assert state[AUTH_RECOVERY_MODE_KEY] is True
    assert state[AUTH_VIEW_KEY] == "reset_password"
    assert state[AUTH_ACCESS_TOKEN_KEY] == "recovery-access"
    assert state["active_page"] == "auth"
    assert "code" not in query
    assert is_password_recovery_pending() is True
    assert is_authenticated() is False


def test_pkce_recovery_query_callback_reaches_reset_password(auth_state, monkeypatch):
    """Canonical recovery URL: ?active_page=auth&type=recovery&code=..."""

    state, query = auth_state
    query["active_page"] = "auth"
    query["type"] = "recovery"
    query["code"] = "recovery-pkce-code"

    exchanged: list[str] = []

    class _Service:
        def exchange_recovery_code(self, code):
            exchanged.append(code)
            return _recovery_session()

        def exchange_recovery_token_hash(self, _token_hash):
            raise AssertionError("token_hash path should not run for PKCE code")

        def establish_recovery_session(self, *_args):
            raise AssertionError("implicit recovery must not run")

    monkeypatch.setattr("core.auth_callbacks.AuthService", _Service)

    assert handle_auth_callback_query_params() is True
    assert exchanged == ["recovery-pkce-code"]
    assert state[AUTH_VIEW_KEY] == "reset_password"
    assert state[AUTH_RECOVERY_MODE_KEY] is True


def test_recovery_callback_with_token_hash(auth_state, monkeypatch):
    state, query = auth_state
    query["type"] = "recovery"
    query["token_hash"] = "hash-token"

    class _Service:
        def exchange_recovery_token_hash(self, token_hash):
            assert token_hash == "hash-token"
            return _recovery_session()

    monkeypatch.setattr("core.auth_callbacks.AuthService", _Service)

    assert handle_auth_callback_query_params() is True
    assert state[AUTH_RECOVERY_MODE_KEY] is True
    assert state[AUTH_VIEW_KEY] == "reset_password"
    assert "token_hash" not in query


def test_implicit_access_token_query_params_are_ignored(auth_state, monkeypatch):
    """Hash/implicit tokens must not drive recovery — only code or token_hash."""

    state, query = auth_state
    query["type"] = "recovery"
    query["access_token"] = "implicit-access"
    query["refresh_token"] = "implicit-refresh"

    class _Service:
        def establish_recovery_session(self, *_args):
            raise AssertionError("implicit recovery is removed")

        def exchange_recovery_code(self, _code):
            raise AssertionError("should not exchange without code")

    monkeypatch.setattr("core.auth_callbacks.AuthService", _Service)

    assert has_actionable_auth_query_params() is False
    assert handle_auth_callback_query_params() is False
    assert state[AUTH_RECOVERY_MODE_KEY] is False
    assert state[AUTH_VIEW_KEY] == "sign_in"


def test_recovery_callback_invalid_link_sets_sign_in_error(auth_state, monkeypatch):
    state, query = auth_state
    query["type"] = "recovery"
    query["code"] = "bad-code"

    class _Service:
        def exchange_recovery_code(self, _code):
            raise AuthError("invalid")

    monkeypatch.setattr("core.auth_callbacks.AuthService", _Service)

    assert handle_auth_callback_query_params() is True
    assert state[AUTH_VIEW_KEY] == "sign_in"
    assert state.auth_error
    assert recovery_failed()


def test_send_password_reset_uses_pkce_redirect(monkeypatch):
    from config import AUTH_REDIRECT_URL

    monkeypatch.setattr("config.auth_dev_bypass_enabled", lambda: False)
    monkeypatch.setattr("services.auth_service.is_supabase_configured", lambda: False)

    captured: list[tuple[str, dict]] = []

    class FakeAuth:
        def reset_password_for_email(self, email, options):
            captured.append((email, options))

    class FakeClient:
        auth = FakeAuth()

    service = AuthService()
    service._client = FakeClient()
    service.send_password_reset("user@example.com")

    assert captured == [("user@example.com", {"redirect_to": AUTH_REDIRECT_URL})]
    assert "active_page=auth" in AUTH_REDIRECT_URL


def test_auth_service_creates_client_with_pkce_flow(monkeypatch):
    captured: dict = {}

    class FakeOptions:
        def __init__(self, **kwargs):
            captured["options_kwargs"] = kwargs
            self.flow_type = kwargs.get("flow_type")

    def fake_create_client(url, key, options=None):
        captured["url"] = url
        captured["key"] = key
        captured["options"] = options
        return object()

    monkeypatch.setattr("services.auth_service.is_supabase_configured", lambda: True)
    monkeypatch.setattr("config.SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr("config.SUPABASE_ANON_KEY", "anon-key")

    import supabase

    monkeypatch.setattr(supabase, "create_client", fake_create_client)
    monkeypatch.setattr(supabase, "ClientOptions", FakeOptions)

    AuthService()

    assert captured["url"] == "https://example.supabase.co"
    assert captured["key"] == "anon-key"
    assert captured["options_kwargs"] == {
        "flow_type": "pkce",
        "persist_session": False,
        "auto_refresh_token": False,
    }
    assert getattr(captured["options"], "flow_type", None) == "pkce"


def test_recovery_callback_exchange_exception_sets_terminal_error(auth_state, monkeypatch):
    state, query = auth_state
    query["type"] = "recovery"
    query["code"] = "bad-code"

    class _Service:
        def exchange_recovery_code(self, _code):
            raise RuntimeError("network down")

    monkeypatch.setattr("core.auth_callbacks.AuthService", _Service)

    assert handle_auth_callback_query_params() is True
    assert state[AUTH_VIEW_KEY] == "sign_in"
    assert recovery_failed() is True


def test_recovery_callback_supabase_error_param(auth_state):
    state, query = auth_state
    query["type"] = "recovery"
    query["error"] = "access_denied"
    query["error_description"] = "Email link is invalid or has expired"

    assert handle_auth_callback_query_params() is True
    assert state[AUTH_VIEW_KEY] == "sign_in"
    assert recovery_failed() is True


def test_recovery_session_does_not_count_as_authenticated(auth_state):
    state, _query = auth_state
    _store_recovery_session(_recovery_session())

    assert is_password_recovery_pending() is True
    assert is_authenticated() is False
    assert state["active_page"] == "auth"


def test_initialize_auth_skips_session_restore_while_recovery_pending(auth_state, monkeypatch):
    state, query = auth_state
    _store_recovery_session(_recovery_session())
    query["type"] = "recovery"
    query["code"] = "should-not-run"

    called = {"restore": False}

    class _Service:
        def exchange_recovery_code(self, _code):
            called["restore"] = True
            return _recovery_session()

        def restore_session(self, *_args):
            called["restore"] = True
            raise AssertionError("restore_session should not run during recovery")

    monkeypatch.setattr("core.auth_callbacks.AuthService", _Service)
    monkeypatch.setattr("services.auth_service.AuthService", _Service)

    initialize_auth()

    assert called["restore"] is False
    assert is_password_recovery_pending() is True
