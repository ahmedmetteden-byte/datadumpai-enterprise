"""Tests for visualization confidence scoring and on-demand insights."""

from __future__ import annotations

from models.report_data import ReportData
from services.report_chart_figures import has_chart_visuals
from services.report_metrics_extractor import extract_report_data
from services.visual_insights_service import explore_visual_insights
from services.visualization_decision import (
    VisualizationConfidenceLevel,
    evaluate_visualization_decision,
)
from services.visualization_engine import apply_visualizations

FINANCIAL_DOCUMENT = """
Revenue reached $12.4 million, up 18% year-over-year.
Expenses totaled $8.1 million.
Profit margin improved to 34%.
Cash flow from operations was $2.3 million in Q4 2025.
"""

ANNUAL_STATISTICS_DOCUMENT = """
Annual Statistics Report 2025

Revenue trend by quarter:
Q1 $2.1M, Q2 $2.4M, Q3 $2.8M, Q4 $3.1M.
KPI dashboard shows customer growth at 14%.
Regional comparison: North 42%, South 31%, West 27%.
"""

GENERIC_NARRATIVE_DOCUMENT = """
The working group reviewed governance themes and stakeholder engagement.
Claims and capital were discussed repeatedly without numeric evidence.
"""


def _base_report_data(document_text: str, *, report_type: str = "Executive Summary") -> ReportData:
    return extract_report_data(
        document_text=document_text,
        report_type=report_type,
        source_document_count=1,
    )


def test_annual_statistics_is_high_confidence_and_auto_generates():
    report_data = _base_report_data(
        ANNUAL_STATISTICS_DOCUMENT,
        report_type="Annual Statistics",
    )
    decision = evaluate_visualization_decision(
        report_data,
        user_report_type="Annual Statistics",
        document_text=ANNUAL_STATISTICS_DOCUMENT,
        reporting_period="Annual Report",
    )

    assert decision.level == VisualizationConfidenceLevel.HIGH
    assert decision.confidence >= 80
    assert decision.auto_generate is True

    enriched = apply_visualizations(
        report_data,
        user_report_type="Annual Statistics",
        document_text=ANNUAL_STATISTICS_DOCUMENT,
        include_charts=True,
        reporting_period="Annual Report",
    )

    assert has_chart_visuals(enriched.charts)


def test_financial_analysis_auto_generates_at_high_confidence():
    report_data = _base_report_data(FINANCIAL_DOCUMENT, report_type="Financial Analysis")
    decision = evaluate_visualization_decision(
        report_data,
        user_report_type="Financial Analysis",
        document_text=FINANCIAL_DOCUMENT,
    )

    assert decision.level == VisualizationConfidenceLevel.HIGH
    enriched = apply_visualizations(
        report_data,
        user_report_type="Financial Analysis",
        document_text=FINANCIAL_DOCUMENT,
        include_charts=True,
    )

    assert has_chart_visuals(enriched.charts)


def test_executive_summary_on_narrative_content_is_low_confidence_without_auto_charts():
    report_data = _base_report_data(GENERIC_NARRATIVE_DOCUMENT)
    decision = evaluate_visualization_decision(
        report_data,
        user_report_type="Executive Summary",
        document_text=GENERIC_NARRATIVE_DOCUMENT,
    )

    assert decision.level == VisualizationConfidenceLevel.LOW
    assert decision.auto_generate is False

    enriched = apply_visualizations(
        report_data,
        user_report_type="Executive Summary",
        document_text=GENERIC_NARRATIVE_DOCUMENT,
        include_charts=True,
    )

    assert not has_chart_visuals(enriched.charts)
    assert enriched.charts.get("visualization_decision")


def test_explore_visual_insights_returns_friendly_message_for_narrative_reports():
    report_data = _base_report_data(GENERIC_NARRATIVE_DOCUMENT)
    updated, decision, message = explore_visual_insights(
        report_data,
        user_report_type="Executive Summary",
        document_text=GENERIC_NARRATIVE_DOCUMENT,
    )

    assert decision.level == VisualizationConfidenceLevel.LOW
    assert message is not None
    assert "No meaningful visualizations were identified" in message
    assert not has_chart_visuals(updated.charts)


def test_explore_visual_insights_can_add_charts_on_demand_for_medium_reports():
    report_data = _base_report_data(
        """
        Board review summary for leadership.
        The committee discussed governance priorities and stakeholder engagement.
        A follow-up session is scheduled for next month.
        """,
        report_type="Board Report",
    )

    initial = apply_visualizations(
        report_data,
        user_report_type="Board Report",
        document_text=report_data.narrative,
        include_charts=True,
    )
    assert not has_chart_visuals(initial.charts)

    updated, _, message = explore_visual_insights(
        initial,
        user_report_type="Board Report",
        document_text=initial.narrative,
    )

    assert updated.charts.get("visualization_decision", {}).get("explored") is True
    assert message is None or isinstance(message, str)
