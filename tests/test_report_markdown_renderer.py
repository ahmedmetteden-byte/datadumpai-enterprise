"""Tests for report markdown rendering used in premium exports."""

from __future__ import annotations

from services.premium_docx_export import DocxExportMetadata, build_premium_docx
from services.premium_pdf_export import PremiumExportMetadata, build_premium_pdf
from services.report_markdown_renderer import (
    classify_label_value,
    drop_duplicate_leading_heading,
    format_bullet_item,
    highlight_value_html,
    humanize_filename,
    humanize_source_value,
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


def test_remove_empty_sections_drops_no_risks_identified_sentence():
    """Phase 3 Step 4 Phase C: the report-writing prompt instructs the
    model to write 'No risks were identified in the evidence reviewed.'
    rather than fabricating a risk — that sentence must be recognized as a
    placeholder and the whole section dropped, not shown to the reader as
    an awkward one-line 'Risks & Issues' section."""

    report = """
## Key Findings
- Premium grew 12% year-over-year.

## Risks & Issues
No risks were identified in the evidence reviewed.

## Strategic Recommendations
1. Continue current pricing strategy.
"""

    cleaned = remove_empty_sections(report)

    assert "## Risks & Issues" not in cleaned
    assert "## Key Findings" in cleaned
    assert "## Strategic Recommendations" in cleaned


def test_remove_empty_sections_drops_no_opportunities_identified_sentence():
    report = """
## Opportunities
No opportunities were identified in the evidence reviewed.

## Strategic Recommendations
1. Continue current pricing strategy.
"""

    cleaned = remove_empty_sections(report)

    assert "## Opportunities" not in cleaned
    assert "## Strategic Recommendations" in cleaned


def test_remove_empty_sections_keeps_a_real_risk_that_merely_starts_with_no():
    """The placeholder match must stay narrow — a genuine finding that
    happens to start with 'No' must never be swept up as a placeholder."""

    report = """
## Risks & Issues
No mitigation plan currently exists for the claims backlog increase from 14 to 31 cases.
"""

    cleaned = remove_empty_sections(report)

    assert "## Risks & Issues" in cleaned
    assert "No mitigation plan currently exists" in cleaned


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


def test_humanize_filename_drops_update_token_and_revision_number():
    # Real filename from a production workspace, confirmed by the Report
    # Output Quality audit to render raw ("Documents: 0" / generic-chart
    # sibling bug) in the sample the user reviewed.
    assert (
        humanize_filename("Annual-Statistical-Market-Report-Updated-01-2023.pdf")
        == "Annual Statistical Market Report 2023"
    )


def test_humanize_filename_leaves_a_clean_filename_mostly_intact():
    assert (
        humanize_filename("Annual-Statistical-Market-Report-2024.pdf")
        == "Annual Statistical Market Report 2024"
    )


def test_humanize_filename_never_fabricates_when_nothing_to_clean():
    assert humanize_filename("q4_revenue.xlsx") == "q4 revenue"
    assert humanize_filename("") == ""


def test_humanize_source_value_handles_multiple_comma_separated_filenames():
    value = (
        "Annual-Statistical-Market-Report-2024.pdf, "
        "Annual-Statistical-Market-Report-Updated-01-2023.pdf, "
        "Annual-Statistical-Market-Report-2022.pdf"
    )

    assert humanize_source_value(value) == (
        "Annual Statistical Market Report 2024, "
        "Annual Statistical Market Report 2023, "
        "Annual Statistical Market Report 2022"
    )


def test_classify_label_value_humanizes_source_but_not_other_labels():
    _, source_value, _ = classify_label_value(
        "Source", "Annual-Statistical-Market-Report-2024.pdf"
    )
    assert source_value == "Annual Statistical Market Report 2024"

    _, basis_value, _ = classify_label_value("Basis", "Source fact")
    assert basis_value == "Source fact"


def test_highlight_value_html_renders_label_and_value_on_one_line():
    html = highlight_value_html("Basis", "Source fact")

    assert "<br/>" not in html
    assert "size='11'" not in html
    assert "<b>Basis:</b>" in html
    assert "Source fact" in html


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
