"""
Supabase PostgreSQL timeline repository for Quick Report workspaces.

Quick Report is user-scoped and never references the projects table.
"""

from __future__ import annotations

from typing import Any

from core.database import get_database_client, handle_response


class SupabaseQuickReportTimelineRepository:
    """Persist Quick Report timeline events without a project UUID."""

    def __init__(self, *, user_id: str) -> None:
        self._user_id = user_id
        self._client = get_database_client()

    def load(self) -> list[dict[str, Any]]:
        response = handle_response(
            self._client.table("quick_report_timeline_events")
            .select("*")
            .eq("user_id", self._user_id)
            .order("timestamp")
            .execute(),
            action="load quick report timeline events",
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
            "user_id": self._user_id,
            "timestamp": event["timestamp"],
            "action": event["action"],
            "message": event["message"],
            "metadata": event.get("metadata", {}),
        }
        handle_response(
            self._client.table("quick_report_timeline_events").insert(row).execute(),
            action="append quick report timeline event",
        )

    def replace_all(self, events: list[dict[str, Any]]) -> None:
        handle_response(
            self._client.table("quick_report_timeline_events")
            .delete()
            .eq("user_id", self._user_id)
            .execute(),
            action="clear quick report timeline events",
        )

        if not events:
            return

        rows = [
            {
                "id": event["id"],
                "user_id": self._user_id,
                "timestamp": event["timestamp"],
                "action": event["action"],
                "message": event["message"],
                "metadata": event.get("metadata", {}),
            }
            for event in events
        ]

        handle_response(
            self._client.table("quick_report_timeline_events").insert(rows).execute(),
            action="save quick report timeline events",
        )
