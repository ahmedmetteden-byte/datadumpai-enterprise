"""
Trim combined source text so report generation stays fast and within model limits.
"""

from __future__ import annotations

import re

SOURCE_SECTION_PATTERN = re.compile(
    r"(=== SOURCE DOCUMENT: .+? ===\n\n)",
    re.DOTALL,
)


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


def trim_combined_source_text(
    combined_text: str,
    *,
    max_chars_per_doc: int,
    max_total_chars: int,
) -> tuple[str, bool]:
    """Fairly trim each document section, then enforce a total size cap."""

    sections = _split_source_sections(combined_text)

    if not sections:
        if len(combined_text) <= max_total_chars:
            return combined_text, False

        return (
            combined_text[:max_total_chars]
            + "\n\n[… source material trimmed for faster report generation …]",
            True,
        )

    doc_count = len(sections)
    per_doc_limit = min(
        max_chars_per_doc,
        max(max_total_chars // doc_count, 1),
    )

    trimmed_sections: list[str] = []
    truncated = False

    for header, body in sections:
        if len(body) > per_doc_limit:
            body = (
                body[:per_doc_limit]
                + f"\n\n[… document trimmed to {per_doc_limit:,} characters "
                "for faster report generation …]"
            )
            truncated = True

        trimmed_sections.append(f"{header}{body}")

    result = "\n\n".join(trimmed_sections)

    if len(result) > max_total_chars:
        result = (
            result[:max_total_chars]
            + "\n\n[… combined source material trimmed for faster report generation …]"
        )
        truncated = True

    return result, truncated
