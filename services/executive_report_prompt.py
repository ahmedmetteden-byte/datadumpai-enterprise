"""
Executive intelligence report prompt and template for DataDumpAI.
"""

from __future__ import annotations

from typing import Any

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

INTELLIGENCE_DASHBOARD_TITLE = "Executive Intelligence Dashboard"


def uses_intelligence_format(report_type: str) -> bool:
    return report_type in INTELLIGENCE_REPORT_TYPES


def build_executive_report_prompt(
    *,
    report_type: str,
    document_text: str,
    writing_style: str,
    audience: str,
    include_recommendations: bool,
    include_charts: bool,
    source_document_count: int,
    report_context: dict[str, Any],
    canonical_metrics_section: str = "",
) -> str:
    """Return the user prompt for an executive intelligence report."""

    source_list = report_context.get("source_documents") or []
    source_manifest = "\n".join(f"- {name}" for name in source_list) or "- (not provided)"
    frequency_hint = report_context.get("frequency_hint", "")
    prior_context = (report_context.get("prior_reports_context") or "").strip()
    prior_section = f"\n\n{prior_context}\n" if prior_context else ""
    has_prior = report_context.get("has_prior_reports", False)

    recommendations_block = f"""
## Strategic Recommendations

For each recommendation use this structure:

### [Recommendation title]
**Priority:** Critical | High | Medium
**Action:** One clear imperative sentence.
**Implementation:** 2–3 specific steps (people, process, technology, or timeline).
**Expected impact:** What improves if this is done.
**Confidence:** NN%
**Cross-document reach:** This theme appeared in X of {source_document_count} documents.
"""

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
Create a professional {report_type} using DataDumpAI's Executive Intelligence format.

You are synthesizing {source_document_count} source document(s). Every section marked
`=== SOURCE DOCUMENT: filename ===` must be reviewed. Combine overlapping information;
do not rely on only the first document.

Audience: {audience}
Writing style: {writing_style}

SOURCE DOCUMENT MANIFEST
{source_manifest}
{metrics_section}
CROSS-DOCUMENT FREQUENCY
{frequency_hint or f"Use 'X of {source_document_count} documents' when citing how often a theme appears."}

RULES
- Never invent facts, figures, dates, or document names.
- Every major claim needs evidence from the supplied sources.
- Assign confidence scores (0–100%) based on how often and how clearly sources support the claim.
- Rank findings by executive importance: Critical, High, Medium.
- Quantify recurring themes as percentages that sum to roughly 100%.
- Recommendations must be specific and actionable — not generic advice.
- Use markdown only for the main report. Do not wrap the report body in code fences.
- Quantify cross-document patterns as "X of {source_document_count} documents" when supportable.
- Use status icons: 🔴 Critical, 🟠 High, 🟡 Medium/Cautious, 🟢 Positive/Opportunity.

REQUIRED REPORT STRUCTURE (use these exact ## headings in order)

## {INTELLIGENCE_DASHBOARD_TITLE}

### Executive Summary Card
Present as a markdown table with exactly these rows:
| Field | Value |
| Industry Status | 🟡 Cautious (or 🟢 Stable / 🔴 At Risk) |
| Confidence | NN% |
| Priority | (top executive priority) |
| Overall Trend | Improving / Stable / Declining |

### Executive Snapshot
Present as a markdown table with rows such as:
| Metric | Value |
| Documents analyzed | {source_document_count} |
| Reporting period | (infer from documents or state "Not specified") |
| Key themes identified | N |
| Critical risks | N |
| Recommendations | N |
| Overall outlook | Stable / Cautious / At Risk / Positive |
| AI confidence | NN% |

### Overall Health Score
**Score:** NN/100
**Outlook:** (one sentence)

### Top Discussion Topics
List 4–6 themes as bullet points with percentages only (charts are rendered separately):
- Claims — 31%
- Capital — 21%

### Top Risks
Use severity icons on each bullet:
- 🔴 **[Risk name]** — one-line impact
- 🟠 **[Risk name]** — one-line impact

### Key Opportunities
Use opportunity icons on each bullet:
- 🟢 **[Opportunity name]** — one-line benefit
- 🟢 **[Opportunity name]** — one-line benefit

## Cross-Document Intelligence
Provide 3–5 quantified intelligence statements such as:
- This recommendation appeared in **7 of {source_document_count}** documents.
- Governance issues increased by **32%** compared to the previous reporting period.
- Claims discussions have become progressively more frequent across the document set.
Each line must be supportable from the sources{" or prior reports" if has_prior else ""}.

## Industry Benchmark
Compare current vs previous period where supportable:
| Metric | Current | Previous | Trend |
| Claims Risk | High | Medium | ↑ |
| Capital Adequacy | Medium | Medium | → |
If prior period data is unavailable, compare **Current Project** vs **Earlier Documents**
or state what cannot be benchmarked yet.

## Executive Quotations
Include 2–4 powerful quotes from the source documents using blockquote format:
> "Exact quote from the document."
> — *Source: filename or document title*

## Key Findings (Ranked by Importance)

Group findings under these ### subheadings:
### Critical
### High
### Medium

For EACH finding use this template:

#### [Finding title]
**Confidence:** NN%
**Summary:** One sentence.
**Mentioned in:**
- ✓ [source filename or document type]
- ✓ [source filename or document type]
**Evidence:**
- [Document/source]: [specific quote, date, figure, or fact]
- [Document/source]: [specific quote, date, figure, or fact]
**Source confidence:** High | Medium | Low

## AI Insights
Provide 2–4 cross-document observations executives would miss from reading files manually.
Each insight must cite which documents support it, quantify frequency where possible,
and explain the connection.

## Trends
If prior reports exist and support comparison, show theme changes with percentages and
interpretation such as: "Claims issues are receiving significantly more attention than
in the previous period."
If not supportable, state that clearly.

{charts_block}
{recommendations_block}

## Detailed Narrative
Executive summary prose, analysis, risks, and opportunities in full paragraphs.
Reference sources inline where helpful.

{prior_section}
SOURCE MATERIAL
===============================

{document_text}
"""
