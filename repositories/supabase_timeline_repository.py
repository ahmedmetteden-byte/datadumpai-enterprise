"""
Supabase PostgreSQL timeline repository.
"""

from __future__ import annotations

from typing import Any

from core.database import get_database_client, handle_response


class SupabaseTimelineRepository:
    """Persist timeline events in PostgreSQL."""

    def __init__(self, project_id: str, *, user_id: str) -> None:
        self._project_id = project_id
        self._user_id = user_id
        self._client = get_database_client()

    def load(self) -> list[dict[str, Any]]:
        response = handle_response(
            self._client.table("timeline_events")
            .select("*")
            .eq("project_id", self._project_id)
            .order("timestamp")
            .execute(),
            action="load timeline events",
        )

        return [
            {
                "id": str(row["id"]),
                "timestamp": row["timestamp"],
                "action": row["action"],
                "message": row["message"],
                "metadata": row.get("metadata") or {},
            }
            for row in (response.data or [])
        ]

    def save(self, events: list[dict[str, Any]]) -> None:
        self.replace_all(events)

    def append(self, event: dict[str, Any]) -> None:
        row = {
            "id": event["id"],
            "project_id": self._project_id,
            "user_id": self._user_id,
            "timestamp": event["timestamp"],
            "action": event["action"],
            "message": event["message"],
            "metadata": event.get("metadata", {}),
        }
        handle_response(
            self._client.table("timeline_events").insert(row).execute(),
            action="append timeline event",
        )

    def replace_all(self, events: list[dict[str, Any]]) -> None:
        handle_response(
            self._client.table("timeline_events")
            .delete()
            .eq("project_id", self._project_id)
            .execute(),
            action="clear timeline events",
        )

        if not events:
            return

        rows = [
            {
                "id": event["id"],
                "project_id": self._project_id,
                "user_id": self._user_id,
                "timestamp": event["timestamp"],
                "action": event["action"],
                "message": event["message"],
                "metadata": event.get("metadata", {}),
            }
            for event in events
        ]

        handle_response(
            self._client.table("timeline_events").insert(rows).execute(),
            action="save timeline events",
        )
