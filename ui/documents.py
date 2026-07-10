"""
Legacy documents page — redirects to workspace documents section.
"""

from __future__ import annotations

from ui.workspace.sections.documents import render as render_documents_workspace


def render_documents() -> None:
    render_documents_workspace()
