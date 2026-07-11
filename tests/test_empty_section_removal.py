"""Tests that empty report sections are omitted from exports."""

from __future__ import annotations

from services.export_service import ExportService
from services.premium_pdf_export import PremiumExportMetadata, build_premium_pdf

REPORT_WITH_EMPTY_QUOTATIONS = """
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

## Executive Quotations

## AI Insights
- Claims issues increased across all four meetings.
"""


def test_export_pdf_omits_empty_executive_quotations_section():
    result = ExportService().export_pdf(
        project_id="empty-section-project",
        report_name="Executive Summary",
        report_text=REPORT_WITH_EMPTY_QUOTATIONS,
    )

    pdf_text = result["data"].decode("latin-1", errors="ignore")

    assert result["data"].startswith(b"%PDF")
    assert "Executive Quotations" not in pdf_text


def test_premium_pdf_omits_empty_executive_quotations_section():
    pdf_bytes = build_premium_pdf(
        report_text=REPORT_WITH_EMPTY_QUOTATIONS,
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
    assert "Executive Quotations" not in pdf_text
