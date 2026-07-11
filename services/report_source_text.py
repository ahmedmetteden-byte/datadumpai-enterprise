"""
Prepare combined source text for report generation without discarding substance.
"""

from __future__ import annotations

import re

SOURCE_SECTION_PATTERN = re.compile(
    r"(=== SOURCE DOCUMENT: .+? ===\n\n)",
    re.DOTALL,
)

WHITESPACE_RUN = re.compile(r"[ \t]+")
BLANK_LINES = re.compile(r"\n{3,}")
REPEATED_LINE_WINDOW = 4


def _split_source_sections(combined_text: str) -> list[tuple[str, str]]:
    parts = SOURCE_SECTION_PATTERN.split(combined_text)

    if len(parts) <= 1:
        return []

    sections: list[tuple[str, str]] = []
    index = 1

    while index < len(parts):
        header = parts[index]
        body = parts[index + 1] if index + 1 < len(parts) else ""
        sections.append((header, body.rstrip()))
        index += 2

    return sections


def _collapse_whitespace(text: str) -> str:
    normalized = WHITESPACE_RUN.sub(" ", text)
    normalized = BLANK_LINES.sub("\n\n", normalized)
    return normalized.strip()


def _dedupe_repeated_lines(text: str) -> str:
    """Remove consecutive duplicate lines (common headers/footers), not unique content."""

    lines = text.splitlines()
    if len(lines) < 2:
        return text

    cleaned: list[str] = []
    previous_window: list[str] = []

    for line in lines:
        stripped = line.strip()

        if (
            stripped
            and len(previous_window) >= REPEATED_LINE_WINDOW
            and previous_window[-REPEATED_LINE_WINDOW:] == [stripped] * REPEATED_LINE_WINDOW
        ):
            continue

        cleaned.append(line)
        if stripped:
            previous_window.append(stripped)
            if len(previous_window) > REPEATED_LINE_WINDOW:
                previous_window.pop(0)

    return "\n".join(cleaned)


def normalize_document_body(text: str) -> str:
    """Normalize one document body — whitespace and boilerplate only."""

    return _dedupe_repeated_lines(_collapse_whitespace(text))


def normalize_combined_source_text(combined_text: str) -> tuple[str, bool]:
    """
    Normalize combined source text without truncating substantive content.

    Returns (normalized_text, was_normalized).
    """

    original = combined_text.strip()
    if not original:
        return "", False

    sections = _split_source_sections(original)

    if not sections:
        normalized = normalize_document_body(original)
        return normalized, normalized != original

    normalized_sections: list[str] = []

    for header, body in sections:
        normalized_body = normalize_document_body(body)
        normalized_sections.append(f"{header}{normalized_body}")

    normalized = "\n\n".join(normalized_sections)
    return normalized, normalized != original


def prepare_combined_source_text(combined_text: str) -> dict[str, object]:
    """Prepare source text for analysis and report whether normalization ran."""

    normalized, was_normalized = normalize_combined_source_text(combined_text)

    return {
        "combined_text": normalized,
        "normalized": was_normalized,
        "multi_stage_recommended": len(normalized) > 0,
    }
