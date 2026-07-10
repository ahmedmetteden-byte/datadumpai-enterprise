"""
User profile metadata stored in JSON or PostgreSQL.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import config
from config import DEFAULT_NOTIFICATION_PREFERENCES
from core.auth import get_current_user_id
from repositories.account_repository import get_profile_repository


class ProfileService:
    """Persist optional profile fields for the signed-in user."""

    _DEFAULT = {
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
        "notification_preferences": dict(DEFAULT_NOTIFICATION_PREFERENCES),
    }

    def __init__(self, user_id: str | None = None) -> None:
        resolved_user_id = user_id or get_current_user_id()
        self._user_id = resolved_user_id
        self._repository = get_profile_repository(
            resolved_user_id,
            default=self._DEFAULT,
        )

    def load(self) -> dict[str, Any]:
        return self._repository.load()

    def save(self, profile: dict[str, Any]) -> dict[str, Any]:
        current = self.load()
        prefs = dict(current.get("notification_preferences", DEFAULT_NOTIFICATION_PREFERENCES))
        incoming_prefs = profile.get("notification_preferences")
        if isinstance(incoming_prefs, dict):
            prefs.update({key: bool(incoming_prefs.get(key, prefs[key])) for key in prefs})

        current.update(
            {
                "full_name": str(profile.get("full_name", current.get("full_name", ""))).strip(),
                "email": str(profile.get("email", current.get("email", ""))).strip(),
                "company": str(profile.get("company", current.get("company", ""))).strip(),
                "job_title": str(profile.get("job_title", current.get("job_title", ""))).strip(),
                "photo_url": str(profile.get("photo_url", current.get("photo_url", ""))).strip(),
                "timezone": str(profile.get("timezone", current.get("timezone", "UTC"))).strip() or "UTC",
                "locale": str(profile.get("locale", current.get("locale", "en"))).strip() or "en",
                "role": str(profile.get("role", current.get("role", "user"))).strip() or "user",
                "onboarding_completed": bool(
                    profile.get("onboarding_completed", current.get("onboarding_completed", False))
                ),
                "onboarding_step": int(
                    profile.get("onboarding_step", current.get("onboarding_step", 1)) or 1
                ),
                "onboarding_completed_at": profile.get(
                    "onboarding_completed_at",
                    current.get("onboarding_completed_at"),
                ),
                "notification_preferences": prefs,
            }
        )
        self._repository.save(current)
        return current

    def get_role(self) -> str:
        return str(self.load().get("role", "user"))

    def get_notification_preferences(self) -> dict[str, bool]:
        prefs = self.load().get("notification_preferences") or {}
        merged = dict(DEFAULT_NOTIFICATION_PREFERENCES)
        merged.update({key: bool(prefs.get(key, merged[key])) for key in merged})
        return merged

    def record_last_login(self) -> None:
        current = self.load()
        current["last_login"] = datetime.now(timezone.utc).isoformat()
        self._repository.save(current)
