"""
Build metadata context for executive intelligence reports.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from services.report_service import ReportService


PRIOR_REPORT_SNIPPET_CHARS = 900
MAX_PRIOR_REPORTS = 2


class ExecutiveReportContextBuilder:
    """Assemble workspace metadata to enrich report generation."""

    def build(
        self,
        *,
        workspace_id: str,
        source_documents: list[str],
        report_type: str,
        include_prior_reports: bool = True,
    ) -> dict[str, Any]:
        prior_reports = (
            self._prior_report_context(workspace_id)
            if include_prior_reports
            else ""
        )

        frequency_hint = ""
        if include_prior_reports:
            frequency_hint = (
                f"When quantifying cross-document patterns, express frequency as "
                f"'X of {len(source_documents)} documents' whenever supportable."
            )

        return {
            "report_type": report_type,
            "source_documents": source_documents,
            "document_count": len(source_documents),
            "generated_at": datetime.now(timezone.utc).strftime("%d %b %Y"),
            "prior_reports_context": prior_reports,
            "has_prior_reports": bool(prior_reports),
            "frequency_hint": frequency_hint,
        }

    def _prior_report_context(self, workspace_id: str) -> str:
        """Summarize recent saved reports so the model can note trends."""

        reports = ReportService.get_reports(workspace_id)

        if not reports:
            return ""

        sorted_reports = sorted(
            reports,
            key=lambda report: report.get("created_at", ""),
            reverse=True,
        )

        blocks: list[str] = []

        for report in sorted_reports[:MAX_PRIOR_REPORTS]:
            path = report.get("path", "")

            if not path:
                continue

            try:
                text = ReportService.load_report(path).strip()
            except OSError:
                continue

            if not text:
                continue

            created = (report.get("created_at") or "")[:10] or "unknown date"
            snippet = text[:PRIOR_REPORT_SNIPPET_CHARS]

            blocks.append(
                f"Prior report: {report.get('name', 'Report')} ({created})\n"
                f"{snippet}"
            )

        if not blocks:
            return ""

        return (
            "PRIOR REPORTS IN THIS WORKSPACE (use only for trend comparison "
            "when the current documents support it; do not invent history):\n\n"
            + "\n\n---\n\n".join(blocks)
        )
