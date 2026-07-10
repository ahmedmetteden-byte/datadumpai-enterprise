"""
Subscription and file storage tests.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from config import TRIAL_PLAN
from services.subscription_service import SubscriptionService
from storage.file_store import FileStore
from tests.conftest import TEST_USER_ID


def test_start_trial_grants_professional_access(isolated_env):
    service = SubscriptionService(TEST_USER_ID)
    state = service.start_trial()

    assert state["subscription_status"] == SubscriptionService.STATUS_TRIALING
    assert state["trial_ends_at"] is not None
    assert service.get_effective_plan(state) == TRIAL_PLAN


def test_expired_trial_falls_back_to_free(isolated_env):
    service = SubscriptionService(TEST_USER_ID)
    expired = datetime.now(timezone.utc) - timedelta(days=1)
    service.save_state(
        {
            "plan": "free",
            "billing_plan": "free",
            "subscription_status": SubscriptionService.STATUS_TRIALING,
            "trial_ends_at": expired.isoformat(),
            "period": "2026-07",
            "reports_generated": 0,
            "uploads": 0,
        }
    )

    assert service.get_effective_plan() == "free"


def test_local_file_store_round_trip(isolated_env):
    store = FileStore(TEST_USER_ID)
    storage_path = store.write(
        "project-1",
        "documents",
        "notes.txt",
        b"hello storage",
    )

    assert store.read_text(storage_path) == "hello storage"
    assert "notes.txt" in store.list_files("project-1", "documents")

    store.delete(storage_path)
    assert not store.exists(storage_path)
