"""
DataDumpAI Enterprise
Copilot Result Model
"""

from __future__ import annotations

from dataclasses import dataclass, field

from models.web_source import WebSource


@dataclass
class CopilotResult:
    """Executive Copilot response."""

    answer: str
    project_name: str
    sources: list[str] = field(default_factory=list)
    web_sources: list[WebSource] = field(default_factory=list)
    notice: str | None = None
