"""
DataDumpAI v1.0
Usage limits — protect AI costs from day one.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from config import DEFAULT_PLAN, PLANS, resolve_plan_id
from core.auth import get_current_user_id
from repositories.account_repository import get_usage_repository
from services.subscription_service import SubscriptionService


class UsageLimitError(Exception):
    """Raised when a plan limit would be exceeded."""

    def __init__(self, message: str, *, limit_type: str) -> None:
        super().__init__(message)
        self.limit_type = limit_type


@dataclass(frozen=True)
class UsageSnapshot:
    """Current usage for the active billing period."""

    plan: str
    billing_plan: str
    subscription_status: str
    trial_ends_at: str | None
    period: str
    reports_used: int
    reports_limit: int | None
    uploads_used: int
    uploads_limit: int | None
    projects_max: int | None
    trial_days_remaining: int | None = None

    @property
    def reports_remaining(self) -> int | None:
        if self.reports_limit is None:
            return None
        return max(self.reports_limit - self.reports_used, 0)

    @property
    def uploads_remaining(self) -> int | None:
        if self.uploads_limit is None:
            return None
        return max(self.uploads_limit - self.uploads_used, 0)

    @property
    def is_pro(self) -> bool:
        return self.plan in {"professional", "enterprise", "pro"}

    @property
    def is_professional(self) -> bool:
        return self.is_pro

    @property
    def is_trialing(self) -> bool:
        return self.subscription_status == SubscriptionService.STATUS_TRIALING and self.is_pro


class UsageService:
    """Track and enforce monthly usage limits per plan."""

    def __init__(self, storage_path: str | None = None, user_id: str | None = None) -> None:
        resolved_user_id = user_id or get_current_user_id()
        self._user_id = resolved_user_id
        self._repository = get_usage_repository(
            resolved_user_id,
            default=self._default_state(),
        )
        self._subscription = SubscriptionService(resolved_user_id)

    @staticmethod
    def _default_state() -> dict:
        return {
            "plan": DEFAULT_PLAN,
            "billing_plan": DEFAULT_PLAN,
            "subscription_status": SubscriptionService.STATUS_NONE,
            "trial_ends_at": None,
            "period": UsageService._current_period(),
            "reports_generated": 0,
            "uploads": 0,
            "payment_provider": None,
            "payment_customer_id": None,
            "payment_subscription_id": None,
            "payment_reference": None,
            "cancel_at_period_end": False,
            "current_period_end": None,
        }

    @staticmethod
    def _current_period() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m")

    def _plan_limits(self, plan: str) -> dict[str, int | None]:
        resolved = resolve_plan_id(plan)
        limits = PLANS.get(resolved, PLANS[DEFAULT_PLAN])
        return {
            "reports_per_month": limits["reports_per_month"],
            "uploads_per_month": limits["uploads_per_month"],
            "projects_max": limits.get("projects_max"),
        }

    def _load_state(self) -> dict:
        state = self._repository.load()
        current_period = self._current_period()
        changed = False

        if state.get("period") != current_period:
            state["period"] = current_period
            state["reports_generated"] = 0
            state["uploads"] = 0
            changed = True

        billing_plan = resolve_plan_id(state.get("billing_plan") or state.get("plan", DEFAULT_PLAN))
        if billing_plan not in PLANS:
            state["billing_plan"] = DEFAULT_PLAN
            state["plan"] = DEFAULT_PLAN
            changed = True

        if changed:
            self._repository.save(state)

        return state

    def get_snapshot(self) -> UsageSnapshot:
        state = self._load_state()
        effective_plan = self._subscription.get_effective_plan(state)
        limits = self._plan_limits(effective_plan)

        return UsageSnapshot(
            plan=effective_plan,
            billing_plan=resolve_plan_id(state.get("billing_plan", DEFAULT_PLAN)),
            subscription_status=state.get("subscription_status", SubscriptionService.STATUS_NONE),
            trial_ends_at=state.get("trial_ends_at"),
            period=state["period"],
            reports_used=int(state.get("reports_generated", 0)),
            reports_limit=limits["reports_per_month"],
            uploads_used=int(state.get("uploads", 0)),
            uploads_limit=limits["uploads_per_month"],
            projects_max=limits["projects_max"],
            trial_days_remaining=self._subscription.trial_days_remaining(state),
        )

    def get_plan(self) -> str:
        return self.get_snapshot().plan

    def set_plan(self, plan: str) -> None:
        self._subscription.set_billing_plan(plan)

    def start_trial(self) -> None:
        self._subscription.start_trial()

    def check_can_upload(self, count: int = 1) -> None:
        snapshot = self.get_snapshot()
        limit = snapshot.uploads_limit

        if limit is None:
            return

        if snapshot.uploads_used + count > limit:
            try:
                from services.notification_service import NotificationService

                NotificationService(self._user_id).notify_usage_limit(
                    limit_type="upload",
                    plan_label=PLANS[snapshot.plan]["label"],
                )
            except Exception:
                pass
            raise UsageLimitError(
                f"Your {PLANS[snapshot.plan]['label']} plan includes "
                f"{limit} uploads per month. Upgrade for more capacity.",
                limit_type="uploads",
            )

    def check_can_generate_report(self) -> None:
        snapshot = self.get_snapshot()
        limit = snapshot.reports_limit

        if limit is None:
            return

        if snapshot.reports_used >= limit:
            try:
                from services.notification_service import NotificationService

                NotificationService(self._user_id).notify_usage_limit(
                    limit_type="report",
                    plan_label=PLANS[snapshot.plan]["label"],
                )
            except Exception:
                pass
            raise UsageLimitError(
                f"Your {PLANS[snapshot.plan]['label']} plan includes "
                f"{limit} reports per month. Upgrade for more capacity.",
                limit_type="reports",
            )

    def record_uploads(self, count: int = 1) -> None:
        if count <= 0:
            return

        state = self._load_state()
        state["uploads"] = int(state.get("uploads", 0)) + count
        self._repository.save(state)

    def record_report_generated(self) -> None:
        state = self._load_state()
        state["reports_generated"] = int(state.get("reports_generated", 0)) + 1
        self._repository.save(state)
