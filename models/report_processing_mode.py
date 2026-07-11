"""
Report processing modes — balance speed vs complete multi-stage analysis.
"""

from __future__ import annotations

from enum import Enum


class ReportProcessingMode(str, Enum):
    """How source documents are analysed before narrative generation."""

    FAST = "fast"
    COMPREHENSIVE = "comprehensive"

    @classmethod
    def from_value(cls, value: str | None) -> ReportProcessingMode:
        if value and value.lower() == cls.FAST.value:
            return cls.FAST
        return cls.COMPREHENSIVE


PROCESSING_MODE_OPTIONS: tuple[tuple[str, str], ...] = (
    (
        ReportProcessingMode.COMPREHENSIVE.value,
        "Comprehensive — analyses all content in multiple stages for maximum accuracy",
    ),
    (
        ReportProcessingMode.FAST.value,
        "Fast — quicker analysis, best for smaller or less critical reports",
    ),
)

DEFAULT_PROCESSING_MODE = ReportProcessingMode.COMPREHENSIVE
