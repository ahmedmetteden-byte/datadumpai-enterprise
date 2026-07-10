"""
Account-level activity logging for users and administrators.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import config
from core.auth import get_current_user_id
from core.database import get_database_client, handle_response
from core.user_paths import get_user_data_root


class ActivityService:
    """Record and retrieve user-facing activity events."""

    def __init__(self, user_id: str | None = None) -> None:
        self._user_id = user_id or get_current_user_id()

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def log(
        self,
        action: str,
        message: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        entry = {
            "id": str(uuid4()),
            "user_id": self._user_id,
            "action": action,
            "message": message,
            "metadata": metadata or {},
            "created_at": self._utc_now(),
        }

        if config.use_database() and config.is_supabase_configured():
            try:
                handle_response(
                    get_database_client()
                    .table("user_activity_logs")
                    .insert(
                        {
                            "user_id": self._user_id,
                            "action": action,
                            "message": message,
                            "metadata": metadata or {},
                        }
                    )
                    .execute(),
                    action="record activity log",
                )
                return
            except Exception:
                pass

        path = self._json_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        logs: list[dict[str, Any]] = []
        if path.exists():
            try:
                logs = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                logs = []
        logs.append(entry)
        path.write_text(json.dumps(logs, indent=2), encoding="utf-8")

    def list_recent(self, *, limit: int = 50) -> list[dict[str, Any]]:
        if config.use_database() and config.is_supabase_configured():
            try:
                response = handle_response(
                    get_database_client()
                    .table("user_activity_logs")
                    .select("*")
                    .eq("user_id", self._user_id)
                    .order("created_at", desc=True)
                    .limit(limit)
                    .execute(),
                    action="list activity logs",
                )
                return list(response.data or [])
            except Exception:
                pass

        path = self._json_path()
        if not path.exists():
            return []

        try:
            logs = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

        return list(reversed(logs[-limit:]))

    def _json_path(self) -> Path:
        return get_user_data_root(self._user_id) / "activity.json"
