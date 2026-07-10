"""
Enterprise Search Bar
"""

from __future__ import annotations

import streamlit as st


def render_search_bar():

    return st.text_input(
        "Search Workspace",
        placeholder="Search reports, documents and knowledge...",
        label_visibility="collapsed",
    )
