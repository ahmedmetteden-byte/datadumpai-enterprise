"""
DataDumpAI Enterprise
Project Model
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Project:

    id: str

    name: str

    description: str = ""

    created_at: str = ""

    updated_at: str = ""

    last_activity: str = ""

    storage_used: int = 0

    documents: list = field(default_factory=list)

    reports: list = field(default_factory=list)

    exports: list = field(default_factory=list)