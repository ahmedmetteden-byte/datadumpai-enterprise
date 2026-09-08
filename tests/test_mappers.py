"""
Tests for api/mappers.py's document -> DTO mapping, focused on the
`truncated` field: whether a document hit the indexing pipeline's
per-document chunk cap (services.indexing_service.MAX_CHUNKS_PER_DOCUMENT)
must be visible in every DTO a client can see it through, not just logged
server-side.
"""

from __future__ import annotations

from api.mappers import (
    document_processing_status,
    document_to_knowledge_detail,
    document_to_knowledge_item,
)

BASE_DOCUMENT = {
    "id": "doc_1",
    "filename": "quarterly-report.pdf",
    "status": "indexed",
    "uploaded_at": "2026-01-01T00:00:00+00:00",
}


def test_knowledge_item_reports_truncated_true():
    document = {**BASE_DOCUMENT, "chunks_truncated": True}

    item = document_to_knowledge_item(
        document,
        workspace_id="ws_1",
        workspace_name="Acme",
        author_id="user_1",
        author_name="Ada",
    )

    assert item.truncated is True


def test_knowledge_item_defaults_to_not_truncated():
    document = dict(BASE_DOCUMENT)

    item = document_to_knowledge_item(
        document,
        workspace_id="ws_1",
        workspace_name="Acme",
        author_id="user_1",
        author_name="Ada",
    )

    assert item.truncated is False


def test_knowledge_item_treats_explicit_false_as_not_truncated():
    document = {**BASE_DOCUMENT, "chunks_truncated": False}

    item = document_to_knowledge_item(
        document,
        workspace_id="ws_1",
        workspace_name="Acme",
        author_id="user_1",
        author_name="Ada",
    )

    assert item.truncated is False


def test_knowledge_detail_includes_truncated_in_metadata():
    document = {**BASE_DOCUMENT, "chunks_truncated": True, "chunk_count": 200}

    detail = document_to_knowledge_detail(
        document,
        workspace_id="ws_1",
        workspace_name="Acme",
        author_id="user_1",
        author_name="Ada",
    )

    assert detail.truncated is True
    assert detail.metadata["truncated"] is True
    assert detail.metadata["chunkCount"] == 200


def test_processing_status_reports_truncated_true():
    document = {**BASE_DOCUMENT, "chunks_truncated": True}

    status = document_processing_status(document)

    assert status.truncated is True
    assert status.status == "indexed"


def test_processing_status_defaults_to_not_truncated():
    document = dict(BASE_DOCUMENT)

    status = document_processing_status(document)

    assert status.truncated is False
