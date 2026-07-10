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
from services.report_chart_data import is_intelligence_report


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
    report_name: str
    report_type: str
    report_text: str
    source_documents: list[str] | None = None
    reporting_period: str = "Not specified"


class PremiumExportService:
    def __init__(self, base_service: ExportService | None = None) -> None:
        self._base = base_service or ExportService()

    def _slugify(self, report_name: str, suffix: str) -> str:
        slug = self._base._slugify(report_name)
        return f"{slug}_{suffix}"

    def export_executive_pdf(self, context: ReportExportContext) -> dict[str, Any]:
        if is_intelligence_report(context.report_text):
            data = build_premium_pdf(
                report_text=context.report_text,
                metadata=PremiumExportMetadata(
                    project_name=context.project_name,
                    report_name=context.report_name,
                    report_type=context.report_type,
                    reporting_period=context.reporting_period,
                    source_documents=context.source_documents,
                    pack_type="executive",
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
            report_name=f"{context.report_name} Executive",
            report_text=context.report_text,
        )

    def export_board_pack_pdf(self, context: ReportExportContext) -> dict[str, Any]:
        if is_intelligence_report(context.report_text):
            data = build_premium_pdf(
                report_text=context.report_text,
                metadata=PremiumExportMetadata(
                    project_name=context.project_name,
                    report_name=context.report_name,
                    report_type=context.report_type,
                    reporting_period=context.reporting_period,
                    source_documents=context.source_documents,
                    pack_type="board_pack",
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
            report_name=f"{context.report_name} Board Pack",
            report_text=context.report_text,
        )

    def export_presentation(self, context: ReportExportContext) -> dict[str, Any]:
        if not is_presentation_export_available():
            raise RuntimeError(
                "Presentation export requires python-pptx. "
                "Run: pip install python-pptx"
            )

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

    def export_markdown(self, context: ReportExportContext) -> dict[str, Any]:
        return self._base.export_markdown(
            project_id=context.project_id,
            report_name=context.report_name,
            report_text=context.report_text,
        )

    def export_docx(self, context: ReportExportContext) -> dict[str, Any]:
        if is_intelligence_report(context.report_text):
            data = build_premium_docx(
                report_text=context.report_text,
                metadata=DocxExportMetadata(
                    project_name=context.project_name,
                    report_name=context.report_name,
                    report_type=context.report_type,
                    reporting_period=context.reporting_period,
                    source_documents=context.source_documents,
                    pack_type="executive",
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
            report_text=context.report_text,
        )
