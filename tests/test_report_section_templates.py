"""Tests for report section templates and narrative filtering."""

from __future__ import annotations

from services.report_metrics_extractor import extract_report_data
from services.report_section_templates import (
    SectionPlan,
    build_report_section_plan,
    filter_report_narrative,
)
from services.executive_report_prompt import build_executive_report_prompt
from services.full_report_prompt import build_full_report_prompt

LEGAL_NARRATIVE = """
## Executive Intelligence Dashboard

### Executive Summary Card
| Field | Value |
| Industry Status | Stable |

### Top Discussion Topics
- Claims — 31%
- Governance — 14%

## Cross-Document Intelligence
- Claims appeared in 3 of 3 documents.

## Visual Summary
Charts are rendered by the application.

## Detailed Narrative
The court held for the plaintiff.
"""

SINGLE_PERIOD_FULL_REPORT = """
## Full Report Overview

### Executive Summary Card
| Field | Value |
| Reporting Period | Q1 2026 |

## Period Narrative
Single quarter review.

## Cross-Period Themes
- Governance — appeared in 1 of 1 documents

## Period-over-Period Comparison
| Area | Earlier | Latest | Trend |
| Claims | Low | High | ↑ |

## Visual Summary
No charts available.
"""


def test_legal_section_plan_omits_theme_sections():
    report_data = extract_report_data(
        document_text=(
            "=== SOURCE DOCUMENT: judgment.pdf ===\n"
            "The court held that the plaintiff succeeded on March 12, 2024."
        ),
        report_type="Executive Summary",
        source_document_count=1,
    )

    plan = build_report_section_plan(
        report_data,
        user_report_type="Executive Summary",
        document_text=(
            "=== SOURCE DOCUMENT: judgment.pdf ===\n"
            "The court held that the plaintiff succeeded on March 12, 2024."
        ),
        include_charts=True,
        source_document_count=1,
    )

    assert plan.detected_report_type == "LEGAL"
    assert "Visual Summary" not in plan.allowed_sections
    assert "Cross-Document Intelligence" not in plan.allowed_sections
    assert "top discussion topics" in plan.suppressed_dashboard_subsections


def test_filter_report_narrative_keeps_only_allowed_sections():
    plan = SectionPlan(
        allowed_sections=[
            "Executive Intelligence Dashboard",
            "Detailed Narrative",
            "Executive Quotations",
        ],
        allowed_dashboard_subsections=[
            "Executive Summary Card",
            "Executive Snapshot",
        ],
    )

    filtered = filter_report_narrative(LEGAL_NARRATIVE, plan)

    assert "Visual Summary" not in filtered
    assert "Cross-Document Intelligence" not in filtered
    assert "Top Discussion Topics" not in filtered
    assert "Detailed Narrative" in filtered


def test_single_period_full_report_suppresses_period_comparison():
    report_data = extract_report_data(
        document_text="=== SOURCE DOCUMENT: q1.pdf ===\nRevenue reached $4.2m.",
        report_type="Full Report",
        source_document_count=1,
    )

    plan = build_report_section_plan(
        report_data,
        user_report_type="Full Report",
        include_charts=True,
        source_document_count=1,
        report_format="full_report",
    )

    assert plan.multi_period is False
    assert "Period-over-Period Comparison" not in plan.allowed_sections
    assert "Cross-Period Themes" not in plan.allowed_sections

    filtered = filter_report_narrative(SINGLE_PERIOD_FULL_REPORT, plan)

    assert "Period-over-Period Comparison" not in filtered
    assert "Cross-Period Themes" not in filtered
    assert "Visual Summary" not in filtered
    assert "Period Narrative" in filtered


def test_dynamic_executive_prompt_uses_report_type_template():
    report_data = extract_report_data(
        document_text=(
            "=== SOURCE DOCUMENT: minutes.pdf ===\n"
            "Meeting minutes. Action item: finalize budget. Owner: CFO. Deadline: Feb 1."
        ),
        report_type="Meeting Intelligence Report",
        source_document_count=1,
    )
    plan = build_report_section_plan(
        report_data,
        user_report_type="Meeting Intelligence Report",
        include_charts=True,
        source_document_count=1,
    )

    prompt = build_executive_report_prompt(
        report_type="Meeting Intelligence Report",
        document_text="meeting content",
        writing_style="Professional",
        audience="Board",
        include_recommendations=True,
        include_charts=True,
        source_document_count=1,
        report_context={"source_documents": ["minutes.pdf"]},
        section_plan=plan,
    )

    assert "Action Items and Owners" in prompt
    assert "## Visual Summary" not in prompt
    assert "## Cross-Document Intelligence" not in prompt


def test_dynamic_full_report_prompt_omits_single_period_sections():
    report_data = extract_report_data(
        document_text="=== SOURCE DOCUMENT: q1.pdf ===\nRevenue $1m.",
        report_type="Full Report",
        source_document_count=1,
    )
    plan = build_report_section_plan(
        report_data,
        user_report_type="Full Report",
        include_charts=True,
        source_document_count=1,
        report_format="full_report",
    )

    prompt = build_full_report_prompt(
        document_text="content",
        writing_style="Professional",
        audience="Executive Management",
        include_recommendations=True,
        include_charts=True,
        source_document_count=1,
        report_context={"source_documents": ["q1.pdf"], "reporting_period": "Q1 2026"},
        section_plan=plan,
    )

    assert "## Period-over-Period Comparison" not in prompt
    assert "## Cross-Period Themes" not in prompt
    assert "Period Narrative" in prompt
