"""
Regression tests: Supabase Storage deletes must retry transient failures
and never leak the raw storage3 client exception up to callers — mirrors
tests/test_file_store_supabase_download_retry.py for delete(). Also
covers list_files()'s pagination, since Storage's list() caps at 100
objects per call and previously wasn't paginated at all.
"""

from __future__ import annotations

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
    def __init__(self, behaviors: list, *, pages: list[list[dict]] | None = None) -> None:
        self._behaviors = list(behaviors)
        self.calls = 0
        self._pages = pages or []
        self.list_calls: list[tuple[str, dict]] = []

    def from_(self, bucket_name: str):
        return self

    def remove(self, keys: list) -> None:
        self.calls += 1
        behavior = self._behaviors.pop(0)
        if isinstance(behavior, Exception):
            raise behavior
        return behavior

    def list(self, prefix: str, options: dict) -> list[dict]:
        self.list_calls.append((prefix, dict(options)))
        offset = options["offset"] // options["limit"]
        if offset >= len(self._pages):
            return []
        return self._pages[offset]


class _FakeSupabaseClient:
    def __init__(self, behaviors: list, *, pages: list[list[dict]] | None = None) -> None:
        self.storage = _FakeBucket(behaviors, pages=pages)


@pytest.fixture(autouse=True)
def _bound_user():
    bind_current_user(TEST_USER)
    yield


def _supabase_file_store(
    monkeypatch, behaviors: list, *, pages: list[list[dict]] | None = None
) -> tuple[FileStore, _FakeSupabaseClient]:
    store = FileStore(TEST_USER, access_token="fake-token")
    store._backend = "supabase"
    fake_client = _FakeSupabaseClient(behaviors, pages=pages)
    monkeypatch.setattr(store, "_supabase_client", lambda: fake_client)
    monkeypatch.setattr("storage.file_store.time.sleep", lambda _seconds: None)
    return store, fake_client


def test_delete_retries_transient_failure_then_succeeds(monkeypatch):
    store, fake_client = _supabase_file_store(
        monkeypatch,
        [RuntimeError("network blip"), None],
    )

    store.delete(f"{TEST_USER.id}/project/documents/report.pdf")

    assert fake_client.storage.calls == 2


def test_delete_raises_clean_error_after_exhausting_retries(monkeypatch):
    store, fake_client = _supabase_file_store(
        monkeypatch,
        [RuntimeError("network blip"), RuntimeError("network blip"), RuntimeError("network blip")],
    )

    with pytest.raises(RuntimeError) as exc_info:
        store.delete(f"{TEST_USER.id}/project/documents/report.pdf")

    message = str(exc_info.value)
    assert "report.pdf" in message
    assert fake_client.storage.calls == 3
    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_delete_succeeds_on_first_attempt_without_sleeping(monkeypatch):
    store, fake_client = _supabase_file_store(monkeypatch, [None])
    monkeypatch.setattr(
        "storage.file_store.time.sleep",
        lambda _seconds: pytest.fail("should not sleep when the first attempt succeeds"),
    )

    store.delete(f"{TEST_USER.id}/project/documents/report.pdf")

    assert fake_client.storage.calls == 1


def test_list_files_paginates_beyond_the_first_page(monkeypatch):
    page_one = [{"name": f"file-{i}.pdf"} for i in range(100)]
    page_two = [{"name": f"file-{i}.pdf"} for i in range(100, 140)]
    store, fake_client = _supabase_file_store(monkeypatch, [], pages=[page_one, page_two])

    names = store.list_files("project", "documents")

    assert len(names) == 140
    assert len(fake_client.storage.list_calls) == 2
    assert fake_client.storage.list_calls[0][1] == {"limit": 100, "offset": 0}
    assert fake_client.storage.list_calls[1][1] == {"limit": 100, "offset": 100}


def test_list_files_stops_after_a_short_page(monkeypatch):
    page_one = [{"name": f"file-{i}.pdf"} for i in range(40)]
    store, fake_client = _supabase_file_store(monkeypatch, [], pages=[page_one])

    names = store.list_files("project", "documents")

    assert len(names) == 40
    assert len(fake_client.storage.list_calls) == 1
