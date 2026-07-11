"""Tests for document chunking."""

from __future__ import annotations

from services.document_chunking import chunk_combined_source_text


def test_chunk_combined_source_text_splits_large_document():
    body = "\n\n".join(f"Paragraph {index}. " + ("detail " * 200) for index in range(20))
    combined = f"=== SOURCE DOCUMENT: large.txt ===\n\n{body}"

    chunks = chunk_combined_source_text(combined, chunk_size=2000)

    assert len(chunks) > 1
    assert all(chunk.source_document == "large.txt" for chunk in chunks)
    assert sum(len(chunk.text) for chunk in chunks) >= len(body) * 0.9


def test_chunk_combined_source_text_respects_headings():
    combined = (
        "=== SOURCE DOCUMENT: report.txt ===\n\n"
        "## Executive Summary\n\nSummary body.\n\n"
        "## Financial Review\n\nFinancial body."
    )

    chunks = chunk_combined_source_text(combined, chunk_size=10000)

    headings = {chunk.heading for chunk in chunks}
    assert "Executive Summary" in headings
    assert "Financial Review" in headings
