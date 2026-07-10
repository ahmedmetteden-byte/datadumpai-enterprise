"""
DataDumpAI Enterprise
Global Command Bar

Primary entry point for common actions on every page.
"""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from core.navigation import set_active_page
from core.workspace_navigation import set_workspace_section
from ui.search_bar import render_search_bar


@dataclass(frozen=True)
class CommandAction:
    """One global command."""

    id: str
    label: str
    page: str | None = None
    section: str | None = None


COMMANDS: list[CommandAction] = [
    CommandAction(
        id="upload",
        label="＋ Upload",
        page="documents",
    ),
    CommandAction(
        id="generate",
        label="📑 Generate Report",
        page="reports",
    ),
    CommandAction(
        id="copilot",
        label="🤖 Ask Copilot",
        page="workspace",
        section="copilot",
    ),
    CommandAction(
        id="export",
        label="📤 Export",
        page="reports",
    ),
]


def _navigate(
    *,
    page: str | None = None,
    section: str | None = None,
) -> None:
    if page:
        set_active_page(page)

    if section:
        set_workspace_section(section)

    st.rerun()


def render_global_command_bar() -> None:
    """
    Render the Global Command Bar at the top of every page.
    """

    search_col, *action_cols = st.columns(
        [3, 1, 1, 1, 1],
        gap="small",
    )

    with search_col:
        st.markdown("**⌘ Search**")
        render_search_bar()

    for column, command in zip(action_cols, COMMANDS):

        with column:
            st.markdown("&nbsp;", unsafe_allow_html=True)

            if st.button(
                command.label,
                key=f"global_command_{command.id}",
                use_container_width=True,
                type="primary" if command.id == "generate" else "secondary",
            ):
                _navigate(
                    page=command.page,
                    section=command.section,
                )

    st.divider()


def render_command_bar() -> None:
    """Backward-compatible alias."""

    render_global_command_bar()
