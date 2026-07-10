"""
DataDumpAI v1.0
Navigation — single workspace entry point.
"""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st


@dataclass(frozen=True)
class NavigationItem:
    """Represents one application page."""

    id: str
    title: str
    icon: str
    enabled: bool = True


NAVIGATION: list[NavigationItem] = [
    NavigationItem(
        id="workspace",
        title="Workspace",
        icon="📂",
    ),
]

PUBLIC_PAGES = ("landing", "auth")
DEFAULT_PAGE = "workspace"
PUBLIC_DEFAULT_PAGE = "landing"


def initialize_navigation() -> None:
    """Create navigation state if it doesn't exist."""

    if "active_page" not in st.session_state:
        st.session_state.active_page = DEFAULT_PAGE


def get_navigation() -> list[NavigationItem]:
    """Return every navigation item."""

    from core.auth import is_admin

    items = list(NAVIGATION)
    if is_admin():
        items.append(
            NavigationItem(
                id="admin",
                title="Admin",
                icon="🛡️",
            )
        )
    return items


def get_active_page() -> str:
    initialize_navigation()
    return st.session_state.active_page


def set_active_page(page_id: str) -> None:
    initialize_navigation()
    st.session_state.active_page = page_id
