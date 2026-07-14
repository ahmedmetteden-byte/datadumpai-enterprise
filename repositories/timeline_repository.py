"""
Timeline repository — JSON or Supabase depending on configuration.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import config
from core.current_user import require_current_user
from core.user_paths import get_user_projects_root
from core.workspace_context import is_quick_report
from repositories.json_timeline_repository import JsonTimelineRepository
from repositories.supabase_quick_report_timeline_repository import (
    SupabaseQuickReportTimelineRepository,
)
from repositories.supabase_timeline_repository import SupabaseTimelineRepository


class TimelineRepository:
    """Persists timeline events for one project."""

    def __init__(
        self,
        project_id: str,
        projects_root: Path | str | None = None,
    ) -> None:
        current_user = require_current_user()
        resolved_user_id = current_user.id

        if config.use_database():
            if is_quick_report(project_id):
                self._impl = SupabaseQuickReportTimelineRepository(
                    user_id=resolved_user_id,
                )
            else:
                self._impl = SupabaseTimelineRepository(
                    project_id,
                    user_id=resolved_user_id,
                )
        else:
            root = (
                Path(projects_root)
                if projects_root is not None
                else get_user_projects_root(resolved_user_id)
            )
            self._impl = JsonTimelineRepository(
                project_id,
                user_id=resolved_user_id,
                projects_root=root,
            )

    def load(self) -> list[dict[str, Any]]:
        return self._impl.load()

    def save(self, events: list[dict[str, Any]]) -> None:
        self._impl.save(events)

    def append(self, event: dict[str, Any]) -> None:
        self._impl.append(event)
