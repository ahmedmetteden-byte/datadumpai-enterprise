"""Tests for report markdown rendering used in premium exports."""

from __future__ import annotations

from services.premium_docx_export import DocxExportMetadata, build_premium_docx
from services.premium_pdf_export import PremiumExportMetadata, build_premium_pdf
from services.report_markdown_renderer import (
    parse_markdown_blocks,
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
