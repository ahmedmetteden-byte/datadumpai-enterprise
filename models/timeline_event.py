"""
DataDumpAI Enterprise
Timeline Event Model
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TimelineEvent:
    """A single recorded workspace action."""

    id: str
    timestamp: str
    action: str
    message: str
    metadata: dict = field(default_factory=dict)
