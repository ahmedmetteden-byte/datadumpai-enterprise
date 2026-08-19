#!/usr/bin/env python3
"""
Read-only inspection of one account's plan/trial/usage state. Prints the
raw `user_usage` row exactly as stored — no writes, no side effects.

(Note: the app's own SubscriptionService.get_effective_plan() has a side
effect of flipping subscription_status to "expired" the first time it's
called after trial_ends_at has passed. This script deliberately avoids
calling that — it only reads the stored row and reports the trial
expiry computation itself, so running it never changes anything.)

Usage:
    python scripts/inspect_account_state.py --email user@example.com
    python scripts/inspect_account_state.py --user-id 00000000-0000-0000-0000-000000000000

Requires (from the server's .env):
    SUPABASE_URL
    SUPABASE_SERVICE_ROLE_KEY
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from config import PLANS  # noqa: E402
from core.database import admin_get_user_by_email  # noqa: E402
from repositories.account_repository import get_usage_repository_for_user  # noqa: E402
from services.usage_service import UsageService  # noqa: E402


def _resolve_user_id(*, email: str | None, user_id: str | None) -> str:
    if user_id:
        return user_id

    if not email:
        raise SystemExit("Pass either --email or --user-id.")

    user = admin_get_user_by_email(email)
    if user is None:
        raise SystemExit(f"No account found for email {email!r}.")

    resolved = user.get("id")
    if not resolved:
        raise SystemExit(f"Admin API returned no id for email {email!r}.")

    return str(resolved)


def _redact(value: str | None) -> str | None:
    if not value:
        return value
    return value[:6] + "…" if len(value) > 6 else value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", help="Account email to inspect.")
    parser.add_argument("--user-id", help="Account user id to inspect (skips email lookup).")
    args = parser.parse_args()

    user_id = _resolve_user_id(email=args.email, user_id=args.user_id)

    repository = get_usage_repository_for_user(
        user_id, default=UsageService._default_state(), use_service_role=True
    )
    state = repository.load()

    plan = state.get("plan")
    billing_plan = state.get("billing_plan")
    status = state.get("subscription_status")
    trial_ends_at = state.get("trial_ends_at")

    trial_expired = None
    if trial_ends_at:
        ends = datetime.fromisoformat(str(trial_ends_at))
        if ends.tzinfo is None:
            ends = ends.replace(tzinfo=timezone.utc)
        trial_expired = ends <= datetime.now(timezone.utc)

    plan_limits = PLANS.get(billing_plan or plan, {})

    print(f"user_id                 = {user_id}")
    print(f"plan                    = {plan}")
    print(f"billing_plan            = {billing_plan}")
    print(f"subscription_status     = {status}")
    print(f"trial_ends_at           = {trial_ends_at}")
    print(f"trial_expired           = {trial_expired}")
    print(f"period                  = {state.get('period')}")
    print(f"reports_generated       = {state.get('reports_generated')} / {plan_limits.get('reports_per_month')}")
    print(f"uploads                 = {state.get('uploads')} / {plan_limits.get('uploads_per_month')}")
    print(f"payment_provider        = {state.get('payment_provider')}")
    print(f"payment_customer_id     = {_redact(state.get('payment_customer_id'))}")
    print(f"payment_subscription_id = {_redact(state.get('payment_subscription_id'))}")
    print(f"payment_reference       = {_redact(state.get('payment_reference'))}")
    print(f"cancel_at_period_end    = {state.get('cancel_at_period_end')}")
    print(f"current_period_end      = {state.get('current_period_end')}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
