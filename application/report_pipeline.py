"""
DataDumpAI
Report Pipeline
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from config import (
    AI_REPORT_MAX_PDF_PAGES,
    AI_REPORT_MAX_TABULAR_ROWS,
    AI_REPORT_MAX_TOTAL_CHARS,
)
from models.report_processing_mode import ReportProcessingMode
from services.ai_service import AIService
from services.document_service import DocumentService
from services.project_service import ProjectService
from services.report_service import ReportService
from services.report_source_text import prepare_combined_source_text
from services.usage_service import UsageService
from services.executive_report_context import ExecutiveReportContextBuilder
from services.plan_service import PlanService
from services.report_document import compose_report_data
from services.report_chunk_processor import process_source_documents
from services.full_report_prompt import is_full_report
from services.report_section_templates import build_report_section_plan
from models.report_data import ReportData
from core.current_user import CurrentUser, require_current_user
from core.workspace_context import QUICK_REPORT_NAME, QUICK_REPORT_PROJECT_ID, is_quick_report

logger = logging.getLogger(__name__)


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
        *,
        current_user: CurrentUser | None = None,
    ) -> None:
        # Resolve once on the calling (Streamlit) thread, then reuse everywhere —
        # including ThreadPoolExecutor workers that cannot see session_state.
        self._current_user = current_user or require_current_user()
        self._ai_service = ai_service or AIService()
        self._report_service = report_service or ReportService()
        self._project_service = project_service or ProjectService(
            current_user=self._current_user,
        )
        self._document_service = document_service or DocumentService(
            current_user=self._current_user,
        )
        self._usage_service = usage_service or UsageService(
            current_user=self._current_user,
        )
        self._plan_service = plan_service or PlanService(self._usage_service)

    @property
    def current_user(self) -> CurrentUser:
        return self._current_user

    @staticmethod
    def _document_extraction_limits(
        processing_mode: ReportProcessingMode,
    ) -> tuple[int | None, int | None]:
        if processing_mode == ReportProcessingMode.COMPREHENSIVE:
            return None, None
        return AI_REPORT_MAX_PDF_PAGES, AI_REPORT_MAX_TABULAR_ROWS

    def load_document_text(
        self,
        project_id: str,
        filenames: list[str],
        *,
        processing_mode: ReportProcessingMode = ReportProcessingMode.COMPREHENSIVE,
    ) -> str:
        """Extract and combine text from selected project documents."""

        max_pdf_pages, max_tabular_rows = self._document_extraction_limits(
            processing_mode,
        )
        texts: list[str] = []

        logger.info(
            "load_document_text start project_id=%s filenames=%s processing_mode=%s "
            "user_id=%s",
            project_id,
            filenames,
            processing_mode,
            self._current_user.id,
        )

        for filename in filenames:
            try:
                text = self._document_service.read_document_text(
                    project_id,
                    filename,
                    max_pdf_pages=max_pdf_pages,
                    max_tabular_rows=max_tabular_rows,
                )
            except Exception:
                logger.exception(
                    "load_document_text failed project_id=%s filename=%s user_id=%s",
                    project_id,
                    filename,
                    self._current_user.id,
                )
                raise

            if text.strip():
                texts.append(text)
            else:
                logger.warning(
                    "load_document_text empty extraction project_id=%s filename=%s",
                    project_id,
                    filename,
                )

        combined = "\n\n".join(texts)
        logger.info(
            "load_document_text finished project_id=%s loaded=%s empty=%s "
            "combined_char_count=%s",
            project_id,
            len(texts),
            len(filenames) - len(texts),
            len(combined),
        )
        return combined

    def _load_selection_item(
        self,
        item: dict[str, str],
        processing_mode: ReportProcessingMode,
    ) -> tuple[str, str | None]:
        """Load one selected document. Returns (filename, chunk or None)."""

        filename = item["filename"]
        project_id = item["project_id"]
        max_pdf_pages, max_tabular_rows = self._document_extraction_limits(
            processing_mode,
        )

        logger.info(
            "_load_selection_item start project_id=%s filename=%s processing_mode=%s "
            "user_id=%s",
            project_id,
            filename,
            processing_mode,
            self._current_user.id,
        )

        # Use the pipeline-bound DocumentService — never require_current_user()
        # inside the worker thread.
        try:
            chunk = self._document_service.read_document_text(
                project_id,
                filename,
                max_pdf_pages=max_pdf_pages,
                max_tabular_rows=max_tabular_rows,
            ).strip()
        except Exception:
            logger.exception(
                "_load_selection_item failed project_id=%s filename=%s user_id=%s",
                project_id,
                filename,
                self._current_user.id,
            )
            raise

        if not chunk:
            logger.warning(
                "_load_selection_item empty text project_id=%s filename=%s",
                project_id,
                filename,
            )
            return filename, None

        logger.info(
            "_load_selection_item success project_id=%s filename=%s char_count=%s",
            project_id,
            filename,
            len(chunk),
        )
        return filename, f"=== SOURCE DOCUMENT: {filename} ===\n\n{chunk}"

    def load_document_text_from_selection(
        self,
        selection: list[dict[str, str]],
        *,
        processing_mode: ReportProcessingMode = ReportProcessingMode.COMPREHENSIVE,
    ) -> dict[str, Any]:
        """Load and combine text from a structured document selection."""

        logger.info(
            "load_document_text_from_selection start count=%s processing_mode=%s "
            "user_id=%s selection=%s",
            len(selection),
            processing_mode,
            self._current_user.id,
            [
                {"project_id": item.get("project_id"), "filename": item.get("filename")}
                for item in selection
            ],
        )

        if not selection:
            logger.warning("load_document_text_from_selection called with empty selection")
            return {
                "combined_text": "",
                "loaded": [],
                "skipped": [],
                "normalized": False,
                "multi_stage": False,
                "chunk_count": 0,
            }

        loaded: list[str] = []
        skipped: list[str] = []
        texts: list[str] = []

        max_workers = min(4, len(selection))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(
                executor.map(
                    lambda item: self._load_selection_item(
                        item,
                        processing_mode,
                    ),
                    selection,
                )
            )

        for filename, chunk in results:
            if chunk:
                texts.append(chunk)
                loaded.append(filename)
            else:
                skipped.append(filename)

        prepared = prepare_combined_source_text("\n\n".join(texts))
        combined_text = str(prepared["combined_text"])
        multi_stage = len(combined_text) > AI_REPORT_MAX_TOTAL_CHARS

        logger.info(
            "load_document_text_from_selection finished loaded=%s skipped=%s "
            "combined_char_count=%s stripped_char_count=%s normalized=%s multi_stage=%s",
            loaded,
            skipped,
            len(combined_text),
            len(combined_text.strip()),
            bool(prepared["normalized"]),
            multi_stage,
        )

        if not combined_text.strip():
            logger.error(
                "load_document_text_from_selection returned empty combined text "
                "loaded=%s skipped=%s selection_count=%s user_id=%s",
                loaded,
                skipped,
                len(selection),
                self._current_user.id,
            )

        return {
            "combined_text": combined_text,
            "loaded": loaded,
            "skipped": skipped,
            "normalized": bool(prepared["normalized"]),
            "multi_stage": multi_stage,
            "chunk_count": 0,
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
        if is_quick_report(project["id"]):
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
        processing_mode: ReportProcessingMode = ReportProcessingMode.COMPREHENSIVE,
    ) -> ReportData:
        """Generate a structured report without persisting it."""

        self._usage_service.check_can_generate_report()

        intelligence_format = self._plan_service.uses_intelligence_format(report_type)
        charts_enabled = (
            include_charts and self._plan_service.include_professional_charts()
        )

        report_context = report_context or {}
        report_data, narrative_input = process_source_documents(
            document_text=document_text,
            report_type=report_type,
            processing_mode=processing_mode,
            ai_service=self._ai_service,
            source_documents=report_context.get("source_documents"),
            report_context=report_context,
            source_document_count=source_document_count,
        )

        report_format = "full_report" if is_full_report(report_type) else "intelligence"
        section_plan = build_report_section_plan(
            report_data,
            user_report_type=report_type,
            document_text=document_text,
            report_context=report_context,
            include_charts=charts_enabled,
            source_document_count=source_document_count,
            report_format=report_format,
        )
        report_data.metadata = {
            **report_data.metadata,
            "section_plan": section_plan.to_dict(),
            "report_context": {
                "has_prior_reports": bool(report_context.get("has_prior_reports")),
                "reporting_period": report_context.get("reporting_period"),
                "source_documents": list(report_context.get("source_documents") or []),
            },
            "source_document_count": source_document_count,
        }

        narrative = self._ai_service.generate_report(
            document_text=narrative_input,
            report_type=report_type,
            writing_style=writing_style,
            audience=audience,
            include_charts=charts_enabled,
            include_recommendations=include_recommendations,
            source_document_count=source_document_count,
            report_context=report_context,
            use_intelligence_format=intelligence_format,
            report_data=report_data,
        )

        report = compose_report_data(
            narrative=narrative,
            base=report_data,
            report_type=report_type,
            title=report_type,
            include_charts=charts_enabled,
        )

        self._usage_service.record_report_generated()

        return report

    def save_generated_report(
        self,
        *,
        project: dict[str, Any],
        report: ReportData,
        report_type: str,
        source_documents: list[str],
    ) -> dict[str, Any]:
        """Persist a generated report draft to the active workspace."""

        metadata = self._report_service.save_report(
            project_id=project["id"],
            report_name=report_type,
            report=report,
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
    ) -> tuple[ReportData, dict[str, Any]]:
        report = self.generate(
            document_text=document_text,
            report_type=report_type,
            writing_style=writing_style,
            audience=audience,
            include_charts=include_charts,
            include_recommendations=include_recommendations,
        )

        metadata = self.save_generated_report(
            project=project,
            report=report,
            report_type=report_type,
            source_documents=source_documents,
        )

        return report, metadata

    def regenerate_and_save(
        self,
        *,
        project: dict[str, Any],
        report: dict[str, Any],
    ) -> tuple[ReportData, dict[str, Any]]:
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
        processing_mode = ReportProcessingMode.from_value(
            report.get("processing_mode")
            or report.get("metadata", {}).get("processing_mode"),
        )
        load_result = self.load_document_text_from_selection(
            selection,
            processing_mode=processing_mode,
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
            include_prior_reports=(
                self._plan_service.include_cross_document_intelligence()
                or self._plan_service.uses_full_report_format(report_type)
            ),
            reporting_period=report.get("reporting_period"),
        )

        intelligence_format = self._plan_service.uses_intelligence_format(report_type)
        charts_enabled = self._plan_service.include_professional_charts()

        report_data, narrative_input = process_source_documents(
            document_text=document_text,
            report_type=report_type,
            processing_mode=processing_mode,
            ai_service=self._ai_service,
            source_documents=source_documents,
            report_context=report_context,
            source_document_count=len(load_result["loaded"]),
        )

        report_format = "full_report" if is_full_report(report_type) else "intelligence"
        section_plan = build_report_section_plan(
            report_data,
            user_report_type=report_type,
            document_text=document_text,
            report_context=report_context,
            include_charts=charts_enabled,
            source_document_count=len(load_result["loaded"]),
            report_format=report_format,
        )
        report_data.metadata = {
            **report_data.metadata,
            "section_plan": section_plan.to_dict(),
            "report_context": {
                "has_prior_reports": bool(report_context.get("has_prior_reports")),
                "reporting_period": report_context.get("reporting_period"),
                "source_documents": list(report_context.get("source_documents") or []),
            },
            "source_document_count": len(load_result["loaded"]),
        }

        narrative = self._ai_service.generate_report(
            document_text=narrative_input,
            report_type=report_type,
            writing_style="Professional",
            audience="Executive Management",
            include_charts=charts_enabled,
            include_recommendations=True,
            source_document_count=len(load_result["loaded"]),
            report_context=report_context,
            use_intelligence_format=intelligence_format,
            report_data=report_data,
        )

        updated_report = compose_report_data(
            narrative=narrative,
            base=report_data,
            report_type=report_type,
            title=report_type,
            include_charts=charts_enabled,
        )

        metadata = self._report_service.update_report(
            project_id=project["id"],
            filename=report["filename"],
            report=updated_report,
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

        return updated_report, metadata
