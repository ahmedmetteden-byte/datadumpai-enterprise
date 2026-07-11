"""
DataDumpAI v1.0
Saved Reports — library with open, regenerate, download, and delete.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from application.report_pipeline import ReportPipeline
from services.export_service import ExportService
from services.report_service import ReportService
from ui.feedback import loading, show_empty_state, show_error, show_success
from ui.formatting import format_file_size
from ui.projects import get_current_project
from ui.report_downloads import render_premium_downloads
from ui.report_viewer import render_report_viewer


def _report_pipeline() -> ReportPipeline:
    return ReportPipeline()


export_service = ExportService()
report_service = ReportService()


def _format_date(value: str) -> str:
    if not value:
        return "—"

    try:
        return datetime.fromisoformat(value).strftime("%d %b %Y")
    except (TypeError, ValueError):
        return value[:10]


def _format_size(size_bytes: int) -> str:
    return format_file_size(size_bytes)


def _source_documents_label(report: dict) -> str:
    sources = report.get("source_documents") or []
    if not sources:
        return ""

    if len(sources) == 1:
        return f"Source: {sources[0]}"

    return f"Sources: {', '.join(sources)}"


def render_reports() -> None:
    """Saved report library for the active project."""

    project = get_current_project()
    reports = report_service.get_reports(project["id"])

    st.markdown("## Saved Reports")
    st.caption(
        "All generated reports for this project. "
        "Open one to read, regenerate from its sources, download, or delete."
    )

    if not reports:
        show_empty_state(
            icon="📑",
            title="No saved reports yet",
            message=(
                "Go to Documents, select the files you want to use, "
                "and generate your first report there."
            ),
        )
        render_report_viewer()
        return

    for report in reports:
        _render_report_row(project, report)

    render_report_viewer()


def _render_report_row(project: dict, report: dict) -> None:
    project_id = project["id"]
    filename = report["filename"]
    safe_key = filename.replace(".", "_")
    source_label = _source_documents_label(report)

    with st.container(border=True):
        info_col, open_col, regen_col, download_col, delete_col = st.columns(
            [3.8, 1, 1.1, 1.1, 1]
        )

        with info_col:
            st.markdown(f"**{report['name']}**")
            caption_parts = [
                _format_size(report["size"]),
                f"Created {_format_date(report.get('created_at', ''))}",
            ]
            if source_label:
                caption_parts.append(source_label)
            st.caption(" · ".join(caption_parts))

        with open_col:
            if st.button("Open", key=f"open_report_{safe_key}", use_container_width=True):
                st.session_state.selected_report = report
                st.session_state.pop("download_report", None)
                st.session_state.pop("confirm_delete_report", None)
                st.rerun()

        with regen_col:
            if st.button(
                "Regenerate",
                key=f"regenerate_report_{safe_key}",
                use_container_width=True,
                help="Regenerate this report from its source documents.",
            ):
                try:
                    with loading(f"Regenerating {report['name']}…"):
                        _, updated = _report_pipeline().regenerate_and_save(
                            project=project,
                            report=report,
                        )

                    st.session_state.selected_report = updated
                    show_success(f"{report['name']} regenerated.")
                    st.rerun()
                except Exception as exc:
                    show_error(exc)

        with download_col:
            if st.button("Download", key=f"download_report_{safe_key}", use_container_width=True):
                current = st.session_state.get("download_report")
                if current == filename:
                    st.session_state.pop("download_report", None)
                else:
                    st.session_state.download_report = filename
                st.session_state.pop("confirm_delete_report", None)
                st.rerun()

        with delete_col:
            if st.button("Delete", key=f"delete_report_{safe_key}", use_container_width=True):
                st.session_state.confirm_delete_report = filename

        if st.session_state.get("download_report") == filename:
            try:
                report_text = report_service.load_report(report["path"])
                report_data = report_service.load_report_data(
                    project_id,
                    filename,
                    markdown_text=report_text,
                )

                render_premium_downloads(
                    project_id=project_id,
                    project_name=project["name"],
                    report=report_data,
                    key_prefix=f"library_{safe_key}",
                )
            except Exception as exc:
                show_error(exc)

        if st.session_state.get("confirm_delete_report") == filename:
            st.warning(f"Delete **{report['name']}**? This cannot be undone.")

            yes_col, no_col = st.columns(2)

            with yes_col:
                if st.button(
                    "Yes, delete",
                    key=f"confirm_delete_report_yes_{safe_key}",
                    type="primary",
                    use_container_width=True,
                ):
                    try:
                        with loading("Deleting report..."):
                            report_service.delete_report(project_id, filename)

                        if (
                            st.session_state.get("selected_report", {}).get("filename")
                            == filename
                        ):
                            st.session_state.pop("selected_report", None)

                        st.session_state.pop("confirm_delete_report", None)
                        show_success(f"Deleted {report['name']}.")
                        st.rerun()
                    except Exception as exc:
                        show_error(exc)

            with no_col:
                if st.button(
                    "Cancel",
                    key=f"confirm_delete_report_no_{safe_key}",
                    use_container_width=True,
                ):
                    st.session_state.pop("confirm_delete_report", None)
                    st.rerun()
