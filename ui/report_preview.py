"""
Floating preview for a generated report before it is saved.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from application.report_pipeline import ReportPipeline
from core.workspace_navigation import set_workspace_section
from models.report_data import ReportData
from models.report_processing_mode import ReportProcessingMode
from services.executive_report_context import ExecutiveReportContextBuilder
from ui.feedback import loading, show_error, show_success
from ui.report_downloads import render_premium_downloads
from ui.report_renderer import render_report_content


def _report_pipeline() -> ReportPipeline:
    return ReportPipeline()


context_builder = ExecutiveReportContextBuilder()

DRAFT_REPORT_KEY = "draft_report"


def set_draft_report(
    *,
    report: ReportData,
    source_documents: list[str],
    workspace: dict[str, Any],
    document_selection: list[dict[str, str]],
    processing_mode: str | None = None,
) -> None:
    st.session_state[DRAFT_REPORT_KEY] = {
        "report": report.to_dict(),
        "source_documents": source_documents,
        "workspace": workspace,
        "document_selection": document_selection,
        "processing_mode": processing_mode,
    }


def clear_draft_report() -> None:
    st.session_state.pop(DRAFT_REPORT_KEY, None)


def render_report_preview_if_open() -> None:
    """Open the floating preview dialog when a draft report exists."""

    if DRAFT_REPORT_KEY not in st.session_state:
        return

    _report_preview_dialog()


@st.dialog("Generated Report", width="large")
def _report_preview_dialog() -> None:
    draft = st.session_state.get(DRAFT_REPORT_KEY)

    if not draft:
        return

    report = ReportData.from_dict(draft.get("report"))
    report_type = report.report_type
    workspace = draft["workspace"]

    st.markdown(
        f"""
<div class="dde-report-preview-header">
<div class="dde-report-preview-eyebrow">Preview · not saved yet</div>
<div class="dde-report-preview-title">{report_type}</div>
<div class="dde-report-preview-sub">Review your report, then save it or discard.</div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="dde-report-preview-body">', unsafe_allow_html=True)
    render_report_content(report)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    save_col, regen_col, discard_col = st.columns(3)

    with save_col:
        if st.button("Save", type="primary", use_container_width=True, key="draft_save"):
            try:
                with loading("Saving report..."):
                    metadata = _report_pipeline().save_generated_report(
                        project=workspace,
                        report=report,
                        report_type=report_type,
                        source_documents=draft["source_documents"],
                    )

                clear_draft_report()
                st.session_state.selected_report = metadata
                show_success(f"{report_type} saved to **Saved Reports**.")
                set_workspace_section("reports")
                st.rerun()
            except Exception as exc:
                show_error(exc)

    with regen_col:
        if st.button("Regenerate", use_container_width=True, key="draft_regenerate"):
            from core.auth import get_current_user_id

            document_text = _report_pipeline().load_document_text_from_selection(
                draft["document_selection"],
                user_id=get_current_user_id(),
            )["combined_text"].strip()

            if not document_text:
                st.warning("Could not read the selected source documents.")
                return

            try:
                report_context = context_builder.build(
                    workspace_id=workspace["id"],
                    source_documents=draft["source_documents"],
                    report_type=report_type,
                )

                with loading(f"Regenerating {report_type}…"):
                    new_report = _report_pipeline().generate(
                        document_text=document_text,
                        report_type=report_type,
                        source_document_count=len(
                            draft["document_selection"],
                        ),
                        report_context=report_context,
                        processing_mode=ReportProcessingMode.from_value(
                            draft.get("processing_mode"),
                        ),
                    )

                draft["report"] = new_report.to_dict()
                st.session_state[DRAFT_REPORT_KEY] = draft
                st.rerun()
            except Exception as exc:
                show_error(exc)

    with discard_col:
        if st.button("Discard", use_container_width=True, key="draft_discard"):
            clear_draft_report()
            st.rerun()

    render_premium_downloads(
        project_id=workspace["id"],
        project_name=workspace.get("name", "Quick Report"),
        report=report,
        key_prefix="draft",
    )
