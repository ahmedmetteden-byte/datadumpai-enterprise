"""
Project Workspace — Timeline
"""

from __future__ import annotations

from core.workspace import Workspace
from ui.projects import get_current_project
from ui.timeline import render_timeline


def render() -> None:

    workspace = Workspace(
        get_current_project()["id"]
    )

    render_timeline(workspace)
