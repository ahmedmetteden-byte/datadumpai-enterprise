"""
McKinsey-grade PDF export for DataDumpAI executive intelligence reports.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from config import APP_NAME
from services.export_chart_blocks import get_export_chart_images
from services.report_document_parser import (
    ParsedIntelligenceReport,
    ai_insight_bullets,
    dashboard_metrics,
    estimated_reading_minutes,
    first_ai_insight,
    parse_intelligence_report,
    strategic_recommendation,
    table_of_contents,
    top_opportunities,
    top_risks,
)
from services.report_markdown_renderer import (
    MarkdownBlock,
    escape_xml,
    format_bullet_item,
    group_blocks_for_keep_together,
    highlight_value_html,
    inline_to_reportlab_html,
    parse_markdown_blocks,
    strip_inline_markdown,
)

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
LOGO_CANDIDATES = (
    ASSETS_DIR / "logo.png",
    ASSETS_DIR / "datadump-hero-logo.png",
    ASSETS_DIR / "datadump-sidebar-word.png",
)
WINDOWS_FONTS = Path("C:/Windows/Fonts")

COLOR_BLUE = colors.HexColor("#1D4ED8")
COLOR_GREEN = colors.HexColor("#059669")
COLOR_AMBER = colors.HexColor("#D97706")
COLOR_RED = colors.HexColor("#DC2626")
COLOR_SLATE = colors.HexColor("#0F172A")
COLOR_MUTED = colors.HexColor("#64748B")
COLOR_LINE = colors.HexColor("#E2E8F0")
COLOR_PANEL = colors.HexColor("#F8FAFC")
COLOR_CALLOUT = colors.HexColor("#EFF6FF")

MARGIN_LEFT = 0.9 * inch
MARGIN_RIGHT = 0.9 * inch
MARGIN_TOP = 0.75 * inch
MARGIN_BOTTOM = 0.75 * inch

BODY_SIZE = 11
BODY_LEADING = round(BODY_SIZE * 1.45)


def _register_fonts() -> tuple[str, str, str]:
    body_font = "Helvetica"
    heading_font = "Helvetica-Bold"
    quote_font = "Helvetica-Oblique"

    if sys.platform == "win32":
        try:
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont

            font_map = {
                "Calibri": WINDOWS_FONTS / "calibri.ttf",
                "Calibri-Bold": WINDOWS_FONTS / "calibrib.ttf",
                "Calibri-Italic": WINDOWS_FONTS / "calibrii.ttf",
            }

            for name, path in font_map.items():
                if path.is_file():
                    pdfmetrics.registerFont(TTFont(name, str(path)))

            if (WINDOWS_FONTS / "calibri.ttf").is_file():
                body_font = "Calibri"
                quote_font = "Calibri-Italic"

            if (WINDOWS_FONTS / "calibrib.ttf").is_file():
                heading_font = "Calibri-Bold"
        except Exception:
            pass

    return body_font, heading_font, quote_font


BODY_FONT, HEADING_FONT, QUOTE_FONT = _register_fonts()


@dataclass
class PremiumExportMetadata:
    project_name: str
    report_name: str
    report_type: str = "Executive Intelligence Report"
    reporting_period: str = "Not specified"
    source_documents: list[str] | None = None
    pack_type: str = "executive"


class PremiumPDFBuilder:
    """Build consulting-style PDF documents."""

    def __init__(self, metadata: PremiumExportMetadata) -> None:
        self.metadata = metadata
        self.page_count = 0
        self.styles = self._build_styles()

    def _build_styles(self) -> dict[str, ParagraphStyle]:
        base = getSampleStyleSheet()

        return {
            "cover_title": ParagraphStyle(
                "CoverTitle",
                parent=base["Title"],
                fontName=HEADING_FONT,
                fontSize=28,
                leading=32,
                textColor=COLOR_SLATE,
                alignment=TA_CENTER,
                spaceAfter=14,
            ),
            "cover_subtitle": ParagraphStyle(
                "CoverSubtitle",
                parent=base["Normal"],
                fontName=BODY_FONT,
                fontSize=16,
                leading=22,
                textColor=COLOR_BLUE,
                alignment=TA_CENTER,
                spaceAfter=28,
            ),
            "cover_meta_label": ParagraphStyle(
                "CoverMetaLabel",
                parent=base["Normal"],
                fontName=BODY_FONT,
                fontSize=10,
                textColor=COLOR_MUTED,
                alignment=TA_CENTER,
                spaceBefore=8,
            ),
            "cover_meta_value": ParagraphStyle(
                "CoverMetaValue",
                parent=base["Normal"],
                fontName=HEADING_FONT,
                fontSize=13,
                textColor=COLOR_SLATE,
                alignment=TA_CENTER,
            ),
            "section_heading": ParagraphStyle(
                "SectionHeading",
                parent=base["Heading1"],
                fontName=HEADING_FONT,
                fontSize=24,
                leading=28,
                textColor=COLOR_BLUE,
                spaceBefore=6,
                spaceAfter=10,
            ),
            "subheading": ParagraphStyle(
                "Subheading",
                parent=base["Heading2"],
                fontName=HEADING_FONT,
                fontSize=18,
                leading=22,
                textColor=COLOR_SLATE,
                spaceBefore=6,
                spaceAfter=10,
            ),
            "h3": ParagraphStyle(
                "Heading3",
                parent=base["Heading3"],
                fontName=HEADING_FONT,
                fontSize=15,
                leading=19,
                textColor=COLOR_SLATE,
                spaceBefore=6,
                spaceAfter=10,
            ),
            "h4": ParagraphStyle(
                "Heading4",
                parent=base["Heading4"],
                fontName=HEADING_FONT,
                fontSize=13,
                leading=17,
                textColor=COLOR_SLATE,
                spaceBefore=6,
                spaceAfter=10,
            ),
            "body": ParagraphStyle(
                "Body",
                parent=base["Normal"],
                fontName=BODY_FONT,
                fontSize=BODY_SIZE,
                leading=BODY_LEADING,
                textColor=COLOR_SLATE,
                alignment=TA_JUSTIFY,
                spaceBefore=6,
                spaceAfter=10,
            ),
            "label": ParagraphStyle(
                "Label",
                parent=base["Normal"],
                fontName=HEADING_FONT,
                fontSize=BODY_SIZE,
                leading=BODY_LEADING,
                textColor=COLOR_SLATE,
                spaceBefore=8,
                spaceAfter=4,
            ),
            "bullet": ParagraphStyle(
                "Bullet",
                parent=base["Normal"],
                fontName=BODY_FONT,
                fontSize=BODY_SIZE,
                leading=BODY_LEADING,
                textColor=COLOR_SLATE,
                leftIndent=18,
                bulletIndent=8,
                spaceBefore=2,
                spaceAfter=4,
            ),
            "caption": ParagraphStyle(
                "Caption",
                parent=base["Normal"],
                fontName=BODY_FONT,
                fontSize=10,
                leading=14,
                textColor=COLOR_MUTED,
            ),
            "quote": ParagraphStyle(
                "Quote",
                parent=base["Normal"],
                fontName=QUOTE_FONT,
                fontSize=12,
                leading=17,
                textColor=COLOR_SLATE,
                leftIndent=18,
                rightIndent=18,
                spaceBefore=8,
                spaceAfter=10,
            ),
            "toc_item": ParagraphStyle(
                "TocItem",
                parent=base["Normal"],
                fontName=BODY_FONT,
                fontSize=11,
                leading=18,
                textColor=COLOR_SLATE,
            ),
            "callout_title": ParagraphStyle(
                "CalloutTitle",
                parent=base["Normal"],
                fontName=HEADING_FONT,
                fontSize=12,
                leading=16,
                textColor=COLOR_BLUE,
                spaceAfter=6,
            ),
            "callout_body": ParagraphStyle(
                "CalloutBody",
                parent=base["Normal"],
                fontName=BODY_FONT,
                fontSize=BODY_SIZE,
                leading=BODY_LEADING,
                textColor=COLOR_SLATE,
                alignment=TA_JUSTIFY,
                spaceAfter=6,
            ),
        }

    def _logo_path(self) -> Path | None:
        for candidate in LOGO_CANDIDATES:
            if candidate.is_file():
                return candidate

        return None

    def _draw_page_decorations(self, canvas_obj, doc) -> None:
        canvas_obj.saveState()
        width, height = letter

        canvas_obj.setFillColor(colors.Color(0.92, 0.94, 0.97, alpha=0.35))
        canvas_obj.setFont(HEADING_FONT, 46)
        canvas_obj.translate(width / 2, height / 2)
        canvas_obj.rotate(35)
        canvas_obj.drawCentredString(0, 0, APP_NAME)
        canvas_obj.restoreState()

        if getattr(doc, "page", 1) <= 1:
            return

        canvas_obj.saveState()
        canvas_obj.setStrokeColor(COLOR_LINE)
        canvas_obj.line(MARGIN_LEFT, height - 0.55 * inch, width - MARGIN_RIGHT, height - 0.55 * inch)
        canvas_obj.setFont(HEADING_FONT, 9)
        canvas_obj.setFillColor(COLOR_BLUE)
        canvas_obj.drawString(MARGIN_LEFT, height - 0.45 * inch, APP_NAME)
        canvas_obj.setFont(BODY_FONT, 9)
        canvas_obj.setFillColor(COLOR_MUTED)
        canvas_obj.drawRightString(
            width - MARGIN_RIGHT,
            height - 0.45 * inch,
            "Executive Intelligence Report",
        )

        canvas_obj.setStrokeColor(COLOR_LINE)
        canvas_obj.line(MARGIN_LEFT, 0.65 * inch, width - MARGIN_RIGHT, 0.65 * inch)
        canvas_obj.setFont(BODY_FONT, 8)
        canvas_obj.setFillColor(COLOR_MUTED)
        canvas_obj.drawString(MARGIN_LEFT, 0.45 * inch, "Confidential · Generated by DataDumpAI")
        canvas_obj.drawRightString(
            width - MARGIN_RIGHT,
            0.45 * inch,
            f"Page {doc.page}",
        )
        canvas_obj.restoreState()

    def _cover_page(self) -> list[Any]:
        story: list[Any] = []
        story.append(Spacer(1, 1.2 * inch))

        logo = self._logo_path()

        if logo:
            story.append(Image(str(logo), width=1.6 * inch, height=1.6 * inch, kind="proportional"))
            story.append(Spacer(1, 0.45 * inch))

        story.append(Paragraph("Executive Intelligence Report", self.styles["cover_subtitle"]))
        story.append(Spacer(1, 0.35 * inch))
        story.append(Paragraph("Prepared by", self.styles["cover_meta_label"]))
        story.append(Paragraph(APP_NAME, self.styles["cover_meta_value"]))
        story.append(Spacer(1, 0.45 * inch))

        meta_rows = [
            ("Project", self.metadata.project_name),
            ("Reporting Period", self.metadata.reporting_period),
            ("Generated", datetime.now(timezone.utc).strftime("%d %B %Y")),
        ]

        for label, value in meta_rows:
            story.append(Paragraph(label, self.styles["cover_meta_label"]))
            story.append(Paragraph(value, self.styles["cover_meta_value"]))

        story.append(Spacer(1, 0.8 * inch))
        story.append(Paragraph(self.metadata.report_name, self.styles["cover_meta_value"]))
        story.append(PageBreak())

        return story

    def _executive_summary_page(self, parsed: ParsedIntelligenceReport) -> list[Any]:
        metrics = dashboard_metrics(parsed)
        story: list[Any] = []

        story.append(Paragraph("Executive Summary", self.styles["section_heading"]))
        story.append(Spacer(1, 0.15 * inch))

        health_score = metrics.get("health_score", "—")
        outlook = metrics.get("outlook", "—")
        recommendation = strategic_recommendation(parsed) or metrics.get("priority", "—")

        summary_rows = [
            [
                Paragraph("<b>Overall Health</b>", self.styles["label"]),
                Paragraph(
                    f"<font color='#059669' size='14'><b>🟢 {escape_xml(str(health_score))}/100</b></font>",
                    self.styles["body"],
                ),
            ],
            [
                Paragraph("<b>Overall Outlook</b>", self.styles["label"]),
                Paragraph(escape_xml(str(outlook)), self.styles["body"]),
            ],
        ]

        summary_table = Table(summary_rows, colWidths=[1.8 * inch, 4.5 * inch])
        summary_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(summary_table)
        story.append(Spacer(1, 0.12 * inch))
        story.extend(self._chart_story_elements(parsed.chart_data))

        story.append(Paragraph("Top Risks", self.styles["subheading"]))
        risks = top_risks(parsed)

        if risks:
            for card in risks[:5]:
                story.append(
                    Paragraph(
                        f"• {escape_xml(card['title'])}",
                        self.styles["bullet"],
                    )
                )
        else:
            story.append(Paragraph("No critical risks identified.", self.styles["body"]))

        story.append(Spacer(1, 0.1 * inch))
        story.append(Paragraph("Top Opportunities", self.styles["subheading"]))
        opportunities = top_opportunities(parsed)

        if opportunities:
            for item in opportunities[:5]:
                story.append(
                    Paragraph(
                        format_bullet_item(strip_inline_markdown(item)),
                        self.styles["bullet"],
                    )
                )
        else:
            story.append(Paragraph("See Key Opportunities in the dashboard section.", self.styles["body"]))

        story.append(Spacer(1, 0.1 * inch))
        story.append(Paragraph("Strategic Recommendation", self.styles["subheading"]))
        story.append(Paragraph(escape_xml(recommendation), self.styles["body"]))
        story.append(PageBreak())

        return story

    def _modern_table_style(self, *, header: bool = True) -> TableStyle:
        commands: list[tuple[Any, ...]] = [
            ("BOX", (0, 0), (-1, -1), 0.75, COLOR_LINE),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, COLOR_LINE),
            ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [colors.white, COLOR_PANEL]),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("FONTSIZE", (0, 0), (-1, -1), 11),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]

        if header:
            commands.extend(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), COLOR_BLUE),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), HEADING_FONT),
                ]
            )

        return TableStyle(commands)

    def _at_a_glance_page(self, parsed: ParsedIntelligenceReport, report_text: str) -> list[Any]:
        metrics = dashboard_metrics(parsed)
        story: list[Any] = []

        story.append(Paragraph("At a Glance", self.styles["section_heading"]))
        story.append(Spacer(1, 0.1 * inch))

        glance_rows = [
            ["Overall Status", metrics.get("outlook", "—")],
            ["Health Score", f"{metrics.get('health_score', '—')}/100"],
            ["Confidence", metrics.get("confidence", "—")],
            ["Documents", metrics.get("documents", "—")],
            ["Critical Risks", metrics.get("key_risks", "—")],
            ["Top Recommendation", metrics.get("priority", "—")],
            ["Estimated Reading Time", f"{estimated_reading_minutes(report_text)} minutes"],
            ["AI Insight", first_ai_insight(parsed) or "See AI Insights section."],
        ]

        table = Table(glance_rows, colWidths=[2.0 * inch, 4.3 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), COLOR_BLUE),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), HEADING_FONT),
                    ("FONTNAME", (0, 1), (0, -1), HEADING_FONT),
                    ("FONTNAME", (1, 1), (1, -1), BODY_FONT),
                    ("FONTSIZE", (0, 0), (-1, -1), 11),
                    ("TEXTCOLOR", (0, 1), (0, -1), COLOR_MUTED),
                    ("TEXTCOLOR", (1, 1), (1, -1), COLOR_SLATE),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_PANEL]),
                    ("BOX", (0, 0), (-1, -1), 0.75, COLOR_LINE),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, COLOR_LINE),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )

        story.append(table)
        story.append(PageBreak())

        return story

    def _table_of_contents(self, parsed: ParsedIntelligenceReport) -> list[Any]:
        story: list[Any] = []
        story.append(Paragraph("Table of Contents", self.styles["section_heading"]))

        entries = table_of_contents(
            parsed.sections,
            include_appendix=bool(parsed.appendix_sections),
        )

        for index, entry in enumerate(entries, start=1):
            story.append(Paragraph(f"{index}&nbsp;&nbsp;{escape_xml(entry)}", self.styles["toc_item"]))

        story.append(PageBreak())
        return story

    def _callout_box(self, title: str, body_elements: list[Any]) -> Table:
        rows: list[list[Any]] = [
            [Paragraph(f"💡 {escape_xml(title)}", self.styles["callout_title"])],
        ]

        for element in body_elements:
            rows.append([element])

        table = Table(rows, colWidths=[6.3 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), COLOR_CALLOUT),
                    ("BOX", (0, 0), (-1, -1), 0.75, COLOR_BLUE),
                    ("LEFTPADDING", (0, 0), (-1, -1), 14),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )

        return table

    def _render_block(self, block: MarkdownBlock) -> list[Any]:
        story: list[Any] = []

        if block.block_type == "spacer":
            story.append(Spacer(1, 0.08 * inch))
            return story

        if block.block_type == "heading":
            style_map = {
                3: self.styles["h3"],
                4: self.styles["h4"],
                5: self.styles["h4"],
            }
            style = style_map.get(block.level, self.styles["subheading"])
            story.append(Paragraph(escape_xml(block.content), style))
            return story

        if block.block_type == "label_value":
            story.append(
                Paragraph(
                    highlight_value_html(block.label, block.value),
                    self.styles["body"],
                )
            )
            return story

        if block.block_type == "bullets":
            for item in block.items:
                story.append(
                    Paragraph(
                        inline_to_reportlab_html(item),
                        self.styles["bullet"],
                    )
                )
            story.append(Spacer(1, 0.04 * inch))
            return story

        if block.block_type == "quote":
            story.append(Paragraph(f"“{escape_xml(block.content)}”", self.styles["quote"]))
            return story

        if block.block_type == "table" and block.rows:
            col_count = max(len(row) for row in block.rows)
            col_width = 6.3 * inch / max(col_count, 1)
            table = Table(block.rows, colWidths=[col_width] * col_count)
            table.setStyle(self._modern_table_style(header=True))
            story.append(table)
            story.append(Spacer(1, 0.12 * inch))
            return story

        if block.block_type == "paragraph" and block.content:
            story.append(
                Paragraph(
                    inline_to_reportlab_html(block.content),
                    self.styles["body"],
                )
            )

        return story

    def _markdown_paragraphs(
        self,
        text: str,
        *,
        callout: bool = False,
        callout_title: str = "AI Insight",
    ) -> list[Any]:
        blocks = parse_markdown_blocks(text)
        story: list[Any] = []

        if callout and blocks:
            callout_elements: list[Any] = []

            for block in blocks:
                if block.block_type == "bullets":
                    for item in block.items:
                        callout_elements.append(
                            Paragraph(
                                inline_to_reportlab_html(item),
                                self.styles["callout_body"],
                            )
                        )
                elif block.block_type == "paragraph":
                    callout_elements.append(
                        Paragraph(
                            inline_to_reportlab_html(block.content),
                            self.styles["callout_body"],
                        )
                    )

            if callout_elements:
                story.append(self._callout_box(callout_title, callout_elements))
                story.append(Spacer(1, 0.12 * inch))

            return story

        groups = group_blocks_for_keep_together(blocks)

        for group in groups:
            group_story: list[Any] = []

            for block in group:
                group_story.extend(self._render_block(block))

            if group_story:
                story.append(KeepTogether(group_story))

        return story

    def _dashboard_content(self, parsed: ParsedIntelligenceReport) -> list[Any]:
        story: list[Any] = []
        story.extend(self._metric_cards(parsed))

        risk_table = self._risk_card_table(parsed)

        if risk_table:
            story.append(Paragraph("Top Risks", self.styles["subheading"]))
            story.append(risk_table)
            story.append(Spacer(1, 0.15 * inch))

        return story

    def _metric_cards(self, parsed: ParsedIntelligenceReport) -> list[Any]:
        metrics = dashboard_metrics(parsed)
        story: list[Any] = []

        cards = [
            ("Health Score", f"{metrics.get('health_score', '—')}/100"),
            ("Overall Outlook", metrics.get("outlook", "—")),
            ("Confidence", metrics.get("confidence", "—")),
            ("Documents", metrics.get("documents", "—")),
            ("Key Risks", metrics.get("key_risks", "—")),
            ("Recommendations", metrics.get("recommendations", "—")),
        ]

        rows = [cards[index : index + 3] for index in range(0, len(cards), 3)]
        formatted_rows = []

        for row in rows:
            formatted_rows.append(
                [
                    Paragraph(
                        f"<b>{escape_xml(label)}</b><br/>"
                        f"<font size='12' color='#0F172A'>{escape_xml(str(value))}</font>",
                        self.styles["caption"],
                    )
                    for label, value in row
                ]
            )

        table = Table(formatted_rows, colWidths=[2.1 * inch, 2.1 * inch, 2.1 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.5, COLOR_LINE),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, COLOR_LINE),
                    ("BACKGROUND", (0, 0), (-1, -1), COLOR_PANEL),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )

        story.append(table)
        story.append(Spacer(1, 0.2 * inch))

        return story

    def _chart_story_elements(self, chart_data: dict[str, Any]) -> list[Any]:
        chart_export = get_export_chart_images(chart_data)

        if not chart_export.images and not chart_export.unavailable_note:
            return []

        story: list[Any] = []

        for title, png_bytes in chart_export.images:
            story.append(Paragraph(escape_xml(title), self.styles["subheading"]))
            story.append(
                Image(
                    BytesIO(png_bytes),
                    width=6.6 * inch,
                    height=2.7 * inch,
                    kind="proportional",
                )
            )
            story.append(Spacer(1, 0.12 * inch))

        if chart_export.unavailable_note:
            story.append(
                Paragraph(
                    escape_xml(chart_export.unavailable_note),
                    self.styles["caption"],
                )
            )
            story.append(Spacer(1, 0.12 * inch))

        return story

    def _risk_card_table(self, parsed: ParsedIntelligenceReport) -> Table | None:
        cards = top_risks(parsed)

        if not cards:
            return None

        rows = [
            [
                Paragraph(
                    f"<b>{escape_xml(card['title'])}</b><br/>{escape_xml(card['detail'])}",
                    self.styles["caption"],
                ),
                Paragraph(card["severity"], self.styles["caption"]),
            ]
            for card in cards[:6]
        ]

        table = Table(rows, colWidths=[4.8 * inch, 1.3 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.75, COLOR_LINE),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, COLOR_LINE),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                    ("BACKGROUND", (1, 0), (1, -1), COLOR_PANEL),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )

        return table

    def _section_story(
        self,
        parsed: ParsedIntelligenceReport,
        *,
        include_evidence: bool,
    ) -> list[Any]:
        story: list[Any] = []

        for section in parsed.sections:
            if section.title == "Introduction":
                continue

            section_block: list[Any] = [
                Paragraph(escape_xml(section.title), self.styles["section_heading"]),
            ]

            if "dashboard" in section.title.lower():
                section_block.extend(self._dashboard_content(parsed))
                story.append(KeepTogether(section_block))
                continue

            body = section.body

            if not include_evidence and "Key Findings" in section.title:
                body = re.sub(r"\*\*Evidence:\*\*[\s\S]*?(?=\n\*\*|\n#### |\n### |\Z)", "", body)

            is_ai_insights = section.title.lower() == "ai insights"

            if is_ai_insights:
                bullets = ai_insight_bullets(parsed)

                if bullets:
                    callout_elements = [
                        Paragraph(
                            inline_to_reportlab_html(format_bullet_item(strip_inline_markdown(item))),
                            self.styles["callout_body"],
                        )
                        for item in bullets
                    ]
                    section_block.append(self._callout_box("AI Insight", callout_elements))
                else:
                    section_block.extend(
                        self._markdown_paragraphs(body, callout=True, callout_title="AI Insight"),
                    )
            else:
                section_block.extend(self._markdown_paragraphs(body))

            story.append(KeepTogether(section_block))

        return story

    def _appendix_story(self, parsed: ParsedIntelligenceReport) -> list[Any]:
        if not parsed.appendix_sections:
            return []

        story: list[Any] = [PageBreak(), Paragraph("Appendix", self.styles["section_heading"])]

        for section in parsed.appendix_sections:
            appendix_block = [
                Paragraph(escape_xml(section.title), self.styles["subheading"]),
                *self._markdown_paragraphs(section.body),
            ]
            story.append(KeepTogether(appendix_block))

        return story

    def build(self, report_text: str) -> bytes:
        parsed = parse_intelligence_report(
            report_text,
            source_documents=self.metadata.source_documents,
            pack_type=self.metadata.pack_type,
        )

        if not parsed.snapshot.get("Reporting period"):
            period_match = re.search(
                r"Reporting period\s*\|\s*([^|\n]+)",
                report_text,
                re.IGNORECASE,
            )

            if period_match:
                self.metadata.reporting_period = period_match.group(1).strip()

        buffer = BytesIO()
        doc = BaseDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=MARGIN_LEFT,
            rightMargin=MARGIN_RIGHT,
            topMargin=MARGIN_TOP,
            bottomMargin=MARGIN_BOTTOM,
        )

        frame = Frame(
            doc.leftMargin,
            doc.bottomMargin,
            doc.width,
            doc.height,
            id="normal",
        )

        template = PageTemplate(
            id="main",
            frames=[frame],
            onPage=self._draw_page_decorations,
        )
        doc.addPageTemplates([template])

        include_evidence = self.metadata.pack_type == "board_pack"
        story: list[Any] = []
        story.extend(self._cover_page())
        story.extend(self._executive_summary_page(parsed))
        story.extend(self._at_a_glance_page(parsed, report_text))
        story.extend(self._table_of_contents(parsed))
        story.extend(
            self._section_story(parsed, include_evidence=include_evidence),
        )
        story.extend(self._appendix_story(parsed))

        doc.build(story)
        return buffer.getvalue()


def build_premium_pdf(
    *,
    report_text: str,
    metadata: PremiumExportMetadata,
) -> bytes:
    return PremiumPDFBuilder(metadata).build(report_text)
