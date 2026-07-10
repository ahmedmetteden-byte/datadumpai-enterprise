"""
Recent Reports — quick access to the latest work on the project home page.
"""

from __future__ import annotations

import streamlit as st

from core.workspace_navigation import set_workspace_section
from services.report_service import ReportService
from ui.formatting import format_report_timestamp
from ui.projects import get_current_project

RECENT_REPORT_LIMIT = 5

report_service = ReportService()


def _sort_reports_newest_first(reports: list[dict]) -> list[dict]:
    return sorted(
        reports,
        key=lambda report: report.get("created_at", ""),
        reverse=True,
    )


def render_recent_reports() -> None:
    """Show the latest reports for quick access from the project home page."""

    project = get_current_project()
    reports = _sort_reports_newest_first(
        report_service.get_reports(project["id"])
    )

    if not reports:
        return

    recent_reports = reports[:RECENT_REPORT_LIMIT]

    st.markdown('<div class="dde-recent-reports">', unsafe_allow_html=True)
    st.markdown("### Recent Reports")

    for report in recent_reports:
        _render_recent_report_row(report)

    if len(reports) > RECENT_REPORT_LIMIT:
        if st.button(
            "View all saved reports",
            key="recent_reports_view_all",
            use_container_width=False,
        ):
            set_workspace_section("reports")
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def _render_recent_report_row(report: dict) -> None:
    filename = report["filename"]
    safe_key = filename.replace(".", "_")
    generated_label = format_report_timestamp(report.get("created_at", ""))
    is_open = (
        st.session_state.get("selected_report", {}).get("filename") == filename
    )

    with st.container(border=True):
        info_col, action_col = st.columns([5.5, 1], gap="small")

        with info_col:
            st.markdown(
                f"""
<div class="dde-recent-report-row">
<div class="dde-recent-report-name">✓ {report["name"]}</div>
<div class="dde-recent-report-time">{generated_label}</div>
</div>
""",
                unsafe_allow_html=True,
            )

        with action_col:
            open_label = "Open" if not is_open else "Opened"
            if st.button(
                open_label,
                key=f"recent_report_open_{safe_key}",
                use_container_width=True,
                type="primary" if is_open else "secondary",
            ):
                st.session_state.selected_report = report
                st.session_state.pop("confirm_delete_report", None)
                st.rerun()
