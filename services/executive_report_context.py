"""
Build metadata context for executive intelligence reports.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from services.report_service import ReportService


PRIOR_REPORT_SNIPPET_CHARS = 900
MAX_PRIOR_REPORTS = 2
FULL_REPORT_PRIOR_SNIPPET_CHARS = 1200
MAX_FULL_REPORT_PRIOR_REPORTS = 8

PERIOD_GUIDANCE = {
    "Weekly Report": (
        "Roll up daily or weekly inputs into one weekly summary. Highlight what changed "
        "within the week and carry forward unresolved items."
    ),
    "Monthly Report": (
        "Roll up weekly or partial-month reports (e.g. week 1–4) into one monthly "
        "executive report. Show progression across the month and month-end priorities."
    ),
    "Quarterly Report": (
        "Roll up monthly or period reports (e.g. January–March) into one quarterly "
        "report. Emphasize quarterly trends, cumulative metrics, and strategic outlook."
    ),
    "Annual Report": (
        "Roll up monthly, quarterly, or period reports (e.g. Q1–Q4 or January–December) "
        "into one annual report. Emphasize full-year performance, year-over-year trends, "
        "and strategic priorities for the year ahead."
    ),
    "Comprehensive Report": (
        "Synthesize all uploaded period documents into one comprehensive rollup regardless "
        "of cadence. Infer the best reporting period from filenames and content."
    ),
}


class ExecutiveReportContextBuilder:
    """Assemble workspace metadata to enrich report generation."""

    def build(
        self,
        *,
        workspace_id: str,
        source_documents: list[str],
        report_type: str,
        include_prior_reports: bool = True,
        reporting_period: str | None = None,
    ) -> dict[str, Any]:
        full_report = report_type == "Full Report"
        prior_reports = (
            self._prior_report_context(
                workspace_id,
                full_report=full_report,
            )
            if include_prior_reports
            else ""
        )

        frequency_hint = ""
        if include_prior_reports:
            frequency_hint = (
                f"When quantifying cross-document patterns, express frequency as "
                f"'X of {len(source_documents)} documents' whenever supportable."
            )

        period = reporting_period or "Comprehensive Report"
        period_guidance = PERIOD_GUIDANCE.get(period, PERIOD_GUIDANCE["Comprehensive Report"])

        return {
            "report_type": report_type,
            "source_documents": source_documents,
            "document_count": len(source_documents),
            "generated_at": datetime.now(timezone.utc).strftime("%d %b %Y"),
            "prior_reports_context": prior_reports,
            "has_prior_reports": bool(prior_reports),
            "frequency_hint": frequency_hint,
            "reporting_period": period,
            "period_guidance": period_guidance,
            "is_full_report": full_report,
        }

    def _prior_report_context(self, workspace_id: str, *, full_report: bool = False) -> str:
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
        snippet_limit = (
            FULL_REPORT_PRIOR_SNIPPET_CHARS if full_report else PRIOR_REPORT_SNIPPET_CHARS
        )
        report_limit = MAX_FULL_REPORT_PRIOR_REPORTS if full_report else MAX_PRIOR_REPORTS

        for report in sorted_reports[:report_limit]:
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
            snippet = text[:snippet_limit]

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
