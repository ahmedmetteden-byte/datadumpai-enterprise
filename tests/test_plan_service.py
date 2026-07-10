"""
Unit tests for PlanService.
"""

from __future__ import annotations

import pytest

from services.plan_service import PlanLimitError, PlanService
from services.usage_service import UsageService
from tests.conftest import TEST_USER_ID


@pytest.fixture
def plan_service(isolated_env) -> PlanService:
    usage = UsageService(user_id=TEST_USER_ID)
    return PlanService(usage)


def test_free_plan_report_types(plan_service: PlanService):
    assert plan_service.get_available_report_types() == ["Executive Summary"]
    assert "Board Report" in plan_service.locked_report_types()
    assert not plan_service.uses_intelligence_format("Executive Summary")
    assert not plan_service.can_use_web_research()


def test_professional_plan_unlocks_intelligence(isolated_env):
    usage = UsageService(user_id=TEST_USER_ID)
    usage.set_plan("professional")
    plans = PlanService(usage)

    assert plans.is_professional
    assert "Board Report" in plans.get_available_report_types()
    assert plans.uses_intelligence_format("Executive Summary")
    assert plans.uses_intelligence_format("Risk Assessment Report")
    assert plans.can_use_web_research()
    assert plans.can_use_professional_exports()


def test_free_project_limit(plan_service: PlanService):
    with pytest.raises(PlanLimitError) as exc:
        plan_service.check_can_create_project(3)

    assert exc.value.limit_type == "projects"

    plan_service.check_can_create_project(2)
