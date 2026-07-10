"""
DataDumpAI
Report Pipeline
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

from config import (
    AI_REPORT_MAX_CHARS_PER_DOC,
    AI_REPORT_MAX_PDF_PAGES,
    AI_REPORT_MAX_TABULAR_ROWS,
    AI_REPORT_MAX_TOTAL_CHARS,
)
from services.ai_service import AIService
from services.document_service import DocumentService
from services.document_processor import DocumentProcessor
from services.project_service import ProjectService
from services.report_service import ReportService
from services.report_source_text import trim_combined_source_text
from services.usage_service import UsageService
from services.executive_report_context import ExecutiveReportContextBuilder
from services.plan_service import PlanService
from core.workspace_context import QUICK_REPORT_NAME, QUICK_REPORT_PROJECT_ID, is_quick_report_workspace


class ReportPipeline:
    """Coordinates report generation and regeneration."""

    def __init__(
        self,
        ai_service: AIService | None = None,
        report_service: ReportService | None = None,
        project_service: ProjectService | None = None,
        document_service: DocumentService | None = None,
        usage_service: UsageService | None = None,
        plan_service: PlanService | None = None,
    ) -> None:
        self._ai_service = ai_service or AIService()
        self._report_service = report_service or ReportService()
        self._project_service = project_service or ProjectService()
        self._document_service = document_service or DocumentService()
        self._usage_service = usage_service or UsageService()
        self._plan_service = plan_service or PlanService(self._usage_service)

    @staticmethod
    def load_document_text(
        project_id: str,
        filenames: list[str],
        *,
        user_id: str | None = None,
    ) -> str:
        """Extract and combine text from selected project documents."""

        from core.auth import get_current_user_id

        resolved_user_id = user_id or get_current_user_id()
        texts: list[str] = []

        for filename in filenames:
            try:
                text = DocumentService(user_id=resolved_user_id).read_document_text(
                    project_id,
                    filename,
                    max_pdf_pages=AI_REPORT_MAX_PDF_PAGES,
                    max_tabular_rows=AI_REPORT_MAX_TABULAR_ROWS,
                )
                if text.strip():
                    texts.append(text)
            except Exception:
                continue

        return "\n\n".join(texts)

    @staticmethod
    def _load_selection_item(
        item: dict[str, str],
        user_id: str,
    ) -> tuple[str, str | None]:
        """Load one selected document. Returns (filename, chunk or None)."""

        filename = item["filename"]
        project_id = item["project_id"]

        try:
            chunk = DocumentService(user_id=user_id).read_document_text(
                project_id,
                filename,
                max_pdf_pages=AI_REPORT_MAX_PDF_PAGES,
                max_tabular_rows=AI_REPORT_MAX_TABULAR_ROWS,
            ).strip()
        except Exception:
            return filename, None

        if not chunk:
            return filename, None

        return filename, f"=== SOURCE DOCUMENT: {filename} ===\n\n{chunk}"

    @classmethod
    def load_document_text_from_selection(
        cls,
        selection: list[dict[str, str]],
        *,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Load and combine text from a structured document selection."""

        from core.auth import get_current_user_id

        if not selection:
            return {
                "combined_text": "",
                "loaded": [],
                "skipped": [],
                "truncated": False,
            }

        resolved_user_id = user_id or get_current_user_id()
        loaded: list[str] = []
        skipped: list[str] = []
        texts: list[str] = []

        max_workers = min(4, len(selection))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(
                executor.map(
                    lambda item: cls._load_selection_item(item, resolved_user_id),
                    selection,
                )
            )

        for filename, chunk in results:
            if chunk:
                texts.append(chunk)
                loaded.append(filename)
            else:
                skipped.append(filename)

        combined_text, truncated = trim_combined_source_text(
            "\n\n".join(texts),
            max_chars_per_doc=AI_REPORT_MAX_CHARS_PER_DOC,
            max_total_chars=AI_REPORT_MAX_TOTAL_CHARS,
        )

        return {
            "combined_text": combined_text,
            "loaded": loaded,
            "skipped": skipped,
            "truncated": truncated,
        }

    def _resolve_source_documents(
        self,
        *,
        workspace_id: str,
        source_documents: list[str],
    ) -> list[tuple[str, str]]:
        """Map stored source labels back to workspace id + filename pairs."""

        resolved: list[tuple[str, str]] = []

        for label in source_documents:
            if "/" in label:
                project_name, filename = label.split("/", 1)
                if project_name == QUICK_REPORT_NAME:
                    resolved.append((QUICK_REPORT_PROJECT_ID, filename))
                    continue

                try:
                    project = self._project_service.get_project_by_name(project_name)
                except ValueError:
                    continue

                resolved.append((project["id"], filename))
                continue

            resolved.append((workspace_id, label))

        return resolved

    def load_document_text_from_sources(
        self,
        *,
        workspace_id: str,
        source_documents: list[str],
    ) -> str:
        texts: list[str] = []

        for project_id, filename in self._resolve_source_documents(
            workspace_id=workspace_id,
            source_documents=source_documents,
        ):
            chunk = self.load_document_text(project_id, [filename]).strip()
            if chunk:
                texts.append(chunk)

        return "\n\n".join(texts)

    def _sync_workspace_reports(
        self,
        project: dict[str, Any],
        metadata: dict[str, Any],
    ) -> None:
        if is_quick_report_workspace(project["id"]):
            project.setdefault("reports", [])
            project["reports"] = [
                report
                for report in project["reports"]
                if report.get("filename") != metadata["filename"]
            ]
            project["reports"].append(metadata)
            return

        self._project_service.update_project(project)

    def generate(
        self,
        *,
        document_text: str,
        report_type: str,
        writing_style: str = "Professional",
        audience: str = "Executive Management",
        include_charts: bool = False,
        include_recommendations: bool = True,
        source_document_count: int | None = None,
        report_context: dict | None = None,
    ) -> str:
        """Generate report text without persisting it."""

        self._usage_service.check_can_generate_report()

        intelligence_format = self._plan_service.uses_intelligence_format(report_type)
        charts_enabled = (
            include_charts and self._plan_service.include_professional_charts()
        )

        report_text = self._ai_service.generate_report(
            document_text=document_text,
            report_type=report_type,
            writing_style=writing_style,
            audience=audience,
            include_charts=charts_enabled,
            include_recommendations=include_recommendations,
            source_document_count=source_document_count,
            report_context=report_context,
            use_intelligence_format=intelligence_format,
        )

        self._usage_service.record_report_generated()

        return report_text

    def save_generated_report(
        self,
        *,
        project: dict[str, Any],
        report_text: str,
        report_type: str,
        source_documents: list[str],
    ) -> dict[str, Any]:
        """Persist a generated report draft to the active workspace."""

        metadata = self._report_service.save_report(
            project_id=project["id"],
            report_name=report_type,
            report_text=report_text,
            source_documents=source_documents,
        )

        project.setdefault("reports", [])
        project["reports"] = [
            report
            for report in project["reports"]
            if report.get("filename") != metadata["filename"]
        ]
        project["reports"].append(metadata)
        self._sync_workspace_reports(project, metadata)

        return metadata

    def generate_and_save(
        self,
        *,
        project: dict[str, Any],
        document_text: str,
        report_type: str,
        source_documents: list[str],
        writing_style: str = "Professional",
        audience: str = "Executive Management",
        include_charts: bool = False,
        include_recommendations: bool = True,
    ) -> tuple[str, dict[str, Any]]:
        report_text = self.generate(
            document_text=document_text,
            report_type=report_type,
            writing_style=writing_style,
            audience=audience,
            include_charts=include_charts,
            include_recommendations=include_recommendations,
        )

        metadata = self.save_generated_report(
            project=project,
            report_text=report_text,
            report_type=report_type,
            source_documents=source_documents,
        )

        return report_text, metadata

    def regenerate_and_save(
        self,
        *,
        project: dict[str, Any],
        report: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        """Regenerate an existing saved report from its stored sources."""

        self._usage_service.check_can_generate_report()

        report_type = report.get("report_type") or report.get("name", "Executive Summary")
        source_documents = report.get("source_documents") or []

        if not source_documents:
            source_documents = [
                document["filename"]
                for document in self._document_service.get_documents(project["id"])
            ]

        resolved = self._resolve_source_documents(
            workspace_id=project["id"],
            source_documents=source_documents,
        )
        selection = [
            {"project_id": project_id, "filename": filename}
            for project_id, filename in resolved
        ]
        load_result = self.load_document_text_from_selection(
            selection,
            user_id=self._document_service._user_id,
        )
        document_text = load_result["combined_text"].strip()

        if not document_text:
            raise ValueError(
                "Could not read source documents for this report. "
                "Check that the original files still exist."
            )

        report_context = ExecutiveReportContextBuilder().build(
            workspace_id=project["id"],
            source_documents=source_documents,
            report_type=report_type,
            include_prior_reports=self._plan_service.include_cross_document_intelligence(),
        )

        intelligence_format = self._plan_service.uses_intelligence_format(report_type)

        report_text = self._ai_service.generate_report(
            document_text=document_text,
            report_type=report_type,
            writing_style="Professional",
            audience="Executive Management",
            include_charts=self._plan_service.include_professional_charts(),
            include_recommendations=True,
            source_document_count=len(load_result["loaded"]),
            report_context=report_context,
            use_intelligence_format=intelligence_format,
        )

        metadata = self._report_service.update_report(
            project_id=project["id"],
            filename=report["filename"],
            report_text=report_text,
            source_documents=source_documents,
        )

        project.setdefault("reports", [])
        updated = False
        for index, existing in enumerate(project["reports"]):
            if existing.get("filename") == metadata["filename"]:
                project["reports"][index] = metadata
                updated = True
                break

        if not updated:
            project["reports"].append(metadata)

        self._sync_workspace_reports(project, metadata)
        self._usage_service.record_report_generated()

        return report_text, metadata
