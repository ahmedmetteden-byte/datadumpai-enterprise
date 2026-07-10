"""
Usage and profile repositories — JSON or Supabase backends.
"""

from __future__ import annotations

from typing import Any

import config
from config import DEFAULT_PLAN
from core.auth import get_current_user_id
from core.database import get_database_client, handle_response
from core.user_paths import get_user_profile_json, get_user_usage_json
from repositories.billing_repository import merge_billing_fields
from storage.dict_storage import DictStorage


class JsonUsageRepository:
    def __init__(self, user_id: str, *, default: dict[str, Any]) -> None:
        self._storage = DictStorage(get_user_usage_json(user_id), default=default)

    def load(self) -> dict[str, Any]:
        return self._storage.load()

    def save(self, state: dict[str, Any]) -> None:
        self._storage.save(state)


class SupabaseUsageRepository:
    def __init__(self, user_id: str, *, default: dict[str, Any]) -> None:
        self._user_id = user_id
        self._default = default
        self._client = get_database_client()

    def load(self) -> dict[str, Any]:
        response = handle_response(
            self._client.table("user_usage")
            .select("*")
            .eq("user_id", self._user_id)
            .maybe_single()
            .execute(),
            action="load usage",
        )

        if not response.data:
            return dict(self._default)

        row = response.data
        return merge_billing_fields(
            {
                "plan": row.get("plan", DEFAULT_PLAN),
                "billing_plan": row.get("billing_plan") or row.get("plan", DEFAULT_PLAN),
                "subscription_status": row.get("subscription_status", "none"),
                "trial_ends_at": row.get("trial_ends_at"),
                "period": row["period"],
                "reports_generated": int(row.get("reports_generated", 0)),
                "uploads": int(row.get("uploads", 0)),
                "payment_provider": row.get("payment_provider"),
                "payment_customer_id": row.get("payment_customer_id"),
                "payment_subscription_id": row.get("payment_subscription_id"),
                "payment_reference": row.get("payment_reference"),
                "cancel_at_period_end": bool(row.get("cancel_at_period_end", False)),
                "current_period_end": row.get("current_period_end"),
            }
        )

    def save(self, state: dict[str, Any]) -> None:
        row = {
            "user_id": self._user_id,
            "plan": state.get("billing_plan", state.get("plan", DEFAULT_PLAN)),
            "billing_plan": state.get("billing_plan", state.get("plan", DEFAULT_PLAN)),
            "subscription_status": state.get("subscription_status", "none"),
            "trial_ends_at": state.get("trial_ends_at"),
            "period": state["period"],
            "reports_generated": int(state.get("reports_generated", 0)),
            "uploads": int(state.get("uploads", 0)),
            "payment_provider": state.get("payment_provider"),
            "payment_customer_id": state.get("payment_customer_id"),
            "payment_subscription_id": state.get("payment_subscription_id"),
            "payment_reference": state.get("payment_reference"),
            "cancel_at_period_end": bool(state.get("cancel_at_period_end", False)),
            "current_period_end": state.get("current_period_end"),
        }
        handle_response(
            self._client.table("user_usage").upsert(row).execute(),
            action="save usage",
        )


class JsonProfileRepository:
    def __init__(self, user_id: str, *, default: dict[str, Any]) -> None:
        self._storage = DictStorage(get_user_profile_json(user_id), default=default)

    def load(self) -> dict[str, Any]:
        return self._storage.load()

    def save(self, profile: dict[str, Any]) -> None:
        self._storage.save(profile)


class SupabaseProfileRepository:
    def __init__(self, user_id: str, *, default: dict[str, Any]) -> None:
        self._user_id = user_id
        self._default = default
        self._client = get_database_client()

    def load(self) -> dict[str, Any]:
        response = handle_response(
            self._client.table("user_profiles")
            .select("*")
            .eq("user_id", self._user_id)
            .maybe_single()
            .execute(),
            action="load profile",
        )

        if not response.data:
            return dict(self._default)

        row = response.data
        prefs = row.get("notification_preferences") or {}
        return {
            "full_name": row.get("full_name", ""),
            "email": row.get("email", ""),
            "company": row.get("company", ""),
            "job_title": row.get("job_title", ""),
            "photo_url": row.get("photo_url", ""),
            "timezone": row.get("timezone", "UTC"),
            "locale": row.get("locale", "en"),
            "role": row.get("role", "user"),
            "last_login": row.get("last_login"),
            "onboarding_completed": bool(row.get("onboarding_completed", False)),
            "onboarding_step": int(row.get("onboarding_step", 1) or 1),
            "onboarding_completed_at": row.get("onboarding_completed_at"),
            "notification_preferences": prefs,
        }

    def save(self, profile: dict[str, Any]) -> None:
        row = {
            "user_id": self._user_id,
            "full_name": profile.get("full_name", ""),
            "email": profile.get("email", ""),
            "last_login": profile.get("last_login"),
            "company": profile.get("company", ""),
            "job_title": profile.get("job_title", ""),
            "photo_url": profile.get("photo_url", ""),
            "timezone": profile.get("timezone", "UTC"),
            "locale": profile.get("locale", "en"),
            "role": profile.get("role", "user"),
            "onboarding_completed": bool(profile.get("onboarding_completed", False)),
            "onboarding_step": int(profile.get("onboarding_step", 1) or 1),
            "onboarding_completed_at": profile.get("onboarding_completed_at"),
            "notification_preferences": profile.get(
                "notification_preferences",
                config.DEFAULT_NOTIFICATION_PREFERENCES,
            ),
        }
        handle_response(
            self._client.table("user_profiles").upsert(row).execute(),
            action="save profile",
        )


def get_usage_repository(user_id: str | None = None, *, default: dict[str, Any]):
    resolved_user_id = user_id or get_current_user_id()

    if config.use_database():
        return SupabaseUsageRepository(resolved_user_id, default=default)
    return JsonUsageRepository(resolved_user_id, default=default)


def get_profile_repository(user_id: str | None = None, *, default: dict[str, Any]):
    resolved_user_id = user_id or get_current_user_id()

    if config.use_database():
        return SupabaseProfileRepository(resolved_user_id, default=default)
    return JsonProfileRepository(resolved_user_id, default=default)
