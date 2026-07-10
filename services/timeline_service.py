"""
DataDumpAI Enterprise
Timeline Service

Records every significant workspace action for audit history,
activity feeds, and collaboration.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from models.timeline_event import TimelineEvent
from repositories.timeline_repository import TimelineRepository


class TimelineService:
    """Record and retrieve project workspace timeline events."""

    ACTION_PROJECT_CREATED = "project_created"
    ACTION_DOCUMENT_UPLOADED = "document_uploaded"
    ACTION_REPORT_GENERATED = "report_generated"

    def _utc_now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _repository(self, project_id: str) -> TimelineRepository:
        return TimelineRepository(project_id)

    def _to_event(self, data: dict[str, Any]) -> TimelineEvent:
        return TimelineEvent(
            id=data["id"],
            timestamp=data["timestamp"],
            action=data["action"],
            message=data["message"],
            metadata=data.get("metadata", {}),
        )

    def _to_dict(self, event: TimelineEvent) -> dict[str, Any]:
        return {
            "id": event.id,
            "timestamp": event.timestamp,
            "action": event.action,
            "message": event.message,
            "metadata": event.metadata,
        }

    def record(
        self,
        *,
        project_id: str,
        action: str,
        message: str,
        metadata: dict[str, Any] | None = None,
        timestamp: str | None = None,
    ) -> TimelineEvent:
        """Persist a new timeline event."""

        event = TimelineEvent(
            id=str(uuid.uuid4()),
            timestamp=timestamp or self._utc_now(),
            action=action,
            message=message,
            metadata=metadata or {},
        )

        repository = self._repository(project_id)
        repository.append(self._to_dict(event))

        return event

    def record_project_created(
        self,
        *,
        project_id: str,
        timestamp: str | None = None,
    ) -> TimelineEvent:
        return self.record(
            project_id=project_id,
            action=self.ACTION_PROJECT_CREATED,
            message="Project created",
            timestamp=timestamp,
        )

    def record_document_uploaded(
        self,
        *,
        project_id: str,
        filename: str,
        timestamp: str | None = None,
    ) -> TimelineEvent:
        return self.record(
            project_id=project_id,
            action=self.ACTION_DOCUMENT_UPLOADED,
            message=f"{filename} uploaded",
            metadata={"filename": filename},
            timestamp=timestamp,
        )

    def record_report_generated(
        self,
        *,
        project_id: str,
        report_name: str,
        timestamp: str | None = None,
    ) -> TimelineEvent:
        return self.record(
            project_id=project_id,
            action=self.ACTION_REPORT_GENERATED,
            message=f"{report_name} generated",
            metadata={"report_name": report_name},
            timestamp=timestamp,
        )

    def get_timeline(self, project_id: str) -> list[TimelineEvent]:
        """
        Return all timeline events for a project, oldest first.

        Backfills from existing workspace data when no events have
        been recorded yet (for projects created before timeline support).
        """

        repository = self._repository(project_id)
        raw_events = repository.load()

        if not raw_events:
            raw_events = self._backfill(project_id)

            if raw_events:
                repository.save(raw_events)

        events = [self._to_event(item) for item in raw_events]

        return sorted(events, key=lambda event: event.timestamp)

    def _backfill(self, project_id: str) -> list[dict[str, Any]]:
        """Build initial timeline events from existing project data."""

        from services.document_service import DocumentService
        from services.project_service import ProjectService
        from services.report_service import ReportService

        try:
            project = ProjectService().get_project(project_id)
        except ValueError:
            return []

        events: list[dict[str, Any]] = []

        created_at = project.get("created_at", "")

        if created_at:
            events.append(
                self._to_dict(
                    TimelineEvent(
                        id=str(uuid.uuid4()),
                        timestamp=created_at,
                        action=self.ACTION_PROJECT_CREATED,
                        message="Project created",
                        metadata={},
                    )
                )
            )

        for document in DocumentService().get_documents(project_id):
            uploaded_at = document.get("uploaded_at", "")

            if not uploaded_at:
                continue

            events.append(
                self._to_dict(
                    TimelineEvent(
                        id=str(uuid.uuid4()),
                        timestamp=uploaded_at,
                        action=self.ACTION_DOCUMENT_UPLOADED,
                        message=f"{document['filename']} uploaded",
                        metadata={"filename": document["filename"]},
                    )
                )
            )

        for report in ReportService().get_reports(project_id):
            created_at = report.get("created_at", "")

            if not created_at:
                continue

            events.append(
                self._to_dict(
                    TimelineEvent(
                        id=str(uuid.uuid4()),
                        timestamp=created_at,
                        action=self.ACTION_REPORT_GENERATED,
                        message=f"{report['name']} generated",
                        metadata={"report_name": report["name"]},
                    )
                )
            )

        return sorted(events, key=lambda item: item["timestamp"])
