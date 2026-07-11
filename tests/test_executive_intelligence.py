"""Tests for executive intelligence polish features."""

from __future__ import annotations

from services.executive_report_prompt import (
    INTELLIGENCE_DASHBOARD_TITLE,
    build_executive_report_prompt,
)
from services.report_chart_data import (
    extract_chart_data,
    extract_executive_summary_card,
    is_intelligence_report,
    prepare_report_for_output,
    strip_chart_data,
)
from ui.report_renderer import _health_gauge_html, enhance_report_markdown


def test_intelligence_dashboard_title():
    assert INTELLIGENCE_DASHBOARD_TITLE == "Executive Intelligence Dashboard"


def test_prompt_includes_new_sections():
    prompt = build_executive_report_prompt(
        report_type="Executive Summary",
        document_text="=== SOURCE DOCUMENT: a.txt ===\n\nSample",
        writing_style="Professional",
        audience="Board",
        include_recommendations=True,
        include_charts=True,
        source_document_count=4,
        report_context={
            "source_documents": ["a.txt"],
            "has_prior_reports": True,
        },
    )

    assert "## Executive Intelligence Dashboard" in prompt
    assert "### Executive Summary Card" in prompt
    assert "## Cross-Document Intelligence" in prompt
    assert "## Executive Quotations" in prompt
    assert "## Industry Benchmark" in prompt
    assert "Do NOT output a REPORT_CHARTS block" in prompt
    assert "🔴" in prompt


def test_extract_chart_data_and_strip():
    report = (
        "## Executive Intelligence Dashboard\n\n"
        "Body text.\n\n"
        '<!-- REPORT_CHARTS\n'
        '{"topics": [{"label": "Claims", "value": 31}], "health_score": 75}\n'
        "-->"
    )

    data = extract_chart_data(report)
    stripped = strip_chart_data(report)

    assert data["health_score"] == 75
    assert "REPORT_CHARTS" not in stripped
    assert is_intelligence_report(report)


def test_extract_chart_data_without_underscore():
    report = (
        "## Full Report Overview\n\n"
        "Body text.\n\n"
        '<!-- REPORTCHARTS\n'
        '{"topics": [{"label": "Claims", "value": 31}], "health_score": 75}\n'
        "-->"
    )

    prepared = prepare_report_for_output(report)

    assert prepared.chart_data["health_score"] == 75
    assert "REPORTCHARTS" not in prepared.text
    assert "Body text." in prepared.text


def test_extract_executive_summary_card():
    report = (
        "## Executive Intelligence Dashboard\n\n"
        "### Executive Summary Card\n"
        "| Field | Value |\n"
        "| --- | --- |\n"
        "| Industry Status | 🟡 Cautious |\n"
        "| Confidence | 90% |\n"
        "| Priority | Claims Reform |\n"
        "| Overall Trend | Improving |\n\n"
        "### Executive Snapshot\n"
        "More content."
    )

    card, remaining = extract_executive_summary_card(report)

    assert card["Industry Status"] == "🟡 Cautious"
    assert card["Confidence"] == "90%"
    assert "Executive Summary Card" not in remaining


def test_health_gauge_and_quote_styling():
    markdown = (
        "**Score:** 75/100\n\n"
        '> "Prompt and fair claims settlement is the cornerstone of public trust."\n'
        "> — *Annual Report 2024*"
    )

    enhanced = enhance_report_markdown(markdown)

    assert "dde-health-gauge" in enhanced
    assert "dde-health-bar-fill" in enhanced
    assert "dde-executive-quote" in enhanced
