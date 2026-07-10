"""
Subscription lifecycle — trials, effective plan resolution, and status.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from config import DEFAULT_PLAN, PLANS, TRIAL_DAYS, TRIAL_PLAN, resolve_plan_id
from core.auth import get_current_user_id
from repositories.account_repository import get_usage_repository


class SubscriptionService:
    """Manage plan trials and subscription status for the active user."""

    STATUS_NONE = "none"
    STATUS_TRIALING = "trialing"
    STATUS_ACTIVE = "active"
    STATUS_CANCELED = "canceled"
    STATUS_EXPIRED = "expired"

    def __init__(self, user_id: str | None = None) -> None:
        self._user_id = user_id or get_current_user_id()
        self._repository = get_usage_repository(
            self._user_id,
            default=self._default_state(),
        )

    @staticmethod
    def _default_state() -> dict:
        from services.usage_service import UsageService

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

    def _utc_now(self) -> datetime:
        return datetime.now(timezone.utc)

    def load_state(self) -> dict:
        return self._repository.load()

    def save_state(self, state: dict) -> None:
        self._repository.save(state)

    def start_trial(self) -> dict:
        """Begin a no-card Professional trial for a new account."""

        state = self.load_state()

        if state.get("subscription_status") in {
            self.STATUS_TRIALING,
            self.STATUS_ACTIVE,
        }:
            return state

        trial_end = self._utc_now() + timedelta(days=TRIAL_DAYS)
        state["plan"] = DEFAULT_PLAN
        state["billing_plan"] = DEFAULT_PLAN
        state["subscription_status"] = self.STATUS_TRIALING
        state["trial_ends_at"] = trial_end.isoformat()
        self.save_state(state)
        return state

    def get_effective_plan(self, state: dict | None = None) -> str:
        state = state or self.load_state()
        status = state.get("subscription_status", self.STATUS_NONE)

        if status == self.STATUS_TRIALING:
            trial_ends_at = state.get("trial_ends_at")
            if trial_ends_at:
                try:
                    ends = datetime.fromisoformat(str(trial_ends_at))
                    if ends.tzinfo is None:
                        ends = ends.replace(tzinfo=timezone.utc)
                    if ends > self._utc_now():
                        return TRIAL_PLAN
                except ValueError:
                    pass

            state = dict(state)
            state["subscription_status"] = self.STATUS_EXPIRED
            state["plan"] = DEFAULT_PLAN
            state["billing_plan"] = DEFAULT_PLAN
            state["trial_ends_at"] = None
            self.save_state(state)

        billing_plan = resolve_plan_id(state.get("billing_plan") or state.get("plan", DEFAULT_PLAN))
        if billing_plan not in PLANS:
            return DEFAULT_PLAN
        return billing_plan

    def is_trialing(self, state: dict | None = None) -> bool:
        state = state or self.load_state()
        if state.get("subscription_status") != self.STATUS_TRIALING:
            return False
        return self.get_effective_plan(state) == TRIAL_PLAN

    def trial_days_remaining(self, state: dict | None = None) -> int | None:
        state = state or self.load_state()
        if not self.is_trialing(state):
            return None

        trial_ends_at = state.get("trial_ends_at")
        if not trial_ends_at:
            return None

        ends = datetime.fromisoformat(str(trial_ends_at))
        if ends.tzinfo is None:
            ends = ends.replace(tzinfo=timezone.utc)

        remaining = ends - self._utc_now()
        return max(remaining.days, 0)

    def set_billing_plan(self, plan_id: str, *, status: str = STATUS_ACTIVE) -> dict:
        plan = resolve_plan_id(plan_id)
        if plan not in PLANS:
            raise ValueError(f"Unknown plan: {plan_id!r}")

        state = self.load_state()
        state["plan"] = plan
        state["billing_plan"] = plan
        state["subscription_status"] = status
        state["trial_ends_at"] = None
        self.save_state(state)
        return state

    def activate_paid_plan(
        self,
        plan_id: str,
        *,
        provider: str,
        customer_id: str | None = None,
        subscription_id: str | None = None,
        reference: str | None = None,
        current_period_end: str | None = None,
    ) -> dict:
        plan = resolve_plan_id(plan_id)
        if plan not in PLANS:
            raise ValueError(f"Unknown plan: {plan_id!r}")

        state = self.load_state()
        state["plan"] = plan
        state["billing_plan"] = plan
        state["subscription_status"] = self.STATUS_ACTIVE
        state["trial_ends_at"] = None
        state["payment_provider"] = provider
        state["payment_customer_id"] = customer_id
        state["payment_subscription_id"] = subscription_id
        state["payment_reference"] = reference
        state["cancel_at_period_end"] = False
        state["current_period_end"] = current_period_end
        self.save_state(state)
        return state

    def mark_canceled(self, *, at_period_end: bool = True) -> dict:
        state = self.load_state()
        state["subscription_status"] = self.STATUS_CANCELED
        state["cancel_at_period_end"] = at_period_end
        if not at_period_end:
            state["plan"] = DEFAULT_PLAN
            state["billing_plan"] = DEFAULT_PLAN
            state["payment_subscription_id"] = None
        self.save_state(state)
        return state

    def mark_payment_failed(self) -> dict:
        state = self.load_state()
        state["subscription_status"] = "past_due"
        self.save_state(state)
        return state

    def get_billing_summary(self) -> dict:
        state = self.load_state()
        return {
            "billing_plan": resolve_plan_id(state.get("billing_plan", DEFAULT_PLAN)),
            "effective_plan": self.get_effective_plan(state),
            "subscription_status": state.get("subscription_status", self.STATUS_NONE),
            "payment_provider": state.get("payment_provider"),
            "payment_customer_id": state.get("payment_customer_id"),
            "payment_subscription_id": state.get("payment_subscription_id"),
            "cancel_at_period_end": bool(state.get("cancel_at_period_end", False)),
            "current_period_end": state.get("current_period_end"),
            "trial_days_remaining": self.trial_days_remaining(state),
        }
