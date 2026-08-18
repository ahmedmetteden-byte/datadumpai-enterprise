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


TABULAR_FINANCIAL_DOCUMENT = """
=== SOURCE DOCUMENT: Quarterly_Revenue.pdf ===

### Revenue by Quarter

| Quarter | Revenue |
|---------|---------|
| Q1 | $1,200,000 |
| Q2 | $1,450,000 |
| Q3 | $1,600,000 |
| Q4 | $1,900,000 |
"""


def test_financial_reports_extract_real_values_from_a_markdown_table():
    """Regression test: a row label like "Q1" sitting right after a
    "Revenue" table header used to make the keyword-then-nearest-digits
    regex capture the "1" in "Q1" instead of the real $1,200,000 figure,
    producing a single fabricated-looking bar instead of the real
    per-quarter series. The engine must prefer parsing the actual table."""

    report_data = _base_report_data(TABULAR_FINANCIAL_DOCUMENT, report_type="Financial Analysis")
    enriched = apply_visualizations(
        report_data,
        user_report_type="Financial Analysis",
        document_text=TABULAR_FINANCIAL_DOCUMENT,
        include_charts=True,
        force_generate=True,
    )

    bar_blocks = [
        block
        for block in enriched.charts["visualizations"]
        if block["type"] == VisualizationStrategy.BAR_CHART.value
    ]
    assert bar_blocks, "expected a BAR_CHART block from the quarterly revenue table"

    series = bar_blocks[0]["data"]["series"]
    assert [item["label"] for item in series] == ["Q1", "Q2", "Q3", "Q4"]
    assert [item["value"] for item in series] == [1200000.0, 1450000.0, 1600000.0, 1900000.0]


EXECUTIVE_SUMMARY_FINDINGS_DOCUMENT = """
=== SOURCE DOCUMENT: Annual_Statistical_Market_Report.pdf ===

## Executive Summary
The industry achieved a gross written premium of N1,558.7 billion in 2024, a 49.4% increase from 2023. The passage of the Reform Bill modernizes the regulatory framework.

## Key Findings

### **Consistent Growth in Gross Premiums**
Gross written premiums increased from N789.6 billion in 2022 to N1,558.7 billion in 2024. Growth rate reached a new high.
**Confidence:** High — Supported by consistent data across multiple years.
**Source:** Annual_Statistical_Market_Report.pdf.

### **Dominance of Non-Life Insurance Segment**
The non-life segment accounts for 68.0% of the gross premium pool in 2024.
**Confidence:** High — Consistent data.
**Source:** Annual_Statistical_Market_Report.pdf.

### **Surge in Gross Claims**
Gross claims reported in 2024 grew by 50.9% to N635.5 billion.
**Confidence:** Medium — Supported by recent data.
**Source:** Annual_Statistical_Market_Report.pdf.

### **Technological Integration and Modernization**
The implementation of digital tools and systems, such as Microsoft Office 365 and an Electronic Documentation Management System, has improved operational efficiency.
**Confidence:** Medium — Mentioned in recent reports.
**Source:** Annual_Statistical_Market_Report.pdf.

## Detailed Analysis
The market grew steadily across the period under review.

## Conclusion
The industry is on a positive trajectory.
"""


def test_executive_summary_reports_get_kpi_cards_from_findings():
    """Regression test for a real production report (NAICOM Statistical
    Report, Executive Summary template): EXECUTIVE_BRIEF intent only
    allows KPI_CARDS among numeric chart types, and a REGULATORY-classified
    report (this one, due to "regulatory"/reform-bill language) never
    checked for a KPI signal before — so no chart was ever produced for
    this exact real-world scenario, reproducing the original user report."""

    # Constructed directly (not via _base_report_data()/extract_report_data(),
    # which pre-populates generic synthetic KPIs) to match how the live SPA
    # report-generation flow actually builds ReportData — narrative only,
    # kpis left empty — which is the real-world condition this regression
    # test reproduces.
    report_data = ReportData(
        report_type="Executive Summary",
        title="Executive Summary — Custom / Ad hoc",
        narrative=EXECUTIVE_SUMMARY_FINDINGS_DOCUMENT,
    )
    enriched = apply_visualizations(
        report_data,
        user_report_type="Executive Summary",
        document_text=EXECUTIVE_SUMMARY_FINDINGS_DOCUMENT,
        include_charts=True,
        force_generate=True,
    )

    blocks = enriched.charts["visualizations"]
    assert blocks, "expected at least one visualization block"
    kpi_blocks = [block for block in blocks if block["type"] == VisualizationStrategy.KPI_CARDS.value]
    assert kpi_blocks, "expected a KPI_CARDS block"

    items = kpi_blocks[0]["data"]["items"]
    # "Microsoft Office 365" must not be mistaken for a currency figure
    # ("365 million"-style word-boundary bug), and the mismatched-unit
    # 68.0% finding must be dropped in favor of the larger same-unit
    # (billion-naira) group so the chart doesn't plot incompatible scales.
    labels = {item["label"] for item in items}
    assert "Technological Integration and Modernization" not in labels
    assert "Dominance of Non-Life Insurance Segment" not in labels
    assert labels == {"Consistent Growth in Gross Premiums", "Surge in Gross Claims"}

    values = {item["label"]: item["value"] for item in items}
    assert values["Consistent Growth in Gross Premiums"] == 1558.7
    assert values["Surge in Gross Claims"] == 635.5
    for item in items:
        assert isinstance(item["value"], float)

    # Must actually be renderable — this is exactly the crash this test
    # guards against: KPI_CARDS renders as a Plotly bar chart, which
    # requires float() on every item's value.
    figures = build_report_chart_figures(enriched.charts)
    assert figures


def test_currency_pattern_does_not_match_across_word_boundaries():
    """"Microsoft 365" (digits immediately followed by a word starting
    with "m") must not be treated as a "365 million"-style currency
    figure — the suffix alternatives need a word boundary."""

    from services.visualization_engine import CURRENCY_PATTERN

    assert CURRENCY_PATTERN.search("Microsoft Office 365 was deployed") is None
    assert CURRENCY_PATTERN.search("revenue of $5m was reported") is not None
    assert CURRENCY_PATTERN.search("grew to 12.4 million users") is not None


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
