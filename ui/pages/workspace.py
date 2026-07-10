"""
DataDumpAI Enterprise
Workspace Page
"""

from __future__ import annotations

from ui.workspace.shell import render_workspace_shell


def render() -> None:
    """
    Project workspace — the home for everything inside a project.
    """

    render_workspace_shell()
