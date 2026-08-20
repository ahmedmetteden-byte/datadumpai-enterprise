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
ORDERED_LIST_PATTERN = re.compile(r"^\d{1,2}[.)]\s+(.+)$")
LABEL_VALUE_PATTERN = re.compile(r"^\*\*([^*]+):\*\*\s*(.*)$")
NUMBERED_ITEM_LABEL_PATTERN = re.compile(r"^([A-Za-z][A-Za-z /]{0,30}):\s*(.+)$")
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


PLACEHOLDER_LINE = re.compile(
    r"^(?:"
    r"none(?:\s+identified)?|"
    r"n/?a|"
    r"not\s+(?:applicable|available|identified)|"
    r"no\s+(?:data|quotations?|quotes?|content|"
    r"relevant\s+quotations?)(?:\s+(?:were\s+)?identified)?|"
    r"[—\-]"
    r")\.?$",
    re.IGNORECASE,
)


def _is_substantive_content(text: str) -> bool:
    """Return True when a section body contains renderable report content."""

    if not text or not text.strip():
        return False

    for line in text.splitlines():
        stripped = line.strip()

        if not stripped:
            continue

        if HEADING_PATTERN.match(stripped):
            continue

        if HORIZONTAL_RULE.match(stripped):
            continue

        if TABLE_ROW_PATTERN.match(stripped):
            return True

        if stripped.startswith(("-", "*", ">")):
            return True

        if LABEL_VALUE_PATTERN.match(stripped):
            return True

        cleaned = strip_inline_markdown(stripped)

        if cleaned and not PLACEHOLDER_LINE.match(cleaned):
            return True

    return False


def _parse_heading_sections(text: str, level: int) -> list[tuple[str | None, str]]:
    """Split markdown into (heading title, body) tuples at a fixed heading level."""

    pattern = re.compile(rf"^#{{{level}}}\s+(.+)$")
    sections: list[tuple[str | None, list[str]]] = [(None, [])]

    for line in text.splitlines():
        match = pattern.match(line)

        if match and not line.startswith("#" * (level + 1)):
            sections.append((match.group(1).strip(), []))
            continue

        sections[-1][1].append(line)

    return [
        (title, "\n".join(lines).strip())
        for title, lines in sections
    ]


def _remove_empty_headings_at_level(text: str, level: int, *, max_level: int = 5) -> str:
    if level > max_level:
        return text.strip()

    sections = _parse_heading_sections(text, level)
    rebuilt: list[str] = []

    for title, body in sections:
        if title is None:
            if body.strip():
                rebuilt.append(_remove_empty_headings_at_level(body, level + 1, max_level=max_level))
            continue

        cleaned_body = _remove_empty_headings_at_level(body, level + 1, max_level=max_level)

        if _is_substantive_content(cleaned_body):
            rebuilt.append(f"{'#' * level} {title}\n\n{cleaned_body}".strip())

    return "\n\n".join(part for part in rebuilt if part).strip()


def remove_empty_sections(report_text: str) -> str:
    """Drop section headings that have no substantive content beneath them."""

    if not report_text.strip():
        return report_text

    return _remove_empty_headings_at_level(report_text, level=2).strip()


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


_FILENAME_NOISE_WORDS = {"updated", "update", "final", "draft", "copy", "revised"}
_VERSION_TOKEN = re.compile(r"^v\d+$", re.IGNORECASE)
_SHORT_NUMBER = re.compile(r"^0?\d{1,2}$")
_FOUR_DIGIT_YEAR = re.compile(r"^(19|20)\d{2}$")


def humanize_filename(filename: str) -> str:
    """Turn a real uploaded filename into a readable display title, e.g.
    'Annual-Statistical-Market-Report-Updated-01-2023.pdf' ->
    'Annual Statistical Market Report 2023'. Never fabricates a title not
    derivable from the filename itself — the real filename is preserved
    everywhere else (QC checks, internal source_documents) and this is
    purely a display transform, applied at render time only."""

    if not filename or not filename.strip():
        return filename

    stem = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", filename.strip())
    words = [w for w in re.split(r"[_\-]+", stem) if w]

    kept: list[str] = []
    for i, word in enumerate(words):
        if word.lower() in _FILENAME_NOISE_WORDS or _VERSION_TOKEN.match(word):
            continue

        # Drop a standalone 1-2 digit token (a month/revision number)
        # immediately preceding a 4-digit year, keeping just the year.
        if (
            _SHORT_NUMBER.match(word)
            and i + 1 < len(words)
            and _FOUR_DIGIT_YEAR.match(words[i + 1])
        ):
            continue

        kept.append(word)

    result = re.sub(r"\s+", " ", " ".join(kept)).strip()
    return result or filename


def humanize_source_value(value: str) -> str:
    """Apply humanize_filename() to each comma-separated filename in a
    **Source:** value, preserving the original separator style."""

    if not value or "." not in value:
        return value

    parts = [part.strip() for part in value.split(",")]
    humanized = [humanize_filename(part) if part else part for part in parts]
    return ", ".join(humanized)


def classify_label_value(label: str, value: str) -> tuple[str, str, str]:
    """Return (clean_label, clean_value, hex_color) for a label/value pair,
    applying the same semantic-coloring rules (confidence/priority/severity)
    used by every renderer — the single source of truth for this."""

    label_clean = strip_inline_markdown(label)
    value_clean = strip_inline_markdown(value)
    label_lower = label_clean.lower()

    if label_lower == "source":
        value_clean = humanize_source_value(value_clean)

    color = "#0F172A"

    if not value_clean:
        return label_clean, value_clean, color

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

    return label_clean, value_clean, color


def highlight_value_html(label: str, value: str) -> str:
    """Build ReportLab markup for a label/value pair on a single line, with
    semantic coloring on the value. Font size is left to the caller's
    paragraph style — this only supplies bold/color markup — so the same
    call site can render at dashboard-card size or at the smaller,
    subordinate size used for evidence metadata."""

    label_clean, value_clean, color = classify_label_value(label, value)

    if not value_clean:
        return f"<b>{escape_xml(label_clean)}</b>"

    return (
        f"<b>{escape_xml(label_clean)}:</b> "
        f"<font color='{color}'><b>{escape_xml(value_clean)}</b></font>"
    )


def format_bullet_item(text: str) -> str:
    """Clean a list item's text. The bullet/number glyph itself is drawn by
    the renderer (a real list flowable / Word list style / pptx bullet
    XML) — this must not bake any marker character into the text, or
    renderers that already draw their own glyph end up double-marking."""

    cleaned = strip_inline_markdown(text.strip())
    return cleaned.lstrip("✓•").strip() or cleaned


def is_duplicate_title(heading_text: str, title: str) -> bool:
    """True when a body heading just restates the document title already
    rendered separately (e.g. a report's first heading echoing its own
    template name) — used to skip rendering it a second time."""

    def normalize(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", value.lower())

    heading_norm = normalize(heading_text)
    title_norm = normalize(title)

    if not heading_norm or not title_norm:
        return False

    if heading_norm == title_norm:
        return True

    # e.g. heading "Executive Summary" vs title "Executive Summary — Custom
    # / Ad hoc" — the heading is a substantial prefix/substring of the title.
    return len(heading_norm) >= 6 and heading_norm in title_norm


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


def _collect_ordered_items(lines: list[str], start: int) -> tuple[list[str], int]:
    items: list[str] = []
    index = start

    while index < len(lines):
        line = lines[index].strip()

        if not line:
            index += 1
            break

        match = ORDERED_LIST_PATTERN.match(line)

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

        if ORDERED_LIST_PATTERN.match(line):
            items, index = _collect_ordered_items(lines, index)
            blocks.append(MarkdownBlock(block_type="numbered", items=items))
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
                or ORDERED_LIST_PATTERN.match(peek)
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


def drop_duplicate_leading_heading(
    blocks: list[MarkdownBlock], title: str
) -> list[MarkdownBlock]:
    """Drop a body's first heading when it just restates the document
    title already rendered separately by the exporter — shared by every
    format so PDF/DOCX/PPTX all agree on there being exactly one title."""

    if blocks and blocks[0].block_type == "heading" and is_duplicate_title(
        blocks[0].content, title
    ):
        return blocks[1:]

    return blocks
