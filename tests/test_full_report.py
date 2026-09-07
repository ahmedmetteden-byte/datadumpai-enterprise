"""
Tests for Full Report plan gating.

The prompt-building tests that used to live here (build_full_report_prompt)
were removed along with that dead function — see
services/full_report_prompt.py's module docstring. is_full_report() and the
plan-gating behavior below are the real, live-tested surface of this module.
"""

from __future__ import annotations

import pytest

from services.full_report_prompt import is_full_report
from services.plan_service import PlanService
from services.usage_service import UsageService
from tests.conftest import TEST_USER_ID


def test_is_full_report():
    assert is_full_report("Full Report")
    assert not is_full_report("Executive Summary")


def test_starter_plan_includes_full_report(isolated_env):
    usage = UsageService()
    usage.set_plan("starter")
    plans = PlanService(usage)

    assert "Full Report" in plans.get_available_report_types()
    assert plans.uses_full_report_format("Full Report")
    assert not plans.uses_intelligence_format("Full Report")


def test_free_plan_locks_full_report(isolated_env):
    usage = UsageService()
    plans = PlanService(usage)

    assert "Full Report" in plans.locked_report_types()
    assert not plans.is_report_type_available("Full Report")
