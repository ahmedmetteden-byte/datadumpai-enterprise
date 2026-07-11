"""
Tests for Full Report prompt and plan gating.
"""

from __future__ import annotations

import pytest

from services.full_report_prompt import build_full_report_prompt, is_full_report
from services.plan_service import PlanService
from services.usage_service import UsageService
from tests.conftest import TEST_USER_ID


def test_is_full_report():
    assert is_full_report("Full Report")
    assert not is_full_report("Executive Summary")


def test_build_full_report_prompt_includes_annual_period():
    prompt = build_full_report_prompt(
        document_text="=== SOURCE DOCUMENT: q1.pdf ===\nContent",
        writing_style="Professional",
        audience="Executive Management",
        include_recommendations=True,
        include_charts=False,
        source_document_count=4,
        report_context={
            "source_documents": ["q1.pdf", "q2.pdf", "q3.pdf", "q4.pdf"],
            "reporting_period": "Annual Report",
            "period_guidance": "Roll up quarterly reports into one annual report.",
            "prior_reports_context": "",
            "has_prior_reports": False,
        },
    )

    assert "Annual Report" in prompt
    assert "full-year" in prompt.lower() or "annual" in prompt.lower()


def test_build_full_report_prompt_includes_period_rollup():
    prompt = build_full_report_prompt(
        document_text="=== SOURCE DOCUMENT: week1.pdf ===\nContent",
        writing_style="Professional",
        audience="Executive Management",
        include_recommendations=True,
        include_charts=False,
        source_document_count=4,
        report_context={
            "source_documents": ["week1.pdf", "week2.pdf", "week3.pdf", "week4.pdf"],
            "reporting_period": "Monthly Report",
            "period_guidance": "Roll up weekly reports into one monthly report.",
            "prior_reports_context": "",
            "has_prior_reports": False,
        },
    )

    assert "Full Report" in prompt
    assert "Monthly Report" in prompt
    assert "Period Narrative" in prompt
    assert "Cross-Period Themes" in prompt
    assert "week1.pdf" in prompt
    assert "4 source document" in prompt or "4 source document(s)" in prompt


def test_starter_plan_includes_full_report(isolated_env):
    usage = UsageService(user_id=TEST_USER_ID)
    usage.set_plan("starter")
    plans = PlanService(usage)

    assert "Full Report" in plans.get_available_report_types()
    assert plans.uses_full_report_format("Full Report")
    assert not plans.uses_intelligence_format("Full Report")


def test_free_plan_locks_full_report(isolated_env):
    usage = UsageService(user_id=TEST_USER_ID)
    plans = PlanService(usage)

    assert "Full Report" in plans.locked_report_types()
    assert not plans.is_report_type_available("Full Report")
