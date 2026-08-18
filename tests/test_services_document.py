"""
Unit tests for DocumentService.
"""

from __future__ import annotations

import pytest

from services.document_service import DocumentService
from tests.conftest import MockUpload


def test_save_and_list_documents(
    document_service: DocumentService,
    project_service,
):
    project = project_service.create_project("Document Service Test")

    metadata = document_service.save_document(
        project["id"],
        MockUpload(
            "minutes.txt",
            b"Quarterly board minutes.",
        ),
    )

    assert metadata["filename"] == "minutes.txt"
    assert metadata["size"] > 0

    documents = document_service.get_documents(project["id"])

    assert len(documents) == 1
    assert documents[0]["filename"] == "minutes.txt"


def test_delete_document(
    document_service: DocumentService,
    project_service,
):
    project = project_service.create_project("Delete Document Test")

    document_service.save_document(
        project["id"],
        MockUpload("draft.txt", b"Temporary draft."),
    )

    document_service.delete_document(
        project["id"],
        "draft.txt",
    )

    assert document_service.get_documents(project["id"]) == []


def test_save_document_rejects_duplicate(
    document_service: DocumentService,
    project_service,
):
    project = project_service.create_project("Duplicate Document Test")
    upload = MockUpload("policy.txt", b"Policy document.")

    metadata = document_service.save_document(project["id"], upload)
    # The real upload endpoint always registers the upload on the project
    # record immediately after save_document() succeeds (api/routers/
    # knowledge.py's upload_knowledge()) — the duplicate check now follows
    # that record, so the test must mirror the real flow to exercise it.
    project_service.upsert_document(
        project["id"],
        {"id": "doc-1", "filename": metadata["filename"]},
    )

    with pytest.raises(ValueError, match="already exists"):
        document_service.save_document(project["id"], upload)


def test_save_document_succeeds_after_project_record_removed_but_blob_orphaned(
    document_service: DocumentService,
    project_service,
):
    """
    Regression test reproducing the reported bug: upload a document,
    register it on the project record (matching the real upload endpoint,
    which calls save_document() then ProjectService.upsert_document()),
    then remove it from project["documents"] the way the real delete
    endpoint does — WITHOUT also removing the physical blob, simulating a
    delete whose storage-level removal silently failed. The file is now
    an orphan: physically present, unreferenced. Re-uploading the same
    filename must succeed instead of raising "already exists" — the
    duplicate check must follow project["documents"], not a raw storage
    listing that still has the orphan in it.
    """
    project = project_service.create_project("Orphan Recovery Test")

    document_service.save_document(
        project["id"],
        MockUpload("orphaned.txt", b"Original content."),
    )
    project = project_service.get_project(project["id"])
    project["documents"] = [{"id": "doc-1", "filename": "orphaned.txt"}]
    project_service.update_project(project)

    # The delete endpoint's project-record update, with the physical
    # storage delete having silently failed (the blob is left behind).
    project["documents"] = []
    project_service.update_project(project)

    # The blob is still physically present in storage.
    assert document_service._file_store.list_files(project["id"], "documents") == [
        "orphaned.txt"
    ]

    # Re-upload must now succeed instead of raising ValueError.
    metadata = document_service.save_document(
        project["id"],
        MockUpload("orphaned.txt", b"New content."),
    )

    assert metadata["filename"] == "orphaned.txt"
    assert metadata["size"] == len(b"New content.")


def test_rejects_unsafe_filename(document_service: DocumentService):
    with pytest.raises(ValueError, match="Invalid filename"):
        document_service._safe_filename("")

    with pytest.raises(ValueError, match="Invalid filename"):
        document_service._safe_filename("..")
