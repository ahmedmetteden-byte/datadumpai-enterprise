"""
Tenant-scoped Streamlit session state.

Clears workspace and data-bearing UI keys when the authenticated user changes
or signs out so one browser session cannot leak another user's metadata.
"""

from __future__ import annotations

import streamlit as st

TENANT_USER_KEY = "_tenant_user_id"

TENANT_DATA_KEYS = (
    "projects",
    "current_workspace_id",
    "workspace_mode",
    "active_project_id",
    "project_dialog",
    "confirm_delete_project",
    "active_workspace_select",
    "selected_report",
    "draft_report",
    "report_for_chat",
    "viewing_document",
    "confirm_delete_document",
    "quick_report_documents",
    "project_report_source_id",
    "download_report",
    "confirm_delete_report",
    "copilot_question",
    "copilot_answer",
    "copilot_sources",
    "selected_report_type",
    "current_project",
)


def clear_tenant_session() -> None:
    """Remove cached workspace and content state for the current browser tab."""

    for key in TENANT_DATA_KEYS:
        st.session_state.pop(key, None)

    for key in list(st.session_state.keys()):
        if key.startswith("project_report_documents_"):
            st.session_state.pop(key, None)

    st.session_state.pop(TENANT_USER_KEY, None)


def ensure_tenant_context(user_id: str) -> None:
    """Reset tenant state when the signed-in user changes."""

    cached_user_id = st.session_state.get(TENANT_USER_KEY)
    if cached_user_id != user_id:
        clear_tenant_session()
        st.session_state[TENANT_USER_KEY] = user_id
