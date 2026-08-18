#!/usr/bin/env python3
"""
Reset a user's monthly usage counters (reports and/or uploads) without
waiting for the natural monthly rollover. Intended for support/admin use
— e.g. a user's quota got consumed by verification/testing activity that
wasn't really theirs.

Prints the current state before and after so the change is visible.

Usage:
    python scripts/reset_usage.py --email user@example.com                # reset reports only
    python scripts/reset_usage.py --email user@example.com --uploads      # also reset uploads
    python scripts/reset_usage.py --user-id 00000000-0000-0000-0000-000000000000

Requires (from the server's .env):
    SUPABASE_URL
    SUPABASE_SERVICE_ROLE_KEY
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", help="Account email to reset usage for.")
    parser.add_argument("--user-id", help="Account user id to reset usage for (skips email lookup).")
    parser.add_argument(
        "--uploads", action="store_true", help="Also reset the monthly upload counter."
    )
    args = parser.parse_args()

    user_id = _resolve_user_id(email=args.email, user_id=args.user_id)

    repository = get_usage_repository_for_user(
        user_id, default=UsageService._default_state(), use_service_role=True
    )
    state = repository.load()

    print(f"user_id={user_id}")
    print(f"before: period={state.get('period')} reports_generated={state.get('reports_generated')} uploads={state.get('uploads')}")

    state["reports_generated"] = 0
    if args.uploads:
        state["uploads"] = 0

    repository.save(state)

    reloaded = repository.load()
    print(f"after:  period={reloaded.get('period')} reports_generated={reloaded.get('reports_generated')} uploads={reloaded.get('uploads')}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
