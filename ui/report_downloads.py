"""
Premium download options for executive intelligence reports.
"""

from __future__ import annotations

import re

import streamlit as st

from services.premium_export_service import (
    PremiumExportService,
    ReportExportContext,
    is_presentation_export_available,
)
from services.plan_service import PlanService
from services.report_chart_data import is_intelligence_report
from ui.feedback import show_error
from ui.plan_upgrade import render_upgrade_prompt


def _plan_service() -> PlanService:
    return PlanService()


premium_export_service = PremiumExportService()


def _build_context(
    *,
    project_id: str,
    project_name: str,
    report_name: str,
    report_type: str,
    report_text: str,
    source_documents: list[str] | None,
) -> ReportExportContext:
    reporting_period = "Not specified"
    period_match = re.search(
        r"Reporting period\s*\|\s*([^|\n]+)",
        report_text,
        re.IGNORECASE,
    )

    if period_match:
        reporting_period = period_match.group(1).strip()

    return ReportExportContext(
        project_id=project_id,
        project_name=project_name,
        report_name=report_name,
        report_type=report_type,
        report_text=report_text,
        source_documents=source_documents,
        reporting_period=reporting_period,
    )


def render_premium_downloads(
    *,
    project_id: str,
    project_name: str,
    report_name: str,
    report_type: str,
    report_text: str,
    source_documents: list[str] | None = None,
    key_prefix: str = "report",
) -> None:
    """Render consulting-grade download options."""

    context = _build_context(
        project_id=project_id,
        project_name=project_name,
        report_name=report_name,
        report_type=report_type,
        report_text=report_text,
        source_documents=source_documents,
    )

    if is_intelligence_report(report_text) and _plan_service().can_use_professional_exports():
        st.markdown("#### Download")
        st.caption(
            "Choose a format designed for executives, board packs, or presentations."
        )

        try:
            executive_pdf = premium_export_service.export_executive_pdf(context)
            board_pdf = premium_export_service.export_board_pack_pdf(context)
            docx_export = premium_export_service.export_docx(context)
            markdown_export = premium_export_service.export_markdown(context)
            presentation = None

            if is_presentation_export_available():
                presentation = premium_export_service.export_presentation(context)
        except Exception as exc:
            show_error(exc)
            return

        if presentation:
            primary_col, board_col, deck_col = st.columns(3)
        else:
            primary_col, board_col = st.columns(2)
            deck_col = None

        with primary_col:
            st.download_button(
                "Executive Report",
                executive_pdf["data"],
                file_name=executive_pdf["filename"],
                mime=executive_pdf["mime_type"],
                use_container_width=True,
                key=f"{key_prefix}_download_executive_pdf",
                help="8–12 page CEO-ready PDF with cover, dashboard, and appendix.",
            )

        with board_col:
            st.download_button(
                "Board Pack",
                board_pdf["data"],
                file_name=board_pdf["filename"],
                mime=board_pdf["mime_type"],
                use_container_width=True,
                key=f"{key_prefix}_download_board_pdf",
                help="Full evidence, references, and supporting detail.",
            )

        if deck_col is not None and presentation:
            with deck_col:
                st.download_button(
                    "Presentation Deck",
                    presentation["data"],
                    file_name=presentation["filename"],
                    mime=presentation["mime_type"],
                    use_container_width=True,
                    key=f"{key_prefix}_download_pptx",
                    help="PowerPoint deck with dashboard, risks, and recommendations.",
                )
        elif not is_presentation_export_available():
            st.caption("Install `python-pptx` to enable Presentation Deck export.")

        secondary_col, word_col = st.columns(2)

        with secondary_col:
            st.download_button(
                "Markdown",
                markdown_export["data"],
                file_name=markdown_export["filename"],
                mime=markdown_export["mime_type"],
                use_container_width=True,
                key=f"{key_prefix}_download_md",
            )

        with word_col:
            st.download_button(
                "Word",
                docx_export["data"],
                file_name=docx_export["filename"],
                mime=docx_export["mime_type"],
                use_container_width=True,
                key=f"{key_prefix}_download_docx",
                help="Executive Word report with matching premium styling.",
            )

        return

    if not _plan_service().can_use_professional_exports():
        st.markdown("#### Download")
        st.caption("Free plan includes PDF with DataDumpAI branding.")
        render_upgrade_prompt("professional_exports")
        _render_branded_pdf_download(context, key_prefix=key_prefix)
        return

    _render_basic_downloads(context, key_prefix=key_prefix)


def _render_branded_pdf_download(
    context: ReportExportContext,
    *,
    key_prefix: str,
) -> None:
    try:
        pdf_export = premium_export_service._base.export_pdf(
            project_id=context.project_id,
            report_name=context.report_name,
            report_text=context.report_text,
        )
    except Exception as exc:
        show_error(exc)
        return

    st.download_button(
        "PDF (DataDumpAI branding)",
        pdf_export["data"],
        file_name=pdf_export["filename"],
        mime=pdf_export["mime_type"],
        use_container_width=True,
        key=f"{key_prefix}_download_branded_pdf",
        help="Includes DataDumpAI branding. Upgrade for Word, PowerPoint, and custom branding.",
    )


def _render_basic_downloads(context: ReportExportContext, *, key_prefix: str) -> None:
    try:
        pdf_export = premium_export_service._base.export_pdf(
            project_id=context.project_id,
            report_name=context.report_name,
            report_text=context.report_text,
        )
        docx_export = premium_export_service.export_docx(context)
        markdown_export = premium_export_service.export_markdown(context)
    except Exception as exc:
        show_error(exc)
        return

    col1, col2, col3 = st.columns(3)

    with col1:
        st.download_button(
            "PDF",
            pdf_export["data"],
            file_name=pdf_export["filename"],
            mime=pdf_export["mime_type"],
            use_container_width=True,
            key=f"{key_prefix}_download_pdf",
        )

    with col2:
        st.download_button(
            "Word",
            docx_export["data"],
            file_name=docx_export["filename"],
            mime=docx_export["mime_type"],
            use_container_width=True,
            key=f"{key_prefix}_download_docx",
        )

    with col3:
        st.download_button(
            "Markdown",
            markdown_export["data"],
            file_name=markdown_export["filename"],
            mime=markdown_export["mime_type"],
            use_container_width=True,
            key=f"{key_prefix}_download_md",
        )
