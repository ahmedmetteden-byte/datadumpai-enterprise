"""
Executive intelligence report type gating for DataDumpAI.

The prompt-building side of this module (build_executive_report_prompt,
uses_intelligence_format, and the static template) was removed as dead
code: SpaReportGenerationService (services/spa_report_generation_service.py)
is the actual live report generation path and has its own inline prompt
construction — nothing in the API or services layer called into this
module's prompt builder, only its own unit tests did.
INTELLIGENCE_REPORT_TYPES remains: it's a real plan-gating primitive used
by PlanService.uses_intelligence_format().
"""

from __future__ import annotations

INTELLIGENCE_REPORT_TYPES = frozenset(
    {
        "Executive Summary",
        "Board Report",
        "Management Report",
        "Financial Analysis",
        "Regulatory Compliance Report",
        "Risk Assessment Report",
        "Meeting Intelligence Report",
        "Market Intelligence Report",
        "Strategic Planning Report",
        "Executive Intelligence Dashboard",
    }
)
