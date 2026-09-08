"""
Tests for storage.json_storage.JSONStorage.update() — the atomic
read-modify-write primitive that replaces the previous
load()-then-save() pattern in JsonProjectRepository.upsert_document().

That previous pattern had a real race: two concurrent writers each call
load() and see the same "before" state, each mutate their own in-memory
copy, and whichever save() runs second silently discards the first
writer's change. update() holds one lock across the whole load-mutate-
save cycle specifically to close that window — the concurrency test
below reproduces the race directly (real threads, not just unit-testing
the happy path) to prove it actually does.
"""

from __future__ import annotations

import threading
import time

import pytest

from storage.json_storage import JSONStorage


def test_update_mutates_in_place(tmp_path):
    storage = JSONStorage(tmp_path / "data.json")
    storage.save([{"id": "a"}])

    def add_b(data):
        data.append({"id": "b"})

    result = storage.update(add_b)

    assert result == [{"id": "a"}, {"id": "b"}]
    assert storage.load() == [{"id": "a"}, {"id": "b"}]


def test_update_accepts_a_replacement_return_value(tmp_path):
    storage = JSONStorage(tmp_path / "data.json")
    storage.save([{"id": "a"}])

    result = storage.update(lambda data: [{"id": "replaced"}])

    assert result == [{"id": "replaced"}]
    assert storage.load() == [{"id": "replaced"}]


def test_update_persists_even_when_mutate_returns_none_and_makes_no_change(tmp_path):
    storage = JSONStorage(tmp_path / "data.json")
    storage.save([{"id": "a"}])

    result = storage.update(lambda data: None)

    assert result == [{"id": "a"}]
    assert storage.load() == [{"id": "a"}]


def test_concurrent_updates_to_the_same_file_do_not_lose_writes(tmp_path):
    """The actual regression test for the original bug: two threads each
    add a distinct item to the same underlying file via update(). Every
    item must survive — none silently dropped by a losing writer's save()
    overwriting the other's.

    A deliberate sleep between load and save inside the mutator widens
    the race window so this fails reliably without the fix (proven by
    running the same scenario against the old load()-then-save() pattern
    below) instead of only occasionally under real timing.
    """

    path = tmp_path / "shared.json"
    storage = JSONStorage(path)
    storage.save([])

    errors: list[BaseException] = []

    def add_item(item_id: str):
        try:
            def mutate(data):
                data.append({"id": item_id})
                time.sleep(0.05)  # widen the window while the lock is held

            storage.update(mutate)
        except BaseException as exc:  # pragma: no cover - surfaced via errors list
            errors.append(exc)

    threads = [
        threading.Thread(target=add_item, args=(f"item-{i}",)) for i in range(8)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    assert not errors
    final = storage.load()
    assert {item["id"] for item in final} == {f"item-{i}" for i in range(8)}
    assert len(final) == 8


def test_the_old_load_then_save_pattern_does_lose_writes_under_the_same_race(tmp_path):
    """Not testing production code — this documents *why* update() exists
    by reproducing the exact bug the old JsonProjectRepository.
    upsert_document() had (separate .load() then .save() calls, no lock
    held across them) and showing it really does drop concurrent writes
    under the same race the fixed version survives above."""

    path = tmp_path / "shared.json"
    storage = JSONStorage(path)
    storage.save([])

    def add_item_unsafely(item_id: str):
        data = storage.load()
        data.append({"id": item_id})
        time.sleep(0.05)
        storage.save(data)

    threads = [
        threading.Thread(target=add_item_unsafely, args=(f"item-{i}",))
        for i in range(8)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    final = storage.load()
    # The whole point of this test: at least one write got clobbered.
    assert len(final) < 8
