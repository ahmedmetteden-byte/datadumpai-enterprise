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


def test_heading_detection_does_not_span_a_line_break():
    """Report Output Quality Upgrade Step D: the real root cause of a
    table header row vanishing from chunk text. HEADING_LINE's numbered-
    heading branch used \\s+ between the number and the heading text,
    which also matches a literal newline — so a bare number ending one
    line ("635.5") immediately followed by real content starting the next
    line ("| Year | Gross Premium | Gross Claims |", a table's header
    row) matched as ONE heading spanning both lines, stripping the table
    header out of the section body entirely. A real PDF's extract_text()
    commonly puts one number per line, making this a real-world failure
    mode, not a contrived one."""

    body = (
        "Some narrative text mentioning a figure of 635.5 at the end of a line.\n"
        "| Year | Gross Premium | Gross Claims |\n"
        "| 2022 | 789.6 | 420.0 |\n"
    )
    combined = f"=== SOURCE DOCUMENT: report.pdf ===\n\n{body}"

    chunks = chunk_combined_source_text(combined, chunk_size=10000)

    assert len(chunks) == 1
    assert "| Year | Gross Premium | Gross Claims |" in chunks[0].text
    assert "| Year | Gross Premium | Gross Claims |" not in chunks[0].heading


def test_chunking_never_splits_a_table_header_from_its_data_rows():
    """Report Output Quality Upgrade Step D: a real failure mode — a GFM
    table landing near a fixed-size chunk boundary used to get split
    between its header row and its data rows, leaving the first surviving
    data row mistaken for the header downstream
    (quantitative_analysis_service.extract_metric_tables() would then
    title a chart/finding with a raw figure like "789.6" instead of
    "Gross Premium"). Padding text is sized so the table's header row
    lands exactly where the old "\\n\\n" boundary search used to cut."""

    table = (
        "| Year | Gross Premium | Gross Claims |\n"
        "| 2022 | 789.6 | 420.0 |\n"
        "| 2023 | 1043.1 | 421.0 |\n"
        "| 2024 | 1558.7 | 635.5 |"
    )
    padding = "Filler sentence about the reporting period. " * 40
    combined = (
        "=== SOURCE DOCUMENT: report.pdf ===\n\n"
        f"{padding}\n\n{table}\n\n{padding}"
    )

    chunks = chunk_combined_source_text(combined, chunk_size=len(padding) + 20)

    # Every chunk that contains any table row must contain the whole table
    # — never a partial one starting mid-table.
    for chunk in chunks:
        if "| 2022 |" in chunk.text or "| Year |" in chunk.text:
            assert "| Year | Gross Premium | Gross Claims |" in chunk.text
            assert "| 2024 | 1558.7 | 635.5 |" in chunk.text


def test_chunking_defers_a_table_starting_near_the_window_boundary():
    """The table starts right where the fixed-size window would normally
    end — it must be deferred whole to the next chunk, not split."""

    table = (
        "| Year | Gross Premium |\n"
        "| 2022 | 789.6 |\n"
        "| 2023 | 1043.1 |\n"
        "| 2024 | 1558.7 |"
    )
    padding = "Filler sentence about premium growth trends. " * 30
    combined = f"=== SOURCE DOCUMENT: report.pdf ===\n\n{padding}\n\n{table}"

    chunks = chunk_combined_source_text(combined, chunk_size=len(padding) + 5)

    for chunk in chunks:
        if "| 2022 |" in chunk.text or "| Year |" in chunk.text:
            assert "| Year | Gross Premium |" in chunk.text
            assert "| 2024 | 1558.7 |" in chunk.text
