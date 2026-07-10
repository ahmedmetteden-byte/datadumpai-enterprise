"""
JSON-backed timeline repository.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.user_paths import get_user_projects_root
from storage.json_storage import JSONStorage


class JsonTimelineRepository:
    """Persist timeline events in per-project JSON files."""

    def __init__(
        self,
        project_id: str,
        *,
        user_id: str,
        projects_root: Path | str | None = None,
    ) -> None:
        root = Path(projects_root) if projects_root is not None else get_user_projects_root(user_id)
        timeline_path = root / project_id / "timeline.json"
        self._project_id = project_id
        self._user_id = user_id
        self._storage = JSONStorage(timeline_path)

    def load(self) -> list[dict[str, Any]]:
        return self._storage.load()

    def save(self, events: list[dict[str, Any]]) -> None:
        self._storage.save(events)

    def append(self, event: dict[str, Any]) -> None:
        events = self.load()
        events.append(event)
        self.save(events)

    def replace_all(self, events: list[dict[str, Any]]) -> None:
        self.save(events)
