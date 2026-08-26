"""
Premium export service — consulting-grade PDF and presentation outputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

from services.export_service import ExportService
from services.premium_docx_export import DocxExportMetadata, build_premium_docx
from services.premium_pdf_export import PremiumExportMetadata, build_premium_pdf
from services.report_document import report_is_intelligence
from models.report_data import ReportData


def is_presentation_export_available() -> bool:
    try:
        import pptx  # noqa: F401
    except ImportError:
        return False

    return True


@dataclass
class ReportExportContext:
    project_id: str
    project_name: str
    report: ReportData
    reporting_period: str = "Not specified"
    # Defaults to True (free-tier behavior) so a caller that doesn't
    # resolve the account's plan never accidentally ships an unwatermarked
    # PDF -- callers with plan context (the export API route) pass the
    # real value explicitly.
    show_watermark: bool = True
    # "Branded reports with your logo" (Professional+): the account's
    # uploaded logo bytes, or None to fall back to the default DataDumpAI
    # mark. Callers without plan context (or without an uploaded logo)
    # simply never set this.
    custom_logo_bytes: bytes | None = None

    @property
    def report_name(self) -> str:
        return self.report.title or self.report.report_type or "Report"

    @property
    def report_type(self) -> str:
        return self.report.report_type or self.report_name

    @property
    def report_text(self) -> str:
        return self.report.to_markdown()

    @property
    def source_documents(self) -> list[str] | None:
        return self.report.source_documents or None

    @property
    def metric_tables(self) -> list[dict[str, Any]] | None:
        return self.report.metrics.get("tables") or None

    @property
    def report_plan(self) -> dict[str, Any] | None:
        return self.report.metadata.get("report_plan") or None


class PremiumExportService:
    def __init__(self, base_service: ExportService | None = None) -> None:
        self._base = base_service or ExportService()

    def _slugify(self, report_name: str, suffix: str) -> str:
        slug = self._base._slugify(report_name)
        return f"{slug}_{suffix}"

    def export_executive_pdf(self, context: ReportExportContext) -> dict[str, Any]:
        if report_is_intelligence(context.report):
            data = build_premium_pdf(
                report_text=context.report_text,
                metadata=PremiumExportMetadata(
                    project_name=context.project_name,
                    report_name=context.report_name,
                    report_type=context.report_type,
                    reporting_period=context.reporting_period,
                    source_documents=context.source_documents,
                    pack_type="executive",
                    show_watermark=context.show_watermark,
                    metric_tables=context.metric_tables,
                    report_plan=context.report_plan,
                    custom_logo_bytes=context.custom_logo_bytes,
                ),
            )
            filename = f"{self._slugify(context.report_name, 'executive')}.pdf"
            return self._base._build_result(
                project_id=context.project_id,
                filename=filename,
                data=data,
                mime_type=self._base.MIME_TYPES["pdf"],
            )

        return self._base.export_pdf(
            project_id=context.project_id,
            report_name=context.report_name,
            report=context.report,
            workspace_name=context.project_name,
            period_name=context.reporting_period,
        )

    def export_board_pack_pdf(self, context: ReportExportContext) -> dict[str, Any]:
        if report_is_intelligence(context.report):
            data = build_premium_pdf(
                report_text=context.report_text,
                metadata=PremiumExportMetadata(
                    project_name=context.project_name,
                    report_name=context.report_name,
                    report_type=context.report_type,
                    reporting_period=context.reporting_period,
                    source_documents=context.source_documents,
                    pack_type="board_pack",
                    show_watermark=context.show_watermark,
                    metric_tables=context.metric_tables,
                    report_plan=context.report_plan,
                    custom_logo_bytes=context.custom_logo_bytes,
                ),
            )
            filename = f"{self._slugify(context.report_name, 'board_pack')}.pdf"
            return self._base._build_result(
                project_id=context.project_id,
                filename=filename,
                data=data,
                mime_type=self._base.MIME_TYPES["pdf"],
            )

        return self._base.export_pdf(
            project_id=context.project_id,
            report_name=context.report_name,
            report=context.report,
            workspace_name=context.project_name,
            period_name=context.reporting_period,
        )

    def export_presentation(self, context: ReportExportContext) -> dict[str, Any]:
        if not is_presentation_export_available():
            raise RuntimeError(
                "Presentation export requires python-pptx. "
                "Run: pip install python-pptx"
            )

        if report_is_intelligence(context.report):
            from services.premium_pptx_export import (
                PresentationExportMetadata,
                build_premium_presentation,
            )

            data = build_premium_presentation(
                report_text=context.report_text,
                metadata=PresentationExportMetadata(
                    project_name=context.project_name,
                    report_name=context.report_name,
                    source_documents=context.source_documents,
                    custom_logo_bytes=context.custom_logo_bytes,
                ),
            )
            filename = f"{self._slugify(context.report_name, 'presentation')}.pptx"
            return self._base._build_result(
                project_id=context.project_id,
                filename=filename,
                data=data,
                mime_type=(
                    "application/vnd.openxmlformats-officedocument"
                    ".presentationml.presentation"
                ),
            )

        return self._base.export_pptx(
            project_id=context.project_id,
            report_name=context.report_name,
            report=context.report,
            workspace_name=context.project_name,
            period_name=context.reporting_period,
        )

    def export_markdown(self, context: ReportExportContext) -> dict[str, Any]:
        return self._base.export_markdown(
            project_id=context.project_id,
            report_name=context.report_name,
            report=context.report,
        )

    def export_docx(self, context: ReportExportContext) -> dict[str, Any]:
        if report_is_intelligence(context.report):
            data = build_premium_docx(
                report_text=context.report_text,
                metadata=DocxExportMetadata(
                    project_name=context.project_name,
                    report_name=context.report_name,
                    report_type=context.report_type,
                    reporting_period=context.reporting_period,
                    source_documents=context.source_documents,
                    pack_type="executive",
                    custom_logo_bytes=context.custom_logo_bytes,
                ),
            )
            filename = f"{self._slugify(context.report_name, 'executive')}.docx"
            return self._base._build_result(
                project_id=context.project_id,
                filename=filename,
                data=data,
                mime_type=self._base.MIME_TYPES["docx"],
            )

        return self._base.export_docx(
            project_id=context.project_id,
            report_name=context.report_name,
            report=context.report,
            workspace_name=context.project_name,
            period_name=context.reporting_period,
        )
