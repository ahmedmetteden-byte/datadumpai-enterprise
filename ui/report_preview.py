"""
Floating preview for a generated report before it is saved.
"""

from __future__ import annotations

import logging
from typing import Any

import streamlit as st

from application.report_pipeline import ReportPipeline
from core.current_user import require_current_user
from core.workspace_navigation import set_workspace_section
from models.report_data import ReportData
from models.report_processing_mode import ReportProcessingMode
from services.executive_report_context import ExecutiveReportContextBuilder
from ui.feedback import loading, show_error, show_success
from ui.report_downloads import render_premium_downloads
from ui.report_renderer import render_report_content
from ui.report_session_trace import log_report_session_state

logger = logging.getLogger(__name__)


def _report_pipeline() -> ReportPipeline:
    from core.auth import get_access_token

    return ReportPipeline(
        current_user=require_current_user(),
        access_token=get_access_token(),
    )


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
    log_report_session_state("before_set_draft_report")
    st.session_state[DRAFT_REPORT_KEY] = {
        "report": report.to_dict(),
        "source_documents": source_documents,
        "workspace": workspace,
        "document_selection": document_selection,
        "processing_mode": processing_mode,
    }
    logger.info(
        "Report stored in session_state key=%s report_type=%s narrative_chars=%s "
        "source_documents=%s workspace_id=%s",
        DRAFT_REPORT_KEY,
        report.report_type,
        len(report.narrative or ""),
        source_documents,
        workspace.get("id"),
    )
    log_report_session_state("after_set_draft_report")


def clear_draft_report() -> None:
    logger.info("Clearing draft_report from session_state")
    log_report_session_state("before_clear_draft_report")
    st.session_state.pop(DRAFT_REPORT_KEY, None)
    log_report_session_state("after_clear_draft_report")


def render_report_preview_if_open() -> None:
    """Open the floating preview dialog when a draft report exists."""

    logger.info("Entering render_report_preview_if_open")
    logger.info(
        "draft_report=%s",
        bool(st.session_state.get("draft_report")),
    )

    if DRAFT_REPORT_KEY not in st.session_state:
        return

    logger.info("Opening preview dialog")
    _report_preview_dialog()


@st.dialog("Generated Report", width="large")
def _report_preview_dialog() -> None:
    draft = st.session_state.get(DRAFT_REPORT_KEY)

    if not draft:
        logger.warning("Report preview dialog opened but draft_report is empty")
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

    reporting_period = str(
        (draft.get("report") or {}).get("metadata", {}).get("report_context", {}).get(
            "reporting_period",
            "",
        )
    )

    from ui.report_insights import (
        render_explore_visual_insights,
        render_report_insights_panel,
        render_visual_insights_charts,
    )

    render_report_insights_panel(report, reporting_period=reporting_period)

    def _update_draft(updated_report: ReportData) -> None:
        current = st.session_state.get(DRAFT_REPORT_KEY, {})
        current["report"] = updated_report.to_dict()
        st.session_state[DRAFT_REPORT_KEY] = current

    report = render_explore_visual_insights(
        report,
        key_prefix="draft",
        reporting_period=reporting_period,
        on_report_updated=_update_draft,
    )
    render_visual_insights_charts(report)

    st.markdown("---")

    st.markdown('<div class="dde-report-preview-body">', unsafe_allow_html=True)
    logger.info(
        "Rendering markdown length=%d",
        len(report.narrative or ""),
    )
    render_report_content(report, include_charts=False)
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

                logger.info(
                    "Save complete — clearing draft and setting selected_report "
                    "filename=%s",
                    metadata.get("filename"),
                )
                clear_draft_report()
                st.session_state.selected_report = metadata
                log_report_session_state("after_save_selected_report")
                show_success(f"{report_type} saved to **My Reports**.")
                set_workspace_section("reports")
                st.rerun()
            except Exception as exc:
                show_error(exc)

    with regen_col:
        if st.button("Regenerate", use_container_width=True, key="draft_regenerate"):
            document_text = _report_pipeline().load_document_text_from_selection(
                draft["document_selection"],
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
        st.markdown('<div class="dde-danger-action-marker"></div>', unsafe_allow_html=True)
        if st.button("Discard", use_container_width=True, key="draft_discard", type="secondary"):
            clear_draft_report()
            st.rerun()

    render_premium_downloads(
        project_id=workspace["id"],
        project_name=workspace.get("name", "Quick Report"),
        report=report,
        key_prefix="draft",
    )
