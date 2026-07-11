"""Tests that premium Word exports include chart images."""

from __future__ import annotations

from io import BytesIO

from docx import Document
from services.premium_docx_export import DocxExportMetadata, build_premium_docx

INTELLIGENCE_REPORT = """
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

<!-- REPORT_CHARTS
{
  "topics": [{"label": "Claims", "value": 31}, {"label": "Capital", "value": 21}],
  "health_score": 75
}
-->
"""


def test_premium_docx_includes_chart_images():
    docx_bytes = build_premium_docx(
        report_text=INTELLIGENCE_REPORT,
        metadata=DocxExportMetadata(
            project_name="Insurance Review",
            report_name="Executive Summary",
            reporting_period="December 2022 – November 2024",
            source_documents=["meeting.pdf"],
            pack_type="executive",
        ),
    )

    document = Document(BytesIO(docx_bytes))

    assert docx_bytes.startswith(b"PK")
    assert any("image" in rel.target_ref for rel in document.part.rels.values())
