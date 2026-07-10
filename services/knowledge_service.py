"""
DataDumpAI Enterprise
Knowledge Service

Builds and maintains the Enterprise Knowledge Store for a Workspace.

Every significant artifact is indexed here so Search and AI
operate over one corpus — not scattered file lists.
"""

from __future__ import annotations

from pathlib import Path

from models.knowledge import KnowledgeEntry, KnowledgeStore
from models.timeline_event import TimelineEvent
from services.document_service import DocumentService
from services.export_service import ExportService
from services.report_service import ReportService
from services.timeline_service import TimelineService

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


class KnowledgeService:
    """
    Assembles the Knowledge Store for one project workspace.
    """

    def __init__(
        self,
        document_service: DocumentService | None = None,
        report_service: ReportService | None = None,
        export_service: ExportService | None = None,
        timeline_service: TimelineService | None = None,
    ) -> None:

        self.documents = document_service or DocumentService()
        self.reports = report_service or ReportService()
        self.exports = export_service or ExportService()
        self.timeline = timeline_service or TimelineService()

    def build_store(self, project_id: str) -> KnowledgeStore:
        """
        Index every available artifact into one Knowledge Store.
        """

        documents = self.documents.get_documents(project_id)
        reports = self.reports.get_reports(project_id)
        exports = self.exports.get_exports(project_id)
        events = self.timeline.get_timeline(project_id)

        entries: list[KnowledgeEntry] = []

        meeting_count = 0
        presentation_count = 0

        for document in documents:

            filename = document["filename"]
            suffix = Path(filename).suffix.lower()
            source_type = "document"

            if suffix in MEETING_EXTENSIONS:
                source_type = "meeting"
                meeting_count += 1

            entries.append(
                KnowledgeEntry(
                    id=f"document:{filename}",
                    source_type=source_type,
                    title=filename,
                    path=document.get("path", ""),
                    created_at=document.get("uploaded_at", ""),
                    summary=f"{source_type.title()} uploaded to workspace",
                    metadata={
                        "size": document.get("size", 0),
                        "filename": filename,
                    },
                )
            )

        for report in reports:

            entries.append(
                KnowledgeEntry(
                    id=f"report:{report['filename']}",
                    source_type="report",
                    title=report["name"],
                    path=report.get("path", ""),
                    created_at=report.get("created_at", ""),
                    summary="AI-generated executive report",
                    metadata={
                        "size": report.get("size", 0),
                        "filename": report["filename"],
                    },
                )
            )

        for export in exports:

            filename = export["filename"]
            suffix = Path(filename).suffix.lower()
            source_type = "export"

            if suffix in PRESENTATION_EXTENSIONS:
                source_type = "presentation"
                presentation_count += 1

            entries.append(
                KnowledgeEntry(
                    id=f"export:{filename}",
                    source_type=source_type,
                    title=filename,
                    path=export.get("path", ""),
                    created_at=export.get("exported_at", ""),
                    summary=f"{export.get('format', 'file').upper()} export",
                    metadata={
                        "size": export.get("size", 0),
                        "format": export.get("format", ""),
                        "mime_type": export.get("mime_type", ""),
                    },
                )
            )

        for event in events:

            entries.append(self._entry_from_timeline(event))

        entries.sort(key=lambda entry: entry.created_at, reverse=True)

        document_entries = [
            entry
            for entry in entries
            if entry.source_type == "document"
        ]
        report_entries = [
            entry
            for entry in entries
            if entry.source_type == "report"
        ]
        export_entries = [
            entry
            for entry in entries
            if entry.source_type == "export"
        ]

        return KnowledgeStore(
            entries=entries,
            document_count=len(document_entries),
            report_count=len(report_entries),
            export_count=len(export_entries),
            meeting_count=meeting_count,
            presentation_count=presentation_count,
            conversation_count=0,
            timeline_count=len(events),
        )

    def _entry_from_timeline(
        self,
        event: TimelineEvent,
    ) -> KnowledgeEntry:
        """Convert a timeline event into a knowledge entry."""

        return KnowledgeEntry(
            id=f"timeline:{event.id}",
            source_type="timeline",
            title=event.message,
            path="",
            created_at=event.timestamp,
            summary=f"Activity: {event.action}",
            metadata={
                "action": event.action,
                **event.metadata,
            },
        )
