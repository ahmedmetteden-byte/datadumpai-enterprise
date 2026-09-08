"""
Tests for the document-truncation cap in the indexing pipeline.

services.indexing_service._chunk_document_text caps extremely large
documents at MAX_CHUNKS_PER_DOCUMENT chunks — a real, deliberate limit
(unbounded chunk counts would blow up embedding cost and Qdrant storage
for one outlier upload), but the cap used to bite silently: nothing
recorded whether it actually applied, so a document could be indexed as
"done" while only a fraction of it was ever retrievable for reports or
Ask, with no signal anywhere. These tests cover the fix: the chunker now
reports whether it truncated, so the caller can persist and surface it.
"""

from __future__ import annotations

from services.document_chunking import DocumentChunk
from services.indexing_service import MAX_CHUNKS_PER_DOCUMENT, _chunk_document_text


def _fake_chunks(count: int) -> list[DocumentChunk]:
    return [
        DocumentChunk(
            source_document="doc.txt",
            chunk_index=i,
            total_chunks=count,
            heading="Section",
            text=f"chunk {i} text",
        )
        for i in range(count)
    ]


def test_chunk_document_text_not_truncated_under_the_cap(monkeypatch):
    monkeypatch.setattr(
        "services.indexing_service.chunk_combined_source_text",
        lambda *a, **k: _fake_chunks(MAX_CHUNKS_PER_DOCUMENT - 1),
    )

    chunks, truncated = _chunk_document_text("doc.txt", "some text")

    assert truncated is False
    assert len(chunks) == MAX_CHUNKS_PER_DOCUMENT - 1


def test_chunk_document_text_not_truncated_exactly_at_the_cap(monkeypatch):
    monkeypatch.setattr(
        "services.indexing_service.chunk_combined_source_text",
        lambda *a, **k: _fake_chunks(MAX_CHUNKS_PER_DOCUMENT),
    )

    chunks, truncated = _chunk_document_text("doc.txt", "some text")

    assert truncated is False
    assert len(chunks) == MAX_CHUNKS_PER_DOCUMENT


def test_chunk_document_text_truncated_over_the_cap(monkeypatch):
    monkeypatch.setattr(
        "services.indexing_service.chunk_combined_source_text",
        lambda *a, **k: _fake_chunks(MAX_CHUNKS_PER_DOCUMENT + 50),
    )

    chunks, truncated = _chunk_document_text("doc.txt", "some very large document")

    assert truncated is True
    assert len(chunks) == MAX_CHUNKS_PER_DOCUMENT


def test_chunk_document_text_empty_text_returns_no_chunks_not_truncated():
    chunks, truncated = _chunk_document_text("doc.txt", "   ")

    assert chunks == []
    assert truncated is False
