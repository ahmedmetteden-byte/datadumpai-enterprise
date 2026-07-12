"""
Notification preferences, in-app alerts, and outbound email orchestration.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import streamlit as st

import config
from core.auth import get_current_user
from core.current_user import CurrentUser, require_current_user
from services.email_service import EmailDeliveryError, is_email_configured, send_email
from services.profile_service import ProfileService


class NotificationService:
    """Manage notification preferences and deliver product emails."""

    def __init__(self, *, current_user: CurrentUser | None = None) -> None:
        self._current_user = current_user or require_current_user()
        self._profile = ProfileService(current_user=self._current_user)

    @classmethod
    def for_user_id(cls, user_id: str) -> NotificationService:
        """Internal: webhook and background jobs only."""

        return cls(current_user=CurrentUser(id=user_id, email=""))

    def get_preferences(self) -> dict[str, bool]:
        profile = self._profile.load()
        prefs = profile.get("notification_preferences") or {}
        merged = dict(config.DEFAULT_NOTIFICATION_PREFERENCES)
        merged.update({key: bool(prefs.get(key, merged[key])) for key in merged})
        return merged

    def save_preferences(self, preferences: dict[str, bool]) -> dict[str, bool]:
        profile = self._profile.load()
        current = self.get_preferences()
        current.update({key: bool(preferences.get(key, current[key])) for key in current})
        profile["notification_preferences"] = current
        self._profile.save(profile)
        return current

    def _recipient_email(self, email: str | None = None) -> str | None:
        if email:
            return email.strip()
        user = get_current_user()
        if user and user.email:
            return user.email
        profile_email = (self._profile.load().get("email") or "").strip()
        return profile_email or None

    def _should_send(self, preference_key: str) -> bool:
        return bool(self.get_preferences().get(preference_key, False))

    def push_in_app(self, message: str, *, level: str = "info") -> None:
        notifications = list(st.session_state.get("notifications", []))
        notifications.insert(
            0,
            {
                "message": message,
                "level": level,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        st.session_state.notifications = notifications[:20]

    def notify_report_ready(
        self,
        *,
        report_name: str,
        project_name: str,
        email: str | None = None,
    ) -> str:
        if not self._should_send("report_ready"):
            return "skipped"

        recipient = self._recipient_email(email)
        if not recipient:
            return "skipped"

        subject = f"Your report is ready — {report_name}"
        body = (
            f"Hi,\n\n"
            f'Your report "{report_name}" in project "{project_name}" is ready '
            f"to view in {config.APP_NAME}.\n\n"
            f"Open the app: {config.AUTH_REDIRECT_URL}\n"
        )
        try:
            provider = send_email(to_email=recipient, subject=subject, body_text=body)
            self.push_in_app(f'Report "{report_name}" is ready.', level="success")
            return provider
        except EmailDeliveryError:
            self.push_in_app(f'Report "{report_name}" is ready.', level="success")
            return "failed"

    def notify_usage_limit(
        self,
        *,
        limit_type: str,
        plan_label: str,
        email: str | None = None,
    ) -> str:
        if not self._should_send("usage_alerts"):
            return "skipped"

        recipient = self._recipient_email(email)
        if not recipient:
            return "skipped"

        subject = f"{config.APP_NAME} usage alert"
        body = (
            f"Hi,\n\n"
            f"You are approaching or have reached your {limit_type} limit "
            f"on the {plan_label} plan.\n\n"
            f"Upgrade in Account → Subscription: {config.AUTH_REDIRECT_URL}\n"
        )
        try:
            return send_email(to_email=recipient, subject=subject, body_text=body)
        except EmailDeliveryError:
            return "failed"

    def notify_billing_event(
        self,
        *,
        subject: str,
        body: str,
        email: str | None = None,
    ) -> str:
        if not self._should_send("billing"):
            return "skipped"

        recipient = self._recipient_email(email)
        if not recipient:
            return "skipped"

        try:
            return send_email(to_email=recipient, subject=subject, body_text=body)
        except EmailDeliveryError:
            return "failed"

    def notify_trial_ending(self, *, days_remaining: int, email: str | None = None) -> str:
        subject = f"Your {config.APP_NAME} trial ends in {days_remaining} days"
        body = (
            f"Hi,\n\n"
            f"Your Professional trial ends in {days_remaining} day"
            f"{'s' if days_remaining != 1 else ''}. "
            f"Upgrade to keep unlimited reports and intelligence features.\n\n"
            f"{config.AUTH_REDIRECT_URL}\n"
        )
        return self.notify_billing_event(subject=subject, body=body, email=email)


def render_notification_bell() -> None:
    """Render recent in-app notifications in the sidebar."""

    notifications: list[dict[str, Any]] = st.session_state.get("notifications", [])
    if not notifications:
        return

    with st.expander(f"Notifications ({len(notifications)})", expanded=False):
        for item in notifications[:5]:
            level = item.get("level", "info")
            prefix = {"success": "✅", "error": "⚠️", "info": "ℹ️"}.get(level, "ℹ️")
            st.caption(f"{prefix} {item.get('message', '')}")

        if st.button("Clear notifications", key="clear_notifications"):
            st.session_state.notifications = []
            st.rerun()


def email_status_caption() -> str:
    if is_email_configured():
        return "Email delivery is configured."
    if config.EMAIL_ENABLED:
        return "Email is enabled but not fully configured."
    return "Email notifications are disabled in this environment."
