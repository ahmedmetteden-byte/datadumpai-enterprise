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
- direction consistency (Phase 3 Step 4, Phase A): does the narrative's
  stated direction ("increased"/"decreased") or, for a small list of
  conventionally lower-is-better ratio metrics, sentiment
  ("improved"/"worsened") match the calculated sign?
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


# Words too short, common, or generic to distinguish one metric's title
# from a DIFFERENT metric's — "score", "rate", "value", "total"... appear
# across many unrelated metrics (the same underlying concern
# _check_no_generic_metric_titles below addresses for a whole title).
_TITLE_STOPWORDS = {
    "the", "of", "and", "or", "a", "an", "in", "on", "at", "for", "to", "is",
    "are", "was", "were", "by", "vs", "per",
    "score", "rate", "rating", "value", "total", "amount", "sum", "count",
    "figure", "number", "index", "level",
}

_TITLE_WORD = re.compile(r"[a-zA-Z]{4,}")


def _distinctive_title_words(title: str) -> list[str]:
    """Words from a metric title specific enough to distinguish it from a
    DIFFERENT metric — short/common/generic words excluded, since they'd
    make the proximity check below pass for almost any nearby text."""

    return [w for w in _TITLE_WORD.findall(title.lower()) if w not in _TITLE_STOPWORDS]


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
        cross_sectional = calculations.get("cross_sectional") or {}
        if cross_sectional.get("gap_percent") is not None:
            # Phase 3 Step 2: a categorical finding's gap figure needs the
            # same citation check as a temporal total_change — confirmed
            # via real-pipeline testing that the model can cite a correct
            # highest/lowest comparison while still inventing its own gap
            # magnitude instead of the deterministically computed one.
            percents.append(float(cross_sectional["gap_percent"]))

        distinctive_words = _distinctive_title_words(title)

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
            elif distinctive_words and not _has_nearby_word(narrative, formatted, distinctive_words):
                # Phase 3 Step 3: the figure IS present somewhere, but
                # never near any word distinctive to THIS metric's title
                # — it may be a coincidental match to a different
                # metric's figure that happens to round to the same
                # value (the "right number, wrong claim" case a pure
                # substring search can't catch). Skipped entirely when a
                # title has no distinctive word at all (e.g. an
                # already-generic title, flagged separately by
                # _check_no_generic_metric_titles) rather than risk a
                # false positive against a title too short to check.
                issues.append(
                    QCIssue(
                        severity="medium",
                        category="numerical_consistency",
                        message=(
                            f"The figure {formatted} appears in the narrative, but not near any "
                            f"mention of {title!r} — it may be cited for a different metric."
                        ),
                        location=title,
                    )
                )

    return issues


def _line_bounded_window(text: str, start: int, end: int, radius: int) -> tuple[int, int]:
    """A [start-radius, end+radius) window clamped so it never crosses a
    newline — found via Phase 3 Step 4, Phase B real E2E testing: a
    bulleted multi-metric answer ("- Claims incurred increased...\n-
    Claims backlog decreased...\n- Retention increased...") let a plain
    character-radius window bleed into the ADJACENT bullet's unrelated
    direction word, so a genuine contradiction on one bullet's own figure
    went undetected because both an "increased" (from the bullet above)
    and a "decreased" (the bullet's own, actually wrong, word) landed in
    the same window, tripping the both-directions-present ambiguity
    guard that exists for a different, legitimate case (one bullet
    correctly describing two real transitions of the same metric).
    Report prose (unlike a bulleted list) is typically one long line per
    paragraph, so this only meaningfully narrows the window for
    line-structured text — it's a no-op within a single unbroken line
    short enough that start-radius/end+radius don't reach a boundary."""

    line_start = text.rfind("\n", 0, start)
    line_start = 0 if line_start == -1 else line_start + 1
    line_end = text.find("\n", end)
    line_end = len(text) if line_end == -1 else line_end
    return max(line_start, start - radius), min(line_end, end + radius)


def _has_nearby_word(narrative: str, needle: str, words: list[str], window: int = 300) -> bool:
    for match in re.finditer(re.escape(needle), narrative):
        start = max(0, match.start() - window)
        end = min(len(narrative), match.end() + window)
        context = narrative[start:end].lower()
        if any(word in context for word in words):
            return True
    return False


# Phase 3 Step 4, Phase A: direction/sign consistency.
#
# Pure direction vocabulary — no business-meaning judgment involved.
# "Decreased" contradicts a positive calculated change regardless of what
# the metric is; this tier exists to catch exactly that, e.g. "Claims
# decreased by 9.3%" against a verified +9.3% change.
_INCREASE_WORDS = (
    "increased", "increase", "increasing", "rose", "rising", "grew",
    "growing", "climbed", "climbing", "gained", "surged", "jumped",
)
_DECREASE_WORDS = (
    "decreased", "decrease", "decreasing", "fell", "falling", "dropped",
    "dropping", "declined", "declining", "lost", "shrank", "slipped",
)

# A narrow, explicit list of metrics where "lower is better" is a
# near-universal convention, used ONLY to check "improved"/"worsened"
# sentiment words against the calculated sign for THESE specific metrics
# — deliberately not a general business-polarity classifier (a distinct,
# larger piece of work): this exists only to catch "Loss ratio improved"
# stated against a positive (deteriorating) percentage-point change.
_LOWER_IS_BETTER_RATIO_KEYWORDS = (
    "loss ratio", "expense ratio", "combined ratio", "error rate",
    "defect rate", "attrition rate", "churn rate", "delinquency rate",
)
_IMPROVEMENT_WORDS = ("improved", "improvement", "improving")
_DETERIORATION_WORDS = ("worsened", "worsening", "deteriorated", "deterioration")


def _direction_issue(title: str, formatted: str, stated: str, actual: str) -> QCIssue:
    return QCIssue(
        severity="high",
        category="direction_consistency",
        message=(
            f"The narrative describes {title!r}'s {formatted} figure as {stated}, but the "
            f"verified calculation is {actual} ({formatted})."
        ),
        location=title,
    )


def _sentiment_issue(title: str, formatted: str, stated_word: str, actual: str) -> QCIssue:
    return QCIssue(
        severity="high",
        category="direction_consistency",
        message=(
            f"The narrative describes {title!r} as having {stated_word} at {formatted}, but the "
            f"verified calculation shows the figure {actual} — inconsistent for a metric where "
            "a lower value is conventionally better."
        ),
        location=title,
    )


def check_direction_consistency(
    narrative: str, metric_tables: list[dict[str, Any]]
) -> list[QCIssue]:
    """Catch a narrative stating the WRONG direction or sentiment for a
    verified calculated change — the exact failure mode that shipped
    uncaught in production (e.g. "Claims decreased by 9.3%" against a
    verified +9.3% increase; "Loss ratio improved" against a verified
    +0.3 percentage-point deterioration). Reuses the same figure-mention
    proximity technique as _check_numerical_consistency above, then
    inspects the LOCAL context around each mention for a direction or
    sentiment word and compares it against the calculated sign."""

    issues: list[QCIssue] = []

    for table in metric_tables:
        title = str(table.get("title") or "")
        calculations = table.get("calculations") or {}
        distinctive_words = _distinctive_title_words(title)
        if not distinctive_words:
            continue

        signed_changes: list[float] = []
        total = calculations.get("total_change") or {}
        if total.get("percent") is not None:
            signed_changes.append(float(total["percent"]))
        for change in calculations.get("period_over_period") or []:
            if change.get("percent") is not None:
                signed_changes.append(float(change["percent"]))

        is_lower_is_better_ratio = any(
            keyword in title.lower() for keyword in _LOWER_IS_BETTER_RATIO_KEYWORDS
        )

        for percent in signed_changes:
            formatted = f"{abs(percent):.1f}%"
            for match in re.finditer(re.escape(formatted), narrative):
                start, end = _line_bounded_window(narrative, match.start(), match.end(), 80)
                context = narrative[start:end].lower()
                if not any(word in context for word in distinctive_words):
                    # Not this metric's mention of the figure — a
                    # coincidental match to a different metric's value is
                    # already flagged by _check_numerical_consistency.
                    continue

                found_increase = any(word in context for word in _INCREASE_WORDS)
                found_decrease = any(word in context for word in _DECREASE_WORDS)
                # Only flag when the window contains ONE direction signal,
                # not both — a compound sentence describing two different
                # transitions ("rose 11.8% in February, but decreased in
                # March") legitimately has both words near the figure, and
                # attributing "decreased" to the OTHER clause's number
                # would be a false positive, not a real contradiction.
                if found_increase and not found_decrease and percent < 0:
                    issues.append(_direction_issue(title, formatted, "an increase", "a decrease"))
                elif found_decrease and not found_increase and percent >= 0:
                    issues.append(_direction_issue(title, formatted, "a decrease", "an increase"))

                if is_lower_is_better_ratio:
                    found_improved = any(word in context for word in _IMPROVEMENT_WORDS)
                    found_worsened = any(word in context for word in _DETERIORATION_WORDS)
                    if found_improved and not found_worsened and percent > 0:
                        issues.append(
                            _sentiment_issue(title, formatted, "improved", "increased (a deterioration for this ratio)")
                        )
                    elif found_worsened and not found_improved and percent < 0:
                        issues.append(
                            _sentiment_issue(title, formatted, "worsened", "decreased (an improvement for this ratio)")
                        )

    issues.extend(_check_endpoint_value_direction(narrative, metric_tables))
    return issues


def _format_value_for_search(value: float) -> str:
    """A metric's raw value as it plausibly appears in prose — "418.0"
    (the stored float) is never written as "418.0 cases", always "418
    cases"; "82.1" stays "82.1"."""

    return f"{value:g}"


def _check_endpoint_value_direction(
    narrative: str, metric_tables: list[dict[str, Any]]
) -> list[QCIssue]:
    """Catches a direction contradiction stated via a metric's own raw
    endpoint values rather than a restated percentage — e.g. "Claims
    incurred decreased from $82.1m to $89.7m" has no percentage figure
    anywhere for check_direction_consistency's percent-proximity pass
    above to anchor to, but the contradiction is just as real: 89.7 is
    not less than 82.1. Looks for the series' first and last row values
    both appearing near each other in the narrative, together with a
    direction word, and compares against the true first-to-last sign."""

    issues: list[QCIssue] = []

    for table in metric_tables:
        title = str(table.get("title") or "")
        rows = table.get("rows") or []
        if len(rows) < 2:
            continue
        distinctive_words = _distinctive_title_words(title)
        if not distinctive_words:
            continue

        first_value = float(rows[0]["value"])
        last_value = float(rows[-1]["value"])
        first_str = _format_value_for_search(first_value)
        last_str = _format_value_for_search(last_value)
        if not first_str or not last_str or first_str == last_str:
            continue

        for match in re.finditer(re.escape(first_str), narrative):
            start, end = _line_bounded_window(narrative, match.start(), match.end(), 150)
            window = narrative[start:end]
            if last_str not in window:
                continue

            window_lower = window.lower()
            if not any(word in window_lower for word in distinctive_words):
                continue

            found_increase = any(word in window_lower for word in _INCREASE_WORDS)
            found_decrease = any(word in window_lower for word in _DECREASE_WORDS)
            actual_increase = last_value > first_value
            span = f"{first_str} → {last_str}"
            if found_increase and not found_decrease and not actual_increase:
                issues.append(_direction_issue(title, span, "an increase", "a decrease"))
                break
            if found_decrease and not found_increase and actual_increase:
                issues.append(_direction_issue(title, span, "a decrease", "an increase"))
                break

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


_GENERIC_METRIC_TITLES = {"total", "amount", "value", "sum", "count", "figure", "number"}


def _check_no_generic_metric_titles(metric_tables: list[dict[str, Any]]) -> list[QCIssue]:
    """A metric titled with a single generic word (e.g. a spreadsheet
    column literally headed "Total", with no sibling identity column to
    disambiguate it — quantitative_analysis_service.py only composes a
    specific title when one is available) is confusing on its own as a
    chart title or citation. Flagged (low severity — a labeling
    nicety, not a correctness bug) rather than silently charted or
    guessed at, per "a bad chart is worse than no chart.\""""

    issues: list[QCIssue] = []
    for table in metric_tables:
        title = str(table.get("title") or "").strip()
        if title.lower() in _GENERIC_METRIC_TITLES:
            issues.append(
                QCIssue(
                    severity="low",
                    category="generic_metric_title",
                    message=(
                        f"Metric titled {title!r} has no more specific name available in the "
                        "source table — consider whether an identity/category column (e.g. "
                        "'Product', 'Region') could disambiguate it."
                    ),
                    location=title,
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

    if period_id == "custom":
        # Phase 3 Step 2 safety net: SpaReportGenerationService._find_
        # previous_report() never auto-matches a previous report for an
        # ad-hoc/custom-period request (every ad-hoc report shares the
        # single generic period_id "custom", with no real date-range to
        # tell two unrelated ad-hoc requests apart) — this section should
        # be structurally impossible here. Flag high severity if it ever
        # appears anyway, since a comparison against an unrelated prior
        # ad-hoc report is exactly the failure this fix exists to prevent.
        issues.append(
            QCIssue(
                severity="high",
                category="period_correctness",
                message=(
                    "Narrative includes a 'Changes Since Last Report' section for a Custom / "
                    "Ad hoc report — ad-hoc reports have no reliable way to confirm a previous "
                    "report covers the same scope, so this comparison should never be offered."
                ),
            )
        )
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
    issues.extend(check_direction_consistency(narrative, metric_tables or []))
    issues.extend(_check_no_implausible_ungrounded_percentages(narrative, metric_tables or []))
    issues.extend(_check_no_generic_metric_titles(metric_tables or []))
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
