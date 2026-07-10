"""
DataDumpAI Enterprise
Session Manager

Centralized application session state.
"""

from __future__ import annotations

import streamlit as st


DEFAULT_STATE = {
    "active_page": "workspace",
    "current_project": None,
    "notifications": [],
    "sidebar_collapsed": False,
}


def initialize_session() -> None:
    """
    Initialize application session state.
    Safe to call multiple times.
    """
    for key, value in DEFAULT_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get(key: str, default=None):
    return st.session_state.get(key, default)


def set(key: str, value):
    st.session_state[key] = value


def reset():
    """
    Reset application state back to defaults.
    """
    for key in list(DEFAULT_STATE.keys()):
        st.session_state[key] = DEFAULT_STATE[key]