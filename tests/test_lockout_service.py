"""
Defensive Supabase lockout backend tests.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from core.database import DatabaseError
from services.auth_service import AuthError, AuthService
from services.lockout_service import LockoutService


class FakeSupabaseError:
    def __init__(self, message: str) -> None:
        self.message = message


class FakeSupabaseResponse:
    def __init__(self, *, data=None, error=None) -> None:
        self.data = data
        self.error = error


class FakeQuery:
    def __init__(self, outcome) -> None:
        self._outcome = outcome

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def maybe_single(self):
        return self

    def upsert(self, *_args, **_kwargs):
        return self

    def execute(self):
        if isinstance(self._outcome, Exception):
            raise self._outcome
        if callable(self._outcome):
            return self._outcome()
        return self._outcome


class FakeSupabaseClient:
    def __init__(self, outcome) -> None:
        self._outcome = outcome
        self.upsert_payloads: list[dict] = []

    def table(self, _name: str) -> FakeQuery:
        if isinstance(self._outcome, dict) and "upsert" in self._outcome:
            return FakeUpsertQuery(self._outcome["upsert"], self.upsert_payloads)
        return FakeQuery(self._outcome)


class FakeUpsertQuery(FakeQuery):
    def __init__(self, outcome, payloads: list[dict]) -> None:
        super().__init__(outcome)
        self._payloads = payloads

    def upsert(self, payload, *_args, **_kwargs):
        self._payloads.append(payload)
        return self


def _enable_supabase_lockout(monkeypatch, client: FakeSupabaseClient) -> None:
    monkeypatch.setattr("config.use_database", lambda: True)
    monkeypatch.setattr("config.is_supabase_configured", lambda: True)
    monkeypatch.setattr("core.database.get_service_role_client", lambda: client)


@pytest.fixture
def supabase_lockout_service(monkeypatch):
    client = FakeSupabaseClient(FakeSupabaseResponse(data=None))
    _enable_supabase_lockout(monkeypatch, client)
    return LockoutService(), client


def test_load_treats_none_response_as_not_locked_out(supabase_lockout_service):
    service, client = supabase_lockout_service
    client._outcome = None

    record = service._load_record("user@example.com")

    assert record == LockoutService._default_record()
    service.check_allowed("user@example.com")


def test_load_treats_none_response_data_as_not_locked_out(supabase_lockout_service):
    service, client = supabase_lockout_service
    client._outcome = FakeSupabaseResponse(data=None)

    record = service._load_record("user@example.com")

    assert record == LockoutService._default_record()
    service.check_allowed("user@example.com")


def test_load_treats_empty_response_data_as_not_locked_out(supabase_lockout_service):
    service, client = supabase_lockout_service
    client._outcome = FakeSupabaseResponse(data={})

    record = service._load_record("user@example.com")

    assert record == LockoutService._default_record()
    service.check_allowed("user@example.com")


def test_load_handles_supabase_client_exception(supabase_lockout_service):
    service, client = supabase_lockout_service
    client._outcome = RuntimeError("network failure")

    record = service._load_record("user@example.com")

    assert record == LockoutService._default_record()
    service.check_allowed("user@example.com")


def test_load_handles_missing_table_error(supabase_lockout_service):
    service, client = supabase_lockout_service
    client._outcome = FakeSupabaseResponse(
        error=FakeSupabaseError('relation "public.login_lockouts" does not exist'),
    )

    record = service._load_record("user@example.com")

    assert record == LockoutService._default_record()
    service.check_allowed("user@example.com")


def test_load_handles_permission_denied_error(supabase_lockout_service):
    service, client = supabase_lockout_service
    client._outcome = FakeSupabaseResponse(
        error=FakeSupabaseError("permission denied for table login_lockouts"),
    )

    record = service._load_record("user@example.com")

    assert record == LockoutService._default_record()
    service.check_allowed("user@example.com")


def test_first_login_with_no_existing_lockout_record(supabase_lockout_service):
    service, _client = supabase_lockout_service

    record = service._load_record("new.user@example.com")

    assert record == LockoutService._default_record()
    service.check_allowed("new.user@example.com")
    service.record_failure("new.user@example.com")
    service.record_success("new.user@example.com")


def test_save_handles_none_response(supabase_lockout_service):
    service, client = supabase_lockout_service
    client._outcome = {"upsert": None}

    service.record_failure("user@example.com")
    service.record_success("user@example.com")


def test_save_handles_supabase_client_exception(supabase_lockout_service):
    service, client = supabase_lockout_service
    client._outcome = {"upsert": ConnectionError("connection reset")}

    service.record_failure("user@example.com")
    service.record_success("user@example.com")


def test_save_handles_permission_denied_error(supabase_lockout_service):
    service, client = supabase_lockout_service
    client._outcome = {
        "upsert": FakeSupabaseResponse(
            error=FakeSupabaseError("permission denied for table login_lockouts"),
        )
    }

    service.record_failure("user@example.com")
    service.record_success("user@example.com")


def test_save_handles_missing_table_error(supabase_lockout_service):
    service, client = supabase_lockout_service
    client._outcome = {
        "upsert": FakeSupabaseResponse(
            error=FakeSupabaseError('relation "public.login_lockouts" does not exist'),
        )
    }

    service.record_failure("user@example.com")
    service.record_success("user@example.com")


def test_load_handles_service_role_client_failure(monkeypatch):
    monkeypatch.setattr("config.use_database", lambda: True)
    monkeypatch.setattr("config.is_supabase_configured", lambda: True)
    monkeypatch.setattr(
        "core.database.get_service_role_client",
        lambda: (_ for _ in ()).throw(DatabaseError("Supabase is not configured.")),
    )

    service = LockoutService()

    assert service._load_record("user@example.com") == LockoutService._default_record()
    service.check_allowed("user@example.com")


def test_active_lockout_still_blocks_when_backend_is_healthy(supabase_lockout_service):
    service, client = supabase_lockout_service
    locked_until = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    client._outcome = FakeSupabaseResponse(
        data={
            "email": "locked@example.com",
            "failed_count": 5,
            "locked_until": locked_until,
            "last_attempt_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    with pytest.raises(AuthError, match="Too many failed sign-in attempts"):
        service.check_allowed("locked@example.com")


def test_sign_in_continues_when_lockout_backend_unavailable(monkeypatch):
    monkeypatch.setattr("config.auth_dev_bypass_enabled", lambda: False)
    monkeypatch.setattr("services.auth_service.is_supabase_configured", lambda: True)
    monkeypatch.setattr("config.use_database", lambda: True)
    monkeypatch.setattr("config.is_supabase_configured", lambda: True)
    monkeypatch.setattr(
        "core.database.get_service_role_client",
        lambda: FakeSupabaseClient(RuntimeError("network failure")),
    )

    class FakeUser:
        def model_dump(self):
            return {
                "id": "user-123",
                "email": "user@example.com",
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

    service = object.__new__(AuthService)
    service._client = type("Client", (), {"auth": FakeAuth()})()

    session = service.sign_in("user@example.com", "correct-password")

    assert session.user.email == "user@example.com"
    assert session.access_token == "access"
