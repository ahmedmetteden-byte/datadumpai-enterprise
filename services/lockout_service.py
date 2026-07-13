"""
Account lockout after repeated failed sign-in attempts.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import config
from services.auth_service import AuthError

logger = logging.getLogger(__name__)

_DEFAULT_LOCKOUT_RECORD: dict[str, Any] = {
    "failed_count": 0,
    "locked_until": None,
    "last_attempt_at": None,
}


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

    @classmethod
    def _default_record(cls) -> dict[str, Any]:
        return dict(_DEFAULT_LOCKOUT_RECORD)

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
        try:
            from core.database import get_service_role_client

            response = (
                get_service_role_client()
                .table("login_lockouts")
                .select("*")
                .eq("email", email)
                .maybe_single()
                .execute()
            )
        except Exception as exc:
            self._log_supabase_failure("load login lockout", email, exc)
            return self._default_record()

        return self._parse_supabase_load_response(response, email)

    def _save_record_supabase(self, email: str, payload: dict[str, Any]) -> None:
        try:
            from core.database import get_service_role_client

            response = (
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
                .execute()
            )
        except Exception as exc:
            self._log_supabase_failure("save login lockout", email, exc)
            return

        self._validate_supabase_write_response(response, email, action="save login lockout")

    def _parse_supabase_load_response(self, response: Any, email: str) -> dict[str, Any]:
        if response is None:
            self._log_supabase_failure(
                "load login lockout",
                email,
                detail="Supabase returned no response object",
            )
            return self._default_record()

        error = getattr(response, "error", None)
        if error:
            self._log_supabase_failure("load login lockout", email, error=error)
            return self._default_record()

        data = getattr(response, "data", None)
        if not data:
            return self._default_record()

        return self._coerce_record(data)

    def _validate_supabase_write_response(
        self,
        response: Any,
        email: str,
        *,
        action: str,
    ) -> None:
        if response is None:
            self._log_supabase_failure(action, email, detail="Supabase returned no response object")
            return

        error = getattr(response, "error", None)
        if error:
            self._log_supabase_failure(action, email, error=error)

    @staticmethod
    def _coerce_record(row: Any) -> dict[str, Any]:
        if not isinstance(row, dict):
            return LockoutService._default_record()

        return {
            "failed_count": int(row.get("failed_count", 0)),
            "locked_until": row.get("locked_until"),
            "last_attempt_at": row.get("last_attempt_at"),
        }

    @staticmethod
    def _log_supabase_failure(
        action: str,
        email: str,
        exc: Exception | None = None,
        *,
        error: Any = None,
        detail: str | None = None,
    ) -> None:
        if exc is not None:
            logger.warning(
                "Login lockout backend unavailable while attempting to %s for %s: %s",
                action,
                email,
                exc,
                exc_info=True,
            )
            return

        if error is not None:
            message = getattr(error, "message", None) or str(error)
            logger.warning(
                "Login lockout backend rejected %s for %s: %s",
                action,
                email,
                message,
            )
            return

        logger.warning(
            "Login lockout backend unavailable while attempting to %s for %s: %s",
            action,
            email,
            detail or "unknown failure",
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
