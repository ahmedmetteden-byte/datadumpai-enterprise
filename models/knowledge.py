"""
DataDumpAI Enterprise
Knowledge Model

Enterprise Knowledge is the searchable corpus of a Workspace.

Every document uploaded,
every report generated,
every AI conversation,
every meeting,
every presentation

...becomes part of one Knowledge Store.

Architecture direction:

    Workspace
        ↓
    Knowledge Store
        ↓
    Search
        ↓
    AI
        ↓
    Executive Intelligence
"""

from __future__ import annotations

from dataclasses import dataclass, field


SOURCE_TYPES = (
    "document",
    "report",
    "export",
    "timeline",
    "meeting",
    "presentation",
    "conversation",
)

SOURCE_ICONS = {
    "document": "📄",
    "report": "📑",
    "export": "⬇",
    "timeline": "🕘",
    "meeting": "🎙",
    "presentation": "📽",
    "conversation": "💬",
}


@dataclass
class KnowledgeEntry:
    """
    One unit of enterprise knowledge.

    All source types share this shape so Search and AI
    can query a single corpus.
    """

    id: str
    source_type: str
    title: str
    path: str = ""
    created_at: str = ""
    summary: str = ""
    metadata: dict = field(default_factory=dict)

    @property
    def icon(self) -> str:
        return SOURCE_ICONS.get(self.source_type, "📎")


@dataclass
class KnowledgeStore:
    """
    The complete knowledge corpus for one Workspace.

    This is not a UI concept.
    Search, Copilot, and Executive Intelligence all read from here.
    """

    entries: list[KnowledgeEntry] = field(default_factory=list)
    document_count: int = 0
    report_count: int = 0
    export_count: int = 0
    meeting_count: int = 0
    presentation_count: int = 0
    conversation_count: int = 0
    timeline_count: int = 0

    @property
    def source_count(self) -> int:
        return len(self.entries)

    @property
    def ready(self) -> bool:
        return self.source_count > 0

    def by_type(self, source_type: str) -> list[KnowledgeEntry]:
        return [
            entry
            for entry in self.entries
            if entry.source_type == source_type
        ]

    @property
    def documents(self) -> list[KnowledgeEntry]:
        return self.by_type("document")

    @property
    def reports(self) -> list[KnowledgeEntry]:
        return self.by_type("report")

    @property
    def exports(self) -> list[KnowledgeEntry]:
        return self.by_type("export")

    @property
    def meetings(self) -> list[KnowledgeEntry]:
        return self.by_type("meeting")

    @property
    def presentations(self) -> list[KnowledgeEntry]:
        return self.by_type("presentation")

    @property
    def conversations(self) -> list[KnowledgeEntry]:
        return self.by_type("conversation")
