"""
Admin operations — cross-user visibility and platform management.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import config
from core.database import get_database_client, handle_response
from repositories.account_repository import (
    get_profile_repository_for_user,
    get_usage_repository_for_user,
)
from services.feedback_service import FeedbackService
from services.subscription_service import SubscriptionService


_ADMIN_PROFILE_DEFAULT = {
    "full_name": "",
    "email": "",
    "company": "",
    "job_title": "",
    "photo_url": "",
    "timezone": "UTC",
    "locale": "en",
    "role": "user",
    "last_login": None,
    "onboarding_completed": False,
    "onboarding_step": 1,
    "onboarding_completed_at": None,
    "notification_preferences": dict(config.DEFAULT_NOTIFICATION_PREFERENCES),
}


class AdminService:
    """Platform administration for operators with admin access."""

    def __init__(self) -> None:
        self._feedback = FeedbackService()

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def list_users(self) -> list[dict[str, Any]]:
        if config.use_database():
            return self._list_users_supabase()

        return self._list_users_json()

    def _list_users_json(self) -> list[dict[str, Any]]:
        from core import user_paths

        users_root = user_paths.get_users_root()
        if not users_root.exists():
            return []

        rows: list[dict[str, Any]] = []
        for user_dir in sorted(users_root.iterdir()):
            if not user_dir.is_dir():
                continue

            user_id = user_dir.name
            profile = get_profile_repository_for_user(
                user_id,
                default=_ADMIN_PROFILE_DEFAULT,
            ).load()
            usage = SubscriptionService.for_user_id(user_id).load_state()
            rows.append(self._user_row(user_id, profile, usage))

        return rows

    def _list_users_supabase(self) -> list[dict[str, Any]]:
        client = get_database_client()
        profiles_response = handle_response(
            client.table("user_profiles").select("*").execute(),
            action="list user profiles",
        )
        usage_response = handle_response(
            client.table("user_usage").select("*").execute(),
            action="list user usage",
        )

        usage_by_user = {str(row["user_id"]): row for row in (usage_response.data or [])}
        rows: list[dict[str, Any]] = []

        for profile_row in profiles_response.data or []:
            user_id = str(profile_row["user_id"])
            usage = usage_by_user.get(user_id, {})
            rows.append(self._user_row(user_id, profile_row, usage))

        for user_id, usage in usage_by_user.items():
            if any(row["user_id"] == user_id for row in rows):
                continue
            rows.append(self._user_row(user_id, {}, usage))

        return sorted(rows, key=lambda row: row.get("full_name", ""))

    @staticmethod
    def _user_row(user_id: str, profile: dict[str, Any], usage: dict[str, Any]) -> dict[str, Any]:
        subscription = SubscriptionService.for_user_id(user_id)
        effective_plan = subscription.get_effective_plan(usage)
        return {
            "user_id": user_id,
            "full_name": profile.get("full_name", ""),
            "company": profile.get("company", ""),
            "role": profile.get("role", "user"),
            "billing_plan": usage.get("billing_plan", config.DEFAULT_PLAN),
            "effective_plan": effective_plan,
            "subscription_status": usage.get("subscription_status", "none"),
            "uploads": int(usage.get("uploads", 0)),
            "reports_generated": int(usage.get("reports_generated", 0)),
            "payment_provider": usage.get("payment_provider"),
        }

    def set_user_plan(self, user_id: str, plan_id: str, *, actor_user_id: str | None = None) -> dict:
        state = SubscriptionService.for_user_id(user_id).set_billing_plan(plan_id)
        self.record_audit(
            actor_user_id=actor_user_id,
            action="admin.set_plan",
            target_type="user",
            target_id=user_id,
            metadata={"plan_id": plan_id},
        )
        return state

    def get_platform_stats(self) -> dict[str, Any]:
        users = self.list_users()
        feedback = self._feedback._feedback.load()
        support = self._feedback._support.load()

        plan_counts: dict[str, int] = {}
        for user in users:
            plan = user.get("effective_plan", config.DEFAULT_PLAN)
            plan_counts[plan] = plan_counts.get(plan, 0) + 1

        return {
            "total_users": len(users),
            "plan_counts": plan_counts,
            "feedback_count": len(feedback),
            "support_count": len(support),
            "active_subscriptions": sum(
                1 for user in users if user.get("subscription_status") == "active"
            ),
            "trialing_users": sum(
                1 for user in users if user.get("subscription_status") == "trialing"
            ),
        }

    def list_feedback(self) -> list[dict[str, Any]]:
        return list(reversed(self._feedback._feedback.load()))

    def list_support_requests(self) -> list[dict[str, Any]]:
        return list(reversed(self._feedback._support.load()))

    def record_audit(
        self,
        *,
        actor_user_id: str | None,
        action: str,
        target_type: str | None = None,
        target_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        entry = {
            "id": str(uuid4()),
            "actor_user_id": actor_user_id,
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "metadata": metadata or {},
            "created_at": self._utc_now(),
        }

        if config.use_database():
            client = get_database_client()
            handle_response(
                client.table("audit_logs").insert(
                    {
                        "actor_user_id": actor_user_id,
                        "action": action,
                        "target_type": target_type,
                        "target_id": target_id,
                        "metadata": metadata or {},
                    }
                ).execute(),
                action="record audit log",
            )
            return

        path = Path("data/audit_logs.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        logs: list[dict[str, Any]] = []
        if path.exists():
            try:
                logs = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                logs = []
        logs.append(entry)
        path.write_text(json.dumps(logs, indent=2), encoding="utf-8")

    def list_audit_logs(self, *, limit: int = 100) -> list[dict[str, Any]]:
        if config.use_database():
            client = get_database_client()
            response = handle_response(
                client.table("audit_logs")
                .select("*")
                .order("created_at", desc=True)
                .limit(limit)
                .execute(),
                action="list audit logs",
            )
            return list(response.data or [])

        path = Path("data/audit_logs.json")
        if not path.exists():
            return []
        try:
            logs = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        return list(reversed(logs[-limit:]))
