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


EVIDENCE_REPORT = """
## Executive Summary
Gross premiums increased 97.4% from 2022 to 2024.

## Key Findings

### Gross Premium increased 97.4%
Detail text about the finding.
**Basis:** Calculated result
**Confidence:** High — verified calculations.
**Source:** Annual-Statistical-Market-Report-Updated-01-2023.pdf, Annual-Statistical-Market-Report-2024.pdf

## Conclusion
Momentum should be sustained.
"""


def test_build_premium_pdf_renders_evidence_caption_and_humanized_source_filenames():
    """Report Output Quality Upgrade Step A: Basis/Confidence/Source must
    render as a visually subordinate "Evidence" block with human-readable
    source titles in the Key Finding itself. The real filename is still
    expected to appear verbatim in the separate Source References appendix
    (report_document_parser.py always lists real source_documents there) —
    only the inline evidence tag is humanized, nothing is fabricated or
    hidden."""

    import io

    from PyPDF2 import PdfReader

    pdf_bytes = build_premium_pdf(
        report_text=EVIDENCE_REPORT,
        metadata=PremiumExportMetadata(
            project_name="Q4 Revenue Review",
            report_name="Q4 Revenue Report",
            reporting_period="Custom / Ad hoc",
            source_documents=[
                "Annual-Statistical-Market-Report-Updated-01-2023.pdf",
                "Annual-Statistical-Market-Report-2024.pdf",
            ],
            pack_type="executive",
        ),
    )
    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf_bytes)).pages)

    assert "EVIDENCE" in pdf_text
    assert "Annual Statistical Market Report 2023" in pdf_text
    assert "Annual Statistical Market Report 2024" in pdf_text

    finding_section = pdf_text.split("Gross Premium increased 97.4%", 1)[1].split("Conclusion", 1)[0]
    assert "Annual-Statistical-Market-Report-Updated-01-2023.pdf" not in finding_section


def test_build_premium_docx_renders_evidence_caption_and_humanized_source_filenames():
    docx_bytes = build_premium_docx(
        report_text=EVIDENCE_REPORT,
        metadata=DocxExportMetadata(
            project_name="Q4 Revenue Review",
            report_name="Q4 Revenue Report",
            reporting_period="Custom / Ad hoc",
            source_documents=[
                "Annual-Statistical-Market-Report-Updated-01-2023.pdf",
                "Annual-Statistical-Market-Report-2024.pdf",
            ],
            pack_type="executive",
        ),
    )

    from io import BytesIO

    from docx import Document as DocxDocument

    document = DocxDocument(BytesIO(docx_bytes))
    docx_text = "\n".join(p.text for p in document.paragraphs)

    assert "EVIDENCE" in docx_text
    assert "Annual Statistical Market Report 2023" in docx_text
    assert "Annual Statistical Market Report 2024" in docx_text

    finding_section = docx_text.split("Gross Premium increased 97.4%", 1)[1].split("Conclusion", 1)[0]
    assert "Annual-Statistical-Market-Report-Updated-01-2023.pdf" not in finding_section


NO_RISKS_OR_OPPORTUNITIES_REPORT = """
## Executive Summary
Gross premiums increased 97.4% from 2022 to 2024.

## Risks & Issues
No risks were identified in the evidence reviewed.

## Opportunities
No opportunities were identified in the evidence reviewed.

## Conclusion
Momentum should be sustained.
"""


def test_build_premium_pdf_softens_no_risks_no_opportunities_wording():
    """Report Output Quality Upgrade Step B: 'No critical risks identified.'
    overstates the claim — it reads as 'none exist' when the honest claim
    is 'none were found in the evidence reviewed'."""

    import io

    from PyPDF2 import PdfReader

    pdf_bytes = build_premium_pdf(
        report_text=NO_RISKS_OR_OPPORTUNITIES_REPORT,
        metadata=PremiumExportMetadata(
            project_name="Q4 Revenue Review",
            report_name="Q4 Revenue Report",
            reporting_period="Custom / Ad hoc",
            source_documents=["report.xlsx"],
            pack_type="executive",
        ),
    )
    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf_bytes)).pages)

    assert "No risks were identified in the evidence reviewed." in pdf_text
    assert "No opportunities were identified in the evidence reviewed." in pdf_text
    assert "No critical risks identified." not in pdf_text
    assert "No opportunities identified." not in pdf_text


def test_build_premium_docx_softens_no_risks_no_opportunities_wording():
    docx_bytes = build_premium_docx(
        report_text=NO_RISKS_OR_OPPORTUNITIES_REPORT,
        metadata=DocxExportMetadata(
            project_name="Q4 Revenue Review",
            report_name="Q4 Revenue Report",
            reporting_period="Custom / Ad hoc",
            source_documents=["report.xlsx"],
            pack_type="executive",
        ),
    )

    from io import BytesIO

    from docx import Document as DocxDocument

    docx_text = "\n".join(p.text for p in DocxDocument(BytesIO(docx_bytes)).paragraphs)

    assert "No risks were identified in the evidence reviewed." in docx_text
    assert "No opportunities were identified in the evidence reviewed." in docx_text
    assert "No critical risks identified." not in docx_text
    assert "No opportunities identified." not in docx_text


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
