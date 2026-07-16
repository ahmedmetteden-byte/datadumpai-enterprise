"""
Authentication and per-user storage tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.auth import (
    AUTH_ACCESS_TOKEN_KEY,
    AUTH_REFRESH_TOKEN_KEY,
    AUTH_USER_KEY,
    AUTH_VIEW_KEY,
    clear_auth_session,
)
from core.navigation import PUBLIC_DEFAULT_PAGE
from core.tenant_session import TENANT_USER_KEY
from core.user_paths import get_user_projects_json, get_user_projects_root
from models.user import User
from services.project_service import ProjectService
from services.auth_service import (
    PASSWORD_RESET_GENERIC_MESSAGE,
    PASSWORD_RESET_RATE_LIMIT_MESSAGE,
    AuthError,
    AuthService,
    SignUpDuplicateError,
)
from services.email_uniqueness import (
    DUPLICATE_EMAIL_MESSAGE,
    SIGN_UP_UNVERIFIED_DUPLICATE_MESSAGE,
    SIGN_UP_VERIFIED_DUPLICATE_MESSAGE,
)
from tests.conftest import TEST_USER_ID, enable_dev_auth_bypass


class _SessionState(dict):
    """Minimal Streamlit session_state stand-in for unit tests."""

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


def _logout_service(monkeypatch) -> AuthService:
    monkeypatch.setattr("config.auth_dev_bypass_enabled", lambda: False)
    monkeypatch.setattr("services.auth_service.is_supabase_configured", lambda: False)
    return AuthService()


def _make_logout_fake_client(*, existing_session=None, admin_error=None, sign_out_error=None):
    class FakeAdmin:
        calls: list[str] = []

        def sign_out(self, jwt, scope="global"):
            self.__class__.calls.append(jwt)
            if admin_error is not None:
                raise admin_error

    class FakeAuth:
        set_session_calls: list[tuple[str, str]] = []
        sign_out_calls = 0
        admin = FakeAdmin()

        def get_session(self):
            return existing_session

        def set_session(self, access_token, refresh_token):
            self.__class__.set_session_calls.append((access_token, refresh_token))
            raise AssertionError("set_session should not be called during logout")

        def sign_out(self, options=None):
            self.__class__.sign_out_calls += 1
            if sign_out_error is not None:
                raise sign_out_error

    class FakeClient:
        auth = FakeAuth()

    return FakeClient(), FakeAuth, FakeAdmin


def test_dev_sign_in_returns_stable_user(monkeypatch):
    enable_dev_auth_bypass(monkeypatch)

    session = AuthService().dev_sign_in()

    assert session.user.id
    assert session.user.email
    assert session.access_token


def test_sign_in_uses_dev_bypass(monkeypatch):
    enable_dev_auth_bypass(monkeypatch)

    session = AuthService().sign_in("anyone@example.com", "any-password")

    assert session.user.email_verified is True


def test_sign_up_uses_dev_bypass(monkeypatch, isolated_env, tmp_path):
    enable_dev_auth_bypass(monkeypatch)
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
    monkeypatch.setattr("config.auth_dev_bypass_enabled", lambda: False)
    monkeypatch.setattr("services.auth_service.is_supabase_configured", lambda: False)

    class FakeLockout:
        def check_allowed(self, email):
            return None

        def record_failure(self, email):
            pass

        def record_success(self, email):
            pass

    monkeypatch.setattr("services.lockout_service.LockoutService", lambda: FakeLockout())

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


def test_supabase_sign_up_returns_distinct_user_ids(monkeypatch):
    monkeypatch.setattr("config.auth_dev_bypass_enabled", lambda: False)
    monkeypatch.setattr("services.auth_service.is_supabase_configured", lambda: False)
    monkeypatch.setattr(AuthService, "_admin_sign_up_available", staticmethod(lambda: True))

    user_ids = {
        "ahmed@example.com": "550e8400-e29b-41d4-a716-446655440001",
        "john@example.com": "550e8400-e29b-41d4-a716-446655440002",
    }

    class FakeUser:
        def __init__(self, email: str) -> None:
            self._email = email

        def model_dump(self):
            return {
                "id": user_ids[self._email],
                "email": self._email,
                "email_confirmed_at": "2026-01-01T00:00:00Z",
                "user_metadata": {"full_name": self._email.split("@")[0].title()},
            }

    class FakeSession:
        def __init__(self, email: str) -> None:
            self.access_token = f"access-{email}"
            self.refresh_token = f"refresh-{email}"

    class FakeResponse:
        def __init__(self, email: str) -> None:
            self.session = FakeSession(email)
            self.user = FakeUser(email)

    class FakeAuth:
        def sign_in_with_password(self, credentials):
            return FakeResponse(credentials["email"])

    class FakeClient:
        auth = FakeAuth()

    service = AuthService()
    service._client = FakeClient()
    service._lookup_auth_user_by_email = lambda _email: None
    service._delete_orphaned_account_rows = lambda _email: False
    monkeypatch.setattr(
        "core.database.admin_create_user",
        lambda **kwargs: {
            "id": user_ids[kwargs["email"].lower()],
            "email": kwargs["email"],
        },
    )

    ahmed = service.sign_up("Ahmed@example.com", "password123", full_name="Ahmed")
    john = service.sign_up("John@example.com", "password123", full_name="John")

    assert ahmed is not None
    assert john is not None
    assert ahmed.user.id != john.user.id

    ahmed_sign_in = service.sign_in("Ahmed@example.com", "password123")
    john_sign_in = service.sign_in("John@example.com", "password123")

    assert ahmed_sign_in.user.id == ahmed.user.id
    assert john_sign_in.user.id == john.user.id
    assert ahmed_sign_in.user.id != john_sign_in.user.id


def test_supabase_duplicate_sign_up_returns_verified_error(monkeypatch):
    monkeypatch.setattr("config.auth_dev_bypass_enabled", lambda: False)
    monkeypatch.setattr("services.auth_service.is_supabase_configured", lambda: False)
    monkeypatch.setattr(AuthService, "_admin_sign_up_available", staticmethod(lambda: True))

    class FakeAdminUser:
        id = "existing-id"
        email_confirmed_at = "2026-01-01T00:00:00Z"
        confirmed_at = None

    class FakeClient:
        auth = object()

    service = AuthService()
    service._client = FakeClient()
    service._lookup_auth_user_by_email = lambda _email: FakeAdminUser()
    service._existing_account_verification_status = lambda *_args, **_kwargs: "verified"

    with pytest.raises(SignUpDuplicateError) as exc_info:
        service.sign_up("ahmed@example.com", "password123")

    assert exc_info.value.verification_status == "verified"
    assert str(exc_info.value) == SIGN_UP_VERIFIED_DUPLICATE_MESSAGE


def test_supabase_duplicate_sign_up_empty_identities_unverified(monkeypatch):
    monkeypatch.setattr("config.auth_dev_bypass_enabled", lambda: False)
    monkeypatch.setattr("services.auth_service.is_supabase_configured", lambda: False)
    monkeypatch.setattr(AuthService, "_admin_sign_up_available", staticmethod(lambda: True))

    class FakeAdminUser:
        id = "pending-id"
        email_confirmed_at = None
        confirmed_at = None

    class FakeUser:
        def model_dump(self):
            return {
                "id": "pending-id",
                "email": "pending@example.com",
                "email_confirmed_at": "2026-01-01T00:00:00Z",
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
    service._lookup_auth_user_by_email = lambda _email: FakeAdminUser()
    service._complete_unverified_signup = lambda *_args, **_kwargs: None

    result = service.sign_up("pending@example.com", "password123")

    assert result is not None
    assert result.user.id == "pending-id"
    assert result.user.email_verified is True


def test_supabase_duplicate_sign_up_empty_identities_verified(monkeypatch):
    monkeypatch.setattr("config.auth_dev_bypass_enabled", lambda: False)
    monkeypatch.setattr("services.auth_service.is_supabase_configured", lambda: False)
    monkeypatch.setattr(AuthService, "_admin_sign_up_available", staticmethod(lambda: True))

    class FakeAdminUser:
        id = "verified-id"
        email_confirmed_at = "2026-01-01T00:00:00Z"
        confirmed_at = None

    class FakeClient:
        auth = object()

    service = AuthService()
    service._client = FakeClient()
    service._lookup_auth_user_by_email = lambda _email: FakeAdminUser()
    service._existing_account_verification_status = lambda *_args, **_kwargs: "verified"

    with pytest.raises(SignUpDuplicateError) as exc_info:
        service.sign_up("verified@example.com", "password123")

    assert exc_info.value.verification_status == "verified"
    assert str(exc_info.value) == SIGN_UP_VERIFIED_DUPLICATE_MESSAGE


def test_new_sign_up_creates_confirmed_session(monkeypatch):
    monkeypatch.setattr("config.auth_dev_bypass_enabled", lambda: False)
    monkeypatch.setattr("services.auth_service.is_supabase_configured", lambda: False)
    monkeypatch.setattr(AuthService, "_admin_sign_up_available", staticmethod(lambda: True))

    class FakeUser:
        def model_dump(self):
            return {
                "id": "550e8400-e29b-41d4-a716-446655440099",
                "email": "new@example.com",
                "email_confirmed_at": "2026-01-01T00:00:00Z",
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
    service._lookup_auth_user_by_email = lambda _email: None
    service._delete_orphaned_account_rows = lambda _email: False

    def fake_admin_create_user(*, email, password, full_name="", email_confirm=True):
        assert email_confirm is True
        return {
            "id": "550e8400-e29b-41d4-a716-446655440099",
            "email": email,
        }

    monkeypatch.setattr("core.database.admin_create_user", fake_admin_create_user)

    result = service.sign_up("new@example.com", "password123")

    assert result is not None
    assert result.user.email == "new@example.com"
    assert result.user.email_verified is True


def test_restore_session_uses_supabase_tokens(monkeypatch):
    monkeypatch.setattr("config.auth_dev_bypass_enabled", lambda: False)
    monkeypatch.setattr("services.auth_service.is_supabase_configured", lambda: False)

    class FakeUser:
        def model_dump(self):
            return {
                "id": "550e8400-e29b-41d4-a716-446655440099",
                "email": "ahmed@example.com",
                "email_confirmed_at": "2026-01-01T00:00:00Z",
                "user_metadata": {},
            }

    class FakeSession:
        access_token = "restored-access"
        refresh_token = "restored-refresh"

    class FakeResponse:
        session = FakeSession()
        user = FakeUser()

    class FakeAuth:
        def set_session(self, access_token, refresh_token):
            assert access_token == "stored-access"
            assert refresh_token == "stored-refresh"
            return FakeResponse()

    class FakeClient:
        auth = FakeAuth()

    service = AuthService()
    service._client = FakeClient()

    session = service.restore_session("stored-access", "stored-refresh")

    assert session.user.id == "550e8400-e29b-41d4-a716-446655440099"
    assert session.access_token == "restored-access"


def test_sign_out_method_never_calls_set_session():
    import ast
    from pathlib import Path

    source = Path("services/auth_service.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    sign_out_source = None
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "AuthService":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "sign_out":
                    lines = source.splitlines()
                    sign_out_source = "\n".join(lines[item.lineno - 1 : item.end_lineno])

    assert sign_out_source is not None
    assert "set_session" not in sign_out_source


def test_sign_out_revokes_remote_session_without_set_session(monkeypatch):
    service = _logout_service(monkeypatch)
    fake_client, fake_auth, fake_admin = _make_logout_fake_client()
    service._client = fake_client

    service.sign_out("access-token-123", "refresh-token-456")

    assert fake_admin.calls == ["access-token-123"]
    assert fake_auth.set_session_calls == []
    assert fake_auth.sign_out_calls == 1


def test_sign_out_uses_existing_client_session_without_set_session(monkeypatch):
    class ExistingSession:
        access_token = "in-memory-access"

    service = _logout_service(monkeypatch)
    fake_client, fake_auth, fake_admin = _make_logout_fake_client(
        existing_session=ExistingSession()
    )
    service._client = fake_client

    service.sign_out("stale-access", "stale-refresh")

    assert fake_admin.calls == []
    assert fake_auth.set_session_calls == []
    assert fake_auth.sign_out_calls == 1


def test_sign_out_treats_revoked_session_as_success(monkeypatch):
    from supabase_auth.errors import AuthApiError

    service = _logout_service(monkeypatch)
    fake_client, fake_auth, fake_admin = _make_logout_fake_client(
        admin_error=AuthApiError(
            "Session from session_id claim in JWT does not exist",
            403,
            "session_not_found",
        )
    )
    service._client = fake_client

    service.sign_out("revoked-access", "revoked-refresh")

    assert fake_admin.calls == ["revoked-access"]
    assert fake_auth.sign_out_calls == 1


def test_sign_out_treats_expired_jwt_as_success(monkeypatch):
    from supabase_auth.errors import AuthApiError

    service = _logout_service(monkeypatch)
    fake_client, _, _ = _make_logout_fake_client(
        admin_error=AuthApiError("Session has expired", 403, "session_expired")
    )
    service._client = fake_client

    service.sign_out("expired-access", "expired-refresh")


def test_sign_out_treats_invalid_refresh_token_as_success(monkeypatch):
    from supabase_auth.errors import AuthApiError

    service = _logout_service(monkeypatch)
    fake_client, fake_auth, fake_admin = _make_logout_fake_client(
        admin_error=AuthApiError("Invalid Refresh Token", 400, "refresh_token_not_found")
    )
    service._client = fake_client

    service.sign_out("access-token", "invalid-refresh")

    assert fake_admin.calls == ["access-token"]
    assert fake_auth.set_session_calls == []
    assert fake_auth.sign_out_calls == 1


def _password_reset_service(monkeypatch) -> AuthService:
    monkeypatch.setattr("config.auth_dev_bypass_enabled", lambda: False)
    monkeypatch.setattr("services.auth_service.is_supabase_configured", lambda: False)
    return AuthService()


def _make_password_reset_fake_client(*, reset_error=None):
    class FakeAuth:
        reset_calls: list[tuple[str, dict]] = []

        def reset_password_for_email(self, email, options):
            self.__class__.reset_calls.append((email, options))
            if reset_error is not None:
                raise reset_error

    class FakeClient:
        auth = FakeAuth()

    return FakeClient(), FakeAuth


def test_send_password_reset_success(monkeypatch):
    from config import AUTH_REDIRECT_URL

    service = _password_reset_service(monkeypatch)
    fake_client, fake_auth = _make_password_reset_fake_client()
    service._client = fake_client

    service.send_password_reset("  user@example.com  ")

    assert fake_auth.reset_calls == [
        ("user@example.com", {"redirect_to": AUTH_REDIRECT_URL})
    ]


def test_send_password_reset_rate_limit_exceeded(monkeypatch):
    from supabase_auth.errors import AuthApiError

    service = _password_reset_service(monkeypatch)
    fake_client, _ = _make_password_reset_fake_client(
        reset_error=AuthApiError(
            "Email rate limit exceeded",
            429,
            "over_email_send_rate_limit",
        )
    )
    service._client = fake_client

    with pytest.raises(AuthError) as exc_info:
        service.send_password_reset("user@example.com")

    assert exc_info.value.title == "Too many password reset requests"
    assert PASSWORD_RESET_RATE_LIMIT_MESSAGE in str(exc_info.value)


def test_password_reset_rate_limit_friendly_message(monkeypatch):
    from supabase_auth.errors import AuthApiError
    from ui.feedback import friendly_message

    service = _password_reset_service(monkeypatch)
    fake_client, _ = _make_password_reset_fake_client(
        reset_error=AuthApiError(
            "Email rate limit exceeded",
            429,
            "over_email_send_rate_limit",
        )
    )
    service._client = fake_client

    with pytest.raises(AuthError) as exc_info:
        service.send_password_reset("user@example.com")

    message = friendly_message(exc_info.value)
    assert message.startswith("Too many password reset requests\n\n")
    assert "check your inbox and spam folder" in message
    assert "Something went wrong" not in message


def test_send_password_reset_network_failure(monkeypatch):
    import httpx

    service = _password_reset_service(monkeypatch)
    fake_client, _ = _make_password_reset_fake_client(
        reset_error=httpx.ConnectError("connection refused")
    )
    service._client = fake_client

    with pytest.raises(AuthError, match=PASSWORD_RESET_GENERIC_MESSAGE):
        service.send_password_reset("user@example.com")


def test_send_password_reset_unexpected_supabase_auth_error(monkeypatch, caplog):
    from supabase_auth.errors import AuthApiError

    service = _password_reset_service(monkeypatch)
    fake_client, _ = _make_password_reset_fake_client(
        reset_error=AuthApiError("Invalid email", 400, "validation_failed")
    )
    service._client = fake_client

    with caplog.at_level("WARNING"):
        with pytest.raises(AuthError, match=PASSWORD_RESET_GENERIC_MESSAGE):
            service.send_password_reset("user@example.com")

    assert "Password reset Supabase auth error" in caplog.text


def test_sign_out_without_tokens_clears_client_session(monkeypatch):
    service = _logout_service(monkeypatch)
    fake_client, fake_auth, fake_admin = _make_logout_fake_client()
    service._client = fake_client

    service.sign_out()

    assert fake_admin.calls == []
    assert fake_auth.sign_out_calls == 1


def test_clear_auth_session_after_browser_refresh(monkeypatch):
    from supabase_auth.errors import AuthApiError

    state = _SessionState(
        {
            AUTH_USER_KEY: User(
                id=TEST_USER_ID,
                email="tester@example.com",
                email_verified=True,
            ),
            AUTH_ACCESS_TOKEN_KEY: "restored-access",
            AUTH_REFRESH_TOKEN_KEY: "restored-refresh",
            AUTH_VIEW_KEY: "workspace",
            "active_page": "workspace",
            TENANT_USER_KEY: TEST_USER_ID,
            "projects": [{"id": "project-1"}],
        }
    )
    monkeypatch.setattr("streamlit.session_state", state)

    cleared_cookies: list[bool] = []

    def _clear_persisted_tokens():
        cleared_cookies.append(True)

    service = _logout_service(monkeypatch)
    fake_client, fake_auth, fake_admin = _make_logout_fake_client(
        admin_error=AuthApiError(
            "Session from session_id claim in JWT does not exist",
            403,
            "session_not_found",
        )
    )
    service._client = fake_client
    monkeypatch.setattr("core.auth.AuthService", lambda: service)
    monkeypatch.setattr("core.auth_persistence.clear_persisted_tokens", _clear_persisted_tokens)
    monkeypatch.setattr("core.auth._log_activity", lambda *_args, **_kwargs: None)

    clear_auth_session()

    assert state[AUTH_USER_KEY] is None
    assert state[AUTH_ACCESS_TOKEN_KEY] is None
    assert state[AUTH_REFRESH_TOKEN_KEY] is None
    assert state[AUTH_VIEW_KEY] == "sign_in"
    assert state["active_page"] == PUBLIC_DEFAULT_PAGE
    assert TENANT_USER_KEY not in state
    assert "projects" not in state
    assert cleared_cookies == [True]
    assert fake_admin.calls == ["restored-access"]
    assert fake_auth.set_session_calls == []


def test_clear_auth_session_in_one_tab_does_not_leave_other_tab_signed_in(monkeypatch):
    tab_a = _SessionState(
        {
            AUTH_USER_KEY: User(
                id=TEST_USER_ID,
                email="tester@example.com",
                email_verified=True,
            ),
            AUTH_ACCESS_TOKEN_KEY: "shared-access",
            AUTH_REFRESH_TOKEN_KEY: "shared-refresh",
            "active_page": "workspace",
            TENANT_USER_KEY: TEST_USER_ID,
            "draft_report": {"report": {"narrative": "secret"}},
        }
    )
    tab_b = _SessionState(
        {
            AUTH_USER_KEY: User(
                id=TEST_USER_ID,
                email="tester@example.com",
                email_verified=True,
            ),
            AUTH_ACCESS_TOKEN_KEY: "shared-access",
            AUTH_REFRESH_TOKEN_KEY: "shared-refresh",
            "active_page": "workspace",
            TENANT_USER_KEY: TEST_USER_ID,
            "selected_report": {"name": "secret"},
        }
    )

    cookie_store = {"present": True}

    def _clear_persisted_tokens():
        cookie_store["present"] = False

    service = _logout_service(monkeypatch)
    fake_client, _, _ = _make_logout_fake_client()
    service._client = fake_client
    monkeypatch.setattr("core.auth.AuthService", lambda: service)
    monkeypatch.setattr("core.auth_persistence.clear_persisted_tokens", _clear_persisted_tokens)
    monkeypatch.setattr("core.auth._log_activity", lambda *_args, **_kwargs: None)

    monkeypatch.setattr("streamlit.session_state", tab_a)
    clear_auth_session()

    assert tab_a[AUTH_USER_KEY] is None
    assert cookie_store["present"] is False

    monkeypatch.setattr("streamlit.session_state", tab_b)
    clear_auth_session()

    assert tab_b[AUTH_USER_KEY] is None
    assert tab_b[AUTH_ACCESS_TOKEN_KEY] is None
    assert tab_b[AUTH_REFRESH_TOKEN_KEY] is None
    assert "selected_report" not in tab_b
    assert tab_b["active_page"] == PUBLIC_DEFAULT_PAGE


def test_clear_auth_session_never_raises_when_remote_logout_fails(monkeypatch):
    from supabase_auth.errors import AuthApiError

    state = _SessionState(
        {
            AUTH_USER_KEY: User(
                id=TEST_USER_ID,
                email="tester@example.com",
                email_verified=True,
            ),
            AUTH_ACCESS_TOKEN_KEY: "broken-access",
            AUTH_REFRESH_TOKEN_KEY: "broken-refresh",
            "active_page": "workspace",
        }
    )
    monkeypatch.setattr("streamlit.session_state", state)

    service = _logout_service(monkeypatch)
    fake_client, _, _ = _make_logout_fake_client(
        admin_error=AuthApiError("Invalid JWT", 401, "bad_jwt")
    )
    service._client = fake_client
    monkeypatch.setattr("core.auth.AuthService", lambda: service)
    monkeypatch.setattr("core.auth_persistence.clear_persisted_tokens", lambda: None)
    monkeypatch.setattr("core.auth._log_activity", lambda *_args, **_kwargs: None)

    clear_auth_session()

    assert state[AUTH_USER_KEY] is None
    assert state[AUTH_ACCESS_TOKEN_KEY] is None
    assert state[AUTH_REFRESH_TOKEN_KEY] is None


def test_clear_auth_session_records_activity_after_session_is_cleared(monkeypatch):
    state = _SessionState(
        {
            AUTH_USER_KEY: User(
                id=TEST_USER_ID,
                email="tester@example.com",
                email_verified=True,
            ),
            AUTH_ACCESS_TOKEN_KEY: "access",
            AUTH_REFRESH_TOKEN_KEY: "refresh",
            "active_page": "workspace",
        }
    )
    monkeypatch.setattr("streamlit.session_state", state)

    activity_calls: list[tuple[str, str, str]] = []
    session_snapshot_at_log: list[object] = []

    def _capture_activity(user_id, action, message):
        activity_calls.append((user_id, action, message))
        session_snapshot_at_log.append(state.get(AUTH_USER_KEY))

    service = _logout_service(monkeypatch)
    fake_client, _, _ = _make_logout_fake_client()
    service._client = fake_client
    monkeypatch.setattr("core.auth.AuthService", lambda: service)
    monkeypatch.setattr("core.auth_persistence.clear_persisted_tokens", lambda: None)
    monkeypatch.setattr("core.auth._log_activity", _capture_activity)

    clear_auth_session()

    assert state[AUTH_USER_KEY] is None
    assert state["active_page"] == PUBLIC_DEFAULT_PAGE
    assert activity_calls == [(TEST_USER_ID, "user.signed_out", "Signed out")]
    assert session_snapshot_at_log == [None]


def test_clear_auth_session_is_idempotent_when_cookie_delete_raises(monkeypatch):
    from core.auth_persistence import AUTH_COOKIE_NAME

    state = _SessionState(
        {
            AUTH_USER_KEY: User(
                id=TEST_USER_ID,
                email="tester@example.com",
                email_verified=True,
            ),
            AUTH_ACCESS_TOKEN_KEY: "access",
            AUTH_REFRESH_TOKEN_KEY: "refresh",
            "active_page": "workspace",
            TENANT_USER_KEY: TEST_USER_ID,
            "projects": [{"id": "project-1"}],
        }
    )
    monkeypatch.setattr("streamlit.session_state", state)

    class _MissingCookieManager:
        def delete(self, name):
            raise KeyError(name)

    service = _logout_service(monkeypatch)
    fake_client, _, _ = _make_logout_fake_client()
    service._client = fake_client
    monkeypatch.setattr("core.auth.AuthService", lambda: service)
    monkeypatch.setattr(
        "core.auth_persistence._try_cookie_manager",
        lambda: _MissingCookieManager(),
    )
    monkeypatch.setattr("core.auth._log_activity", lambda *_args, **_kwargs: None)

    clear_auth_session()
    clear_auth_session()

    assert state[AUTH_USER_KEY] is None
    assert state[AUTH_ACCESS_TOKEN_KEY] is None
    assert state[AUTH_REFRESH_TOKEN_KEY] is None
    assert state["active_page"] == PUBLIC_DEFAULT_PAGE
    assert TENANT_USER_KEY not in state
    assert "projects" not in state


def test_clear_auth_session_after_browser_refresh_with_missing_cookie(monkeypatch):
    from supabase_auth.errors import AuthApiError

    state = _SessionState(
        {
            AUTH_USER_KEY: User(
                id=TEST_USER_ID,
                email="tester@example.com",
                email_verified=True,
            ),
            AUTH_ACCESS_TOKEN_KEY: "restored-access",
            AUTH_REFRESH_TOKEN_KEY: "restored-refresh",
            AUTH_VIEW_KEY: "workspace",
            "active_page": "workspace",
            TENANT_USER_KEY: TEST_USER_ID,
            "projects": [{"id": "project-1"}],
        }
    )
    monkeypatch.setattr("streamlit.session_state", state)

    class _MissingCookieManager:
        def delete(self, name):
            raise KeyError(AUTH_COOKIE_NAME)

    service = _logout_service(monkeypatch)
    fake_client, fake_auth, fake_admin = _make_logout_fake_client(
        admin_error=AuthApiError(
            "Session from session_id claim in JWT does not exist",
            403,
            "session_not_found",
        )
    )
    service._client = fake_client
    monkeypatch.setattr("core.auth.AuthService", lambda: service)
    monkeypatch.setattr(
        "core.auth_persistence._try_cookie_manager",
        lambda: _MissingCookieManager(),
    )
    monkeypatch.setattr("core.auth._log_activity", lambda *_args, **_kwargs: None)

    clear_auth_session()

    assert state[AUTH_USER_KEY] is None
    assert state[AUTH_ACCESS_TOKEN_KEY] is None
    assert state[AUTH_REFRESH_TOKEN_KEY] is None
    assert state[AUTH_VIEW_KEY] == "sign_in"
    assert state["active_page"] == PUBLIC_DEFAULT_PAGE
    assert TENANT_USER_KEY not in state
    assert "projects" not in state
    assert fake_admin.calls == ["restored-access"]
    assert fake_auth.set_session_calls == []


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


def test_auth_dev_bypass_blocked_outside_development(monkeypatch):
    monkeypatch.setattr("config.ENVIRONMENT", "production")
    monkeypatch.setattr("config._AUTH_DEV_BYPASS_REQUESTED", True)

    from config import auth_dev_bypass_enabled, validate_production_auth_configuration

    assert auth_dev_bypass_enabled() is False

    warnings = validate_production_auth_configuration()
    assert any("Configuration Error" in message for message in warnings)
    assert any("Development authentication cannot be enabled in production." in message for message in warnings)


def test_production_rejects_localhost_auth_redirect(monkeypatch):
    monkeypatch.setattr("config.ENVIRONMENT", "production")
    monkeypatch.setattr("config._AUTH_DEV_BYPASS_REQUESTED", False)
    monkeypatch.setattr(
        "config.AUTH_REDIRECT_URL",
        "http://localhost:8501/?active_page=auth",
    )
    monkeypatch.setattr("config.SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr("config.SUPABASE_ANON_KEY", "anon-key")

    from config import validate_production_auth_configuration

    warnings = validate_production_auth_configuration()
    assert any("AUTH_REDIRECT_URL" in message for message in warnings)
    assert any("localhost" in message for message in warnings)
