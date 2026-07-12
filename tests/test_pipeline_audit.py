"""Pipeline audit for section plan enforcement."""

from __future__ import annotations

from services.report_document import compose_report_data, prepare_report_view, report_data_from_storage
from services.report_metrics_extractor import extract_report_data
from services.report_section_templates import build_report_section_plan
from services.full_report_prompt import build_full_report_prompt

LEGAL = """=== SOURCE DOCUMENT: judgment.pdf ===
The court held that the plaintiff succeeded on March 12, 2024.
The defendant appealed on May 18, 2024.
"""

NARRATIVE = """## Full Report Overview
### Executive Summary Card
| Field | Value |
| Reporting Period | Q1 2026 |

## Period Narrative
Court held for plaintiff.

## Cross-Period Themes
- Governance appeared in 1 of 1 documents

## Period-over-Period Comparison
| Area | Earlier | Latest | Trend |
| Claims | Low | High | up |

## Visual Summary
Charts rendered automatically.

## Executive Quotations
> "Quote"
"""


def test_compose_filters_forbidden_sections_for_single_legal_full_report():
    base = extract_report_data(
        document_text=LEGAL,
        report_type="Full Report",
        source_document_count=1,
    )
    report_context = {
        "source_documents": ["judgment.pdf"],
    }
    plan_pre = build_report_section_plan(
        base,
        user_report_type="Full Report",
        document_text=LEGAL,
        report_context=report_context,
        include_charts=True,
        source_document_count=1,
        report_format="full_report",
    )

    composed = compose_report_data(
        narrative=NARRATIVE,
        base=base,
        report_type="Full Report",
        title="Full Report",
        include_charts=True,
    )

    assert "Cross-Period Themes" not in composed.narrative
    assert "Period-over-Period Comparison" not in composed.narrative
    assert "Visual Summary" not in composed.narrative

    prepared = prepare_report_view(composed)
    assert "Cross-Period Themes" not in prepared.text

    loaded = report_data_from_storage(
        composed.to_markdown(),
        {
            "report_type": "Full Report",
            "source_documents": ["judgment.pdf"],
            "report_data": composed.to_dict(),
        },
    )
    assert "Cross-Period Themes" not in loaded.narrative


def test_prompt_with_section_plan_omits_forbidden_headings():
    base = extract_report_data(
        document_text=LEGAL,
        report_type="Full Report",
        source_document_count=1,
    )
    plan = build_report_section_plan(
        base,
        user_report_type="Full Report",
        document_text=LEGAL,
        report_context={"source_documents": ["judgment.pdf"], "has_prior_reports": True},
        include_charts=True,
        source_document_count=1,
        report_format="full_report",
    )
    prompt = build_full_report_prompt(
        document_text=LEGAL,
        writing_style="Professional",
        audience="Executive Management",
        include_recommendations=True,
        include_charts=True,
        source_document_count=1,
        report_context={
            "source_documents": ["judgment.pdf"],
            "reporting_period": "Q1 2026",
        },
        section_plan=plan,
    )

    assert "## Cross-Period Themes" not in prompt
    assert "## Period-over-Period Comparison" not in prompt
    assert "## Visual Summary" not in prompt
