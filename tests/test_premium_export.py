"""Tests for premium PDF and presentation export."""

from __future__ import annotations

from services.premium_docx_export import DocxExportMetadata, build_premium_docx
from services.premium_pdf_export import PremiumExportMetadata, build_premium_pdf
from services.premium_pptx_export import PresentationExportMetadata, build_premium_presentation
from services.report_document_parser import parse_intelligence_report

SAMPLE_REPORT = """
## Executive Intelligence Dashboard

### Executive Summary Card
| Field | Value |
| --- | --- |
| Industry Status | 🟡 Cautious |
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

### Top Risks
- 🔴 **Claims** — Settlement delays continue
- 🟠 **Capital** — Adequacy pressure remains

## AI Insights
- Claims issues increased across all four meetings.

<!-- REPORT_CHARTS
{
  "topics": [{"label": "Claims", "value": 31}, {"label": "Capital", "value": 21}],
  "health_score": 75
}
-->
"""


def test_parse_intelligence_report_extracts_card_and_charts():
    parsed = parse_intelligence_report(
        SAMPLE_REPORT,
        source_documents=["meeting.pdf", "report.pdf"],
    )

    assert parsed.summary_card["Priority"] == "Claims Reform"
    assert parsed.chart_data["health_score"] == 75
    assert len(parsed.source_documents) == 2


def test_build_premium_pdf_returns_pdf_bytes():
    pdf_bytes = build_premium_pdf(
        report_text=SAMPLE_REPORT,
        metadata=PremiumExportMetadata(
            project_name="Board Meeting - November 2024",
            report_name="Executive Summary",
            reporting_period="December 2022 – November 2024",
            source_documents=["meeting.pdf"],
            pack_type="executive",
        ),
    )

    assert pdf_bytes.startswith(b"%PDF")


def test_build_premium_presentation_returns_pptx_bytes():
    pptx_bytes = build_premium_presentation(
        report_text=SAMPLE_REPORT,
        metadata=PresentationExportMetadata(
            project_name="Board Meeting - November 2024",
            report_name="Executive Summary",
            source_documents=["meeting.pdf"],
        ),
    )

    assert pptx_bytes.startswith(b"PK")


# Step G: the premium renderer must also work for a real SPA-format
# report (no Executive Intelligence Dashboard heading, no health_score),
# not only the legacy intelligence format above.
SPA_REPORT = """
## Executive Summary
Gross premiums increased 97.4% from 2022 to 2024.

## Key Findings

### Gross Premium increased 97.4%
Detail text.
**Basis:** Calculated result
**Confidence:** High — verified calculations.
**Source:** report.xlsx

## Risks & Issues
- **Rising Claims Costs:** The significant increase in Gross Claims poses a risk to profitability.

## Opportunities
- **Enhanced Claims Management:** Refine claims management processes.

## Strategic Recommendations
1. **Action:** Conduct a comprehensive review of claims management processes.
   **Rationale:** The 51.3% increase in Gross Claims suggests inefficiencies.
   **Measurement:** Track the ratio of Gross Claims to Gross Premium.

## Conclusion
Momentum should be sustained.

<!-- REPORT_CHARTS
{"visualizations": [{"title": "Gross Premium", "type": "LINE_CHART", "description": "d", "data": {"trends": [{"label": "2024", "prior": 1043.1, "current": 1558.7}]}, "priority": 1, "decision_question": "", "unit": "", "x_label": "Period", "y_label": "Gross Premium"}]}
-->
"""


def test_build_premium_pdf_handles_real_spa_format_report_without_crashing():
    pdf_bytes = build_premium_pdf(
        report_text=SPA_REPORT,
        metadata=PremiumExportMetadata(
            project_name="Q4 Revenue Review",
            report_name="Q4 Revenue Report",
            reporting_period="Custom / Ad hoc",
            source_documents=["report.xlsx"],
            pack_type="executive",
        ),
    )
    assert pdf_bytes.startswith(b"%PDF")


def test_build_premium_docx_handles_real_spa_format_report_without_crashing():
    docx_bytes = build_premium_docx(
        report_text=SPA_REPORT,
        metadata=DocxExportMetadata(
            project_name="Q4 Revenue Review",
            report_name="Q4 Revenue Report",
            reporting_period="Custom / Ad hoc",
            source_documents=["report.xlsx"],
            pack_type="executive",
        ),
    )
    assert docx_bytes.startswith(b"PK")


def test_build_premium_presentation_embeds_charts_for_spa_format_report():
    pptx_bytes = build_premium_presentation(
        report_text=SPA_REPORT,
        metadata=PresentationExportMetadata(
            project_name="Q4 Revenue Review",
            report_name="Q4 Revenue Report",
            source_documents=["report.xlsx"],
        ),
    )
    assert pptx_bytes.startswith(b"PK")

    from pptx import Presentation
    import io

    prs = Presentation(io.BytesIO(pptx_bytes))
    has_picture = any(
        shape.shape_type is not None and shape.shape_type == 13  # MSO_SHAPE_TYPE.PICTURE
        for slide in prs.slides
        for shape in slide.shapes
    )
    assert has_picture, "expected at least one embedded chart image across all slides"
