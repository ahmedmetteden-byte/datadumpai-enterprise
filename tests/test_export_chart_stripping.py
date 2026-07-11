"""Tests that internal REPORT_CHARTS metadata is stripped from exports."""

from __future__ import annotations

from services.export_service import ExportService

FULL_REPORT_WITH_CHARTS = """
## Full Report Overview

### Executive Summary Card
| Field | Value |
| Reporting Period | Q1 2024 |
| Confidence | 88% |

## Visual Summary
Charts rendered by the application.

<!-- REPORTCHARTS
{
  "topics": [{"label": "Claims", "value": 31}],
  "health_score": 75
}
-->
"""


def test_export_pdf_strips_report_charts_metadata():
    result = ExportService().export_pdf(
        project_id="export-strip-project",
        report_name="Full Report",
        report_text=FULL_REPORT_WITH_CHARTS,
    )

    assert result["data"].startswith(b"%PDF")
    assert b"REPORTCHARTS" not in result["data"]
    assert b"REPORT_CHARTS" not in result["data"]


def test_export_docx_strips_report_charts_metadata():
    result = ExportService().export_docx(
        project_id="export-strip-project",
        report_name="Full Report",
        report_text=FULL_REPORT_WITH_CHARTS,
    )

    assert result["data"].startswith(b"PK")
    assert b"REPORTCHARTS" not in result["data"]
    assert b"REPORT_CHARTS" not in result["data"]


def test_export_markdown_strips_report_charts_metadata():
    result = ExportService().export_markdown(
        project_id="export-strip-project",
        report_name="Full Report",
        report_text=FULL_REPORT_WITH_CHARTS,
    )

    exported = result["data"].decode("utf-8")

    assert "Visual Summary" in exported
    assert "REPORTCHARTS" not in exported
    assert "REPORT_CHARTS" not in exported
