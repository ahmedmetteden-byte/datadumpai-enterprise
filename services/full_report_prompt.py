"""
Prompt builder for comprehensive period rollup reports (Full Report).
"""

from __future__ import annotations

from typing import Any

FULL_REPORT_TYPE = "Full Report"


def is_full_report(report_type: str) -> bool:
    return report_type == FULL_REPORT_TYPE


def build_full_report_prompt(
    *,
    document_text: str,
    writing_style: str,
    audience: str,
    include_recommendations: bool,
    include_charts: bool,
    source_document_count: int,
    report_context: dict[str, Any],
    canonical_metrics_section: str = "",
) -> str:
    """Return the user prompt for a comprehensive multi-document period rollup."""

    source_list = report_context.get("source_documents") or []
    source_manifest = "\n".join(f"- {name}" for name in source_list) or "- (not provided)"
    reporting_period = report_context.get("reporting_period", "Comprehensive Report")
    period_guidance = report_context.get("period_guidance", "")
    prior_context = (report_context.get("prior_reports_context") or "").strip()
    prior_section = f"\n\n{prior_context}\n" if prior_context else ""
    has_prior = report_context.get("has_prior_reports", False)

    recommendations_block = """
## Consolidated Recommendations

For each recommendation use this structure:

### [Recommendation title]
**Priority:** Critical | High | Medium
**Action:** One clear imperative sentence.
**Implementation:** 2–3 specific steps.
**Expected impact:** What improves if this is done.
**Confidence:** NN%
**Source coverage:** This theme appeared in X of {source_document_count} period documents.
""".format(source_document_count=source_document_count)

    charts_block = """
## Visual Summary

Briefly describe the visuals. Charts are rendered automatically by the application
from the canonical metrics above. Do NOT output a REPORT_CHARTS block or invent
chart values.
"""

    if not include_recommendations:
        recommendations_block = ""

    if not include_charts:
        charts_block = ""
        canonical_metrics_section = ""

    metrics_section = canonical_metrics_section.strip()
    if metrics_section:
        metrics_section = f"\n{metrics_section}\n"

    return f"""
Create a comprehensive **Full Report** — a period rollup that synthesizes multiple
source documents into one cohesive {reporting_period.lower()}.

Use case: the user has uploaded separate reports for individual periods (e.g. week 1–4,
January–March, or monthly updates) and needs a single consolidated report for the
full reporting period.

Reporting period scope: **{reporting_period}**
{period_guidance}

You are synthesizing {source_document_count} source document(s). Treat each
`=== SOURCE DOCUMENT: filename ===` section as a distinct period input unless the
content clearly indicates otherwise. Combine overlapping information; do not rely on
only the first document.

Audience: {audience}
Writing style: {writing_style}

SOURCE DOCUMENT MANIFEST
{source_manifest}
{metrics_section}
RULES
- Never invent facts, figures, dates, or document names.
- Infer the reporting period from document names, dates, and content when possible.
- Show how themes, risks, and metrics evolved across the document set.
- Quantify recurring themes as "X of {source_document_count} documents" when supportable.
- Compare earlier vs later documents in the set when a time sequence is evident.
- Use status icons: 🔴 Critical, 🟠 High, 🟡 Medium/Cautious, 🟢 Positive/Opportunity.
- Use markdown only. Do not wrap the report body in code fences.

REQUIRED REPORT STRUCTURE (use these exact ## headings in order)

## Full Report Overview

### Executive Summary Card
Present as a markdown table with exactly these rows:
| Field | Value |
| Reporting Period | {reporting_period} |
| Documents Consolidated | {source_document_count} |
| Period Status | 🟡 Cautious (or 🟢 Stable / 🔴 At Risk) |
| Confidence | NN% |
| Overall Trend | Improving / Stable / Declining / Mixed |

### Period Snapshot
| Metric | Value |
| Source documents analyzed | {source_document_count} |
| Reporting scope | {reporting_period} |
| Key themes across periods | N |
| Critical risks carried forward | N |
| New issues in latest period | N |
| Overall outlook | Stable / Cautious / At Risk / Positive |

## Period Narrative
Write a cohesive executive narrative that rolls up all source documents into one story.
Explain what happened across the full period, how priorities shifted, and what leadership
should take away. Reference specific source documents by filename.

## Cross-Period Themes
Identify 4–6 themes that appear across multiple source documents. For each:
- **Theme name** — how it evolved from earlier to later documents
- **Frequency:** X of {source_document_count} documents
- **Trend:** Rising / Stable / Declining

## Period-over-Period Comparison
Compare earlier vs later documents in the uploaded set (or vs prior saved reports
when provided). Use a table when helpful:
| Area | Earlier Period | Latest Period | Trend |
If sequence is unclear, state assumptions and compare document clusters instead.

## Consolidated Key Findings
Group findings under ### Critical, ### High Priority, and ### Medium Priority.
Each finding must cite supporting source document(s).

## Consolidated Risks
- 🔴 **[Risk]** — impact and which period documents support it
- 🟠 **[Risk]** — impact and trend across the period

## Consolidated Opportunities
- 🟢 **[Opportunity]** — benefit and supporting evidence

## Executive Quotations
Include 2–4 powerful quotes from across the source documents:
> "Exact quote."
> — *Source: filename*

{prior_section}

{recommendations_block}

{charts_block}

SOURCE MATERIAL
===============================

{document_text}
"""
