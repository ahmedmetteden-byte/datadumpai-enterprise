"""Tests for report source text trimming."""

from __future__ import annotations

from services.report_source_text import trim_combined_source_text


def test_trim_combined_source_text_keeps_small_documents():
    combined = (
        "=== SOURCE DOCUMENT: alpha.txt ===\n\n"
        "Alpha content.\n\n"
        "=== SOURCE DOCUMENT: beta.txt ===\n\n"
        "Beta content."
    )

    trimmed, was_truncated = trim_combined_source_text(
        combined,
        max_chars_per_doc=1000,
        max_total_chars=5000,
    )

    assert not was_truncated
    assert trimmed == combined


def test_trim_combined_source_text_limits_each_document():
    long_body = "x" * 5000
    combined = f"=== SOURCE DOCUMENT: big.txt ===\n\n{long_body}"

    trimmed, was_truncated = trim_combined_source_text(
        combined,
        max_chars_per_doc=1000,
        max_total_chars=5000,
    )

    assert was_truncated
    assert "big.txt" in trimmed
    assert len(trimmed) < len(combined)
    assert "trimmed" in trimmed
