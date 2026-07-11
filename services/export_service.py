"""
DataDumpAI Enterprise
Export Service

Central entry point for all report export operations.
"""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.shared import Inches, Pt, RGBColor
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer

from services.export_chart_blocks import get_export_chart_images
from models.report_data import ReportData
from services.report_chart_data import prepare_report_for_output
from services.report_document import prepare_report_view, report_data_from_markdown
from services.report_markdown_renderer import (
    parse_markdown_blocks,
    strip_inline_markdown,
)
from storage.file_store import FileStore


class ExportService:
    """
    Handles report and project export operations.

    Every export format flows through this service so persistence,
    naming, and future format support stay in one place.
    """

    @staticmethod
    def _file_store() -> FileStore:
        return FileStore.for_current_user()

    MIME_TYPES = {
        "markdown": "text/markdown",
        "pdf": "application/pdf",
        "docx": (
            "application/vnd.openxmlformats-officedocument"
            ".wordprocessingml.document"
        ),
    }

    def get_exports(self, project_id: str) -> list[dict[str, Any]]:
        store = self._file_store()
        exports: list[dict[str, Any]] = []

        for filename in store.list_files(project_id, "exports"):
            suffix = Path(filename).suffix.lower().lstrip(".")

            if suffix == "md":
                mime_type = self.MIME_TYPES["markdown"]
            elif suffix == "pdf":
                mime_type = self.MIME_TYPES["pdf"]
            elif suffix == "docx":
                mime_type = self.MIME_TYPES["docx"]
            else:
                mime_type = "application/octet-stream"

            if store._backend == "local":
                storage_path = str(store._local_root(project_id) / "exports" / filename)
            else:
                storage_path = store._storage_key(project_id, "exports", filename)

            try:
                size = len(store.read_bytes(storage_path))
            except Exception:
                size = 0

            exports.append(
                {
                    "filename": filename,
                    "path": storage_path,
                    "size": size,
                    "mime_type": mime_type,
                    "format": suffix or "unknown",
                    "exported_at": datetime.now(timezone.utc).isoformat(),
                }
            )

        return exports

    def _slugify(self, report_name: str) -> str:
        slug = report_name.strip().replace(" ", "_").lower()

        for char in ('/', '\\', ':', '*', '?', '"', '<', '>', '|'):
            slug = slug.replace(char, "")

        return slug or "report"

    def _append_pdf_charts(self, story: list[Any], charts: list[tuple[str, bytes]], body_style: ParagraphStyle) -> None:
        story.append(Spacer(1, 0.12 * inch))

        for title, png_bytes in charts:
            story.append(Paragraph(f"<b>{title}</b>", body_style))
            story.append(
                Image(
                    BytesIO(png_bytes),
                    width=6.2 * inch,
                    height=2.6 * inch,
                    kind="proportional",
                )
            )
            story.append(Spacer(1, 0.15 * inch))

    def _append_docx_charts(self, document: Document, charts: list[tuple[str, bytes]]) -> None:
        for title, png_bytes in charts:
            heading = document.add_heading(title, level=3)
            for run in heading.runs:
                run.font.size = Pt(12)
                run.font.color.rgb = RGBColor(0x1D, 0x4E, 0xD8)

            paragraph = document.add_paragraph()
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.add_run().add_picture(BytesIO(png_bytes), width=Inches(6.2))

    def _prepend_pdf_charts(
        self,
        story: list[Any],
        chart_data: dict[str, Any],
        *,
        body_style: ParagraphStyle,
        heading_style: ParagraphStyle,
    ) -> None:
        chart_export = get_export_chart_images(chart_data)

        if not chart_export.images and not chart_export.unavailable_note:
            return

        story.append(Paragraph("Visual Analytics", heading_style))

        if chart_export.images:
            self._append_pdf_charts(story, chart_export.images, body_style)

        if chart_export.unavailable_note:
            story.append(Paragraph(chart_export.unavailable_note, body_style))

    def _prepend_docx_charts(self, document: Document, chart_data: dict[str, Any]) -> None:
        chart_export = get_export_chart_images(chart_data)

        if not chart_export.images and not chart_export.unavailable_note:
            return

        document.add_heading("Visual Analytics", level=2)

        if chart_export.images:
            self._append_docx_charts(document, chart_export.images)

        if chart_export.unavailable_note:
            paragraph = document.add_paragraph(chart_export.unavailable_note)
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in paragraph.runs:
                run.font.size = Pt(10)
                run.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)

    def _render_pdf_block(
        self,
        block: Any,
        *,
        story: list[Any],
        body_style: ParagraphStyle,
        heading_style: ParagraphStyle,
    ) -> None:
        if block.block_type == "heading":
            story.append(Paragraph(strip_inline_markdown(block.content), heading_style))
        elif block.block_type == "paragraph":
            safe = (
                strip_inline_markdown(block.content)
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            story.append(Paragraph(safe, body_style))
        elif block.block_type == "bullets":
            for item in block.items:
                safe = (
                    strip_inline_markdown(item)
                    .replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                )
                story.append(Paragraph(safe, body_style))
        elif block.block_type == "label_value":
            label = strip_inline_markdown(block.label)
            value = strip_inline_markdown(block.value)
            story.append(Paragraph(f"<b>{label}:</b> {value}", body_style))
        elif block.block_type == "spacer":
            story.append(Spacer(1, 0.08 * inch))

    def _render_docx_block(self, document: Document, block: Any) -> None:
        if block.block_type == "heading":
            document.add_heading(strip_inline_markdown(block.content), level=min(block.level, 4))
        elif block.block_type == "paragraph":
            paragraph = document.add_paragraph(strip_inline_markdown(block.content))
            paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
            paragraph.paragraph_format.line_spacing = 1.45
            paragraph.paragraph_format.space_before = Pt(6)
            paragraph.paragraph_format.space_after = Pt(10)
            for run in paragraph.runs:
                run.font.size = Pt(11)
                run.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)
        elif block.block_type == "bullets":
            for item in block.items:
                paragraph = document.add_paragraph(strip_inline_markdown(item), style="List Bullet")
                paragraph.paragraph_format.left_indent = Inches(0.35)
        elif block.block_type == "label_value":
            paragraph = document.add_paragraph()
            paragraph.add_run(f"{strip_inline_markdown(block.label)}: ").bold = True
            paragraph.add_run(strip_inline_markdown(block.value))

    def _build_result(
        self,
        *,
        project_id: str,
        filename: str,
        data: bytes,
        mime_type: str,
        report_name: str | None = None,
    ) -> dict[str, Any]:
        storage_path = self._file_store().write(project_id, "exports", filename, data)

        try:
            from core.auth import get_current_user_id
            from services.activity_service import ActivityService

            export_label = (report_name or filename).strip()
            export_format = Path(filename).suffix.lstrip(".").upper() or "FILE"
            ActivityService(get_current_user_id()).log(
                "export.downloaded",
                f"Downloaded {export_label} ({export_format})",
                metadata={"project_id": project_id, "filename": filename},
            )
        except Exception:
            pass

        return {
            "filename": filename,
            "path": storage_path,
            "data": data,
            "mime_type": mime_type,
            "size": len(data),
        }

    def _resolve_report(self, report: ReportData | str) -> ReportData:
        if isinstance(report, ReportData):
            return report
        return report_data_from_markdown(report)

    def _prepare_export(self, report: ReportData | str):
        return prepare_report_view(self._resolve_report(report))

    def _resolve_export_input(
        self,
        *,
        report: ReportData | str | None = None,
        report_text: str | None = None,
    ) -> ReportData | str:
        if report is not None:
            return report
        if report_text is not None:
            return report_text
        raise TypeError("export requires report or report_text")

    def export_markdown(
        self,
        *,
        project_id: str,
        report_name: str,
        report: ReportData | str | None = None,
        report_text: str | None = None,
    ) -> dict[str, Any]:
        """Export a report as Markdown."""

        filename = f"{self._slugify(report_name)}.md"
        data = self._prepare_export(
            self._resolve_export_input(report=report, report_text=report_text)
        ).text.encode("utf-8")

        return self._build_result(
            project_id=project_id,
            filename=filename,
            data=data,
            mime_type=self.MIME_TYPES["markdown"],
            report_name=report_name,
        )

    def export_pdf(
        self,
        *,
        project_id: str,
        report_name: str,
        report: ReportData | str | None = None,
        report_text: str | None = None,
    ) -> dict[str, Any]:
        """Export a report as PDF."""

        prepared = self._prepare_export(
            self._resolve_export_input(report=report, report_text=report_text)
        )
        report_text = prepared.text
        filename = f"{self._slugify(report_name)}.pdf"
        buffer = BytesIO()

        document = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=0.9 * inch,
            rightMargin=0.9 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )
        styles = getSampleStyleSheet()
        body_style = ParagraphStyle(
            "ExportBody",
            parent=styles["Normal"],
            fontSize=11,
            leading=16,
            alignment=TA_JUSTIFY,
            spaceBefore=6,
            spaceAfter=10,
        )
        heading_style = ParagraphStyle(
            "ExportHeading",
            parent=styles["Heading1"],
            fontSize=18,
            spaceBefore=6,
            spaceAfter=10,
        )
        story = []

        self._prepend_pdf_charts(
            story,
            prepared.chart_data,
            body_style=body_style,
            heading_style=heading_style,
        )

        for block in parse_markdown_blocks(report_text):
            self._render_pdf_block(
                block,
                story=story,
                body_style=body_style,
                heading_style=heading_style,
            )

        if not story:
            story.append(Paragraph(" ", body_style))

        document.build(story)
        data = buffer.getvalue()

        return self._build_result(
            project_id=project_id,
            filename=filename,
            data=data,
            mime_type=self.MIME_TYPES["pdf"],
            report_name=report_name,
        )

    def export_docx(
        self,
        *,
        project_id: str,
        report_name: str,
        report: ReportData | str | None = None,
        report_text: str | None = None,
    ) -> dict[str, Any]:
        """Export a report as Word (.docx)."""

        prepared = self._prepare_export(
            self._resolve_export_input(report=report, report_text=report_text)
        )
        report_text = prepared.text
        filename = f"{self._slugify(report_name)}.docx"
        buffer = BytesIO()

        document = Document()
        for section in document.sections:
            section.top_margin = Inches(0.75)
            section.bottom_margin = Inches(0.75)
            section.left_margin = Inches(0.9)
            section.right_margin = Inches(0.9)

        document.add_heading(strip_inline_markdown(report_name), level=1)

        self._prepend_docx_charts(document, prepared.chart_data)

        for block in parse_markdown_blocks(report_text):
            self._render_docx_block(document, block)

        document.save(buffer)
        data = buffer.getvalue()

        return self._build_result(
            project_id=project_id,
            filename=filename,
            data=data,
            mime_type=self.MIME_TYPES["docx"],
            report_name=report_name,
        )
