"""
Ensure application records exist for every authenticated user.
"""

from __future__ import annotations

from datetime import datetime, timezone

from core.current_user import current_user_scope
from models.user import User
from services.profile_service import ProfileService
from services.usage_service import UsageService


def bootstrap_user_account(user: User) -> None:
    """Create or refresh profile and usage records after sign-in."""

    with current_user_scope(user):
        profile_service = ProfileService()
        current = profile_service.load()

        updates: dict[str, str] = {}
        if user.full_name and not current.get("full_name"):
            updates["full_name"] = user.full_name
        if user.email:
            updates["email"] = user.email
            from services.email_uniqueness import EmailUniquenessService, normalize_email

            EmailUniquenessService().register_email(normalize_email(user.email), user.id)

        if updates:
            current.update(updates)
            profile_service.save(current)

        profile_service.record_last_login()

        usage_service = UsageService()
        usage_service.get_snapshot()


def record_last_login(user_id: str) -> None:
    """Update the user's last login timestamp."""

    from models.user import User

    with current_user_scope(User(id=user_id, email="", email_verified=True)):
        ProfileService().record_last_login()
