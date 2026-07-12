"""
DataDumpAI v1.0
Projects — create, open, rename, and delete.
"""

from __future__ import annotations

import html

import streamlit as st

from core.auth import get_current_user_id
from core.tenant_session import ensure_tenant_context
from core.workspace_context import (
    PROJECT_MODE_LABEL,
    QUICK_REPORT_NAME,
    QUICK_REPORT_PROJECT_ID,
    WORKSPACE_MODE_PROJECT,
    WORKSPACE_MODE_QUICK,
    build_pending_project_record,
    is_quick_report_workspace,
)
from services.document_service import DocumentService
from services.plan_service import PlanLimitError, PlanService
from services.project_service import ProjectService
from services.report_service import ReportService
from ui.feedback import loading, show_error, show_success

WORKSPACE_ID_KEY = "current_workspace_id"
WORKSPACE_MODE_KEY = "workspace_mode"
ACTIVE_PROJECT_ID_KEY = "active_project_id"


def _project_service() -> ProjectService:
    return ProjectService()


def _document_service() -> DocumentService:
    return DocumentService()


def _report_service() -> ReportService:
    return ReportService()


def _plan_service() -> PlanService:
    return PlanService()
WORKSPACE_MODE_KEY = "workspace_mode"
ACTIVE_PROJECT_ID_KEY = "active_project_id"


def _refresh_projects() -> None:
    st.session_state.projects = _project_service().get_projects()


def _build_quick_report_workspace() -> dict:
    return {
        "id": QUICK_REPORT_PROJECT_ID,
        "name": QUICK_REPORT_NAME,
        "is_quick_report": True,
        "documents": _document_service().get_documents(QUICK_REPORT_PROJECT_ID),
        "reports": _report_service().get_reports(QUICK_REPORT_PROJECT_ID),
    }


def _has_active_user_project() -> bool:
    project_id = st.session_state.get(ACTIVE_PROJECT_ID_KEY)
    if not project_id:
        return False

    return _project_service().project_exists(project_id)


def _is_project_mode() -> bool:
    return st.session_state.get(WORKSPACE_MODE_KEY) == WORKSPACE_MODE_PROJECT


def is_project_pending() -> bool:
    return _is_project_mode() and not _has_active_user_project()


def initialize_projects() -> None:
    """Load user projects and ensure an active workspace is selected."""

    ensure_tenant_context(get_current_user_id())

    if "projects" not in st.session_state:
        _refresh_projects()

    if WORKSPACE_MODE_KEY not in st.session_state:
        st.session_state[WORKSPACE_MODE_KEY] = WORKSPACE_MODE_QUICK

    if WORKSPACE_ID_KEY not in st.session_state:
        st.session_state[WORKSPACE_ID_KEY] = QUICK_REPORT_PROJECT_ID

    if _is_project_mode() and _has_active_user_project():
        st.session_state[WORKSPACE_ID_KEY] = st.session_state[ACTIVE_PROJECT_ID_KEY]
        return

    if is_quick_report_workspace(st.session_state.get(WORKSPACE_ID_KEY)):
        st.session_state[WORKSPACE_MODE_KEY] = WORKSPACE_MODE_QUICK
        return

    if _has_active_user_project():
        st.session_state[WORKSPACE_MODE_KEY] = WORKSPACE_MODE_PROJECT
        st.session_state[WORKSPACE_ID_KEY] = st.session_state[ACTIVE_PROJECT_ID_KEY]
        return

    st.session_state[WORKSPACE_MODE_KEY] = WORKSPACE_MODE_QUICK
    st.session_state[WORKSPACE_ID_KEY] = QUICK_REPORT_PROJECT_ID


def get_user_projects() -> list[dict]:
    initialize_projects()
    return st.session_state.projects


def set_active_workspace(workspace_id: str) -> None:
    if is_quick_report_workspace(workspace_id):
        st.session_state[WORKSPACE_ID_KEY] = workspace_id
        return

    if not _project_service().project_exists(workspace_id):
        raise ValueError(f"Workspace not found: {workspace_id!r}")

    st.session_state[WORKSPACE_ID_KEY] = workspace_id


def set_quick_report_mode() -> None:
    st.session_state[WORKSPACE_MODE_KEY] = WORKSPACE_MODE_QUICK
    st.session_state[WORKSPACE_ID_KEY] = QUICK_REPORT_PROJECT_ID


def set_project_mode() -> None:
    st.session_state[WORKSPACE_MODE_KEY] = WORKSPACE_MODE_PROJECT

    if _has_active_user_project():
        st.session_state[WORKSPACE_ID_KEY] = st.session_state[ACTIVE_PROJECT_ID_KEY]
    else:
        st.session_state[WORKSPACE_ID_KEY] = ""
        st.session_state.project_dialog = "create"


def get_active_workspace() -> dict:
    initialize_projects()

    if is_project_pending():
        return build_pending_project_record()

    workspace_id = st.session_state[WORKSPACE_ID_KEY]

    if is_quick_report_workspace(workspace_id):
        return _build_quick_report_workspace()

    for project in st.session_state.projects:
        if project["id"] == workspace_id:
            project["is_quick_report"] = False
            project["is_pending"] = False
            project["documents"] = _document_service().get_documents(project["id"])
            project["reports"] = _report_service().get_reports(project["id"])
            return project

    set_quick_report_mode()
    return get_active_workspace()


def get_current_project() -> dict:
    return get_active_workspace()


def is_active_quick_report() -> bool:
    workspace = get_active_workspace()
    return bool(workspace.get("is_quick_report"))


def _workspace_counts(workspace_id: str) -> tuple[int, int]:
    if not workspace_id:
        return 0, 0

    documents = _document_service().get_documents(workspace_id)
    reports = _report_service().get_reports(workspace_id)
    return len(documents), len(reports)


def _activate_project(project_id: str) -> None:
    st.session_state[ACTIVE_PROJECT_ID_KEY] = project_id
    st.session_state[WORKSPACE_MODE_KEY] = WORKSPACE_MODE_PROJECT
    set_active_workspace(project_id)
    st.session_state.project_dialog = None


def render_project_manager() -> None:
    """Sidebar workspace selector with project CRUD."""

    initialize_projects()

    st.markdown(
        '<div class="dde-nav-heading">PROJECT</div>',
        unsafe_allow_html=True,
    )

    workspace_options = [QUICK_REPORT_NAME, PROJECT_MODE_LABEL]
    active_workspace = get_active_workspace()

    if active_workspace.get("is_quick_report"):
        current_index = 0
    else:
        current_index = 1

    selected_label = st.selectbox(
        "Switch workspace",
        workspace_options,
        index=current_index,
        label_visibility="collapsed",
        key="active_workspace_select",
    )

    if selected_label == QUICK_REPORT_NAME:
        set_quick_report_mode()
        st.markdown(
            f'<div class="dde-project-current-name">{html.escape(QUICK_REPORT_NAME)}</div>',
            unsafe_allow_html=True,
        )
        st.caption("Upload here without a project. All files stay in Quick Report.")
        doc_count, report_count = _workspace_counts(QUICK_REPORT_PROJECT_ID)
    else:
        set_project_mode()

        if is_project_pending():
            st.markdown(
                f'<div class="dde-project-current-name">{html.escape(PROJECT_MODE_LABEL)}</div>',
                unsafe_allow_html=True,
            )
            st.caption("Create your project below, then upload documents.")
            doc_count, report_count = 0, 0
        else:
            st.markdown(
                f'<div class="dde-project-current-name">{html.escape(active_workspace["name"])}</div>',
                unsafe_allow_html=True,
            )
            st.caption("Uploads and reports stay inside this project.")
            doc_count, report_count = _workspace_counts(active_workspace["id"])

    st.caption(f"{doc_count} documents · {report_count} reports")

    if selected_label == PROJECT_MODE_LABEL:
        if st.button("Manage", use_container_width=True, key="project_manage"):
            if is_project_pending():
                st.session_state.project_dialog = "create"
            else:
                st.session_state.project_dialog = "manage"

    dialog = st.session_state.get("project_dialog")

    if dialog == "create":
        _render_create_dialog()
    elif dialog == "manage" and _has_active_user_project():
        active_project = _project_service().get_project(st.session_state[ACTIVE_PROJECT_ID_KEY])
        _render_manage_dialog(active_project)


def _render_create_dialog() -> None:
    st.markdown("---")
    st.markdown("**Create project**")
    st.caption("Name your project, then upload documents on the Documents page.")

    new_name = st.text_input(
        "Project name",
        placeholder="Q4 Board Pack",
        key="new_project_name",
    )

    create_col, cancel_col = st.columns(2)

    with create_col:
        if st.button("Create", type="primary", use_container_width=True):
            if not new_name.strip():
                st.warning("Enter a project name.")
                return

            try:
                _plan_service().check_can_create_project(len(get_user_projects()))

                with loading("Creating project..."):
                    created = _project_service().create_project(new_name.strip())
                    _refresh_projects()
                    _activate_project(created["id"])

                show_success(f"Project “{new_name.strip()}” created. You can upload documents now.")
                st.rerun()
            except PlanLimitError as exc:
                st.warning(str(exc))
            except Exception as exc:
                show_error(exc)

    with cancel_col:
        if st.button("Cancel", use_container_width=True):
            st.session_state.project_dialog = None
            if is_project_pending():
                set_quick_report_mode()
            st.rerun()


def _render_manage_dialog(project: dict) -> None:
    st.markdown("---")
    st.markdown("**Manage project**")

    rename_name = st.text_input(
        "Rename project",
        value=project["name"],
        key="rename_project_name",
    )

    rename_col, delete_col = st.columns(2)

    with rename_col:
        if st.button("Save name", use_container_width=True):
            if not rename_name.strip():
                st.warning("Enter a project name.")
                return

            if rename_name.strip() == project["name"]:
                show_success("Name unchanged.")
                return

            try:
                with loading("Saving..."):
                    _project_service().rename_project(project["id"], rename_name.strip())
                    _refresh_projects()

                show_success("Project renamed.")
                st.rerun()
            except Exception as exc:
                show_error(exc)

    with delete_col:
        if st.button(
            "Delete project",
            use_container_width=True,
            type="secondary",
        ):
            st.session_state.confirm_delete_project = project["id"]

    if st.button("Create another project", use_container_width=True, key="project_create_another"):
        st.session_state.project_dialog = "create"

    if st.session_state.get("confirm_delete_project") == project["id"]:
        st.warning(
            f"Delete **{project['name']}** and all its documents and reports? "
            "This cannot be undone."
        )

        confirm_col, abort_col = st.columns(2)

        with confirm_col:
            if st.button(
                "Yes, delete",
                type="primary",
                use_container_width=True,
                key="confirm_delete_project_yes",
            ):
                try:
                    with loading("Deleting project..."):
                        _project_service().delete_project(project["id"])
                        _refresh_projects()

                    st.session_state.pop(ACTIVE_PROJECT_ID_KEY, None)
                    set_quick_report_mode()

                    st.session_state.project_dialog = None
                    st.session_state.pop("confirm_delete_project", None)
                    st.session_state.pop("selected_report", None)
                    show_success("Project deleted.")
                    st.rerun()
                except Exception as exc:
                    show_error(exc)

        with abort_col:
            if st.button("Cancel", use_container_width=True, key="confirm_delete_project_no"):
                st.session_state.pop("confirm_delete_project", None)
                st.rerun()

    if st.button("Close", use_container_width=True, key="close_manage_dialog"):
        st.session_state.project_dialog = None
        st.session_state.pop("confirm_delete_project", None)
        st.rerun()


def render_project_selector() -> None:
    render_project_manager()
