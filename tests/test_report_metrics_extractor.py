"""Tests for deterministic canonical report metrics."""

from __future__ import annotations

from pathlib import Path

from services.report_assembler import assemble_report_text, format_chart_block
from services.report_metrics_extractor import extract_report_data

SAMPLE_DOCUMENTS = """
=== SOURCE DOCUMENT: Annual-Statistical-Market-Report-2022.pdf ===

Claims settlement delays and capital adequacy pressure remain critical themes.
Regulatory reform advanced with new compliance requirements.

=== SOURCE DOCUMENT: Annual-Statistical-Market-Report-2023.pdf ===

Claims growth continued while regulatory reform and digital transformation expanded.
Premium growth accelerated across the market.

=== SOURCE DOCUMENT: Annual-Statistical-Market-Report-2024.pdf ===

Claims volatility and capital requirements remain high priority risks.
Regulatory reform bill passed. Premium growth reached record levels.
"""


def test_extract_report_data_is_deterministic_for_same_inputs():
    kwargs = {
        "document_text": SAMPLE_DOCUMENTS,
        "report_type": "Full Report",
        "source_documents": [
            "Annual-Statistical-Market-Report-2022.pdf",
            "Annual-Statistical-Market-Report-2023.pdf",
            "Annual-Statistical-Market-Report-2024.pdf",
        ],
        "report_context": {"reporting_period": "2022–2024"},
        "source_document_count": 3,
    }

    first = extract_report_data(**kwargs)
    second = extract_report_data(**kwargs)

    assert first.charts == second.charts
    assert first.metrics == second.metrics
    assert first.kpis == second.kpis
    assert first.metadata["content_hash"] == second.metadata["content_hash"]


def test_assemble_report_text_replaces_llm_chart_block_with_canonical_data():
    report_data = extract_report_data(
        document_text=SAMPLE_DOCUMENTS,
        report_type="Full Report",
        source_document_count=3,
    )

    llm_narrative = (
        "## Full Report Overview\n\n"
        "Narrative body.\n\n"
        '<!-- REPORT_CHARTS\n{"topics": [{"label": "Random", "value": 99}], "health_score": 11}\n-->'
    )

    assembled = assemble_report_text(
        llm_narrative,
        report_data,
        include_charts=True,
    )

    assert "Random" not in assembled
    assert format_chart_block(report_data.charts) in assembled
    assert assembled.count("<!-- REPORT_CHARTS") == 1


def test_real_saved_report_documents_produce_stable_chart_topics():
    report_path = Path(
        "data/users/00000000-0000-4000-8000-000000000001/projects/__quick_report__/reports/full_report.md"
    )

    if not report_path.exists():
        return

    saved = report_path.read_text(encoding="utf-8")
    document_text = "\n".join(
        line
        for line in saved.splitlines()
        if not line.strip().startswith("<!-- REPORT_CHARTS")
        and line.strip() != "-->"
        and not line.strip().startswith('"topics"')
        and not line.strip().startswith('"trends"')
        and not line.strip().startswith('"health_score"')
    )

    first = extract_report_data(
        document_text=document_text,
        report_type="Full Report",
        source_document_count=3,
    )
    second = extract_report_data(
        document_text=document_text,
        report_type="Full Report",
        source_document_count=3,
    )

    assert first.charts["topics"] == second.charts["topics"]
    assert first.charts["health_score"] == second.charts["health_score"]
