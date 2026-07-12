"""
Email normalization and duplicate-account prevention.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import config


DUPLICATE_EMAIL_MESSAGE = "An account already exists with this email address."


def normalize_email(email: str) -> str:
    """Normalize email for uniqueness checks and account creation."""

    return email.strip().lower()


class EmailUniquenessService:
    """Verify email addresses are not already registered."""

    def email_exists(self, email: str) -> bool:
        normalized = normalize_email(email)
        if not normalized:
            return False

        if config.use_database() and config.is_supabase_configured():
            return self._exists_supabase(normalized)

        return self._exists_json(normalized)

    def register_email(self, email: str, user_id: str) -> None:
        """Record an email after successful account creation (JSON/dev backends)."""

        normalized = normalize_email(email)
        if not normalized:
            return

        if config.use_database() and config.is_supabase_configured():
            return

        registry = self._load_registry()
        registry[normalized] = user_id
        self._save_registry(registry)

    def _exists_supabase(self, email: str) -> bool:
        from core.database import get_service_role_client, handle_response

        client = get_service_role_client()
        response = handle_response(
            client.table("user_profiles")
            .select("user_id")
            .eq("email", email)
            .limit(1)
            .execute(),
            action="check email uniqueness",
        )
        rows = response.data or []
        return bool(rows)

    def _exists_json(self, email: str) -> bool:
        if email in self._load_registry():
            return True

        from core.user_paths import get_users_root

        users_root = get_users_root()
        if not users_root.exists():
            return False

        for user_dir in users_root.iterdir():
            if not user_dir.is_dir():
                continue

            profile_path = user_dir / "profile.json"
            if not profile_path.is_file():
                continue

            try:
                profile = json.loads(profile_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue

            if normalize_email(str(profile.get("email", ""))) == email:
                return True

        return False

    @staticmethod
    def _registry_path() -> Path:
        path = Path("data") / "auth_email_registry.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _load_registry(self) -> dict[str, str]:
        path = self._registry_path()
        if not path.is_file():
            return {}

        try:
            payload: Any = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

        if not isinstance(payload, dict):
            return {}

        return {
            normalize_email(str(email)): str(user_id)
            for email, user_id in payload.items()
            if email and user_id
        }

    def _save_registry(self, registry: dict[str, str]) -> None:
        path = self._registry_path()
        path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")


def is_duplicate_email_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(
        token in message
        for token in (
            "already registered",
            "already exists",
            "user already registered",
            "email address is already",
            "duplicate key",
        )
    )
