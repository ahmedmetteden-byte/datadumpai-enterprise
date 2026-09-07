"""
Full Report type gating for DataDumpAI.

The prompt-building side of this module (build_full_report_prompt and its
static template) was removed as dead code: SpaReportGenerationService
(services/spa_report_generation_service.py) is the actual live report
generation path and has its own inline prompt construction — nothing in
the API or services layer called into this module's prompt builder, only
its own unit tests did. FULL_REPORT_TYPE / is_full_report() remain: they're
real plan-gating primitives used by PlanService and report_document.py.
"""

from __future__ import annotations

FULL_REPORT_TYPE = "Full Report"


def is_full_report(report_type: str) -> bool:
    return report_type == FULL_REPORT_TYPE
