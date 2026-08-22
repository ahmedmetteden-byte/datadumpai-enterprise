"""
Quality-control pass for generated reports (Step F of the Premium Report
Generation Upgrade).

Runs after the narrative and charts are built, before the report is
saved. This pass FLAGS issues, it never fails the request — spec: "The
QC pass should flag or correct issues before export where safely
possible." Every check here is deterministic Python; a single optional
LLM-assisted check (unsupported claims, recommendation grounding — both
need semantic judgment regex can't do) is available but off by default,
since it adds latency/cost and is the least mature part of this layer.

Checks (deterministic, always run when enabled):
- numerical consistency: do the narrative's cited figures actually match
  quantitative_analysis_service's computed values?
- citation consistency: does every "**Source:**" filename actually belong
  to this report's source documents?
- chart consistency: did every chart the Report Plan required actually
  get built?
- period correctness: if the narrative compares against a previous
  report, was that report actually matched on the same period (second
  line of defense on top of SpaReportGenerationService._find_previous_
  report()'s own period_id filter)?
- duplicate content: does Executive Summary repeat Key Findings verbatim,
  or does a recommendation repeat another recommendation's Action?
- growth terminology: does the narrative say "CAGR"/"compound annual
  growth rate" even though this system never computes one?
- risk/opportunity formatting: is Risks & Issues / Opportunities either
  bulleted or a clean "none identified" statement, matching what the
  prompt asked for?
- recommendation structure: does every numbered Strategic Recommendation
  carry its own Action clause?
- evidence leaks: does Basis/Confidence/Source start its own line, or
  did it run into the preceding prose?
- document coverage: when the user explicitly requested every workspace
  document, does the report's evidence set actually cover all of them?
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

CHAT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"

REPORT_QC_ENABLED = os.getenv("REPORT_QC_ENABLED", "true").strip().lower() not in {
    "0",
    "false",
    "no",
}
REPORT_QC_LLM_CHECKS_ENABLED = os.getenv(
    "REPORT_QC_LLM_CHECKS_ENABLED", "false"
).strip().lower() not in {"0", "false", "no"}


@dataclass
class QCIssue:
    severity: str  # "high" | "medium" | "low"
    category: str
    message: str
    location: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "location": self.location,
        }


@dataclass
class QCReport:
    passed: bool
    issues: list[QCIssue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"passed": self.passed, "issues": [issue.to_dict() for issue in self.issues]}


_H2_HEADING = re.compile(r"^## (.+)$", re.MULTILINE)


def _split_sections(narrative: str) -> dict[str, str]:
    """Minimal H2-heading splitter — deliberately local and format-
    agnostic rather than reusing report_document_parser.py's
    _split_sections(), which is hard-wired to a different (dead)
    report format's section-title vocabulary."""

    matches = list(_H2_HEADING.finditer(narrative))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        title = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(narrative)
        sections[title] = narrative[start:end].strip()
    return sections


def _check_numerical_consistency(
    narrative: str, metric_tables: list[dict[str, Any]]
) -> list[QCIssue]:
    issues: list[QCIssue] = []

    for table in metric_tables:
        title = str(table.get("title") or "")
        calculations = table.get("calculations") or {}
        percents: list[float] = []

        total = calculations.get("total_change") or {}
        if total.get("percent") is not None:
            percents.append(float(total["percent"]))
        for change in calculations.get("period_over_period") or []:
            if change.get("percent") is not None:
                percents.append(float(change["percent"]))

        for percent in percents:
            formatted = f"{abs(percent):.1f}%"
            if formatted not in narrative:
                issues.append(
                    QCIssue(
                        severity="medium",
                        category="numerical_consistency",
                        message=(
                            f"Calculated figure {formatted} for {title!r} does not appear "
                            "anywhere in the narrative."
                        ),
                        location=title,
                    )
                )

    return issues


_NARRATIVE_PERCENT = re.compile(r"(-?\d+(?:\.\d+)?)\s*%")
_IMPLAUSIBLE_PERCENT_THRESHOLD = 200.0


def _check_no_implausible_ungrounded_percentages(
    narrative: str, metric_tables: list[dict[str, Any]]
) -> list[QCIssue]:
    """Safety net for Phase 3's structured-data fixes: an implausibly
    large percentage (>200%) that doesn't match any deterministically
    computed or as-reported figure is exactly the failure signature of the
    414.3%-style bug this phase fixed at the extraction layer (a
    change/rate column mistakenly recomputed on top of itself). Only
    flags large, unmatched figures — small everyday percentages are left
    alone, since ordinary prose cites plenty of legitimate ones this
    system never tries to model."""

    known: set[str] = set()
    for table in metric_tables:
        calculations = table.get("calculations") or {}
        total = calculations.get("total_change") or {}
        if total.get("percent") is not None:
            known.add(f"{abs(float(total['percent'])):.1f}")
        for change in calculations.get("period_over_period") or []:
            if change.get("percent") is not None:
                known.add(f"{abs(float(change['percent'])):.1f}")
        for item in table.get("reported_change") or []:
            match = _NARRATIVE_PERCENT.search(str(item.get("reported") or ""))
            if match:
                known.add(f"{abs(float(match.group(1))):.1f}")

    if not known:
        # No structured metrics in this report at all — nothing to
        # cross-check narrative percentages against; skip rather than
        # flag every percentage as "ungrounded".
        return []

    issues: list[QCIssue] = []
    seen: set[str] = set()
    for match in _NARRATIVE_PERCENT.finditer(narrative):
        value = abs(float(match.group(1)))
        if value <= _IMPLAUSIBLE_PERCENT_THRESHOLD:
            continue
        formatted = f"{value:.1f}"
        if formatted in known or formatted in seen:
            continue
        seen.add(formatted)
        issues.append(
            QCIssue(
                severity="high",
                category="implausible_percentage",
                message=(
                    f"Narrative cites {match.group(0).strip()}, an implausibly large change "
                    "that does not match any Verified Calculation or as-reported figure — "
                    "likely a fabricated or miscomputed percentage."
                ),
                location=match.group(0).strip(),
            )
        )

    return issues


_SOURCE_LINE = re.compile(r"\*\*Source:\*\*\s*(.+)")


def _check_citation_consistency(
    narrative: str, source_documents: list[str]
) -> list[QCIssue]:
    issues: list[QCIssue] = []
    known = set(source_documents)

    for match in _SOURCE_LINE.finditer(narrative):
        raw = match.group(1).strip()
        for filename in raw.split(","):
            filename = filename.strip().strip("`*").strip()
            if not filename or filename in known:
                continue
            issues.append(
                QCIssue(
                    severity="high",
                    category="citation_consistency",
                    message=f"Cited source {filename!r} is not among this report's source documents.",
                    location=filename,
                )
            )

    return issues


def _check_chart_consistency(
    chart_requirements: list[dict[str, Any]], visualizations: list[dict[str, Any]]
) -> list[QCIssue]:
    issues: list[QCIssue] = []
    visualization_titles = {str(v.get("title") or "") for v in visualizations}

    for requirement in chart_requirements:
        title = str(requirement.get("metric_title") or "")
        if title and title not in visualization_titles:
            issues.append(
                QCIssue(
                    severity="medium",
                    category="chart_consistency",
                    message=(
                        f"The Report Plan required a chart for {title!r} but no matching "
                        "visualization was built."
                    ),
                    location=title,
                )
            )

    return issues


_RISK_OR_OPPORTUNITY_HEADING = re.compile(r"risk|opportunit", re.IGNORECASE)
_BULLET_LINE = re.compile(r"^[-*]\s+", re.MULTILINE)
_WHOLE_SECTION_NEGATIVE = re.compile(
    r"^(no|none|not\s+applicable|n/a)\b.*$", re.IGNORECASE | re.DOTALL
)


def _check_risk_opportunity_formatting(narrative: str) -> list[QCIssue]:
    """Risks & Issues / Opportunities are prompted to be either bulleted
    items or a single 'No ... were identified in the evidence reviewed'
    sentence. Unstructured prose with real content still gets picked up
    by report_document_parser.py's prose fallback at export time, but is
    flagged here as a quality regression worth a second look — it means
    the model didn't follow the requested format."""

    issues: list[QCIssue] = []
    sections = _split_sections(narrative)

    for title, body in sections.items():
        if not _RISK_OR_OPPORTUNITY_HEADING.search(title):
            continue

        stripped = body.strip()
        if not stripped or _BULLET_LINE.search(stripped) or _WHOLE_SECTION_NEGATIVE.match(stripped):
            continue

        issues.append(
            QCIssue(
                severity="low",
                category="risk_opportunity_formatting",
                message=(
                    f"{title!r} is neither bulleted nor a clean 'none identified' "
                    "statement — the model didn't follow the requested format."
                ),
                location=title,
            )
        )

    return issues


_NUMBERED_ITEM = re.compile(r"^\d{1,2}[.)]\s+.*?(?=^\d{1,2}[.)]\s+|\Z)", re.MULTILINE | re.DOTALL)


def _check_recommendation_has_action(narrative: str) -> list[QCIssue]:
    """Every numbered Strategic Recommendation must carry its own
    **Action:** clause — premium_pdf_export.py's "numbered" block
    rendering (Step C) depends on it being present to show anything
    other than Rationale/Measurement with no visible title."""

    sections = _split_sections(narrative)
    body = sections.get("Strategic Recommendations", "")
    if not body.strip():
        return []

    issues: list[QCIssue] = []
    for index, match in enumerate(_NUMBERED_ITEM.finditer(body), start=1):
        if "**Action:**" not in match.group(0):
            issues.append(
                QCIssue(
                    severity="medium",
                    category="recommendation_structure",
                    message=f"Strategic Recommendation #{index} has no Action clause.",
                    location=f"Recommendation {index}",
                )
            )

    return issues


_EVIDENCE_LABELS = ("Basis", "Confidence", "Source")


def _check_evidence_leaks_into_narrative(narrative: str) -> list[QCIssue]:
    """Basis/Confidence/Source must each start their own line — if the
    model runs one onto the end of the finding's prose instead (despite
    the prompt explicitly forbidding this, Step A), the parser can't
    isolate it and it renders as plain, unstyled text inside the
    paragraph rather than the subordinate Evidence block."""

    issues: list[QCIssue] = []

    for line in narrative.splitlines():
        stripped = line.strip()

        for label in _EVIDENCE_LABELS:
            marker = f"{label}:"
            idx = stripped.find(marker)
            if idx <= 0:
                continue

            prefix = stripped[:idx].strip().strip("*").strip()
            if prefix:
                issues.append(
                    QCIssue(
                        severity="medium",
                        category="evidence_leak",
                        message=(
                            f"{label!r} tag appears to run into preceding text instead of "
                            f"starting its own line: {stripped[:80]!r}"
                        ),
                        location=label,
                    )
                )
                break

    return issues


_CAGR_TERM = re.compile(r"\bCAGR\b|compound(?:ed)? annual growth rate", re.IGNORECASE)


def _check_growth_terminology(narrative: str) -> list[QCIssue]:
    """The system has no CAGR-computation capability today —
    quantitative_analysis_service.py only ever computes period-over-
    period and total-change deltas, never a rate compounded across
    multiple periods — so any 'CAGR' / 'compound annual growth rate' in
    the narrative is always an unverified LLM word choice, not a cited
    calculation, regardless of how many periods the evidence spans."""

    issues: list[QCIssue] = []
    match = _CAGR_TERM.search(narrative)
    if match:
        issues.append(
            QCIssue(
                severity="medium",
                category="growth_terminology",
                message=(
                    f"Narrative uses {match.group(0)!r}, but no compound annual growth rate is "
                    "ever computed by this system — likely mislabeling a year-over-year or "
                    "total-period change as a compounded rate."
                ),
                location=match.group(0),
            )
        )

    return issues


def _check_period_correctness(
    narrative: str, previous_report: dict[str, Any] | None, period_id: str
) -> list[QCIssue]:
    issues: list[QCIssue] = []
    if "## Changes Since Last Report" not in narrative:
        return issues

    if not previous_report:
        issues.append(
            QCIssue(
                severity="high",
                category="period_correctness",
                message=(
                    "Narrative includes a 'Changes Since Last Report' section but no previous "
                    "report was matched for comparison."
                ),
            )
        )
        return issues

    previous_period_id = previous_report.get("periodId")
    if previous_period_id and previous_period_id != period_id:
        issues.append(
            QCIssue(
                severity="high",
                category="period_correctness",
                message=(
                    "'Changes Since Last Report' compares against a previous report with period "
                    f"{previous_period_id!r}, not the current report's period {period_id!r}."
                ),
            )
        )

    return issues


def _sentences(text: str) -> set[str]:
    return {s.strip() for s in text.replace("\n", " ").split(".") if len(s.strip()) > 25}


_ACTION_LINE = re.compile(r"\*\*Action:\*\*\s*(.+)")


def _check_duplicate_content(narrative: str) -> list[QCIssue]:
    issues: list[QCIssue] = []
    sections = _split_sections(narrative)

    executive_summary = sections.get("Executive Summary", "")
    key_findings = sections.get("Key Findings", "")
    overlap = _sentences(executive_summary) & _sentences(key_findings)
    if overlap:
        issues.append(
            QCIssue(
                severity="low",
                category="duplicate_content",
                message=(
                    f"{len(overlap)} sentence(s) appear verbatim in both Executive Summary and "
                    "Key Findings."
                ),
            )
        )

    recommendations = sections.get("Strategic Recommendations", "")
    actions = [match.group(1).strip() for match in _ACTION_LINE.finditer(recommendations)]
    seen: set[str] = set()
    for action in actions:
        if action in seen:
            issues.append(
                QCIssue(
                    severity="low",
                    category="duplicate_content",
                    message=f"Duplicate recommendation action: {action!r}",
                )
            )
        seen.add(action)

    return issues


def _check_document_coverage(source_coverage: dict[str, Any] | None) -> list[QCIssue]:
    """When the user explicitly requested every document in the workspace
    (Document Coverage fix), verify the report's evidence set actually
    covers all of them — a document silently missing despite an explicit
    "use all documents" request is a trust violation the user must be
    able to see, not something that passes unnoticed. High severity: this
    is exactly the failure mode the fix exists to prevent."""

    if not source_coverage or not source_coverage.get("all_documents_requested"):
        return []

    in_scope = int(source_coverage.get("documents_in_scope") or 0)
    covered = int(source_coverage.get("documents_covered") or 0)

    if covered >= in_scope:
        return []

    gaps = source_coverage.get("gaps") or []
    gap_desc = "; ".join(f"{gap['filename']} ({gap['reason']})" for gap in gaps) or "unspecified"

    return [
        QCIssue(
            severity="high",
            category="document_coverage",
            message=(
                f"User requested all {in_scope} workspace documents, but only {covered} are "
                f"represented in the report's evidence set. Missing: {gap_desc}."
            ),
        )
    ]


def _run_llm_qc_check(client: Any, narrative: str, evidence: str) -> list[QCIssue]:
    """LLM-assisted checks needing semantic judgment: does every
    non-obvious claim trace to the evidence, and does every recommendation
    follow from a stated finding? Off by default
    (REPORT_QC_LLM_CHECKS_ENABLED). Never raises — a failed call just
    means no LLM-derived issues are added; the deterministic checks above
    still ran regardless."""

    prompt = (
        "Review this report narrative against its evidence. Identify only genuine problems:\n"
        "1. UNSUPPORTED CLAIMS: a specific factual claim with no clear basis in the evidence.\n"
        "2. UNGROUNDED RECOMMENDATIONS: a Strategic Recommendation whose Rationale does not "
        "follow from any Key Finding.\n"
        "Do not flag stylistic issues, and do not flag a claim just because it is an "
        "interpretation labeled as such ('Basis: Analytical inference' is expected, not a "
        "defect).\n"
        'Respond with a JSON object: {"issues": [{"category": "unsupported_claim" or '
        '"ungrounded_recommendation", "message": "..."}]}. Return {"issues": []} if none.\n\n'
        f"Evidence:\n{evidence}\n\nReport narrative:\n{narrative}"
    )

    try:
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            temperature=0,
            max_tokens=1024,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a meticulous fact-checker for executive reports. Only flag "
                        "genuine problems, never stylistic preferences."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        payload = json.loads(response.choices[0].message.content or "{}")
    except Exception:
        logger.exception("QC LLM check failed; skipping LLM-derived issues")
        return []

    issues: list[QCIssue] = []
    for item in payload.get("issues") or []:
        message = str(item.get("message") or "").strip()
        if not message:
            continue
        category = str(item.get("category") or "unsupported_claim")
        issues.append(QCIssue(severity="medium", category=category, message=message))

    return issues


def run_qc_pass(
    narrative: str,
    source_documents: list[str],
    *,
    metric_tables: list[dict[str, Any]] | None = None,
    chart_requirements: list[dict[str, Any]] | None = None,
    visualizations: list[dict[str, Any]] | None = None,
    previous_report: dict[str, Any] | None = None,
    period_id: str = "",
    evidence: str = "",
    source_coverage: dict[str, Any] | None = None,
    llm_client: Any = None,
) -> QCReport:
    """Run every enabled QC check and return a QCReport. Never raises and
    never blocks generation — callers should attach the result to
    report.metadata["qc_report"] for visibility, not act as a gate."""

    if not REPORT_QC_ENABLED:
        return QCReport(passed=True, issues=[])

    issues: list[QCIssue] = []
    issues.extend(_check_numerical_consistency(narrative, metric_tables or []))
    issues.extend(_check_no_implausible_ungrounded_percentages(narrative, metric_tables or []))
    issues.extend(_check_citation_consistency(narrative, source_documents))
    issues.extend(_check_chart_consistency(chart_requirements or [], visualizations or []))
    issues.extend(_check_period_correctness(narrative, previous_report, period_id))
    issues.extend(_check_duplicate_content(narrative))
    issues.extend(_check_growth_terminology(narrative))
    issues.extend(_check_risk_opportunity_formatting(narrative))
    issues.extend(_check_recommendation_has_action(narrative))
    issues.extend(_check_evidence_leaks_into_narrative(narrative))
    issues.extend(_check_document_coverage(source_coverage))

    if REPORT_QC_LLM_CHECKS_ENABLED and llm_client is not None:
        issues.extend(_run_llm_qc_check(llm_client, narrative, evidence))

    passed = not any(issue.severity == "high" for issue in issues)
    return QCReport(passed=passed, issues=issues)
