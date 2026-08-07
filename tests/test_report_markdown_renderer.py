"""Tests for report markdown rendering used in premium exports."""

from __future__ import annotations

from services.premium_docx_export import DocxExportMetadata, build_premium_docx
from services.premium_pdf_export import PremiumExportMetadata, build_premium_pdf
from services.report_markdown_renderer import (
    drop_duplicate_leading_heading,
    format_bullet_item,
    is_duplicate_title,
    parse_markdown_blocks,
    remove_empty_sections,
    strip_inline_markdown,
)

FINDING_BLOCK = """
### Critical

#### Sustained Double-Digit Premium Growth

**Confidence:** 100%

**Summary:** The Nigerian insurance industry maintained positive double-digit gross premium growth from 2019 through 2024.

**Mentioned in:**
- Annual-Statistical-Market-Report-2024.pdf
- Annual-Statistical-Market-Report-2023.pdf

**Source confidence:** High
"""


def test_strip_inline_markdown_removes_markers():
    raw = "**Confidence:** 100% and (**3 of 3** documents)"
    cleaned = strip_inline_markdown(raw)

    assert "**" not in cleaned
    assert cleaned == "Confidence: 100% and (3 of 3 documents)"


def test_parse_markdown_blocks_renders_findings_without_hash_symbols():
    blocks = parse_markdown_blocks(FINDING_BLOCK)

    headings = [block for block in blocks if block.block_type == "heading"]

    assert headings[0].content == "Critical"
    assert headings[1].content == "Sustained Double-Digit Premium Growth"
    assert all("#" not in heading.content for heading in headings)

    labels = [block for block in blocks if block.block_type == "label_value"]

    assert labels[0].label == "Confidence"
    assert labels[0].value == "100%"
    assert labels[1].label == "Summary"
    assert "Nigerian insurance industry" in labels[1].value


def test_remove_empty_sections_drops_heading_without_content():
    report = """
## Executive Intelligence Dashboard

### Executive Snapshot
| Metric | Value |
| --- | --- |
| Documents analyzed | 4 |

## Executive Quotations

## AI Insights
- Claims issues increased across all four meetings.
"""

    cleaned = remove_empty_sections(report)

    assert "## Executive Quotations" not in cleaned
    assert "## AI Insights" in cleaned
    assert "Claims issues increased" in cleaned


def test_remove_empty_sections_drops_empty_subsections():
    report = """
## Executive Intelligence Dashboard

### Executive Summary Card
| Field | Value |
| --- | --- |
| Confidence | 90% |

### Key Opportunities

### Top Risks
- Claims delays continue
"""

    cleaned = remove_empty_sections(report)

    assert "### Key Opportunities" not in cleaned
    assert "### Top Risks" in cleaned
    assert "Claims delays continue" in cleaned


def test_remove_empty_sections_keeps_placeholder_free_content():
    report = """
## Executive Quotations
> "Prompt and fair claims settlement builds trust."
> — Annual Report 2024
"""

    cleaned = remove_empty_sections(report)

    assert "## Executive Quotations" in cleaned
    assert "Prompt and fair claims settlement" in cleaned


def test_premium_pdf_has_no_raw_markdown_headings():
    report = f"""
## Executive Intelligence Dashboard

### Executive Summary Card
| Field | Value |
| --- | --- |
| Industry Status | Cautious |
| Confidence | 90% |
| Priority | Claims Reform |
| Overall Trend | Improving |

### Executive Snapshot
| Metric | Value |
| --- | --- |
| Documents analyzed | 4 |
| Reporting period | December 2022 – November 2024 |
| Critical risks | 4 |
| Recommendations | 7 |
| Overall outlook | Cautious |
| AI confidence | 90% |

## Key Findings (Ranked by Importance)
{FINDING_BLOCK}

## AI Insights
- The aggregate premium growth indicates sustained market expansion.
"""

    pdf_bytes = build_premium_pdf(
        report_text=report,
        metadata=PremiumExportMetadata(
            project_name="Insurance Review",
            report_name="Executive Summary",
            reporting_period="December 2022 – November 2024",
            source_documents=["meeting.pdf"],
            pack_type="executive",
        ),
    )

    pdf_text = pdf_bytes.decode("latin-1", errors="ignore")

    assert pdf_bytes.startswith(b"%PDF")
    assert "### Critical" not in pdf_text
    assert "#### Sustained" not in pdf_text
    assert "**Confidence:**" not in pdf_text


def test_parse_markdown_blocks_renders_ordered_list_as_numbered_block():
    report = """
## Strategic Recommendations

1. Commission an independent reserve adequacy review this quarter.
2. Renegotiate reinsurance treaty terms ahead of renewal.
3. Launch a cross-sell pilot into the commercial lines segment.
"""

    blocks = parse_markdown_blocks(report)
    numbered = [block for block in blocks if block.block_type == "numbered"]

    assert len(numbered) == 1
    assert numbered[0].items == [
        "Commission an independent reserve adequacy review this quarter.",
        "Renegotiate reinsurance treaty terms ahead of renewal.",
        "Launch a cross-sell pilot into the commercial lines segment.",
    ]
    # No leaked digits/periods and no run-on paragraph block for this section.
    assert not any(block.block_type == "paragraph" and "1." in block.content for block in blocks)


def test_ordered_list_line_breaks_an_in_progress_paragraph():
    report = "Some intro text.\n1. First item.\n2. Second item."

    blocks = parse_markdown_blocks(report)

    assert blocks[0].block_type == "paragraph"
    assert blocks[0].content == "Some intro text."
    assert blocks[1].block_type == "numbered"
    assert blocks[1].items == ["First item.", "Second item."]


def test_format_bullet_item_no_longer_prepends_checkmark():
    assert format_bullet_item("Reinsurance costs are trending upward") == (
        "Reinsurance costs are trending upward"
    )
    assert not format_bullet_item("Some risk item").startswith("✓")


def test_is_duplicate_title_matches_prefix_variants():
    title = "Executive Summary — Custom / Ad hoc"

    assert is_duplicate_title("Executive Summary", title) is True
    assert is_duplicate_title("EXECUTIVE SUMMARY", title) is True
    assert is_duplicate_title(title, title) is True
    assert is_duplicate_title("Key Findings", title) is False
    assert is_duplicate_title("", title) is False


def test_drop_duplicate_leading_heading_removes_only_matching_first_block():
    title = "Executive Summary — Custom / Ad hoc"
    blocks = parse_markdown_blocks(
        "## Executive Summary\n\nSome intro text.\n\n## Key Findings\n\nMore text."
    )

    trimmed = drop_duplicate_leading_heading(blocks, title)

    assert trimmed[0].block_type == "paragraph"
    assert trimmed[0].content == "Some intro text."

    unrelated_blocks = parse_markdown_blocks("## Key Findings\n\nMore text.")
    unchanged = drop_duplicate_leading_heading(unrelated_blocks, title)
    assert unchanged == unrelated_blocks


def test_build_premium_docx_returns_docx_bytes():
    report = """
## Executive Intelligence Dashboard

### Executive Summary Card
| Field | Value |
| --- | --- |
| Industry Status | Cautious |
| Confidence | 90% |
| Priority | Claims Reform |
| Overall Trend | Improving |

### Executive Snapshot
| Metric | Value |
| --- | --- |
| Documents analyzed | 4 |
| Reporting period | December 2022 – November 2024 |
| Critical risks | 4 |
| Recommendations | 7 |
| Overall outlook | Cautious |
| AI confidence | 90% |

## AI Insights
- Claims issues increased across all four meetings.
"""

    docx_bytes = build_premium_docx(
        report_text=report,
        metadata=DocxExportMetadata(
            project_name="Insurance Review",
            report_name="Executive Summary",
            reporting_period="December 2022 – November 2024",
            source_documents=["meeting.pdf"],
            pack_type="executive",
        ),
    )

    assert docx_bytes.startswith(b"PK")
