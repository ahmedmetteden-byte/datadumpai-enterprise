"""
Project Workspace — AI Workspace (conversational report and analysis)
"""

from __future__ import annotations

import inspect
import logging

from ui.ai_workspace import render_ai_workspace

logger = logging.getLogger(__name__)


def render() -> None:
    logger.info(
        "Documents section delegating to %s (%s)",
        render_ai_workspace.__module__,
        inspect.getfile(render_ai_workspace),
    )
    render_ai_workspace()
