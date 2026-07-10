"""
DataDumpAI Enterprise
Copilot Context Service

Assembles workspace knowledge for project-aware Executive Copilot.
"""

from __future__ import annotations

from pathlib import Path

from models.workspace import Workspace
from services.report_service import ReportService
from services.search_service import SearchService
from services.workspace_service import WorkspaceService

MAX_REPORTS_IN_CONTEXT = 3
MAX_REPORT_CHARS = 12_000
MAX_EXCERPT_CHARS = 800
MAX_EXCERPTS = 8


class CopilotContextService:
    """
    Build executive context from the active workspace.

    The user never has to explain which project they mean —
    context is assembled automatically from disk.
    """

    def __init__(
        self,
        workspace_service: WorkspaceService | None = None,
        search_service: SearchService | None = None,
    ) -> None:
        self._workspace = workspace_service or WorkspaceService()
        self._search = search_service or SearchService()

    def build(
        self,
        *,
        project_id: str,
        question: str,
        focus_report: dict | None = None,
        include_saved_knowledge: bool = True,
    ) -> tuple[Workspace, str, list[str]]:
        """
        Return workspace, assembled context text, and source labels.
        """

        workspace = self._workspace.load_workspace(project_id)
        sections: list[str] = []
        sources: list[str] = []

        sections.append(
            self._project_overview(workspace)
        )

        sorted_reports = sorted(
            workspace.reports,
            key=lambda report: report.get("created_at", ""),
            reverse=True,
        )

        if include_saved_knowledge and sorted_reports:
            sections.append(
                self._reports_index(sorted_reports)
            )
            sections.append(
                self._recent_reports(sorted_reports, sources)
            )

        if workspace.documents:
            sections.append(
                self._documents_index(workspace)
            )

        excerpts = self._search.search_excerpts(
            project_id,
            question,
            max_excerpts=MAX_EXCERPTS,
            excerpt_length=MAX_EXCERPT_CHARS,
        )

        if excerpts:
            sections.append(
                self._relevant_excerpts(excerpts, sources)
            )

        if include_saved_knowledge and focus_report:
            sections.append(
                self._focused_report(focus_report, sources)
            )

        context = "\n\n".join(section for section in sections if section)

        return workspace, context, sources

    def _project_overview(self, workspace: Workspace) -> str:
        return (
            f"ACTIVE PROJECT\n"
            f"Name: {workspace.name}\n"
            f"Documents: {workspace.document_count}\n"
            f"Reports: {workspace.report_count}\n"
            f"Last Activity: {workspace.last_activity or '—'}\n"
            f"AI Ready: {workspace.ai.status}"
        )

    def _reports_index(self, reports: list[dict]) -> str:
        lines = ["REPORTS INDEX (newest first)"]

        for index, report in enumerate(reports, start=1):
            created = report.get("created_at", "")[:10] or "—"
            lines.append(
                f"{index}. {report['name']} · {created} · {report['filename']}"
            )

        return "\n".join(lines)

    def _recent_reports(
        self,
        reports: list[dict],
        sources: list[str],
    ) -> str:
        blocks = ["RECENT REPORTS"]

        for report in reports[:MAX_REPORTS_IN_CONTEXT]:
            try:
                text = ReportService.load_report(report["path"])
            except OSError:
                continue

            trimmed = text[:MAX_REPORT_CHARS]
            blocks.append(
                f"### {report['name']}\n"
                f"File: {report['filename']}\n"
                f"Created: {report.get('created_at', '')[:19]}\n\n"
                f"{trimmed}"
            )
            sources.append(report["name"])

        return "\n\n".join(blocks)

    def _documents_index(self, workspace: Workspace) -> str:
        lines = ["DOCUMENT LIBRARY"]

        for document in workspace.documents:
            uploaded = document.get("uploaded_at", "")[:10] or "—"
            lines.append(
                f"- {document['filename']} · uploaded {uploaded}"
            )

        return "\n".join(lines)

    def _relevant_excerpts(
        self,
        excerpts: list[dict],
        sources: list[str],
    ) -> str:
        lines = ["RELEVANT EXCERPTS FOR THIS QUESTION"]

        for index, excerpt in enumerate(excerpts, start=1):
            label = excerpt.get("filename", "Source")
            location = excerpt.get("location", "")

            if location:
                lines.append(
                    f"[{index}] {label} · {location}\n"
                    f"{excerpt.get('excerpt', '')}"
                )
            else:
                lines.append(
                    f"[{index}] {label}\n"
                    f"{excerpt.get('excerpt', '')}"
                )

            if label not in sources:
                sources.append(label)

        return "\n\n".join(lines)

    def _focused_report(
        self,
        report: dict,
        sources: list[str],
    ) -> str:
        path = report.get("path", "")

        if not path or not Path(path).is_file():
            return ""

        text = ReportService.load_report(path)

        name = report.get("name", report.get("filename", "Report"))

        if name not in sources:
            sources.append(name)

        return (
            f"FOCUSED REPORT\n"
            f"Name: {name}\n"
            f"File: {report.get('filename', '')}\n\n"
            f"{text[:MAX_REPORT_CHARS]}"
        )
