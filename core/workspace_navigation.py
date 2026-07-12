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
    subtitle: str = ""
    enabled: bool = True
    is_primary: bool = False
    show_in_nav: bool = True


WORKSPACE_SECTIONS: list[WorkspaceSection] = [
    WorkspaceSection("overview", "Overview", "🏠", is_primary=True),
    WorkspaceSection("documents", "AI Workspace", "✨", subtitle="Ask & create"),
    WorkspaceSection("library", "My Documents", "📂", subtitle="Dump Box"),
    WorkspaceSection("reports", "My Reports", "📄", subtitle="View completed reports"),
    WorkspaceSection("copilot", "Ask AI", "🤖"),
    WorkspaceSection("account", "Account", "👤", show_in_nav=False),
    WorkspaceSection("settings", "Settings", "⚙️", show_in_nav=False),
]

DEFAULT_SECTION = "overview"

LEGACY_PAGE_ALIASES: dict[str, str] = {
    "dashboard": "overview",
    "overview": "overview",
    "documents": "documents",
    "report_studio": "documents",
    "ai_workspace": "documents",
    "library": "library",
    "document_library": "library",
    "reports": "reports",
    "generate": "documents",
    "copilot": "copilot",
    "settings": "settings",
    "account": "account",
    "profile": "account",
    "history": "reports",
    "knowledge": "documents",
    "analytics": "overview",
}


REPORT_STUDIO_SECTION = "documents"


def initialize_workspace_navigation() -> None:
    """Ensure workspace section state exists."""

    if "workspace_section" not in st.session_state:
        st.session_state.workspace_section = DEFAULT_SECTION


def get_workspace_sections() -> list[WorkspaceSection]:
    """Return every enabled workspace section."""

    return [section for section in WORKSPACE_SECTIONS if section.enabled]


def get_sidebar_workspace_sections() -> list[WorkspaceSection]:
    """Return workspace sections shown in the primary sidebar navigation."""

    return [
        section
        for section in WORKSPACE_SECTIONS
        if section.enabled and section.show_in_nav
    ]


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


REPORT_STUDIO_SECTION = "documents"
AI_WORKSPACE_SECTION = "documents"


def navigate_to_ai_workspace() -> None:
    """Open AI Workspace — conversational report and analysis."""

    set_workspace_section(AI_WORKSPACE_SECTION)


def navigate_to_report_studio() -> None:
    """Backward-compatible alias for AI Workspace."""

    navigate_to_ai_workspace()


def resolve_workspace_section(page_id: str) -> str | None:
    """Map a legacy top-level page id to a workspace section."""

    return LEGACY_PAGE_ALIASES.get(page_id)
