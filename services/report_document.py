"""
Report document operations — compose, parse, and convert ReportData views.
"""

from __future__ import annotations

from typing import Any

from models.report_data import ReportData
from services.report_assembler import assemble_report_text
from services.report_chart_data import (
    extract_chart_data,
    is_intelligence_report,
    prepare_report_for_output,
    strip_chart_data,
)


def compose_report_data(
    *,
    narrative: str,
    base: ReportData,
    report_type: str,
    title: str,
    include_charts: bool,
) -> ReportData:
    """Merge AI narrative with extracted canonical metrics into a ReportData object."""

    cleaned_narrative = strip_chart_data(narrative).strip()

    return ReportData(
        report_type=report_type,
        title=title or report_type,
        narrative=cleaned_narrative,
        metadata={
            **base.metadata,
            "report_type": report_type,
            "title": title or report_type,
            "include_charts": include_charts,
        },
        metrics=dict(base.metrics),
        charts=dict(base.charts),
        kpis=dict(base.kpis),
        source_documents=list(base.source_documents),
        executive_summary=dict(base.executive_summary),
        sections=list(base.sections),
        recommendations=list(base.recommendations),
        citations=list(base.citations),
    )


def report_data_to_markdown(report: ReportData, *, include_charts: bool | None = None) -> str:
    """Markdown storage view of a ReportData object."""

    if include_charts is None:
        include_charts = bool(report.metadata.get("include_charts", report.charts))

    return assemble_report_text(
        report.narrative,
        report,
        include_charts=include_charts and bool(report.charts),
    )


def report_data_from_markdown(
    markdown_text: str,
    *,
    report_type: str = "",
    title: str = "",
    source_documents: list[str] | None = None,
    stored: ReportData | None = None,
) -> ReportData:
    """Reconstruct ReportData from persisted markdown, optionally enriched by stored metadata."""

    narrative = strip_chart_data(markdown_text).strip()
    embedded_charts = extract_chart_data(markdown_text)

    if stored and stored.narrative:
        report = ReportData.from_dict(stored.to_dict())
        if not report.narrative:
            report.narrative = narrative
        if not report.charts and embedded_charts:
            report.charts = embedded_charts
        return report

    report = stored or ReportData()
    charts = report.charts or embedded_charts

    return ReportData(
        report_type=report_type or report.report_type,
        title=title or report.title or report_type,
        narrative=narrative,
        metadata=dict(report.metadata),
        metrics=dict(report.metrics),
        charts=dict(charts),
        kpis=dict(report.kpis),
        source_documents=list(source_documents or report.source_documents),
        executive_summary=dict(report.executive_summary),
        sections=list(report.sections),
        recommendations=list(report.recommendations),
        citations=list(report.citations),
    )


def report_data_from_storage(
    markdown_text: str,
    metadata: dict[str, Any] | None = None,
) -> ReportData:
    """Load ReportData from saved markdown plus sidecar metadata."""

    metadata = metadata or {}
    stored = ReportData.from_dict(metadata.get("report_data"))

    return report_data_from_markdown(
        markdown_text,
        report_type=str(metadata.get("report_type") or stored.report_type or ""),
        title=str(metadata.get("report_type") or stored.title or ""),
        source_documents=list(metadata.get("source_documents") or stored.source_documents),
        stored=stored,
    )


def prepare_report_view(report: ReportData):
    """Return cleaned narrative text and chart data for browser rendering."""

    return prepare_report_for_output(report.to_markdown(), report)


def report_is_intelligence(report: ReportData) -> bool:
    return is_intelligence_report(report.narrative)
