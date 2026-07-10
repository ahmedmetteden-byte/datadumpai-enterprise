"""
DataDumpAI Enterprise
Search Result Model
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SearchResult:
    """
    A single enterprise search hit across projects, documents, or reports.
    """

    source_type: str
    title: str
    location: str
    excerpt: str
    project_id: str
    project_name: str
    path: str = ""

    def to_dict(self) -> dict:
        """Return a plain dictionary representation."""

        return {
            "source_type": self.source_type,
            "title": self.title,
            "location": self.location,
            "excerpt": self.excerpt,
            "project_id": self.project_id,
            "project_name": self.project_name,
            "path": self.path,
        }
