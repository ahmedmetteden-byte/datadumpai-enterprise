"""
Ensure application records exist for every authenticated user.
"""

from __future__ import annotations

from datetime import datetime, timezone

from models.user import User
from services.profile_service import ProfileService
from services.usage_service import UsageService


def bootstrap_user_account(user: User) -> None:
    """Create or refresh profile and usage records after sign-in."""

    profile_service = ProfileService(user.id)
    current = profile_service.load()

    updates: dict[str, str] = {}
    if user.full_name and not current.get("full_name"):
        updates["full_name"] = user.full_name
    if user.email:
        updates["email"] = user.email

    if updates:
        current.update(updates)
        profile_service.save(current)

    profile_service.record_last_login()

    usage_service = UsageService(user_id=user.id)
    usage_service.get_snapshot()


def record_last_login(user_id: str) -> None:
    """Update the user's last login timestamp."""

    ProfileService(user_id).record_last_login()
