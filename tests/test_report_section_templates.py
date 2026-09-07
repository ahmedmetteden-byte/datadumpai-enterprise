"""Tests for report section templates and narrative filtering."""

from __future__ import annotations

from services.report_metrics_extractor import extract_report_data
from services.report_section_templates import (
    SectionPlan,
    build_report_section_plan,
    filter_report_narrative,
)

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


def test_section_plan_covers_meeting_intelligence_report_type():
    """The two removed tests here (test_dynamic_executive_prompt_uses_report_
    type_template, test_dynamic_full_report_prompt_omits_single_period_
    sections) fed build_report_section_plan()'s output into the now-removed
    dead prompt builders (build_executive_report_prompt / build_full_report_
    prompt — see services/executive_report_prompt.py and services/full_
    report_prompt.py's module docstrings). The live assertion worth keeping
    is that build_report_section_plan() itself correctly detects a Meeting
    Intelligence Report's action-item section — SpaReportGenerationService's
    own inline prompt construction (the actual live path) is covered
    separately in tests/test_spa_report_generation_service.py."""

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

    assert "Action Items and Owners" in plan.allowed_sections
    assert "Visual Summary" not in plan.allowed_sections
    assert "Cross-Document Intelligence" not in plan.allowed_sections


def test_section_plan_omits_single_period_sections_for_full_report():
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

    assert "Period-over-Period Comparison" not in plan.allowed_sections
    assert "Cross-Period Themes" not in plan.allowed_sections
