"""
Account lockout after repeated failed sign-in attempts.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import config
from services.auth_service import AuthError


class LockoutService:
    """Track failed logins and enforce temporary account lockouts."""

    _JSON_PATH = Path("data/login_lockouts.json")

    def check_allowed(self, email: str) -> None:
        record = self._load_record(email)
        locked_until = record.get("locked_until")

        if not locked_until:
            return

        expiry = datetime.fromisoformat(str(locked_until))
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)

        if datetime.now(timezone.utc) < expiry:
            minutes_left = max(int((expiry - datetime.now(timezone.utc)).total_seconds() // 60), 1)
            raise AuthError(
                f"Too many failed sign-in attempts. Try again in {minutes_left} minute"
                f"{'s' if minutes_left != 1 else ''}."
            )

        self._save_record(email, {"failed_count": 0, "locked_until": None})

    def record_failure(self, email: str) -> None:
        record = self._load_record(email)
        failed_count = int(record.get("failed_count", 0)) + 1
        payload: dict[str, Any] = {
            "failed_count": failed_count,
            "locked_until": record.get("locked_until"),
            "last_attempt_at": self._utc_now(),
        }

        if failed_count >= config.LOCKOUT_MAX_ATTEMPTS:
            locked_until = datetime.now(timezone.utc) + timedelta(
                minutes=config.LOCKOUT_DURATION_MINUTES
            )
            payload["locked_until"] = locked_until.isoformat()

        self._save_record(email, payload)

    def record_success(self, email: str) -> None:
        self._save_record(
            email,
            {
                "failed_count": 0,
                "locked_until": None,
                "last_attempt_at": self._utc_now(),
            },
        )

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().lower()

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _load_record(self, email: str) -> dict[str, Any]:
        key = self._normalize_email(email)

        if config.use_database() and config.is_supabase_configured():
            return self._load_record_supabase(key)

        return self._load_record_json(key)

    def _save_record(self, email: str, payload: dict[str, Any]) -> None:
        key = self._normalize_email(email)

        if config.use_database() and config.is_supabase_configured():
            self._save_record_supabase(key, payload)
            return

        self._save_record_json(key, payload)

    def _load_record_supabase(self, email: str) -> dict[str, Any]:
        from core.database import get_service_role_client, handle_response

        response = handle_response(
            get_service_role_client()
            .table("login_lockouts")
            .select("*")
            .eq("email", email)
            .maybe_single()
            .execute(),
            action="load login lockout",
        )

        if not response.data:
            return {"failed_count": 0, "locked_until": None}

        row = response.data
        return {
            "failed_count": int(row.get("failed_count", 0)),
            "locked_until": row.get("locked_until"),
            "last_attempt_at": row.get("last_attempt_at"),
        }

    def _save_record_supabase(self, email: str, payload: dict[str, Any]) -> None:
        from core.database import get_service_role_client, handle_response

        handle_response(
            get_service_role_client()
            .table("login_lockouts")
            .upsert(
                {
                    "email": email,
                    "failed_count": int(payload.get("failed_count", 0)),
                    "locked_until": payload.get("locked_until"),
                    "last_attempt_at": payload.get("last_attempt_at") or self._utc_now(),
                }
            )
            .execute(),
            action="save login lockout",
        )

    def _load_record_json(self, email: str) -> dict[str, Any]:
        data = self._read_json_store()
        record = data.get(email, {})
        return {
            "failed_count": int(record.get("failed_count", 0)),
            "locked_until": record.get("locked_until"),
            "last_attempt_at": record.get("last_attempt_at"),
        }

    def _save_record_json(self, email: str, payload: dict[str, Any]) -> None:
        data = self._read_json_store()
        data[email] = payload
        self._JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._JSON_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _read_json_store(self) -> dict[str, Any]:
        if not self._JSON_PATH.exists():
            return {}

        try:
            data = json.loads(self._JSON_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

        return data if isinstance(data, dict) else {}
