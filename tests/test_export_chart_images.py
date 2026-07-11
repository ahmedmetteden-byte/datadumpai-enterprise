"""Tests for chart image generation in PDF and Word exports."""

from __future__ import annotations

from io import BytesIO

from docx import Document
from services.export_service import ExportService
from services.report_chart_export import render_chart_pngs
from services.report_chart_figures import has_chart_visuals

SAMPLE_CHART_DATA = {
    "topics": [
        {"label": "Claims", "value": 31},
        {"label": "Capital", "value": 21},
    ],
    "trends": [
        {"label": "Claims", "prior": 15, "current": 31},
        {"label": "Capital", "prior": 20, "current": 21},
    ],
    "health_score": 75,
}

FULL_REPORT = """
## Full Report Overview

### Executive Summary Card
| Field | Value |
| Reporting Period | Q1 2024 |
| Confidence | 88% |

## Visual Summary
Charts are rendered by the application.

<!-- REPORT_CHARTS
{
  "topics": [{"label": "Claims", "value": 31}, {"label": "Capital", "value": 21}],
  "trends": [{"label": "Claims", "prior": 15, "current": 31}],
  "health_score": 75
}
-->
"""


def test_render_chart_pngs_returns_png_bytes():
    images = render_chart_pngs(SAMPLE_CHART_DATA)

    assert len(images) >= 3
    assert images[0][0] == "Top Discussion Topics"
    assert images[1][0] == "Theme Distribution"
    assert images[0][1].startswith(b"\x89PNG")
    assert has_chart_visuals(SAMPLE_CHART_DATA)


def test_export_docx_places_charts_near_top_of_document():
    result = ExportService().export_docx(
        project_id="chart-export-project",
        report_name="Full Report",
        report_text=FULL_REPORT,
    )

    document = Document(BytesIO(result["data"]))
    image_indexes = [
        index
        for index, paragraph in enumerate(document.paragraphs)
        if paragraph._element.xpath(".//a:blip")
    ]
    overview_index = next(
        index
        for index, paragraph in enumerate(document.paragraphs)
        if paragraph.text == "Full Report Overview"
    )

    assert image_indexes
    assert min(image_indexes) < overview_index
    assert any(paragraph.text == "Visual Analytics" for paragraph in document.paragraphs)


def test_export_pdf_embeds_chart_images():
    result = ExportService().export_pdf(
        project_id="chart-export-project",
        report_name="Full Report",
        report_text=FULL_REPORT,
    )

    assert result["data"].startswith(b"%PDF")
    assert len(result["data"]) > 5000


def test_export_docx_embeds_chart_images():
    result = ExportService().export_docx(
        project_id="chart-export-project",
        report_name="Full Report",
        report_text=FULL_REPORT,
    )

    assert result["data"].startswith(b"PK")

    document = Document(BytesIO(result["data"]))
    assert any("image" in rel.target_ref for rel in document.part.rels.values())
