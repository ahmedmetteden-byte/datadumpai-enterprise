"""
DataDumpAI Enterprise
Workspace Service

Assembles the complete domain Workspace.

The Workspace is the core of DataDumpAI — not a page, not a project.
Everything revolves around it. The UI only renders what this service returns.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from core.user_paths import get_user_projects_root
from models.workspace import (
    HEALTH_ICONS,
    Workspace,
    WorkspaceAI,
    WorkspaceAnalytics,
    WorkspaceHealthIndicator,
)
from core.workspace_context import (
    QUICK_REPORT_NAME,
    build_quick_report_record,
    is_quick_report_workspace,
)
from services.document_service import DocumentService
from services.export_service import ExportService
from services.knowledge_service import KnowledgeService
from services.project_service import ProjectService
from services.report_service import ReportService
from services.timeline_service import TimelineService

RECENT_ITEM_LIMIT = 5


class WorkspaceService:
    """
    Aggregates every Workspace facet into one domain object.
    """

    @staticmethod
    def _root() -> Path:
        return get_user_projects_root(WorkspaceService._current_user_id())

    @staticmethod
    def _current_user_id() -> str:
        from core.current_user import current_user_id

        return current_user_id()

    MEETING_EXTENSIONS = {
        ".mp3",
        ".wav",
        ".m4a",
        ".mp4",
        ".webm",
        ".ogg",
    }

    PRESENTATION_EXTENSIONS = {
        ".pptx",
        ".ppt",
    }

    def __init__(self) -> None:

        self.projects = ProjectService()
        self.documents = DocumentService()
        self.reports = ReportService()
        self.exports = ExportService()
        self.timeline = TimelineService()
        self.knowledge = KnowledgeService()

    def load_workspace(self, project_id: str) -> Workspace:
        """
        Assemble a complete Workspace for the given project.

        Facets assembled:
            Project, Documents, Reports, AI, Timeline,
            Analytics, Exports, Knowledge

        All counts and readiness are calculated here —
        never in the UI layer.
        """

        project = (
            build_quick_report_record()
            if is_quick_report_workspace(project_id)
            else self.projects.get_project(project_id)
        )
        documents = self.documents.get_documents(project_id)
        reports = self.reports.get_reports(project_id)
        exports = self.exports.get_exports(project_id)
        timeline = self.timeline.get_timeline(project_id)

        storage_used = sum(document["size"] for document in documents)
        last_activity = self._calculate_last_activity(
            project,
            documents,
            reports,
            exports,
        )

        project["documents"] = documents
        project["reports"] = reports
        project["exports"] = exports
        project["storage_used"] = storage_used
        project["last_activity"] = last_activity

        analytics = WorkspaceAnalytics(
            document_count=len(documents),
            report_count=len(reports),
            export_count=len(exports),
            storage_used=storage_used,
            last_activity=last_activity,
            created_at=project.get("created_at", ""),
            updated_at=project.get("updated_at", ""),
        )

        knowledge = self.knowledge.build_store(project_id)
        ai = self._build_ai(documents, reports)

        return Workspace(
            project=project,
            documents=documents,
            reports=reports,
            ai=ai,
            timeline=timeline,
            analytics=analytics,
            exports=exports,
            knowledge=knowledge,
            health=self._build_health(
                project_id,
                project,
                documents,
                reports,
                exports,
            ),
            recent_documents=self._get_recent_documents(documents),
            recent_reports=self._get_recent_reports(reports),
        )

    def _build_ai(
        self,
        documents: list[dict],
        reports: list[dict],
    ) -> WorkspaceAI:
        """Build AI readiness for this workspace."""

        ready = bool(documents)

        return WorkspaceAI(
            ready=ready,
            document_count=len(documents),
            report_count=len(reports),
            status="AI ready" if ready else "AI not ready",
        )

    def _calculate_last_activity(
        self,
        project: dict,
        documents: list[dict],
        reports: list[dict],
        exports: list[dict],
    ) -> str:
        """Return the most recent activity timestamp in the workspace."""

        candidates: list[str] = []

        for key in ("last_activity", "updated_at", "created_at"):
            value = project.get(key, "")

            if value:
                candidates.append(value)

        for document in documents:
            uploaded_at = document.get("uploaded_at", "")

            if uploaded_at:
                candidates.append(uploaded_at)

        for report in reports:
            created_at = report.get("created_at", "")

            if created_at:
                candidates.append(created_at)

        for export in exports:
            exported_at = export.get("exported_at", "")

            if exported_at:
                candidates.append(exported_at)

        if not candidates:
            return ""

        return max(candidates, key=self._parse_timestamp)

    def _parse_timestamp(self, value: str) -> datetime:
        """Parse an ISO timestamp for comparison."""

        try:
            return datetime.fromisoformat(value)

        except (TypeError, ValueError):
            return datetime.min

    def _get_recent_documents(
        self,
        documents: list[dict],
    ) -> list[dict]:
        """Return the most recently uploaded documents."""

        sorted_documents = sorted(
            documents,
            key=lambda document: document.get("uploaded_at", ""),
            reverse=True,
        )

        return sorted_documents[:RECENT_ITEM_LIMIT]

    def _get_recent_reports(
        self,
        reports: list[dict],
    ) -> list[dict]:
        """Return the most recently created reports."""

        sorted_reports = sorted(
            reports,
            key=lambda report: report.get(
                "created_at",
                report.get("filename", ""),
            ),
            reverse=True,
        )

        return sorted_reports[:RECENT_ITEM_LIMIT]

    def _health_indicator(
        self,
        status: str,
        message: str,
    ) -> WorkspaceHealthIndicator:
        """Build a display-ready health indicator."""

        return WorkspaceHealthIndicator(
            status=status,
            icon=HEALTH_ICONS[status],
            message=message,
        )

    def _build_health(
        self,
        project_id: str,
        project: dict,
        documents: list[dict],
        reports: list[dict],
        exports: list[dict],
    ) -> list[WorkspaceHealthIndicator]:
        """
        Assess workspace readiness and return instant guidance on
        what is complete, what is missing, and what needs attention.
        """

        indicators: list[WorkspaceHealthIndicator] = []

        indicators.append(
            self._health_indicator(
                "ready",
                "Project created",
            )
        )

        if documents:
            indicators.append(
                self._health_indicator(
                    "ready",
                    "Documents uploaded",
                )
            )
        else:
            indicators.append(
                self._health_indicator(
                    "critical",
                    "No documents uploaded",
                )
            )

        if reports:
            indicators.append(
                self._health_indicator(
                    "ready",
                    "Reports generated",
                )
            )
        else:
            indicators.append(
                self._health_indicator(
                    "warning",
                    "No reports generated",
                )
            )

        if self._has_presentation(exports):
            indicators.append(
                self._health_indicator(
                    "ready",
                    "Presentation exported",
                )
            )
        else:
            indicators.append(
                self._health_indicator(
                    "warning",
                    "No presentation exported",
                )
            )

        if self._has_meeting_recording(
            project_id,
            documents,
            project,
        ):
            indicators.append(
                self._health_indicator(
                    "ready",
                    "Meeting recording uploaded",
                )
            )
        else:
            indicators.append(
                self._health_indicator(
                    "critical",
                    "No meeting recording",
                )
            )

        if documents:
            indicators.append(
                self._health_indicator(
                    "ready",
                    "AI ready",
                )
            )
        else:
            indicators.append(
                self._health_indicator(
                    "critical",
                    "AI not ready",
                )
            )

        return indicators

    def _has_meeting_recording(
        self,
        project_id: str,
        documents: list[dict],
        project: dict,
    ) -> bool:
        """Return True when a meeting recording exists in the workspace."""

        if project.get("meetings"):
            return True

        for document in documents:
            suffix = Path(document["filename"]).suffix.lower()

            if suffix in self.MEETING_EXTENSIONS:
                return True

        meetings_dir = self._root() / project_id / "documents"

        if meetings_dir.exists():
            for file in meetings_dir.iterdir():
                if file.is_file() and file.suffix.lower() in self.MEETING_EXTENSIONS:
                    return True

        return False

    def _has_presentation(self, exports: list[dict]) -> bool:
        """Return True when a presentation exists in workspace exports."""

        for export in exports:
            suffix = Path(export["filename"]).suffix.lower()

            if suffix in self.PRESENTATION_EXTENSIONS:
                return True

        return False
