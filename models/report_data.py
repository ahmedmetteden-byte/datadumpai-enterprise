"""
Structured report data model — the canonical object for all report views.

Markdown, HTML, PDF, Word, and PowerPoint are rendered views of ReportData.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ReportData:
    """Canonical structured data for a generated report."""

    report_type: str = ""
    title: str = ""
    narrative: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    charts: dict[str, Any] = field(default_factory=dict)
    kpis: dict[str, Any] = field(default_factory=dict)
    source_documents: list[str] = field(default_factory=list)
    executive_summary: dict[str, Any] = field(default_factory=dict)
    sections: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[dict[str, Any]] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> ReportData:
        if not payload:
            return cls()

        return cls(
            report_type=str(payload.get("report_type") or ""),
            title=str(payload.get("title") or ""),
            narrative=str(payload.get("narrative") or ""),
            metadata=dict(payload.get("metadata") or {}),
            metrics=dict(payload.get("metrics") or {}),
            charts=dict(payload.get("charts") or {}),
            kpis=dict(payload.get("kpis") or {}),
            source_documents=list(payload.get("source_documents") or []),
            executive_summary=dict(payload.get("executive_summary") or {}),
            sections=list(payload.get("sections") or []),
            recommendations=list(payload.get("recommendations") or []),
            citations=list(payload.get("citations") or []),
        )

    def to_markdown(self, *, include_charts: bool = True) -> str:
        from services.report_document import report_data_to_markdown

        return report_data_to_markdown(self, include_charts=include_charts)

    @property
    def markdown(self) -> str:
        """Serialized markdown view, including canonical chart metadata when present."""

        return self.to_markdown()

    def with_narrative(self, narrative: str, *, include_charts: bool = True) -> ReportData:
        from services.report_chart_data import strip_chart_data
        from services.report_document import compose_report_data

        return compose_report_data(
            narrative=strip_chart_data(narrative),
            base=self,
            report_type=self.report_type,
            title=self.title or self.report_type,
            include_charts=include_charts,
        )
