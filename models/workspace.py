"""
DataDumpAI Enterprise
Workspace Model

The Workspace is the core domain object of DataDumpAI.

It is not a Streamlit page.
It is not a project.

A Project lives inside a Workspace.
The UI is only a window into a Workspace.

Workspace
│
├── Project
├── Documents
├── Reports
├── AI
├── Timeline
├── Analytics
├── Exports
└── Knowledge
"""

from __future__ import annotations

from dataclasses import dataclass, field

from models.knowledge import KnowledgeStore
from models.timeline_event import TimelineEvent


HEALTH_ICONS = {
    "ready": "🟢",
    "warning": "🟡",
    "critical": "🔴",
}


@dataclass
class WorkspaceHealthIndicator:
    """A single workspace readiness indicator."""

    status: str
    icon: str
    message: str


@dataclass
class WorkspaceAI:
    """
    AI readiness and capacity for this workspace.

    Describes whether Copilot and report generation can run,
    and what corpus they have available — not UI state.
    """

    ready: bool = False
    document_count: int = 0
    report_count: int = 0
    status: str = "AI not ready"


@dataclass
class WorkspaceAnalytics:
    """
    Aggregated workspace metrics.

    Calculated by WorkspaceService — never by the UI.
    """

    document_count: int = 0
    report_count: int = 0
    export_count: int = 0
    storage_used: int = 0
    last_activity: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass
class Workspace:
    """
    Complete domain Workspace assembled by WorkspaceService.

    Everything in DataDumpAI revolves around this object.
    The UI only renders what the Workspace contains.
    """

    project: dict
    documents: list = field(default_factory=list)
    reports: list = field(default_factory=list)
    ai: WorkspaceAI = field(default_factory=WorkspaceAI)
    timeline: list[TimelineEvent] = field(default_factory=list)
    analytics: WorkspaceAnalytics = field(default_factory=WorkspaceAnalytics)
    exports: list = field(default_factory=list)
    knowledge: KnowledgeStore = field(default_factory=KnowledgeStore)
    health: list[WorkspaceHealthIndicator] = field(default_factory=list)
    recent_documents: list = field(default_factory=list)
    recent_reports: list = field(default_factory=list)

    # ------------------------------------------------------------------
    # Convenience accessors (mirror analytics for callers)
    # ------------------------------------------------------------------

    @property
    def id(self) -> str:
        return self.project.get("id", "")

    @property
    def name(self) -> str:
        return self.project.get("name", "")

    @property
    def created_at(self) -> str:
        return self.analytics.created_at or self.project.get("created_at", "")

    @property
    def updated_at(self) -> str:
        return self.analytics.updated_at or self.project.get("updated_at", "")

    @property
    def document_count(self) -> int:
        return self.analytics.document_count

    @property
    def report_count(self) -> int:
        return self.analytics.report_count

    @property
    def storage_used(self) -> int:
        return self.analytics.storage_used

    @property
    def last_activity(self) -> str:
        return self.analytics.last_activity

    @property
    def export_count(self) -> int:
        return self.analytics.export_count
