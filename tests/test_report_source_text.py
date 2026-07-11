"""Tests for report source text normalization."""

from __future__ import annotations

from services.report_source_text import normalize_combined_source_text


def test_normalize_combined_source_text_keeps_small_documents():
    combined = (
        "=== SOURCE DOCUMENT: alpha.txt ===\n\n"
        "Alpha content.\n\n"
        "=== SOURCE DOCUMENT: beta.txt ===\n\n"
        "Beta content."
    )

    normalized, was_normalized = normalize_combined_source_text(combined)

    assert "Alpha content." in normalized
    assert "Beta content." in normalized
    assert "trimmed" not in normalized.lower()


def test_normalize_combined_source_text_preserves_large_documents():
    long_body = "x" * 5000
    combined = f"=== SOURCE DOCUMENT: big.txt ===\n\n{long_body}"

    normalized, _was_normalized = normalize_combined_source_text(combined)

    assert len(normalized) >= len(long_body)
    assert "trimmed" not in normalized.lower()
    assert "big.txt" in normalized


def test_normalize_combined_source_text_collapses_excess_whitespace():
    combined = (
        "=== SOURCE DOCUMENT: notes.txt ===\n\n"
        "Line one.\n\n\n\n\nLine two."
    )

    normalized, was_normalized = normalize_combined_source_text(combined)

    assert "Line one.\n\nLine two." in normalized
    assert was_normalized
