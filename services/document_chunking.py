"""
Split large source documents into logical chunks for multi-stage analysis.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from services.report_source_text import SOURCE_SECTION_PATTERN


# [ \t]+ (not \s+) between the marker and the heading text in the first two
# alternatives — \s+ also matches newlines, so a bare "#" or a lone number
# at the end of one line followed by ordinary text starting the next line
# (a common PDF-extraction artifact: page.extract_text() puts one number
# per line) could otherwise match as a single heading spanning both lines,
# incorrectly carving real body content (including a table's header row,
# if it happened to be the next line) out into a heading label instead of
# leaving it in the section body.
HEADING_LINE = re.compile(
    r"^(#{1,6}[ \t]+.+|(?:\d+(?:\.\d+)*)[ \t]+.+|[A-Z][A-Z0-9 &/-]{3,})$",
    re.MULTILINE,
)

SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")

_TABLE_ROW_LINE = re.compile(r"^\s*\|.+\|\s*$", re.MULTILINE)


def _table_spans(text: str) -> list[tuple[int, int]]:
    """Character-offset (start, end) spans of contiguous GFM table-row
    runs in text — a chunk boundary must never fall strictly inside one.
    Splitting a table's header row from its data rows (or a data row from
    its neighbours) leaves downstream table parsing
    (quantitative_analysis_service.extract_metric_tables()) to mistake a
    data row for the header, mislabeling a chart/finding with a raw
    figure instead of a metric name. Blank lines inside/around a run
    don't break it, so a table separated from surrounding prose by a
    blank line (document_processor.py's PDF table extraction) is still
    treated as one contiguous span."""

    spans: list[tuple[int, int]] = []
    offset = 0
    span_start: int | None = None
    span_end = 0

    for line in text.splitlines(keepends=True):
        stripped = line.strip()

        if _TABLE_ROW_LINE.match(stripped):
            if span_start is None:
                span_start = offset
            span_end = offset + len(line.rstrip("\n"))
        elif stripped:
            if span_start is not None:
                spans.append((span_start, span_end))
                span_start = None

        offset += len(line)

    if span_start is not None:
        spans.append((span_start, span_end))

    return spans


def _snap_outside_table_spans(cut_offset: int, spans: list[tuple[int, int]]) -> int:
    """Push a computed chunk-boundary offset outside any table span it
    falls strictly inside — to the span's start (deferring the whole
    table to the next chunk) when that's not degenerate, otherwise to the
    span's end (the table is bigger than one window; best effort)."""

    for start, end in spans:
        if start < cut_offset < end:
            return start if start > 0 else end

    return cut_offset


@dataclass(frozen=True)
class DocumentChunk:
    """A logical slice of one source document."""

    source_document: str
    chunk_index: int
    total_chunks: int
    heading: str
    text: str


def _split_by_headings(body: str) -> list[tuple[str, str]]:
    matches = list(HEADING_LINE.finditer(body))

    if not matches:
        return [("Section", body.strip())] if body.strip() else []

    sections: list[tuple[str, str]] = []
    preamble = body[: matches[0].start()].strip()

    if preamble:
        sections.append(("Introduction", preamble))

    for index, match in enumerate(matches):
        heading = match.group(0).strip().lstrip("#").strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        section_text = body[start:end].strip()

        if section_text:
            sections.append((heading, section_text))

    return sections


def _split_fixed_size(text: str, *, chunk_size: int, heading: str) -> list[tuple[str, str]]:
    if len(text) <= chunk_size:
        return [(heading, text)]

    parts: list[tuple[str, str]] = []
    remaining = text
    part_number = 1

    while remaining:
        if len(remaining) <= chunk_size:
            label = heading if part_number == 1 else f"{heading} (part {part_number})"
            parts.append((label, remaining.strip()))
            break

        window = remaining[:chunk_size]
        split_at = window.rfind("\n\n")

        if split_at < chunk_size // 2:
            sentences = SENTENCE_BOUNDARY.split(window)
            consumed = 0
            cut = 0

            for sentence in sentences:
                next_len = len(sentence) + (1 if cut else 0)
                if consumed + next_len > chunk_size and cut:
                    break
                consumed += next_len
                cut += 1

            cut_len = len(" ".join(sentences[:cut])) if cut else chunk_size
        else:
            cut_len = split_at

        # Never let the computed boundary fall inside a detected GFM
        # table — that would split a table's header from its data rows.
        cut_len = _snap_outside_table_spans(cut_len, _table_spans(remaining[:chunk_size]))
        cut_len = max(cut_len, 1)

        chunk = remaining[:cut_len].strip()
        remaining = remaining[cut_len:].lstrip()

        if chunk:
            label = heading if part_number == 1 else f"{heading} (part {part_number})"
            parts.append((label, chunk))
            part_number += 1

    return parts


def _chunk_document_body(
    body: str,
    *,
    source_document: str,
    chunk_size: int,
) -> list[DocumentChunk]:
    sections = _split_by_headings(body)
    labelled_parts: list[tuple[str, str]] = []

    for heading, section_text in sections:
        if len(section_text) <= chunk_size:
            labelled_parts.append((heading, section_text))
        else:
            labelled_parts.extend(
                _split_fixed_size(section_text, chunk_size=chunk_size, heading=heading)
            )

    if not labelled_parts and body.strip():
        labelled_parts = _split_fixed_size(body.strip(), chunk_size=chunk_size, heading="Document")

    total = len(labelled_parts)

    return [
        DocumentChunk(
            source_document=source_document,
            chunk_index=index,
            total_chunks=total,
            heading=heading,
            text=text,
        )
        for index, (heading, text) in enumerate(labelled_parts, start=1)
        if text.strip()
    ]


def chunk_combined_source_text(
    combined_text: str,
    *,
    chunk_size: int,
) -> list[DocumentChunk]:
    """Split combined source material into chunks, preserving every character of substance."""

    combined_text = combined_text.strip()
    if not combined_text:
        return []

    parts = SOURCE_SECTION_PATTERN.split(combined_text)

    if len(parts) <= 1:
        return _chunk_document_body(
            combined_text,
            source_document="combined",
            chunk_size=chunk_size,
        )

    chunks: list[DocumentChunk] = []
    index = 1

    while index < len(parts):
        header = parts[index]
        body = parts[index + 1] if index + 1 < len(parts) else ""
        match = re.search(r"=== SOURCE DOCUMENT:\s*(.+?)\s*===", header)

        source_document = match.group(1).strip() if match else f"document_{index}"
        chunks.extend(
            _chunk_document_body(
                body,
                source_document=source_document,
                chunk_size=chunk_size,
            )
        )
        index += 2

    return chunks
