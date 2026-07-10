"""Tests for premium PDF and presentation export."""

from __future__ import annotations

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
