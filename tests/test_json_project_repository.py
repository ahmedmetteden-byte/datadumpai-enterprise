"""
Regression test for the real-world scenario JSONStorage.update() was
built to fix: two concurrent document uploads (or an upload racing the
indexing background job's status update) into the same project must not
silently drop one another — see
services.project_service.ProjectService.upsert_document()'s docstring
and JSONStorage.update()'s docstring for the mechanics.
"""

from __future__ import annotations

import threading
import time

from core.current_user import CurrentUser
from repositories.project_repository import ProjectRepository
from services.project_service import ProjectService
from tests.conftest import TEST_USER


def test_concurrent_document_uploads_into_the_same_project_all_survive(isolated_env):
    project = ProjectService().create_project("Acme Q4")
    project_id = project["id"]

    errors: list[BaseException] = []

    def upload(index: int):
        try:
            # contextvars.ContextVar (core.current_user's binding) is not
            # inherited by a new OS thread, so pass the user explicitly
            # rather than relying on require_current_user() here — this
            # also matches how a real request thread and the indexing
            # background task each build their own independent
            # ProjectRepository, rather than sharing one instance.
            repository = ProjectRepository(CurrentUser.from_user(TEST_USER))
            document = {
                "id": f"doc-{index}",
                "filename": f"file-{index}.pdf",
                "status": "uploaded",
            }
            repository.upsert_document(project_id, document, size_delta=100)
        except BaseException as exc:  # pragma: no cover - surfaced via errors list
            errors.append(exc)

    # Patch a brief delay into the write path so the ten near-simultaneous
    # uploads below actually overlap instead of completing too fast to
    # ever race in practice.
    from storage import json_storage

    original_save_unlocked = json_storage.JSONStorage._save_unlocked

    def delayed_save_unlocked(self, data):
        time.sleep(0.02)
        original_save_unlocked(self, data)

    json_storage.JSONStorage._save_unlocked = delayed_save_unlocked
    try:
        threads = [threading.Thread(target=upload, args=(i,)) for i in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)
    finally:
        json_storage.JSONStorage._save_unlocked = original_save_unlocked

    assert not errors

    final_project = ProjectService().get_project(project_id)
    filenames = {doc["filename"] for doc in final_project["documents"]}
    assert filenames == {f"file-{i}.pdf" for i in range(10)}
    # storage_used must reflect every upload's size_delta too, not just
    # whichever write happened to win a race.
    assert final_project["storage_used"] == 100 * 10


def test_upsert_document_updates_existing_document_by_id(isolated_env):
    project = ProjectService().create_project("Acme Q4")
    project_id = project["id"]
    repository = ProjectRepository()

    repository.upsert_document(
        project_id, {"id": "doc-1", "filename": "a.pdf", "status": "uploaded"}
    )
    repository.upsert_document(
        project_id, {"id": "doc-1", "filename": "a.pdf", "status": "indexed"}
    )

    documents = ProjectService().get_project(project_id)["documents"]
    assert len(documents) == 1
    assert documents[0]["status"] == "indexed"
