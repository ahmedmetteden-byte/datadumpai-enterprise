"""
DataDumpAI v1.0
Project Workspace Navigation

Single source of truth for workspace sections.
"""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st


@dataclass(frozen=True)
class WorkspaceSection:
    """One section inside the active project."""

    id: str
    title: str
    icon: str
    enabled: bool = True
    is_primary: bool = False


WORKSPACE_SECTIONS: list[WorkspaceSection] = [
    WorkspaceSection("overview", "Overview", "📊", is_primary=True),
    WorkspaceSection("documents", "Documents", "📁"),
    WorkspaceSection("library", "Document Library", "📚"),
    WorkspaceSection("reports", "Saved Reports", "📑"),
    WorkspaceSection("copilot", "Ask AI", "🤖"),
    WorkspaceSection("settings", "Settings", "⚙️"),
]

DEFAULT_SECTION = "overview"

LEGACY_PAGE_ALIASES: dict[str, str] = {
    "dashboard": "overview",
    "overview": "overview",
    "documents": "documents",
    "library": "library",
    "document_library": "library",
    "reports": "reports",
    "generate": "documents",
    "copilot": "copilot",
    "settings": "settings",
    "history": "reports",
    "knowledge": "documents",
    "analytics": "overview",
}


def initialize_workspace_navigation() -> None:
    """Ensure workspace section state exists."""

    if "workspace_section" not in st.session_state:
        st.session_state.workspace_section = DEFAULT_SECTION


def get_workspace_sections() -> list[WorkspaceSection]:
    """Return every workspace section."""

    return [section for section in WORKSPACE_SECTIONS if section.enabled]


def get_workspace_section() -> str:
    """Return the active workspace section id."""

    initialize_workspace_navigation()

    valid_ids = {section.id for section in WORKSPACE_SECTIONS}
    section_id = st.session_state.workspace_section

    if section_id not in valid_ids:
        st.session_state.workspace_section = DEFAULT_SECTION
        return DEFAULT_SECTION

    return section_id


def set_workspace_section(section_id: str) -> None:
    """Switch the active workspace section."""

    initialize_workspace_navigation()

    valid_ids = {section.id for section in WORKSPACE_SECTIONS}

    if section_id in valid_ids:
        st.session_state.workspace_section = section_id


def resolve_workspace_section(page_id: str) -> str | None:
    """Map a legacy top-level page id to a workspace section."""

    return LEGACY_PAGE_ALIASES.get(page_id)
