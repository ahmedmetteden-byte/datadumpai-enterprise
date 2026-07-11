"""
Split large source documents into logical chunks for multi-stage analysis.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from services.report_source_text import SOURCE_SECTION_PATTERN

HEADING_LINE = re.compile(
    r"^(#{1,6}\s+.+|(?:\d+(?:\.\d+)*)\s+.+|[A-Z][A-Z0-9 &/-]{3,})$",
    re.MULTILINE,
)

SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")


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

            if cut:
                chunk = " ".join(sentences[:cut]).strip()
                remaining = remaining[len(chunk) :].lstrip()
            else:
                chunk = window.strip()
                remaining = remaining[chunk_size:].lstrip()
        else:
            chunk = window[:split_at].strip()
            remaining = remaining[split_at:].lstrip()

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
