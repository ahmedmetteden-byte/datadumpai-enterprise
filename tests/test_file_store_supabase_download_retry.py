"""
Regression tests: Supabase Storage downloads must retry transient failures
and never leak the raw storage3 client exception (which can itself be a
confusing json.JSONDecodeError when the client's own error handling hits
an empty error response body) up to callers.
"""

from __future__ import annotations

import json

import pytest

from core.current_user import bind_current_user
from models.user import User
from storage.file_store import FileStore

TEST_USER = User(
    id="00000000-0000-4000-8000-000000000009",
    email="filestore-tester@example.com",
    full_name="File Store Tester",
    email_verified=True,
)


class _FakeBucket:
    def __init__(self, behaviors: list) -> None:
        self._behaviors = list(behaviors)
        self.calls = 0

    def from_(self, bucket_name: str):
        return self

    def download(self, key: str) -> bytes:
        self.calls += 1
        behavior = self._behaviors.pop(0)
        if isinstance(behavior, Exception):
            raise behavior
        return behavior


class _FakeSupabaseClient:
    def __init__(self, behaviors: list) -> None:
        self.storage = _FakeBucket(behaviors)


@pytest.fixture(autouse=True)
def _bound_user():
    bind_current_user(TEST_USER)
    yield


def _supabase_file_store(monkeypatch, behaviors: list) -> tuple[FileStore, _FakeSupabaseClient]:
    store = FileStore(TEST_USER, access_token="fake-token")
    store._backend = "supabase"
    fake_client = _FakeSupabaseClient(behaviors)
    monkeypatch.setattr(store, "_supabase_client", lambda: fake_client)
    monkeypatch.setattr("storage.file_store.time.sleep", lambda _seconds: None)
    return store, fake_client


def test_read_bytes_retries_transient_failure_then_succeeds(monkeypatch):
    empty_body_error = json.JSONDecodeError("Expecting value", "", 0)
    store, fake_client = _supabase_file_store(
        monkeypatch,
        [empty_body_error, b"file contents"],
    )

    data = store.read_bytes(f"{TEST_USER.id}/project/documents/report.pdf")

    assert data == b"file contents"
    assert fake_client.storage.calls == 2


def test_read_bytes_raises_clean_error_after_exhausting_retries(monkeypatch):
    empty_body_error = json.JSONDecodeError("Expecting value", "", 0)
    store, fake_client = _supabase_file_store(
        monkeypatch,
        [empty_body_error, empty_body_error, empty_body_error],
    )

    with pytest.raises(RuntimeError) as exc_info:
        store.read_bytes(f"{TEST_USER.id}/project/documents/report.pdf")

    message = str(exc_info.value)
    assert "report.pdf" in message
    assert "Expecting value" not in message
    assert fake_client.storage.calls == 3
    assert isinstance(exc_info.value.__cause__, json.JSONDecodeError)


def test_read_bytes_succeeds_on_first_attempt_without_sleeping(monkeypatch):
    store, fake_client = _supabase_file_store(monkeypatch, [b"file contents"])
    monkeypatch.setattr(
        "storage.file_store.time.sleep",
        lambda _seconds: pytest.fail("should not sleep when the first attempt succeeds"),
    )

    data = store.read_bytes(f"{TEST_USER.id}/project/documents/report.pdf")

    assert data == b"file contents"
    assert fake_client.storage.calls == 1
