"""
Unit tests for ProjectService.
"""

from __future__ import annotations

import pytest

from services.project_service import ProjectService


def test_create_project_persists_metadata(project_service: ProjectService):
    project = project_service.create_project("Strategy Review")

    assert project["id"]
    assert project["name"] == "Strategy Review"
    assert project["documents"] == []
    assert project["reports"] == []

    loaded = project_service.get_project(project["id"])

    assert loaded["name"] == "Strategy Review"


def test_get_project_returns_copy(project_service: ProjectService):
    project = project_service.create_project("Copy Check")

    loaded = project_service.get_project(project["id"])
    loaded["name"] = "Mutated"

    reloaded = project_service.get_project(project["id"])

    assert reloaded["name"] == "Copy Check"


def test_create_project_rejects_duplicate_name(
    project_service: ProjectService,
):
    project_service.create_project("Duplicate Name")

    with pytest.raises(ValueError, match="already exists"):
        project_service.create_project("Duplicate Name")


def test_rename_project(project_service: ProjectService):
    project = project_service.create_project("Old Name")

    updated = project_service.rename_project(
        project["id"],
        "New Name",
    )

    assert updated["name"] == "New Name"
    assert project_service.get_project(project["id"])["name"] == "New Name"


def test_delete_project(project_service: ProjectService):
    project = project_service.create_project("Temporary Project")

    project_service.delete_project(project["id"])

    with pytest.raises(ValueError, match="Project not found"):
        project_service.get_project(project["id"])


def test_get_statistics(project_service: ProjectService):
    project_service.create_project("Stats Project A")
    project_service.create_project("Stats Project B")

    stats = project_service.get_statistics()

    assert stats["projects"] >= 2


def test_upsert_document_does_not_drop_other_documents(
    project_service: ProjectService,
):
    """
    Regression test: a document upload used to go through update_project(),
    which reads and rewrites a project's *entire* document list. The
    indexing background job does the same for every status update. Those
    two full-list read-modify-write cycles can interleave — a status update
    for an earlier document, still working from a snapshot taken before a
    later document was uploaded, would silently delete that later document
    when it wrote its stale list back. upsert_document() scopes the write
    to a single document row so this can't happen.
    """

    project = project_service.create_project("Race Safety")

    doc_a = {
        "id": "doc-a",
        "filename": "a.pdf",
        "size": 10,
        "uploaded_at": "t1",
        "path": "a.pdf",
    }
    project_service.upsert_document(
        project["id"], doc_a, size_delta=10, last_activity="t1"
    )

    doc_b = {
        "id": "doc-b",
        "filename": "b.pdf",
        "size": 20,
        "uploaded_at": "t2",
        "path": "b.pdf",
    }
    project_service.upsert_document(
        project["id"], doc_b, size_delta=20, last_activity="t2"
    )

    loaded = project_service.get_project(project["id"])
    assert {d["filename"] for d in loaded["documents"]} == {"a.pdf", "b.pdf"}

    # Simulate a delayed indexing status update for doc_a, computed from a
    # snapshot taken before doc_b existed. It must not remove doc_b.
    doc_a_indexed = {**doc_a, "status": "indexed"}
    project_service.upsert_document(project["id"], doc_a_indexed, last_activity="t3")

    reloaded = project_service.get_project(project["id"])
    filenames = {d["filename"] for d in reloaded["documents"]}
    assert filenames == {"a.pdf", "b.pdf"}
    assert reloaded["storage_used"] == 30
    updated_doc_a = next(d for d in reloaded["documents"] if d["filename"] == "a.pdf")
    assert updated_doc_a["status"] == "indexed"
