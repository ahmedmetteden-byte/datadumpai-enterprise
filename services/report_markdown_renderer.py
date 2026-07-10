"""
Shared markdown parsing and cleaning for premium PDF and Word exports.

Strips raw markdown syntax and structures report body text into renderable blocks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterator

HEADING_PATTERN = re.compile(r"^(#{1,5})\s+(.+)$")
BULLET_PATTERN = re.compile(r"^[-*]\s+(.+)$")
LABEL_VALUE_PATTERN = re.compile(r"^\*\*([^*]+):\*\*\s*(.*)$")
HORIZONTAL_RULE = re.compile(r"^-{3,}$")
TABLE_ROW_PATTERN = re.compile(r"^\|(.+)\|$")

LABELS_WITH_HIGHLIGHT = {
    "confidence",
    "priority",
    "source confidence",
    "overall outlook",
    "score",
    "expected impact",
    "cross-document reach",
}

SEVERITY_VALUES = {"critical", "high", "medium", "low"}


@dataclass
class MarkdownBlock:
    block_type: str
    content: str = ""
    level: int = 0
    label: str = ""
    value: str = ""
    items: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)


def strip_inline_markdown(text: str) -> str:
    """Remove inline markdown markers while preserving readable text."""

    cleaned = text.strip()
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"__([^_]+)__", r"\1", cleaned)
    cleaned = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", cleaned)
    cleaned = re.sub(r"(?<!_)_([^_]+)_(?!_)", r"\1", cleaned)
    cleaned = cleaned.replace("**", "").replace("__", "").replace("*", "")
    cleaned = re.sub(r"\(\*\*(\d+)\s+of\s+(\d+)\*\*\s*documents\)", r"(\1 of \2 documents)", cleaned, flags=re.I)
    cleaned = re.sub(r"\(\*\*([^*]+)\*\*\)", r"(\1)", cleaned)
    return cleaned.strip()


def clean_heading(text: str) -> tuple[int, str]:
    """Return heading level (1-5) and plain title text."""

    match = HEADING_PATTERN.match(text.strip())

    if match:
        return len(match.group(1)), strip_inline_markdown(match.group(2))

    return 0, strip_inline_markdown(text.lstrip("#").strip())


def escape_xml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def inline_to_reportlab_html(text: str) -> str:
    """Convert limited inline markdown to ReportLab paragraph markup."""

    safe = escape_xml(text)
    safe = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", safe)
    safe = re.sub(r"__([^_]+)__", r"<b>\1</b>", safe)
    safe = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", safe)
    safe = safe.replace("**", "").replace("__", "")
    return safe


def highlight_value_html(label: str, value: str) -> str:
    """Build ReportLab markup for label/value pairs with semantic coloring."""

    label_clean = strip_inline_markdown(label)
    value_clean = strip_inline_markdown(value)
    label_lower = label_clean.lower()

    if not value_clean:
        return f"<b>{escape_xml(label_clean)}</b>"

    color = "#0F172A"

    if "confidence" in label_lower and "%" in value_clean:
        color = "#1D4ED8"
    elif label_lower == "priority" or value_clean.lower() in SEVERITY_VALUES:
        severity = value_clean.lower()
        if severity == "critical":
            color = "#DC2626"
        elif severity == "high":
            color = "#D97706"
        elif severity == "medium":
            color = "#CA8A04"
        elif severity == "low":
            color = "#059669"
    elif label_lower in LABELS_WITH_HIGHLIGHT:
        color = "#1D4ED8"

    return (
        f"<b>{escape_xml(label_clean)}:</b><br/>"
        f"<font color='{color}' size='11'><b>{escape_xml(value_clean)}</b></font>"
    )


def format_bullet_item(text: str) -> str:
    """Normalize list items to checkmark bullets."""

    cleaned = strip_inline_markdown(text.strip())

    if cleaned.startswith("✓") or cleaned.startswith("•"):
        return cleaned

    return f"✓ {cleaned}"


def _collect_bullets(lines: list[str], start: int) -> tuple[list[str], int]:
    items: list[str] = []
    index = start

    while index < len(lines):
        line = lines[index].strip()

        if not line:
            index += 1
            break

        match = BULLET_PATTERN.match(line)

        if match:
            items.append(format_bullet_item(match.group(1)))
            index += 1
            continue

        break

    return items, index


def _collect_table(lines: list[str], start: int) -> tuple[list[list[str]], int]:
    rows: list[list[str]] = []
    index = start

    while index < len(lines):
        line = lines[index].strip()

        if not line or not TABLE_ROW_PATTERN.match(line):
            break

        if re.match(r"^\|[\s\-:|]+\|$", line):
            index += 1
            continue

        cells = [strip_inline_markdown(cell.strip()) for cell in line.strip("|").split("|")]
        rows.append(cells)
        index += 1

    return rows, index


def parse_markdown_blocks(text: str) -> list[MarkdownBlock]:
    """Parse markdown body text into structured blocks for export renderers."""

    if not text.strip():
        return []

    lines = text.splitlines()
    blocks: list[MarkdownBlock] = []
    index = 0

    while index < len(lines):
        raw_line = lines[index]
        line = raw_line.strip()

        if not line:
            index += 1
            continue

        if HORIZONTAL_RULE.match(line):
            blocks.append(MarkdownBlock(block_type="spacer"))
            index += 1
            continue

        heading_match = HEADING_PATTERN.match(line)

        if heading_match:
            level = len(heading_match.group(1))
            title = strip_inline_markdown(heading_match.group(2))
            blocks.append(MarkdownBlock(block_type="heading", content=title, level=level))
            index += 1
            continue

        if line.startswith(">"):
            quote_lines: list[str] = []

            while index < len(lines):
                current = lines[index].strip()

                if not current.startswith(">"):
                    break

                quote_lines.append(strip_inline_markdown(current.lstrip(">").strip().strip('"')))
                index += 1

            blocks.append(
                MarkdownBlock(
                    block_type="quote",
                    content=" ".join(quote_lines).strip(),
                )
            )
            continue

        if TABLE_ROW_PATTERN.match(line):
            rows, index = _collect_table(lines, index)

            if rows:
                blocks.append(MarkdownBlock(block_type="table", rows=rows))

            continue

        label_match = LABEL_VALUE_PATTERN.match(line)

        if label_match:
            label = label_match.group(1).strip()
            value = label_match.group(2).strip()
            index += 1

            if not value and index < len(lines):
                next_line = lines[index].strip()

                if next_line and not HEADING_PATTERN.match(next_line) and not BULLET_PATTERN.match(next_line):
                    value = strip_inline_markdown(next_line)
                    index += 1

            blocks.append(
                MarkdownBlock(
                    block_type="label_value",
                    label=label,
                    value=value,
                )
            )
            continue

        if BULLET_PATTERN.match(line):
            items, index = _collect_bullets(lines, index)
            blocks.append(MarkdownBlock(block_type="bullets", items=items))
            continue

        paragraph_lines: list[str] = [line]
        index += 1

        while index < len(lines):
            peek = lines[index].strip()

            if (
                not peek
                or HEADING_PATTERN.match(peek)
                or peek.startswith(">")
                or TABLE_ROW_PATTERN.match(peek)
                or LABEL_VALUE_PATTERN.match(peek)
                or BULLET_PATTERN.match(peek)
                or HORIZONTAL_RULE.match(peek)
            ):
                break

            paragraph_lines.append(peek)
            index += 1

        blocks.append(
            MarkdownBlock(
                block_type="paragraph",
                content=strip_inline_markdown(" ".join(paragraph_lines)),
            )
        )

    return blocks


def group_blocks_for_keep_together(blocks: list[MarkdownBlock]) -> list[list[MarkdownBlock]]:
    """Group finding and recommendation blocks so they stay on one page when possible."""

    groups: list[list[MarkdownBlock]] = []
    current: list[MarkdownBlock] = []

    for block in blocks:
        if block.block_type == "heading" and block.level >= 4 and current:
            groups.append(current)
            current = [block]
            continue

        if block.block_type == "heading" and block.level == 3 and current:
            groups.append(current)
            current = [block]
            continue

        current.append(block)

    if current:
        groups.append(current)

    return groups if groups else [blocks]
