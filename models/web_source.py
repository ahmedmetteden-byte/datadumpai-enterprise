"""
Web search result for Ask AI citations.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WebSource:
    title: str
    url: str
    snippet: str
