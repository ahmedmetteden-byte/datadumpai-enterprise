"""Tests for ReportData as the canonical report object."""

from __future__ import annotations

from models.report_data import ReportData
from services.report_document import (
    compose_report_data,
    report_data_from_markdown,
    report_data_from_storage,
    report_data_to_markdown,
)


def test_compose_report_data_sets_narrative_and_preserves_metrics():
    base = ReportData(
        metrics={"documents_analyzed": 3},
        charts={"topics": [{"label": "Claims", "value": 10}]},
        source_documents=["notes.txt"],
    )

    report = compose_report_data(
        narrative="# Executive Summary\n\nBody text.",
        base=base,
        report_type="Executive Summary",
        title="Executive Summary",
        include_charts=True,
    )

    assert report.narrative == "# Executive Summary\n\nBody text."
    assert report.report_type == "Executive Summary"
    assert report.metrics["documents_analyzed"] == 3
    assert report.charts["topics"][0]["label"] == "Claims"


def test_report_data_round_trip_through_markdown():
    report = ReportData(
        report_type="Full Report",
        title="Full Report",
        narrative="## Executive Dashboard\n\nNarrative body.",
        charts={"health_score": 82, "topics": [{"label": "Risk", "value": 5}]},
        metadata={"include_charts": True},
    )

    markdown = report_data_to_markdown(report)
    restored = report_data_from_markdown(
        markdown,
        report_type="Full Report",
        title="Full Report",
    )

    assert restored.narrative == report.narrative
    assert restored.charts == report.charts


def test_report_data_from_storage_prefers_stored_object():
    markdown = "## Executive Dashboard\n\nLegacy body.\n\n<!-- REPORT_CHARTS\n{\"health_score\": 70}\n-->"
    metadata = {
        "report_type": "Executive Summary",
        "source_documents": ["a.pdf"],
        "report_data": ReportData(
            report_type="Executive Summary",
            title="Executive Summary",
            narrative="Stored narrative.",
            charts={"health_score": 70},
            source_documents=["a.pdf"],
        ).to_dict(),
    }

    report = report_data_from_storage(markdown, metadata)

    assert report.narrative == "Stored narrative."
    assert report.charts["health_score"] == 70
    assert report.source_documents == ["a.pdf"]
