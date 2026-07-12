"""Integration tests for AI Workspace routing."""

from __future__ import annotations

import inspect

from core.workspace_navigation import (
    AI_WORKSPACE_SECTION,
    LEGACY_PAGE_ALIASES,
    resolve_workspace_section,
)
from ui.ai_workspace import render_ai_workspace
from ui.workspace.sections import documents as documents_section
from ui.workspace.shell import _section_renderer


def test_legacy_page_aliases_route_documents_to_ai_workspace_section():
    for page_id in ("documents", "report_studio", "ai_workspace", "generate", "knowledge"):
        assert resolve_workspace_section(page_id) == AI_WORKSPACE_SECTION
        assert LEGACY_PAGE_ALIASES[page_id] == "documents"


def test_shell_section_renderer_documents_uses_workspace_section_module():
    renderer = _section_renderer("documents")
    assert renderer is documents_section.render


def test_documents_section_delegates_to_ai_workspace_module():
    source = inspect.getsource(documents_section.render)
    assert "render_ai_workspace" in source
    assert render_ai_workspace.__module__ == "ui.ai_workspace"
