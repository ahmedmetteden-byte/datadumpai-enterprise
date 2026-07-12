"""
Premium download options for executive intelligence reports.
"""

from __future__ import annotations

import re

import streamlit as st

from models.report_data import ReportData
from services.premium_export_service import (
    PremiumExportService,
    ReportExportContext,
    is_presentation_export_available,
)
from services.plan_service import PlanService
from services.report_document import report_is_intelligence
from ui.feedback import show_error
from ui.plan_upgrade import render_upgrade_prompt


def _plan_service() -> PlanService:
    return PlanService()


premium_export_service = PremiumExportService()


def _build_context(
    *,
    project_id: str,
    project_name: str,
    report: ReportData,
) -> ReportExportContext:
    reporting_period = "Not specified"
    period_match = re.search(
        r"Reporting period\s*\|\s*([^|\n]+)",
        report.narrative,
        re.IGNORECASE,
    )

    if period_match:
        reporting_period = period_match.group(1).strip()

    return ReportExportContext(
        project_id=project_id,
        project_name=project_name,
        report=report,
        reporting_period=reporting_period,
    )


def render_premium_downloads(
    *,
    project_id: str,
    project_name: str,
    report: ReportData,
    key_prefix: str = "report",
) -> None:
    """Render consulting-grade download options."""

    context = _build_context(
        project_id=project_id,
        project_name=project_name,
        report=report,
    )

    if report_is_intelligence(report) and _plan_service().can_use_professional_exports():
        st.markdown("#### Download")
        st.caption("Each option downloads a specific file format.")

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

        st.markdown('<div class="dde-download-grid">', unsafe_allow_html=True)

        primary_col, board_col = st.columns(2)

        with primary_col:
            st.download_button(
                "⬇ Download PDF",
                executive_pdf["data"],
                file_name=executive_pdf["filename"],
                mime=executive_pdf["mime_type"],
                use_container_width=True,
                key=f"{key_prefix}_download_executive_pdf",
                help="8–12 page CEO-ready PDF with cover, dashboard, and appendix.",
            )

        with board_col:
            st.download_button(
                "⬇ Download Board Pack (PDF)",
                board_pdf["data"],
                file_name=board_pdf["filename"],
                mime=board_pdf["mime_type"],
                use_container_width=True,
                key=f"{key_prefix}_download_board_pdf",
                help="Full evidence, references, and supporting detail.",
            )

        word_col, markdown_col = st.columns(2)

        with word_col:
            st.download_button(
                "⬇ Download Word (.docx)",
                docx_export["data"],
                file_name=docx_export["filename"],
                mime=docx_export["mime_type"],
                use_container_width=True,
                key=f"{key_prefix}_download_docx",
                help="Executive Word report with matching premium styling.",
            )

        with markdown_col:
            st.download_button(
                "⬇ Download Markdown (.md)",
                markdown_export["data"],
                file_name=markdown_export["filename"],
                mime=markdown_export["mime_type"],
                use_container_width=True,
                key=f"{key_prefix}_download_md",
            )

        if presentation:
            _, deck_col, _ = st.columns([1, 2, 1])
            with deck_col:
                st.download_button(
                    "⬇ Download Presentation (.pptx)",
                    presentation["data"],
                    file_name=presentation["filename"],
                    mime=presentation["mime_type"],
                    use_container_width=True,
                    key=f"{key_prefix}_download_pptx",
                    help="PowerPoint deck with dashboard, risks, and recommendations.",
                )
        elif not is_presentation_export_available():
            st.caption("Install `python-pptx` to enable Presentation export.")

        st.markdown("</div>", unsafe_allow_html=True)
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
            report=context.report,
        )
    except Exception as exc:
        show_error(exc)
        return

    st.download_button(
        "⬇ Download PDF",
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
            report=context.report,
        )
        docx_export = premium_export_service.export_docx(context)
        markdown_export = premium_export_service.export_markdown(context)
    except Exception as exc:
        show_error(exc)
        return

    st.markdown("#### Download")
    st.caption("Each option downloads a specific file format.")
    st.markdown('<div class="dde-download-grid">', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.download_button(
            "⬇ Download PDF",
            pdf_export["data"],
            file_name=pdf_export["filename"],
            mime=pdf_export["mime_type"],
            use_container_width=True,
            key=f"{key_prefix}_download_pdf",
        )

    with col2:
        st.download_button(
            "⬇ Download Word (.docx)",
            docx_export["data"],
            file_name=docx_export["filename"],
            mime=docx_export["mime_type"],
            use_container_width=True,
            key=f"{key_prefix}_download_docx",
        )

    with col3:
        st.download_button(
            "⬇ Download Markdown (.md)",
            markdown_export["data"],
            file_name=markdown_export["filename"],
            mime=markdown_export["mime_type"],
            use_container_width=True,
            key=f"{key_prefix}_download_md",
        )

    st.markdown("</div>", unsafe_allow_html=True)
