"""
Phase 5–8 feature tests — notifications, admin, telemetry.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import config
from core.telemetry import get_recent_events, track
from services.admin_service import AdminService
from services.notification_service import NotificationService
from services.profile_service import ProfileService
from tests.conftest import TEST_USER, TEST_USER_ID


def test_notification_preferences_round_trip(isolated_env):
    service = NotificationService(TEST_USER_ID)
    saved = service.save_preferences(
        {
            "report_ready": False,
            "usage_alerts": True,
            "billing": True,
            "product_updates": True,
        }
    )

    assert saved["report_ready"] is False
    assert saved["product_updates"] is True
    assert NotificationService(TEST_USER_ID).get_preferences()["product_updates"] is True


def test_profile_timezone_persisted(isolated_env):
    profile = ProfileService(TEST_USER_ID)
    profile.save({"timezone": "Africa/Lagos"})
    assert profile.load()["timezone"] == "Africa/Lagos"


def test_notify_report_ready_skips_when_disabled(isolated_env, monkeypatch):
    NotificationService(TEST_USER_ID).save_preferences({"report_ready": False})
    result = NotificationService(TEST_USER_ID).notify_report_ready(
        report_name="Board Pack",
        project_name="Q1",
        email=TEST_USER.email,
    )
    assert result == "skipped"


def test_is_admin_by_user_id(isolated_env, monkeypatch):
    monkeypatch.setattr("config.ADMIN_USER_IDS", (TEST_USER_ID,))
    from core.auth import is_admin

    assert is_admin() is True


def test_admin_lists_local_user(isolated_env, monkeypatch):
    monkeypatch.setattr("config.ADMIN_USER_IDS", (TEST_USER_ID,))
    ProfileService(TEST_USER_ID).save({"full_name": "Admin Tester"})

    users = AdminService().list_users()
    assert any(user["user_id"] == TEST_USER_ID for user in users)


def test_admin_set_user_plan(isolated_env, monkeypatch):
    monkeypatch.setattr("config.ADMIN_USER_IDS", (TEST_USER_ID,))
    AdminService().set_user_plan(TEST_USER_ID, "starter", actor_user_id=TEST_USER_ID)

    from services.subscription_service import SubscriptionService

    state = SubscriptionService(TEST_USER_ID).load_state()
    assert state["billing_plan"] == "starter"


def test_telemetry_writes_local_events(tmp_path, monkeypatch):
    events_path = tmp_path / "analytics.json"
    monkeypatch.setattr("config.ANALYTICS_ENABLED", True)
    monkeypatch.setattr("config.ANALYTICS_EVENTS_PATH", str(events_path))

    track("test_event", user_id=TEST_USER_ID, properties={"source": "pytest"})

    events = json.loads(events_path.read_text(encoding="utf-8"))
    assert events[-1]["event"] == "test_event"
    assert events[-1]["user_id"] == TEST_USER_ID

    recent = get_recent_events(limit=1)
    assert recent[0]["event"] == "test_event"
