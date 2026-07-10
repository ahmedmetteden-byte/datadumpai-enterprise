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

    document_service.save_document(project["id"], upload)

    with pytest.raises(ValueError, match="already exists"):
        document_service.save_document(project["id"], upload)


def test_rejects_unsafe_filename(document_service: DocumentService):
    with pytest.raises(ValueError, match="Invalid filename"):
        document_service._safe_filename("")

    with pytest.raises(ValueError, match="Invalid filename"):
        document_service._safe_filename("..")
