"""
DataDumpAI Enterprise
JSON Storage Engine
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Callable

# One lock per underlying file, shared across every JSONStorage instance
# pointed at it. A fresh JSONStorage (and the repository/service wrapping
# it) is constructed per request/background-task, so a lock as an
# *instance* attribute would do nothing to serialize two instances racing
# on the same file — this registry is what actually makes that happen.
# In-process threading.Lock is the right primitive here (not multiprocess
# file locking): this is dev/test-only storage, and FastAPI's sync
# BackgroundTasks (e.g. the indexing job) run in this same process's
# thread pool, genuinely concurrently with request-handling threads.
_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _lock_for(path: Path) -> threading.Lock:
    key = str(path.resolve())
    with _locks_guard:
        lock = _locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _locks[key] = lock
        return lock


class JSONStorage:
    """
    Generic JSON persistence layer.
    """

    def __init__(self, path: str | Path):

        self.path = Path(path)
        self._lock = _lock_for(self.path)

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not self.path.exists():

            self.save([])

    def _load_unlocked(self) -> list[dict[str, Any]]:
        with self.path.open(
            encoding="utf-8",
        ) as file:

            return json.load(file)

    def _save_unlocked(
        self,
        data: list[dict[str, Any]],
    ) -> None:
        with self.path.open(
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                data,
                file,
                indent=2,
            )

            file.write("\n")

    def load(self) -> list[dict[str, Any]]:
        with self._lock:
            return self._load_unlocked()

    def save(
        self,
        data: list[dict[str, Any]],
    ) -> None:
        with self._lock:
            self._save_unlocked(data)

    def update(
        self,
        mutate: Callable[[list[dict[str, Any]]], list[dict[str, Any]] | None],
    ) -> list[dict[str, Any]]:
        """Atomically load, mutate, and save in one critical section — the
        only safe way to do a read-modify-write against this file.

        `mutate` receives the current list and may either mutate it in
        place (returning None) or return a replacement list. Holding the
        lock across the whole load+mutate+save cycle is the actual fix:
        calling .load() and .save() as two separate calls (the previous
        pattern in callers like JsonProjectRepository.upsert_document)
        leaves a window where a second writer's load() sees the same
        stale "before" state, and whichever save() runs second silently
        discards the first writer's change.
        """

        with self._lock:
            data = self._load_unlocked()
            result = mutate(data)
            final = result if result is not None else data
            self._save_unlocked(final)
            return final