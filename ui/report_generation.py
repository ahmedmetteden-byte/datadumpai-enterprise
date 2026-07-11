"""
DataDumpAI v1.0
Report generation UI — used on the Documents page.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from config import FULL_REPORT_PERIODS
from application.report_pipeline import ReportPipeline
from core.workspace_context import QUICK_REPORT_PROJECT_ID, QUICK_REPORT_NAME
from services.document_service import DocumentService
from core.workspace_navigation import set_workspace_section
from services.executive_report_context import ExecutiveReportContextBuilder
from services.plan_service import PlanService
from ui.feedback import loading, show_error
from ui.plan_upgrade import render_upgrade_prompt
from ui.projects import get_active_workspace, get_user_projects
from ui.report_preview import set_draft_report


def _report_pipeline() -> ReportPipeline:
    return ReportPipeline()


def _document_service() -> DocumentService:
    return DocumentService()


def _plan_service() -> PlanService:
    return PlanService()


context_builder = ExecutiveReportContextBuilder()

REPORT_TYPE_META = {
    "Executive Summary": {
        "description": "Fast, polished summary for leaders.",
        "badge": "Most Popular",
        "rating": "★★★★★",
        "tier": "free",
    },
    "Full Report": {
        "description": "Roll up weekly, monthly, or quarterly reports into one comprehensive period report.",
        "badge": "Most Popular",
        "rating": "★★★★★",
        "tier": "starter",
    },
    "Board Report": {
        "description": "Structured update for board review.",
        "badge": "Professional",
        "rating": "★★★★☆",
        "tier": "pro",
    },
    "Management Report": {
        "description": "Operational performance and next steps.",
        "badge": "Professional",
        "rating": "★★★★☆",
        "tier": "pro",
    },
    "Financial Analysis": {
        "description": "Focus on numbers, trends, and risks.",
        "badge": "Professional",
        "rating": "★★★★☆",
        "tier": "pro",
    },
    "Regulatory Compliance Report": {
        "description": "Track obligations, gaps, and regulatory exposure.",
        "badge": "Professional",
        "rating": "★★★★☆",
        "tier": "pro",
    },
    "Risk Assessment Report": {
        "description": "Severity-ranked risks with mitigation priorities.",
        "badge": "Professional",
        "rating": "★★★★☆",
        "tier": "pro",
    },
    "Meeting Intelligence Report": {
        "description": "Decisions, actions, themes, and recurring issues.",
        "badge": "Professional",
        "rating": "★★★★☆",
        "tier": "pro",
    },
    "Market Intelligence Report": {
        "description": "Competitive signals, trends, and market outlook.",
        "badge": "Professional",
        "rating": "★★★★☆",
        "tier": "pro",
    },
    "Strategic Planning Report": {
        "description": "Strategic options, priorities, and recommendations.",
        "badge": "Professional",
        "rating": "★★★★☆",
        "tier": "pro",
    },
    "Executive Intelligence Dashboard": {
        "description": "Health score, heat map, outlook, and executive snapshot.",
        "badge": "Professional",
        "rating": "★★★★★",
        "tier": "pro",
    },
}

QUICK_REPORT_KEY = "quick_report_documents"
PROJECT_SOURCE_KEY = "project_report_source_id"
PROJECT_DOCUMENTS_KEY = "project_report_documents"
NOTHING_SELECTED = "Nothing Selected"
QUICK_REPORT_OPTION = "Quick Report"
QUICK_SOURCE_SELECT_KEY = "quick_report_source_select"
PROJECT_SOURCE_SELECT_KEY = "project_report_source_select"
FULL_REPORT_PERIOD_KEY = "full_report_period"


def _project_document_filenames(project_id: str) -> list[str]:
    return [
        document["filename"]
        for document in _document_service().get_documents(project_id)
    ]


def _select_all_flag_key(state_key: str) -> str:
    return f"{state_key}__select_all"


def _coerce_multiselect_values(value: Any, available: list[str]) -> list[str]:
    """Normalize multiselect session values without iterating strings character-wise."""

    available_set = set(available)

    if value is None:
        return []

    if isinstance(value, list):
        return [
            item
            for item in value
            if isinstance(item, str) and item in available_set
        ]

    if isinstance(value, str):
        return [value] if value in available_set else []

    return []


def _read_document_selection(state_key: str, available: list[str]) -> list[str]:
    """Read the effective document selection, honoring explicit select-all mode."""

    if not available:
        return []

    flag_key = _select_all_flag_key(state_key)

    if st.session_state.get(flag_key):
        return list(available)

    selected = _coerce_multiselect_values(
        st.session_state.get(state_key, []),
        available,
    )

    # Streamlit's built-in multiselect "Select all" can leave state out of sync
    # with our buttons; treat a full selection as select-all for generation.
    if len(selected) == len(available):
        st.session_state[flag_key] = True
        return list(available)

    return selected


def _clear_selection(state_key: str) -> None:
    st.session_state[state_key] = []
    st.session_state[_select_all_flag_key(state_key)] = False


def _merge_document_selection(
    *,
    quick_selected: list[str],
    project_id: str,
    project_selected: list[str],
) -> list[dict[str, str]]:
    """Combine selections from both dropdowns, deduplicated by project + filename."""

    merged: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for filename in quick_selected:
        key = (QUICK_REPORT_PROJECT_ID, filename)
        if key not in seen:
            seen.add(key)
            merged.append({"project_id": QUICK_REPORT_PROJECT_ID, "filename": filename})

    for filename in project_selected:
        key = (project_id, filename)
        if key not in seen:
            seen.add(key)
            merged.append({"project_id": project_id, "filename": filename})

    return merged


def _selection_source_labels(
    selection: list[dict[str, str]],
    projects: list[dict[str, Any]],
) -> list[str]:
    """Human-readable source labels stored with generated reports."""

    project_names = {project["id"]: project["name"] for project in projects}
    active_workspace = get_active_workspace()
    active_workspace_id = active_workspace["id"]

    labels: list[str] = []

    for item in selection:
        filename = item["filename"]
        project_id = item["project_id"]

        if project_id == QUICK_REPORT_PROJECT_ID:
            if active_workspace_id == QUICK_REPORT_PROJECT_ID:
                labels.append(filename)
            else:
                labels.append(f"{QUICK_REPORT_NAME}/{filename}")
        elif project_id == active_workspace_id:
            labels.append(filename)
        else:
            project_name = project_names.get(project_id, "Project")
            labels.append(f"{project_name}/{filename}")

    return labels


def _get_document_selection_from_state(
    projects: list[dict[str, Any]] | None = None,
    active_workspace: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Build the current document selection from Streamlit session state."""

    active_workspace = active_workspace or get_active_workspace()
    user_projects = projects if projects is not None else get_user_projects()

    quick_selected: list[str] = []
    project_selected: list[str] = []
    selected_project_id = active_workspace["id"]

    if st.session_state.get(QUICK_SOURCE_SELECT_KEY) == QUICK_REPORT_OPTION:
        quick_documents = _project_document_filenames(QUICK_REPORT_PROJECT_ID)
        quick_selected = _read_document_selection(QUICK_REPORT_KEY, quick_documents)

    selected_project_name = st.session_state.get(
        PROJECT_SOURCE_SELECT_KEY,
        NOTHING_SELECTED,
    )

    if selected_project_name != NOTHING_SELECTED:
        project_options = {project["name"]: project["id"] for project in user_projects}

        if selected_project_name in project_options:
            selected_project_id = project_options[selected_project_name]
            project_docs_key = f"{PROJECT_DOCUMENTS_KEY}_{selected_project_id}"
            project_documents = _project_document_filenames(selected_project_id)
            project_selected = _read_document_selection(
                project_docs_key,
                project_documents,
            )

    return _merge_document_selection(
        quick_selected=quick_selected,
        project_id=selected_project_id,
        project_selected=project_selected,
    )


def _sync_multiselect_state(state_key: str, available: list[str]) -> None:
    """Keep multiselect session state aligned after user changes."""

    selected = _coerce_multiselect_values(
        st.session_state.get(state_key, []),
        available,
    )
    st.session_state[state_key] = selected
    st.session_state[_select_all_flag_key(state_key)] = (
        len(selected) == len(available) and len(available) > 0
    )


def _render_document_multiselect(
    *,
    state_key: str,
    documents: list[str],
    label: str,
    help_text: str,
    select_all_key: str,
    clear_all_key: str,
) -> list[str]:
    """Multiselect with explicit select-all support backed by session state."""

    if state_key not in st.session_state:
        st.session_state[state_key] = []

    select_col, clear_col = st.columns(2)
    with select_col:
        if st.button(
            "Select all",
            key=select_all_key,
            use_container_width=True,
        ):
            st.session_state[state_key] = list(documents)
            st.session_state[_select_all_flag_key(state_key)] = True
            st.rerun()

    with clear_col:
        if st.button("Clear", key=clear_all_key, use_container_width=True):
            _clear_selection(state_key)
            st.rerun()

    selected_count = len(_read_document_selection(state_key, documents))
    if documents:
        st.caption(
            f"{selected_count} of {len(documents)} document(s) selected"
        )

    return st.multiselect(
        label,
        options=documents,
        label_visibility="collapsed",
        key=state_key,
        placeholder="Choose documents to include",
        help=help_text,
        on_change=_sync_multiselect_state,
        args=(state_key, documents),
    )


def load_document_text_from_selection(selection: list[dict[str, str]]) -> str:
    """Load and combine text from documents that may span multiple projects."""

    from core.auth import get_current_user_id

    return _report_pipeline().load_document_text_from_selection(
        selection,
        user_id=get_current_user_id(),
    )["combined_text"]


def render_document_source_selection(
    projects: list[dict[str, Any]] | None = None,
    active_workspace: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """
    Let the user pick documents from Quick Report or from a user-created project.
    """

    active_workspace = active_workspace or get_active_workspace()
    user_projects = projects if projects is not None else get_user_projects()

    quick_documents = _project_document_filenames(QUICK_REPORT_PROJECT_ID)
    project_selected: list[str] = []
    quick_selected: list[str] = []
    selected_project_id = active_workspace["id"]

    with st.container(border=True):
        st.markdown("### Select documents for your report")
        st.caption(
            "Choose **Quick Report** for files uploaded without a project, "
            "or pick a **Project** for its own isolated documents and reports."
        )

        quick_col, project_col = st.columns(2, gap="medium")

        with quick_col:
            with st.container(border=True):
                st.markdown(
                    '<div class="dde-report-source-label">Quick Report</div>',
                    unsafe_allow_html=True,
                )

                quick_source = st.selectbox(
                    "Quick Report source",
                    [NOTHING_SELECTED, QUICK_REPORT_OPTION],
                    index=0,
                    label_visibility="collapsed",
                    key=QUICK_SOURCE_SELECT_KEY,
                    help="Use documents uploaded without creating a project.",
                )

                if quick_source == QUICK_REPORT_OPTION:
                    if quick_documents:
                        quick_selected = _render_document_multiselect(
                            state_key=QUICK_REPORT_KEY,
                            documents=quick_documents,
                            label="Quick Report documents",
                            help_text="Select one or more files from Quick Report.",
                            select_all_key="quick_report_select_all",
                            clear_all_key="quick_report_clear_all",
                        )
                    else:
                        _clear_selection(QUICK_REPORT_KEY)
                        st.caption(
                            "No Quick Report documents yet. "
                            "Stay on **Quick Report** in the sidebar and upload files in **Documents**."
                        )
                else:
                    _clear_selection(QUICK_REPORT_KEY)

        with project_col:
            with st.container(border=True):
                st.markdown(
                    '<div class="dde-report-source-label">Project</div>',
                    unsafe_allow_html=True,
                )

                if not user_projects:
                    st.caption(
                        "Create a project in the sidebar to use project documents."
                    )
                    return _get_document_selection_from_state(user_projects, active_workspace)

                project_options = {
                    project["name"]: project["id"] for project in user_projects
                }
                project_names = list(project_options.keys())
                project_source_options = [NOTHING_SELECTED, *project_names]

                selected_project_name = st.selectbox(
                    "Project source",
                    project_source_options,
                    index=0,
                    label_visibility="collapsed",
                    key=PROJECT_SOURCE_SELECT_KEY,
                    help="Choose a project to pull documents from.",
                )

                if selected_project_name != NOTHING_SELECTED:
                    selected_project_id = project_options[selected_project_name]
                    st.session_state[PROJECT_SOURCE_KEY] = selected_project_id

                    project_documents = _project_document_filenames(selected_project_id)
                    project_docs_key = f"{PROJECT_DOCUMENTS_KEY}_{selected_project_id}"

                    if project_documents:
                        project_selected = _render_document_multiselect(
                            state_key=project_docs_key,
                            documents=project_documents,
                            label="Project documents",
                            help_text=(
                                f"Select one or more files from {selected_project_name}."
                            ),
                            select_all_key=f"project_select_all_{selected_project_id}",
                            clear_all_key=f"project_clear_all_{selected_project_id}",
                        )
                    else:
                        _clear_selection(project_docs_key)
                        st.caption(
                            f"No documents in {selected_project_name} yet. "
                            "Select that project in the sidebar and upload files in **Documents**."
                        )
                else:
                    st.session_state.pop(PROJECT_SOURCE_KEY, None)

    return _get_document_selection_from_state(user_projects, active_workspace)


def render_report_type_picker() -> str:
    st.markdown("### Choose a report type")

    available_types = _plan_service().get_available_report_types()
    locked_types = _plan_service().locked_report_types()
    selected = st.session_state.get("selected_report_type", available_types[0])

    if selected not in available_types and selected not in locked_types:
        selected = available_types[0]
        st.session_state.selected_report_type = selected

    display_types = available_types + locked_types

    for row_start in range(0, len(display_types), 2):
        columns = st.columns(2, gap="medium")
        for index, report_type in enumerate(display_types[row_start:row_start + 2]):
            meta = REPORT_TYPE_META.get(report_type, {})
            is_locked = report_type in locked_types
            is_selected = report_type == selected and not is_locked

            with columns[index]:
                lock_label = " 🔒" if is_locked else ""
                st.markdown(
                    f"""
<div class="dde-report-type-card {'selected' if is_selected else ''}{' locked' if is_locked else ''}">
<div class="dde-report-type-top">
<div class="dde-report-type-name">{report_type}{lock_label}</div>
<div class="dde-report-type-rating">{meta.get('rating', '')}</div>
</div>
<div class="dde-report-type-description">{meta.get('description', '')}</div>
{f'<div class="dde-report-type-badge">{meta["badge"]}</div>' if meta.get("badge") else ""}
</div>
""",
                    unsafe_allow_html=True,
                )
                if is_locked:
                    if st.button(
                        f"Unlock {report_type}",
                        key=f"select_report_type_{report_type}",
                        use_container_width=True,
                        type="secondary",
                    ):
                        st.session_state["settings_tab"] = "plan"
                        set_workspace_section("settings")
                        st.rerun()
                elif st.button(
                    f"Select {report_type}",
                    key=f"select_report_type_{report_type}",
                    use_container_width=True,
                    type="primary" if is_selected else "secondary",
                ):
                    st.session_state.selected_report_type = report_type
                    st.rerun()

    if locked_types:
        render_upgrade_prompt("report_types")

    return st.session_state.get("selected_report_type", available_types[0])


def render_full_report_period_selector(report_type: str) -> str:
    """Let the user choose the rollup period when Full Report is selected."""

    if report_type != "Full Report":
        return "Comprehensive Report"

    if FULL_REPORT_PERIOD_KEY not in st.session_state:
        st.session_state[FULL_REPORT_PERIOD_KEY] = FULL_REPORT_PERIODS[0]

    current = st.session_state.get(FULL_REPORT_PERIOD_KEY, FULL_REPORT_PERIODS[0])
    if current not in FULL_REPORT_PERIODS:
        current = FULL_REPORT_PERIODS[0]

    with st.container(border=True):
        st.markdown('<div class="dde-full-report-period-marker"></div>', unsafe_allow_html=True)
        st.markdown(
            """
<div class="dde-full-report-period-title">Reporting period</div>
<div class="dde-full-report-period-subtitle">
Choose how DataDumpAI should consolidate your uploaded documents — for example,
four weekly reports into a <strong>monthly</strong> report, three monthly reports
into a <strong>quarterly</strong> report, or four quarterly reports into an
<strong>annual</strong> report.
</div>
""",
            unsafe_allow_html=True,
        )

        selected = st.selectbox(
            "Choose reporting period",
            FULL_REPORT_PERIODS,
            index=FULL_REPORT_PERIODS.index(current),
            key=FULL_REPORT_PERIOD_KEY,
            help="Select the time span this Full Report should cover.",
        )

    return selected


def render_documents_page_generation(
    projects: list[dict[str, Any]],
    document_selection: list[dict[str, str]],
) -> None:
    """Generate a report from the selected documents without leaving the Documents page."""

    if not document_selection:
        quick_active = (
            st.session_state.get(QUICK_SOURCE_SELECT_KEY) == QUICK_REPORT_OPTION
        )
        project_active = (
            st.session_state.get(PROJECT_SOURCE_SELECT_KEY, NOTHING_SELECTED)
            != NOTHING_SELECTED
        )

        if not quick_active and not project_active:
            st.info(
                "Choose **Quick Report** or a **Project** above, "
                "then select the documents you want to include."
            )
        else:
            st.info("Select one or more documents above to generate a report.")
        return

    report_type = render_report_type_picker()

    if not _plan_service().is_report_type_available(report_type):
        render_upgrade_prompt("report_types")
        return

    reporting_period = render_full_report_period_selector(report_type)

    st.caption(
        f"**{len(document_selection)}** document(s) will be analyzed for this report."
    )

    if _plan_service().uses_full_report_format(report_type):
        st.caption(
            f"**Full Report** will consolidate your selected documents into a "
            f"**{reporting_period.lower()}** with period narrative, cross-period themes, "
            "consolidated findings, risks, and recommendations."
        )
        if _plan_service().include_professional_charts():
            st.caption(
                "Professional charts and trend visuals are included when your plan supports them."
            )
    elif _plan_service().uses_intelligence_format(report_type):
        st.caption(
            "This report includes an **Executive Intelligence Dashboard**, "
            "summary card, professional charts, ranked findings with confidence scores, "
            "cross-document intelligence, quotations, and benchmarks."
        )
    elif report_type == "Executive Summary":
        st.caption(
            "Free Executive Summary reports provide a polished overview. "
            "Upgrade to **Professional** for intelligence dashboards, charts, "
            "and cross-document analysis."
        )

    st.markdown("---")

    if st.button(
        "✨ Generate Report",
        type="primary",
        use_container_width=True,
        key="documents_generate_report",
    ):
        workspace = get_active_workspace()
        document_selection = _get_document_selection_from_state(projects)

        if not document_selection:
            st.warning("Select one or more documents above to generate a report.")
            return

        from core.auth import get_current_user_id

        load_result = _report_pipeline().load_document_text_from_selection(
            document_selection,
            user_id=get_current_user_id(),
        )
        document_text = load_result["combined_text"].strip()
        source_labels = _selection_source_labels(document_selection, get_user_projects())

        if load_result["skipped"]:
            st.warning(
                "Could not extract text from: "
                + ", ".join(load_result["skipped"])
                + ". The report will use the remaining documents."
            )
            st.caption(
                "Tip: scanned PDFs are read with OCR automatically when "
                "`rapidocr-onnxruntime` is installed."
            )

        if not document_text:
            st.warning(
                "Could not read text from the selected documents. "
                "Scanned PDFs need OCR — run `pip install rapidocr-onnxruntime Pillow` "
                "in your environment, then try again (first run may take a minute to download OCR models). "
                "You can also upload Word or Excel exports if available."
            )
            return

        if len(load_result["loaded"]) < len(document_selection):
            st.info(
                f"Using {len(load_result['loaded'])} of "
                f"{len(document_selection)} selected documents."
            )

        if load_result.get("truncated"):
            st.info(
                "Large documents were trimmed to speed up generation. "
                "Your original files are unchanged."
            )

        try:
            report_context = context_builder.build(
                workspace_id=workspace["id"],
                source_documents=source_labels,
                report_type=report_type,
                include_prior_reports=_plan_service().include_cross_document_intelligence()
                or _plan_service().uses_full_report_format(report_type),
                reporting_period=reporting_period,
            )

            with loading(
                f"Generating {report_type} from "
                f"{len(load_result['loaded'])} document(s)…"
            ):
                report_text = _report_pipeline().generate(
                    document_text=document_text,
                    report_type=report_type,
                    source_document_count=len(load_result["loaded"]),
                    report_context=report_context,
                    include_charts=_plan_service().include_professional_charts(),
                )

            set_draft_report(
                report_type=report_type,
                report_text=report_text,
                source_documents=source_labels,
                workspace=workspace,
                document_selection=document_selection,
            )
            st.rerun()
        except Exception as exc:
            show_error(exc)
