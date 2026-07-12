"""Tests for the intelligent visualization engine."""

from __future__ import annotations

from models.report_data import ReportData
from services.report_chart_figures import build_report_chart_figures, has_chart_visuals
from services.report_document import compose_report_data
from services.report_metrics_extractor import extract_report_data
from services.visualization_engine import (
    ReportIntent,
    ReportType,
    VisualizationStrategy,
    apply_visualizations,
    build_data_profile,
    classify_report_intent,
    classify_report_type,
    decide_visualization_strategies,
)

LEGAL_DOCUMENT = """
=== SOURCE DOCUMENT: Smith_v_Jones_Judgment.pdf ===

IN THE HIGH COURT OF JUSTICE
Case No. HC/2024/1182

On March 12, 2024 the court heard submissions from the plaintiff and defendant.
The court held that the defendant breached contractual obligations.
On April 3, 2024 judgment was entered for the plaintiff.
An appeal was noted on May 18, 2024.
"""

MEETING_DOCUMENT = """
=== SOURCE DOCUMENT: Board_Meeting_Minutes.pdf ===

Meeting held on January 15, 2026.

Attendees: CEO, CFO, General Counsel.

Decisions:
- Approved Q1 budget.

Action Items:
- Action: Finalize vendor contract — Owner: Procurement — Deadline: February 1, 2026
- Follow-up on compliance audit — Owner: Legal — Deadline: March 1, 2026
"""

FINANCIAL_DOCUMENT = """
=== SOURCE DOCUMENT: Q4_Financials.pdf ===

Revenue reached $12.4 million, up 18% year-over-year.
Expenses totaled $8.1 million.
Profit margin improved to 34%.
Cash flow from operations was $2.3 million in Q4 2025.
"""

RISK_DOCUMENT = """
=== SOURCE DOCUMENT: Enterprise_Risk_Register.pdf ===

Critical risk identified in cyber security exposure.
High priority operational risk in supply chain disruption.
Medium risk in regulatory reporting delays.

Risk assessment completed for the enterprise risk register.
Mitigation plans are required for critical and high severity risks.
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


def test_legal_reports_generate_timeline_not_theme_charts():
    report_data = _base_report_data(LEGAL_DOCUMENT, report_type="Executive Summary")
    enriched = apply_visualizations(
        report_data,
        user_report_type="Executive Summary",
        document_text=LEGAL_DOCUMENT,
        include_charts=True,
        force_generate=True,
    )

    assert enriched.charts["detected_report_type"] == ReportType.LEGAL.value
    assert enriched.charts["_suppress_theme_charts"] is True

    visualization_types = {block["type"] for block in enriched.charts["visualizations"]}
    assert VisualizationStrategy.TIMELINE.value in visualization_types
    assert VisualizationStrategy.BAR_CHART.value not in visualization_types
    assert VisualizationStrategy.PIE_CHART.value not in visualization_types

    figures = build_report_chart_figures(enriched.charts)
    titles = [title for title, _ in figures]

    assert any("Timeline" in title for title in titles)
    assert "Top Discussion Topics" not in titles
    assert "Theme Distribution" not in titles


def test_meeting_reports_generate_action_summary():
    report_data = _base_report_data(MEETING_DOCUMENT, report_type="Meeting Intelligence Report")
    enriched = apply_visualizations(
        report_data,
        user_report_type="Meeting Intelligence Report",
        document_text=MEETING_DOCUMENT,
        include_charts=True,
        force_generate=True,
    )

    assert enriched.charts["detected_report_type"] == ReportType.MEETING.value

    blocks = enriched.charts["visualizations"]
    assert any(block["title"] == "Action Tracker" for block in blocks)
    assert blocks[0]["decision_question"]


def test_financial_reports_generate_charts():
    report_data = _base_report_data(FINANCIAL_DOCUMENT, report_type="Financial Analysis")
    enriched = apply_visualizations(
        report_data,
        user_report_type="Financial Analysis",
        document_text=FINANCIAL_DOCUMENT,
        include_charts=True,
    )

    assert enriched.charts["detected_report_type"] == ReportType.FINANCIAL.value

    strategies = {block["type"] for block in enriched.charts["visualizations"]}
    assert VisualizationStrategy.BAR_CHART.value in strategies or VisualizationStrategy.KPI_CARDS.value in strategies

    figures = build_report_chart_figures(enriched.charts)
    assert figures


def test_risk_reports_generate_risk_matrix():
    report_data = _base_report_data(RISK_DOCUMENT, report_type="Risk Assessment Report")
    enriched = apply_visualizations(
        report_data,
        user_report_type="Risk Assessment Report",
        document_text=RISK_DOCUMENT,
        include_charts=True,
        force_generate=True,
    )

    assert enriched.charts["detected_report_type"] == ReportType.RISK.value
    assert any(
        block["type"] == VisualizationStrategy.RISK_MATRIX.value
        for block in enriched.charts["visualizations"]
    )


def test_documents_without_quantitative_data_generate_no_charts():
    report_data = _base_report_data(GENERIC_NARRATIVE_DOCUMENT)
    enriched = apply_visualizations(
        report_data,
        user_report_type="Executive Summary",
        document_text=GENERIC_NARRATIVE_DOCUMENT,
        include_charts=True,
    )

    assert enriched.charts["_suppress_theme_charts"] is True
    assert not has_chart_visuals(enriched.charts)
    assert build_report_chart_figures(enriched.charts) == []


def test_existing_report_exports_continue_to_work_with_legacy_chart_data():
    legacy_chart_data = {
        "topics": [{"label": "Claims", "value": 31}, {"label": "Capital", "value": 21}],
        "trends": [{"label": "Claims", "prior": 15, "current": 31}],
        "health_score": 75,
    }

    figures = build_report_chart_figures(legacy_chart_data)

    assert [title for title, _ in figures] == [
        "Top Discussion Topics",
        "Theme Distribution",
        "Theme Trends",
    ]


def test_compose_report_data_applies_visualization_engine():
    base = _base_report_data(FINANCIAL_DOCUMENT, report_type="Financial Analysis")

    composed = compose_report_data(
        narrative="## Financial Analysis\n\nRevenue grew to $12.4 million.",
        base=base,
        report_type="Financial Analysis",
        title="Financial Analysis",
        include_charts=True,
    )

    assert composed.charts.get("_suppress_theme_charts") is True
    assert composed.metadata.get("detected_report_type") == ReportType.FINANCIAL.value


def test_report_intent_changes_visualization_priority():
    profile = build_data_profile(
        ReportData(
            charts={"trends": [{"label": "A", "prior": 1, "current": 2}]},
            kpis={"health_score": 80},
        )
    )

    executive = decide_visualization_strategies(
        ReportType.FINANCIAL,
        profile,
        ReportIntent.EXECUTIVE_BRIEF,
    )
    analytical = decide_visualization_strategies(
        ReportType.FINANCIAL,
        profile,
        ReportIntent.ANALYTICAL_REPORT,
    )

    assert VisualizationStrategy.LINE_CHART in analytical
    assert classify_report_intent("Executive Summary") == ReportIntent.EXECUTIVE_BRIEF
    assert classify_report_intent("Full Report") == ReportIntent.ANALYTICAL_REPORT


def test_classify_report_type_from_content():
    legal = classify_report_type(
        ReportData(narrative="The court held that the plaintiff succeeded."),
        document_text=LEGAL_DOCUMENT,
    )
    meeting = classify_report_type(
        ReportData(narrative="Meeting minutes and action items."),
        user_report_type="Meeting Intelligence Report",
    )

    assert legal == ReportType.LEGAL
    assert meeting == ReportType.MEETING


def test_executive_dashboard_metadata_is_attached():
    enriched = apply_visualizations(
        _base_report_data(MEETING_DOCUMENT, report_type="Meeting Intelligence Report"),
        user_report_type="Meeting Intelligence Report",
        document_text=MEETING_DOCUMENT,
        include_charts=True,
        force_generate=True,
    )

    dashboard = enriched.charts["executive_dashboard"]
    assert dashboard["sections"]
    assert any(section["title"] == "Action Items" for section in dashboard["sections"])
