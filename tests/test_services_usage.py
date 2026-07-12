"""
Unit tests for UsageService.
"""

from __future__ import annotations

import pytest

from services.usage_service import UsageService
from storage.dict_storage import DictStorage
from tests.conftest import TEST_USER_ID


@pytest.fixture
def usage_service(isolated_env) -> UsageService:
    return UsageService()


def test_free_plan_defaults(usage_service: UsageService):
    snapshot = usage_service.get_snapshot()

    assert snapshot.plan == "free"
    assert snapshot.reports_limit == 5
    assert snapshot.uploads_limit == 10
    assert snapshot.projects_max == 3
    assert snapshot.reports_used == 0
    assert snapshot.uploads_used == 0


def test_record_uploads_and_reports(usage_service: UsageService):
    usage_service.record_uploads(3)
    usage_service.record_report_generated()

    snapshot = usage_service.get_snapshot()

    assert snapshot.uploads_used == 3
    assert snapshot.reports_used == 1


def test_upload_and_report_limits_are_enforced(usage_service: UsageService):
    from services.usage_service import UsageLimitError

    usage_service.record_uploads(10)
    with pytest.raises(UsageLimitError):
        usage_service.check_can_upload(1)

    for _ in range(5):
        usage_service.record_report_generated()

    with pytest.raises(UsageLimitError):
        usage_service.check_can_generate_report()


def test_pro_plan_is_unlimited(usage_service: UsageService):
    usage_service.set_plan("professional")

    usage_service.record_uploads(100)
    usage_service.check_can_upload(50)
    usage_service.check_can_generate_report()

    snapshot = usage_service.get_snapshot()

    assert snapshot.is_pro is True
    assert snapshot.reports_limit is None
    assert snapshot.uploads_limit is None


def test_usage_resets_on_new_period(isolated_env):
    storage_path = isolated_env["usage_json"]
    storage = DictStorage(
        storage_path,
        default={
            "plan": "free",
            "period": "2020-01",
            "reports_generated": 5,
            "uploads": 10,
        },
    )
    storage.save(storage.load())

    service = UsageService()
    snapshot = service.get_snapshot()

    assert snapshot.period != "2020-01"
    assert snapshot.reports_used == 0
    assert snapshot.uploads_used == 0
