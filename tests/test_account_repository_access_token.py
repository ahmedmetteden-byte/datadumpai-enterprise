"""
Tests that access_token / use_service_role thread correctly from the API
layer down to the Supabase client construction for billing/usage data.

This is the same class of bug fixed repeatedly elsewhere in this codebase:
without an explicit access_token, core.database.get_database_client() falls
back to a Streamlit-only session accessor and raises under FastAPI. These
tests pin the fix at each layer so it can't silently regress.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from repositories import account_repository
from services import subscription_service, usage_service
from services.billing_service import BillingService, activate_subscription_for_user
from services.subscription_service import SubscriptionService
from services.usage_service import UsageService
from tests.conftest import TEST_USER, TEST_USER_ID


@pytest.fixture
def supabase_backend(monkeypatch):
    monkeypatch.setattr("config.use_database", lambda: True)


def test_supabase_usage_repository_uses_access_token(supabase_backend, monkeypatch):
    calls = []
    fake_client = MagicMock()

    def fake_get_database_client(*, access_token=None):
        calls.append(access_token)
        return fake_client

    monkeypatch.setattr(
        account_repository, "get_database_client", fake_get_database_client
    )

    repo = account_repository.SupabaseUsageRepository(
        TEST_USER_ID, default={}, access_token="tok-123"
    )

    assert repo._client is fake_client
    assert calls == ["tok-123"]


def test_supabase_usage_repository_uses_service_role_client(
    supabase_backend, monkeypatch
):
    calls = []
    fake_client = MagicMock()

    def fake_get_service_role_client():
        calls.append(True)
        return fake_client

    monkeypatch.setattr(
        account_repository, "get_service_role_client", fake_get_service_role_client
    )

    repo = account_repository.SupabaseUsageRepository(
        TEST_USER_ID, default={}, use_service_role=True
    )

    assert repo._client is fake_client
    assert calls == [True]


def test_get_usage_repository_for_user_threads_kwargs(supabase_backend, monkeypatch):
    captured = {}

    class FakeRepo:
        def __init__(self, user_id, *, default, access_token=None, use_service_role=False):
            captured["access_token"] = access_token
            captured["use_service_role"] = use_service_role

    monkeypatch.setattr(account_repository, "SupabaseUsageRepository", FakeRepo)

    account_repository.get_usage_repository_for_user(
        TEST_USER_ID, default={}, access_token="tok-abc", use_service_role=True
    )

    assert captured == {"access_token": "tok-abc", "use_service_role": True}


def test_get_usage_repository_threads_access_token(supabase_backend, monkeypatch):
    captured = {}

    def fake_for_user(user_id, *, default, access_token=None, use_service_role=False):
        captured["access_token"] = access_token
        captured["use_service_role"] = use_service_role

    monkeypatch.setattr(
        account_repository, "get_usage_repository_for_user", fake_for_user
    )

    account_repository.get_usage_repository(default={}, access_token="tok-xyz")

    assert captured == {"access_token": "tok-xyz", "use_service_role": False}


def test_subscription_service_threads_access_token(monkeypatch):
    captured = {}

    def fake_get_usage_repository(*, default, access_token=None):
        captured["access_token"] = access_token
        return MagicMock()

    monkeypatch.setattr(
        subscription_service, "get_usage_repository", fake_get_usage_repository
    )

    SubscriptionService(current_user=TEST_USER, access_token="tok-sub")

    assert captured["access_token"] == "tok-sub"


def test_subscription_service_for_user_id_threads_service_role(monkeypatch):
    captured = {}

    def fake_for_user(user_id, *, default, access_token=None, use_service_role=False):
        captured["use_service_role"] = use_service_role
        return MagicMock()

    monkeypatch.setattr(
        subscription_service, "get_usage_repository_for_user", fake_for_user
    )

    SubscriptionService.for_user_id(TEST_USER_ID, use_service_role=True)

    assert captured["use_service_role"] is True


def test_usage_service_threads_access_token(monkeypatch):
    repo_calls = {}

    def fake_get_usage_repository(*, default, access_token=None):
        repo_calls["access_token"] = access_token
        return MagicMock()

    monkeypatch.setattr(
        usage_service, "get_usage_repository", fake_get_usage_repository
    )

    sub_calls = {}

    class FakeSubscriptionService(SubscriptionService):
        def __init__(self, *, current_user=None, access_token=None):
            sub_calls["access_token"] = access_token

    monkeypatch.setattr(usage_service, "SubscriptionService", FakeSubscriptionService)

    UsageService(current_user=TEST_USER, access_token="tok-usage")

    assert repo_calls["access_token"] == "tok-usage"
    assert sub_calls["access_token"] == "tok-usage"


def test_billing_service_threads_access_token(monkeypatch):
    import services.billing_service as billing_service_module

    captured = {}

    class FakeSubscriptionService:
        def __init__(self, *, current_user=None, access_token=None):
            captured["access_token"] = access_token

    monkeypatch.setattr(
        billing_service_module, "SubscriptionService", FakeSubscriptionService
    )

    BillingService(access_token="tok-billing")

    assert captured["access_token"] == "tok-billing"


def test_activate_subscription_for_user_defaults_to_service_role(monkeypatch):
    import services.billing_service as billing_service_module

    captured = {}

    class FakeSubscription:
        def activate_paid_plan(self, plan_id, **kwargs):
            return {"plan_id": plan_id, **kwargs}

    def fake_for_user_id(user_id, *, use_service_role=False):
        captured["use_service_role"] = use_service_role
        return FakeSubscription()

    monkeypatch.setattr(
        billing_service_module.SubscriptionService, "for_user_id", fake_for_user_id
    )

    activate_subscription_for_user(
        TEST_USER_ID, {"plan_id": "starter", "provider": "stripe"}
    )

    assert captured["use_service_role"] is True
