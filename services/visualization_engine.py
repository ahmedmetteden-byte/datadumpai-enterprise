"""
Intelligent visualization engine for DataDumpAI reports.

This module is the single authority for deciding whether visuals appear in reports,
what type they should be, and how they are structured for export renderers.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from models.report_data import ReportData

EXECUTIVE_DASHBOARD_HEADING = "Executive Dashboard"
LEGACY_VISUAL_ANALYTICS_HEADING = "Visual Analytics"

CURRENCY_PATTERN = re.compile(
    r"(?:[$€£₦]\s?[\d,]+(?:\.\d{1,2})?|[\d,]+(?:\.\d{1,2})?\s?(?:USD|EUR|GBP|NGN|million|billion|bn|m)\b)",
    re.IGNORECASE,
)
PERCENTAGE_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\s?%")
DATE_PATTERN = re.compile(
    r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|"
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s+\d{1,2},?\s+\d{4}|\d{4}-\d{2}-\d{2})\b",
    re.IGNORECASE,
)
TABLE_ROW_PATTERN = re.compile(r"^\|[^|]+\|", re.MULTILINE)
NUMERIC_TABLE_PATTERN = re.compile(r"\|\s*[\d,$€£₦.%]+\s*\|")
KPI_PATTERN = re.compile(
    r"\b(?:kpi|target|actual|variance|yoy|qoq|growth rate|margin|roi|ebitda)\b",
    re.IGNORECASE,
)
SCORE_PATTERN = re.compile(r"\b(?:score|rating|index)\s*[:\s]?\s*\d+(?:\.\d+)?", re.IGNORECASE)
RANKING_PATTERN = re.compile(r"\b(?:top\s+\d+|rank(?:ed)?|#\d+|first|second|third)\b", re.IGNORECASE)
GEOGRAPHIC_PATTERN = re.compile(
    r"\b(?:region|country|state|province|territory|geographic|by market)\b",
    re.IGNORECASE,
)
ACTION_ITEM_PATTERN = re.compile(
    r"(?:action item|action:|todo|follow[- ]?up|assigned to|owner:|deadline:)",
    re.IGNORECASE,
)
MILESTONE_PATTERN = re.compile(
    r"\b(?:milestone|phase\s+\d|deliverable|sprint|go-live|launch date)\b",
    re.IGNORECASE,
)


class ReportType(str, Enum):
    FINANCIAL = "FINANCIAL"
    SALES = "SALES"
    PROJECT = "PROJECT"
    MEETING = "MEETING"
    LEGAL = "LEGAL"
    POLICY = "POLICY"
    REGULATORY = "REGULATORY"
    AUDIT = "AUDIT"
    RISK = "RISK"
    RESEARCH = "RESEARCH"
    OPERATIONS = "OPERATIONS"
    HR = "HR"
    PROCUREMENT = "PROCUREMENT"
    CUSTOM = "CUSTOM"


class ReportIntent(str, Enum):
    EXECUTIVE_BRIEF = "EXECUTIVE_BRIEF"
    ANALYTICAL_REPORT = "ANALYTICAL_REPORT"
    RESEARCH_REPORT = "RESEARCH_REPORT"
    PRESENTATION = "PRESENTATION"


class VisualizationStrategy(str, Enum):
    NONE = "NONE"
    BAR_CHART = "BAR_CHART"
    LINE_CHART = "LINE_CHART"
    PIE_CHART = "PIE_CHART"
    TIMELINE = "TIMELINE"
    KPI_CARDS = "KPI_CARDS"
    DECISION_MATRIX = "DECISION_MATRIX"
    PROCESS_FLOW = "PROCESS_FLOW"
    HEATMAP = "HEATMAP"
    RISK_MATRIX = "RISK_MATRIX"
    ORGANIZATIONAL_FLOW = "ORGANIZATIONAL_FLOW"
    TABLE_ONLY = "TABLE_ONLY"


@dataclass
class DataProfile:
    contains_numeric_tables: bool = False
    contains_time_series: bool = False
    contains_currency: bool = False
    contains_percentages: bool = False
    contains_dates: bool = False
    contains_kpis: bool = False
    contains_categories: bool = False
    contains_scores: bool = False
    contains_rankings: bool = False
    contains_geographic_breakdown: bool = False

    def has_quantitative_signal(self) -> bool:
        return any(
            (
                self.contains_numeric_tables,
                self.contains_time_series,
                self.contains_currency,
                self.contains_percentages,
                self.contains_kpis,
                self.contains_scores,
                self.contains_rankings,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VisualizationBlock:
    title: str
    type: VisualizationStrategy
    description: str
    data: dict[str, Any]
    priority: int = 1
    decision_question: str = ""
    unit: str = ""
    x_label: str = ""
    y_label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "type": self.type.value,
            "description": self.description,
            "data": self.data,
            "priority": self.priority,
            "decision_question": self.decision_question,
            "unit": self.unit,
            "x_label": self.x_label,
            "y_label": self.y_label,
        }


@dataclass
class ExecutiveDashboard:
    sections: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"sections": self.sections}


REPORT_TYPE_KEYWORDS: dict[ReportType, tuple[str, ...]] = {
    ReportType.FINANCIAL: (
        "revenue",
        "expense",
        "profit",
        "loss",
        "ebitda",
        "balance sheet",
        "income statement",
        "cash flow",
        "financial statement",
        "fiscal",
    ),
    ReportType.SALES: (
        "sales",
        "pipeline",
        "quota",
        "conversion",
        "customer acquisition",
        "deal",
        "win rate",
        "crm",
    ),
    ReportType.PROJECT: (
        "project",
        "milestone",
        "deliverable",
        "sprint",
        "workstream",
        "phase",
        "gantt",
    ),
    ReportType.MEETING: (
        "meeting minutes",
        "minutes of meeting",
        "action item",
        "attendees",
        "agenda",
        "resolved that",
        "meeting held",
    ),
    ReportType.LEGAL: (
        "court",
        "judgment",
        "judgement",
        "plaintiff",
        "defendant",
        "tribunal",
        "appellate",
        "ruling",
        "case no",
        "litigation",
    ),
    ReportType.POLICY: (
        "policy",
        "objective",
        "stakeholder",
        "implementation plan",
        "framework",
        "guideline",
        "strategic plan",
    ),
    ReportType.REGULATORY: (
        "regulatory",
        "regulation",
        "compliance",
        "obligation",
        "statutory",
        "naicom",
        "sec filing",
    ),
    ReportType.AUDIT: (
        "audit",
        "finding",
        "internal control",
        "material weakness",
        "auditor",
        "assurance",
    ),
    ReportType.RISK: (
        "risk assessment",
        "risk matrix",
        "severity",
        "likelihood",
        "mitigation",
        "risk register",
    ),
    ReportType.RESEARCH: (
        "methodology",
        "hypothesis",
        "literature review",
        "citation",
        "research question",
        "findings",
        "abstract",
    ),
    ReportType.OPERATIONS: (
        "operations",
        "operational",
        "throughput",
        "supply chain",
        "logistics",
        "efficiency",
    ),
    ReportType.HR: (
        "human resources",
        "headcount",
        "recruitment",
        "employee",
        "workforce",
        "talent",
    ),
    ReportType.PROCUREMENT: (
        "procurement",
        "vendor",
        "supplier",
        "rfp",
        "purchase order",
        "sourcing",
    ),
}

USER_REPORT_TYPE_HINTS: dict[str, ReportType] = {
    "annual statistics": ReportType.FINANCIAL,
    "financial analysis": ReportType.FINANCIAL,
    "regulatory compliance report": ReportType.REGULATORY,
    "risk assessment report": ReportType.RISK,
    "meeting intelligence report": ReportType.MEETING,
    "market intelligence report": ReportType.SALES,
    "strategic planning report": ReportType.POLICY,
    "board report": ReportType.FINANCIAL,
    "management report": ReportType.OPERATIONS,
}

INTENT_BY_USER_REPORT_TYPE: dict[str, ReportIntent] = {
    "executive summary": ReportIntent.EXECUTIVE_BRIEF,
    "board report": ReportIntent.EXECUTIVE_BRIEF,
    "executive intelligence dashboard": ReportIntent.EXECUTIVE_BRIEF,
    "financial analysis": ReportIntent.ANALYTICAL_REPORT,
    "management report": ReportIntent.ANALYTICAL_REPORT,
    "full report": ReportIntent.ANALYTICAL_REPORT,
    "regulatory compliance report": ReportIntent.ANALYTICAL_REPORT,
    "risk assessment report": ReportIntent.ANALYTICAL_REPORT,
    "meeting intelligence report": ReportIntent.EXECUTIVE_BRIEF,
    "market intelligence report": ReportIntent.ANALYTICAL_REPORT,
    "strategic planning report": ReportIntent.PRESENTATION,
}


def _combined_text(report_data: ReportData, document_text: str = "") -> str:
    parts = [
        document_text,
        report_data.narrative,
        report_data.title,
        report_data.report_type,
        " ".join(report_data.source_documents),
    ]

    for section in report_data.sections:
        parts.append(str(section.get("heading", "")))
        parts.append(str(section.get("summary", "")))

    for key, value in report_data.metadata.items():
        parts.append(f"{key} {value}")

    for key, value in report_data.metrics.items():
        parts.append(f"{key} {value}")

    return "\n".join(str(part) for part in parts if part).lower()


def classify_report_intent(user_report_type: str) -> ReportIntent:
    normalized = (user_report_type or "").strip().lower()
    return INTENT_BY_USER_REPORT_TYPE.get(normalized, ReportIntent.ANALYTICAL_REPORT)


def classify_report_type(
    report_data: ReportData,
    *,
    document_text: str = "",
    user_report_type: str = "",
) -> ReportType:
    """Classify document content into a report type."""

    user_hint = USER_REPORT_TYPE_HINTS.get((user_report_type or "").strip().lower())
    if user_hint:
        return user_hint

    text = _combined_text(report_data, document_text)
    scores: dict[ReportType, int] = {}

    for report_type, keywords in REPORT_TYPE_KEYWORDS.items():
        score = sum(text.count(keyword) for keyword in keywords)
        if score:
            scores[report_type] = score

    metadata_type = str(report_data.metadata.get("report_type", "")).lower()
    for label, mapped in USER_REPORT_TYPE_HINTS.items():
        if label in metadata_type:
            scores[mapped] = scores.get(mapped, 0) + 5

    if not scores:
        return ReportType.CUSTOM

    return max(scores.items(), key=lambda item: (item[1], item[0].value))[0]


def build_data_profile(
    report_data: ReportData,
    *,
    document_text: str = "",
) -> DataProfile:
    """Detect quantitative and structural signals in report content."""

    text = _combined_text(report_data, document_text)
    raw_text = document_text or report_data.narrative

    profile = DataProfile(
        contains_numeric_tables=bool(TABLE_ROW_PATTERN.search(raw_text) and NUMERIC_TABLE_PATTERN.search(raw_text)),
        contains_time_series=bool(
            re.search(r"\b(?:trend|over time|year[- ]over[- ]year|yoy|monthly|quarterly|time series)\b", text)
            or len(DATE_PATTERN.findall(raw_text)) >= 3
        ),
        contains_currency=bool(CURRENCY_PATTERN.search(raw_text)),
        contains_percentages=bool(PERCENTAGE_PATTERN.search(raw_text)),
        contains_dates=bool(DATE_PATTERN.search(raw_text)),
        contains_kpis=bool(KPI_PATTERN.search(text) or report_data.kpis),
        contains_categories=bool(report_data.charts.get("topics") or report_data.metrics.get("top_themes")),
        contains_scores=bool(SCORE_PATTERN.search(text) or report_data.charts.get("health_score") is not None),
        contains_rankings=bool(RANKING_PATTERN.search(text)),
        contains_geographic_breakdown=bool(GEOGRAPHIC_PATTERN.search(text)),
    )

    trends = report_data.charts.get("trends") or []
    if trends:
        profile.contains_time_series = True

    return profile


def decide_visualization_strategies(
    report_type: ReportType,
    data_profile: DataProfile,
    intent: ReportIntent,
) -> list[VisualizationStrategy]:
    """Choose visualization strategies based on report type, data, and user intent."""

    if intent == ReportIntent.RESEARCH_REPORT:
        if data_profile.contains_numeric_tables:
            return [VisualizationStrategy.TABLE_ONLY]
        return [VisualizationStrategy.NONE]

    strategies: list[VisualizationStrategy] = []

    if report_type == ReportType.FINANCIAL:
        if data_profile.contains_time_series:
            strategies.append(VisualizationStrategy.LINE_CHART)
        if data_profile.contains_currency or data_profile.contains_percentages:
            strategies.append(VisualizationStrategy.BAR_CHART)
        if data_profile.contains_kpis:
            strategies.append(VisualizationStrategy.KPI_CARDS)

    elif report_type == ReportType.SALES:
        if data_profile.contains_time_series:
            strategies.append(VisualizationStrategy.LINE_CHART)
        elif data_profile.has_quantitative_signal():
            strategies.append(VisualizationStrategy.BAR_CHART)

    elif report_type == ReportType.MEETING:
        strategies.append(VisualizationStrategy.TABLE_ONLY)
        if data_profile.contains_dates:
            strategies.append(VisualizationStrategy.TIMELINE)

    elif report_type == ReportType.LEGAL:
        if data_profile.contains_dates:
            strategies.append(VisualizationStrategy.TIMELINE)
        strategies.append(VisualizationStrategy.DECISION_MATRIX)

    elif report_type == ReportType.POLICY:
        strategies.append(VisualizationStrategy.ORGANIZATIONAL_FLOW)
        if data_profile.contains_categories:
            strategies.append(VisualizationStrategy.TABLE_ONLY)

    elif report_type == ReportType.REGULATORY:
        strategies.append(VisualizationStrategy.TABLE_ONLY)
        if data_profile.contains_dates:
            strategies.append(VisualizationStrategy.TIMELINE)
        if data_profile.contains_currency or data_profile.contains_percentages:
            strategies.append(VisualizationStrategy.BAR_CHART)

    elif report_type == ReportType.RISK:
        strategies.append(VisualizationStrategy.RISK_MATRIX)

    elif report_type == ReportType.PROJECT:
        if data_profile.contains_dates:
            strategies.append(VisualizationStrategy.TIMELINE)

    elif report_type == ReportType.RESEARCH:
        strategies.append(VisualizationStrategy.TABLE_ONLY)

    elif report_type == ReportType.AUDIT:
        strategies.append(VisualizationStrategy.TABLE_ONLY)
        if data_profile.contains_rankings:
            strategies.append(VisualizationStrategy.BAR_CHART)

    elif report_type == ReportType.OPERATIONS:
        if data_profile.has_quantitative_signal():
            strategies.append(VisualizationStrategy.BAR_CHART)

    elif report_type == ReportType.CUSTOM:
        if data_profile.has_quantitative_signal():
            strategies.append(VisualizationStrategy.BAR_CHART)

    if intent == ReportIntent.EXECUTIVE_BRIEF:
        # EXECUTIVE_BRIEF intent excludes bar/line/pie charts below, but if
        # one was chosen because the content has genuine quantitative
        # signal (currency, percentages, etc.), substitute KPI cards rather
        # than silently dropping the visualization entirely.
        had_chart_strategy = any(
            strategy
            in {
                VisualizationStrategy.BAR_CHART,
                VisualizationStrategy.LINE_CHART,
                VisualizationStrategy.PIE_CHART,
            }
            for strategy in strategies
        )
        strategies = [
            strategy
            for strategy in strategies
            if strategy
            in {
                VisualizationStrategy.KPI_CARDS,
                VisualizationStrategy.TIMELINE,
                VisualizationStrategy.DECISION_MATRIX,
                VisualizationStrategy.RISK_MATRIX,
                VisualizationStrategy.TABLE_ONLY,
            }
        ] or strategies[:2]
        if had_chart_strategy and VisualizationStrategy.KPI_CARDS not in strategies:
            strategies.append(VisualizationStrategy.KPI_CARDS)

    elif intent == ReportIntent.PRESENTATION:
        if VisualizationStrategy.BAR_CHART not in strategies and data_profile.has_quantitative_signal():
            strategies.insert(0, VisualizationStrategy.BAR_CHART)
        if VisualizationStrategy.PIE_CHART not in strategies and data_profile.contains_categories:
            strategies.append(VisualizationStrategy.PIE_CHART)

    strategies = _dedupe_strategies(strategies)

    if not strategies:
        return [VisualizationStrategy.NONE]

    if not data_profile.has_quantitative_signal() and report_type in {
        ReportType.LEGAL,
        ReportType.MEETING,
        ReportType.POLICY,
        ReportType.RESEARCH,
        ReportType.REGULATORY,
    }:
        strategies = [
            strategy
            for strategy in strategies
            if strategy
            not in {
                VisualizationStrategy.BAR_CHART,
                VisualizationStrategy.PIE_CHART,
                VisualizationStrategy.LINE_CHART,
            }
        ] or strategies

    if strategies == [VisualizationStrategy.NONE]:
        return strategies

    filtered = [strategy for strategy in strategies if strategy != VisualizationStrategy.NONE]
    return filtered or [VisualizationStrategy.NONE]


def _dedupe_strategies(strategies: list[VisualizationStrategy]) -> list[VisualizationStrategy]:
    seen: set[VisualizationStrategy] = set()
    ordered: list[VisualizationStrategy] = []

    for strategy in strategies:
        if strategy not in seen:
            seen.add(strategy)
            ordered.append(strategy)

    return ordered


def _extract_timeline_events(text: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []

    for match in DATE_PATTERN.finditer(text):
        start = max(0, match.start() - 80)
        end = min(len(text), match.end() + 120)
        snippet = re.sub(r"\s+", " ", text[start:end]).strip(" .,-")
        label = snippet[:100].strip()
        if label:
            events.append({"date": match.group(0), "label": label})

    deduped: list[dict[str, Any]] = []
    seen_dates: set[str] = set()

    for event in events:
        if event["date"] in seen_dates:
            continue
        seen_dates.add(event["date"])
        deduped.append(event)

    return deduped[:8]


def _extract_action_items(text: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if ACTION_ITEM_PATTERN.search(stripped) or stripped.startswith(("-", "•", "*")):
            owner_match = re.search(r"(?:owner|assigned to)\s*[:\-]\s*([^|;\n]+)", stripped, re.IGNORECASE)
            deadline_match = re.search(r"(?:deadline|due)\s*[:\-]\s*([^|;\n]+)", stripped, re.IGNORECASE)
            items.append(
                {
                    "action": re.sub(r"^[-•*]\s*", "", stripped),
                    "owner": owner_match.group(1).strip() if owner_match else "",
                    "deadline": deadline_match.group(1).strip() if deadline_match else "",
                }
            )

    return items[:10]


_FINANCIAL_COLUMN_KEYWORDS = (
    "revenue",
    "expense",
    "cost",
    "profit",
    "margin",
    "growth",
    "sales",
    "amount",
    "value",
    "total",
)


def _parse_numeric_cell(cell: str) -> float | None:
    cleaned = re.sub(r"[$€£₦,%\s]", "", cell)
    if not cleaned:
        return None

    try:
        return float(cleaned)
    except ValueError:
        return None


_BARE_YEAR_CELL = re.compile(r"^(19|20)\d{2}$")


def _looks_like_bare_year(raw_cell: str, value: float) -> bool:
    """A cell that parses as a plain 4-digit 1900-2100 number with no
    currency, percent, or scale suffix — almost certainly a reporting
    year that leaked into a value column, never a genuine financial
    figure (Phase C.1: found in production charting a "Financial
    Performance" bar chart where Revenue/Profit/Growth all showed
    "2,026" — the LLM-authored table's value column held the report's
    own year, not real figures)."""

    return bool(_BARE_YEAR_CELL.match(raw_cell.strip().replace(",", ""))) and value == int(value)


def _table_financial_series(text: str) -> list[dict[str, Any]]:
    """Extract a (label, value) series from a markdown table whose header
    names a recognizable financial/quantitative column.

    Preferred over scanning prose for a keyword followed by "the nearest
    digits" — that approach can match the wrong number entirely (e.g. the
    "1" in a "Q1" row label immediately following a "Revenue" table
    header), producing a chart with a fabricated-looking single value
    instead of the real per-row figures.

    Two plausibility guards reject the whole series rather than risk a
    second flavor of the same fabrication (Phase C.1): every value being
    a bare calendar year (the LLM padded a table it had no real figures
    for with the report's own year), or every value being identical
    (genuine Revenue/Profit/Growth figures are never exactly equal) —
    both signal a table the model invented rather than one grounded in
    real per-row figures.
    """

    from services.report_markdown_renderer import parse_markdown_blocks

    for block in parse_markdown_blocks(text):
        if block.block_type != "table" or len(block.rows) < 2:
            continue

        header = [cell.strip().lower() for cell in block.rows[0]]
        value_col = next(
            (
                index
                for index, name in enumerate(header)
                if index > 0 and any(keyword in name for keyword in _FINANCIAL_COLUMN_KEYWORDS)
            ),
            None,
        )
        if value_col is None:
            continue

        series: list[dict[str, Any]] = []
        all_bare_years = True
        for row in block.rows[1:]:
            if len(row) <= value_col:
                continue
            raw_cell = row[value_col]
            value = _parse_numeric_cell(raw_cell)
            label = row[0].strip()
            if value is None or value <= 0 or not label:
                continue
            if not _looks_like_bare_year(raw_cell, value):
                all_bare_years = False
            series.append({"label": label, "value": value})

        if not series:
            continue
        if all_bare_years:
            continue
        if len({item["value"] for item in series}) == 1 and len(series) > 1:
            continue

        return series

    return []


def _financial_series(report_data: ReportData, text: str) -> list[dict[str, Any]]:
    """Financial-performance bar-chart data, sourced ONLY from a real
    markdown table (_table_financial_series) or a structured "trends"
    entry already on report_data.charts — never scraped from prose.

    Phase 3 Step 4, Phase A: this used to fall back to searching the
    entire narrative for the words "revenue"/"expenses"/"profit"/"growth"
    and grabbing the NEAREST following digits with no check that the
    number actually belonged to that label — confirmed in production to
    match unrelated numbers anywhere later in the document (including a
    bare year like "2026"), fabricating a "Revenue/Profit/Growth" chart
    with no basis in the source data at all. Removed outright rather than
    made safer: per this phase's explicit principle, a report with no
    chart is strictly better than one with a fabricated chart, and the
    real fix (see quantitative_analysis_service.py's cross-document
    prose extraction) now gives genuine metrics a real chance to reach
    this pipeline as an actual table/metric-derived series instead."""

    table_series = _table_financial_series(text)
    if table_series:
        return table_series

    trends = report_data.charts.get("trends") or []
    if trends:
        return [
            {"label": item.get("label", ""), "value": float(item.get("current", 0))}
            for item in trends
            if float(item.get("current", 0)) > 0
        ]

    return []


_FINDING_HEADING_PATTERN = re.compile(r"^###\s+\*\*(.+?)\*\*\s*$", re.MULTILINE)
_SECTION_HEADING_PATTERN = re.compile(r"^##\s+(?!#)", re.MULTILINE)


_KPI_VALUE_PATTERN = re.compile(
    r"^(?P<currency_symbol>[$€£₦])?\s?(?P<number>[\d,]+(?:\.\d+)?)\s?"
    r"(?P<suffix>%|USD|EUR|GBP|NGN|million|billion|bn|m)?$",
    re.IGNORECASE,
)


def _normalize_kpi_value(raw: str) -> tuple[float, str] | None:
    """Parse a matched currency/percentage figure into (numeric magnitude,
    unit key), so figures that share a unit can be grouped onto one
    comparable chart axis (a bar chart mixing e.g. "68.0%" with "N1,558.7
    billion" on the same axis would be visually meaningless)."""

    match = _KPI_VALUE_PATTERN.match(raw.strip())
    if not match:
        return None

    try:
        number = float(match.group("number").replace(",", ""))
    except ValueError:
        return None

    unit = (match.group("currency_symbol") or match.group("suffix") or "").lower()
    return number, unit


def _extract_finding_kpis(text: str) -> dict[str, float]:
    """Pull headline KPI values from the report's own "### **Finding**"
    sub-headings — the structured shape the report-generation prompt
    enforces for every finding (bolded title, then explanation, then
    Confidence/Source lines).

    Using the model's own bolded finding title as the label is far safer
    than deriving one from a keyword regex: it's human-readable text the
    model already wrote about that specific figure, not a guess about
    which nearby number a keyword refers to. Values are grouped by unit
    and only the largest same-unit group is kept, so the resulting chart
    never plots incompatible magnitudes against each other.
    """

    candidates: list[tuple[str, float, str]] = []
    headings = list(_FINDING_HEADING_PATTERN.finditer(text))
    section_starts = [m.start() for m in _SECTION_HEADING_PATTERN.finditer(text)]

    for index, match in enumerate(headings):
        start = match.end()
        # Bound the body by whichever comes first: the next finding, or the
        # next top-level "## " section (e.g. "## Detailed Analysis") — the
        # last finding in "## Key Findings" would otherwise sweep in every
        # section that follows, since it has no next "###" heading to stop at.
        next_finding = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        next_section = next((pos for pos in section_starts if pos > start), len(text))
        end = min(next_finding, next_section)
        body = text[start:end]

        # Prefer the LAST figure in the body over the first: findings are
        # commonly phrased as "grew from X to Y", and the ending/resulting
        # value is the more meaningful headline number to surface.
        figure_matches = list(CURRENCY_PATTERN.finditer(body)) or list(PERCENTAGE_PATTERN.finditer(body))
        if not figure_matches:
            continue

        normalized = _normalize_kpi_value(figure_matches[-1].group(0))
        if normalized is None:
            continue

        label = match.group(1).strip()
        if label:
            candidates.append((label, normalized[0], normalized[1]))

    if not candidates:
        return {}

    groups: dict[str, list[tuple[str, float]]] = {}
    for label, number, unit in candidates:
        groups.setdefault(unit, []).append((label, number))

    # Keep only the unit shared by the most findings, so the resulting bar
    # chart never plots incompatible magnitudes (e.g. a 68% figure next to
    # a 1,558.7-billion figure) against each other on one axis.
    winning = max(groups.values(), key=len)

    kpis: dict[str, float] = {}
    for label, number in winning:
        if label not in kpis:
            kpis[label] = number
        if len(kpis) >= 6:
            break

    return kpis


def _kpi_items(report_data: ReportData, text: str = "") -> list[dict[str, Any]]:
    # Real, deterministic KPI data — Step A's report_plan_service.py
    # already computed the latest value + direction for the metrics that
    # matter most (report_plan_service.select_dashboard_items). Preferred
    # over every fallback below, which either re-parses the narrative via
    # regex or reads a field (report_data.kpis) nothing in the SPA
    # pipeline ever actually populates.
    dashboard_kpis = (report_data.metadata.get("dashboard_selection") or {}).get("kpis") or []
    real_items: list[dict[str, Any]] = []
    for kpi in dashboard_kpis:
        label = str(kpi.get("label") or "")
        value = kpi.get("value")
        if not label or value is None:
            continue
        real_items.append(
            {
                "label": label,
                "value": value,
                "unit": str(kpi.get("unit") or ""),
                "total_change_percent": kpi.get("total_change_percent"),
                "direction": kpi.get("direction") or "flat",
            }
        )
    if real_items:
        # Unit-consistency gate (Phase 3 Step 3): report_plan_service.py's
        # materiality ranking selects these purely by percent-change
        # magnitude, with no unit awareness — a $-denominated metric and
        # a %-denominated metric can both legitimately rank in the top
        # slots. Without this gate they'd land on one shared-axis KPI
        # chart together (e.g. "Total Gross Premium" at $1,567m next to
        # "Total Loss Ratio" at 77.9%). Reuses the exact same
        # group-by-unit-keep-the-largest-group safeguard
        # _extract_finding_kpis() above already applies to its own
        # (legacy, regex-parsed) candidates — this is the one place that
        # safeguard was missing from the preferred, deterministic path.
        unit_groups: dict[str, list[dict[str, Any]]] = {}
        for item in real_items:
            unit_groups.setdefault(item["unit"], []).append(item)
        winning_unit_items = max(unit_groups.values(), key=len)
        return winning_unit_items[:6]

    items: list[dict[str, Any]] = []

    for key, value in report_data.kpis.items():
        label = key.replace("_", " ").title()
        items.append({"label": label, "value": value})

    if not items and text:
        for label, value in _extract_finding_kpis(text).items():
            items.append({"label": label, "value": value})

    health_score = report_data.charts.get("health_score")
    if health_score is not None and not any(item["label"] == "Health Score" for item in items):
        items.append({"label": "Health Score", "value": health_score})

    return items[:6]


def _risk_matrix_data(report_data: ReportData, text: str) -> list[dict[str, Any]]:
    distribution = report_data.charts.get("risk_distribution") or []
    if distribution:
        return [
            {
                "risk": item.get("label", ""),
                "severity": item.get("value", 0),
                "likelihood": max(1, min(5, int(item.get("value", 1)))),
            }
            for item in distribution
        ]

    risks: list[dict[str, Any]] = []
    for label, severity_word in (("Critical", "critical"), ("High", "high"), ("Medium", "medium")):
        count = len(re.findall(rf"\b{severity_word}\b", text, re.IGNORECASE))
        if count:
            risks.append({"risk": label, "severity": count, "likelihood": min(5, count)})

    return risks


def _decision_matrix_data(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for pattern, outcome in (
        (r"plaintiff", "Claimant position"),
        (r"defendant", "Respondent position"),
        (r"court held", "Court holding"),
        (r"ordered that", "Order"),
        (r"appeal", "Appeal outcome"),
    ):
        if re.search(pattern, text, re.IGNORECASE):
            rows.append({"party": outcome, "status": "Identified"})

    return rows[:6]


def _build_executive_dashboard(
    report_type: ReportType,
    report_data: ReportData,
    blocks: list[VisualizationBlock],
) -> ExecutiveDashboard:
    templates: dict[ReportType, list[str]] = {
        ReportType.FINANCIAL: ["Revenue", "Expenses", "Profit", "Growth"],
        ReportType.LEGAL: ["Court", "Case", "Outcome", "Orders", "Timeline"],
        ReportType.POLICY: ["Objectives", "Stakeholders", "Compliance", "Implementation"],
        ReportType.MEETING: ["Attendees", "Decisions", "Action Items", "Deadlines"],
        ReportType.RISK: ["Top Risks", "Severity", "Likelihood", "Mitigation"],
        ReportType.PROJECT: ["Milestones", "Status", "Dependencies", "Timeline"],
        ReportType.SALES: ["Pipeline", "Conversion", "Targets", "Trend"],
        ReportType.REGULATORY: ["Obligations", "Gaps", "Compliance", "Timeline"],
    }

    section_labels = templates.get(report_type, ["Key Insights", "Metrics", "Decisions", "Next Steps"])
    sections: list[dict[str, Any]] = []

    for label in section_labels:
        section_items: list[str] = []

        if label.lower() == "action items":
            section_items = [block.title for block in blocks if block.type == VisualizationStrategy.TABLE_ONLY]
        elif label.lower() in {"timeline", "milestones"}:
            section_items = [event.get("label", "") for block in blocks if block.type == VisualizationStrategy.TIMELINE for event in block.data.get("events", [])]
        elif label.lower() in {"top risks", "severity", "likelihood", "mitigation"}:
            section_items = [row.get("risk", "") for block in blocks if block.type == VisualizationStrategy.RISK_MATRIX for row in block.data.get("rows", [])]
        elif report_data.kpis:
            section_items = [f"{key.replace('_', ' ').title()}: {value}" for key, value in list(report_data.kpis.items())[:4]]

        sections.append({"title": label, "items": [item for item in section_items if item][:5]})

    return ExecutiveDashboard(sections=sections)


def build_visualization_blocks(
    report_type: ReportType,
    data_profile: DataProfile,
    strategies: list[VisualizationStrategy],
    report_data: ReportData,
    *,
    document_text: str = "",
) -> list[VisualizationBlock]:
    """Build structured visualization blocks for export renderers.

    Metric-table-derived blocks (built from quantitative_analysis_service's
    calculated MetricSeries via services.quantitative_chart_bridge) come
    first and take priority over the generic per-strategy blocks below,
    which stay as the fallback for reports without usable metric tables.
    Once any metric-table-derived block exists, the generic BAR_CHART/
    LINE_CHART strategies are skipped entirely (not just a matching
    strategy type) — both draw from the same underlying financial-series
    text, so leaving the generic one enabled would show the reader a
    second, vaguer chart of the same data the metric-derived chart(s)
    already cover accurately (spec: "fewer excellent charts, not many
    mediocre ones").
    """

    from services.quantitative_chart_bridge import select_chart_candidates

    text = document_text or report_data.narrative
    metric_tables = report_data.metrics.get("tables") or []
    chart_requirements = (
        (report_data.metadata.get("report_plan") or {}).get("chart_requirements") or []
    )
    metric_blocks = select_chart_candidates(metric_tables, chart_requirements)

    blocks: list[VisualizationBlock] = list(metric_blocks)
    priority = len(metric_blocks) + 1

    for strategy in strategies:
        if strategy == VisualizationStrategy.NONE:
            continue

        if metric_blocks and strategy in (
            VisualizationStrategy.BAR_CHART,
            VisualizationStrategy.LINE_CHART,
        ):
            continue

        if strategy == VisualizationStrategy.TIMELINE:
            events = _extract_timeline_events(text)
            if not events:
                continue
            blocks.append(
                VisualizationBlock(
                    title="Case Timeline" if report_type == ReportType.LEGAL else "Milestone Timeline",
                    type=strategy,
                    description="Chronological sequence of key events.",
                    data={"events": events},
                    priority=priority,
                    decision_question="What happened when, and what milestone comes next?",
                )
            )
            priority += 1

        elif strategy == VisualizationStrategy.DECISION_MATRIX:
            rows = _decision_matrix_data(text)
            if not rows:
                continue
            blocks.append(
                VisualizationBlock(
                    title="Decision Matrix",
                    type=strategy,
                    description="Parties, holdings, and outcomes at a glance.",
                    data={"rows": rows},
                    priority=priority,
                    decision_question="Who decided what, and what are the implications?",
                )
            )
            priority += 1

        elif strategy == VisualizationStrategy.RISK_MATRIX:
            rows = _risk_matrix_data(report_data, text)
            if not rows:
                continue
            blocks.append(
                VisualizationBlock(
                    title="Risk Matrix",
                    type=strategy,
                    description="Severity and likelihood of identified risks.",
                    data={"rows": rows},
                    priority=priority,
                    decision_question="Which risks require immediate mitigation?",
                )
            )
            priority += 1

        elif strategy == VisualizationStrategy.KPI_CARDS:
            items = _kpi_items(report_data, text)
            if not items:
                continue
            blocks.append(
                VisualizationBlock(
                    title="Key Performance Indicators",
                    type=strategy,
                    description="Headline metrics for executive review.",
                    data={"items": items},
                    priority=priority,
                    decision_question="Are we on track against key targets?",
                    x_label="Metric",
                    y_label="Latest Reported Value",
                )
            )
            priority += 1

        elif strategy == VisualizationStrategy.BAR_CHART:
            series = _financial_series(report_data, text)
            if not series:
                continue
            blocks.append(
                VisualizationBlock(
                    title="Financial Performance",
                    type=strategy,
                    description="Comparative view of core financial metrics.",
                    data={"series": series},
                    priority=priority,
                    decision_question="Where is performance strong or weak?",
                )
            )
            priority += 1

        elif strategy == VisualizationStrategy.LINE_CHART:
            trends = report_data.charts.get("trends") or []
            if not trends:
                continue
            blocks.append(
                VisualizationBlock(
                    title="Performance Trend",
                    type=strategy,
                    description="Direction of change across reporting periods.",
                    data={"trends": trends},
                    priority=priority,
                    decision_question="Is performance improving or deteriorating?",
                )
            )
            priority += 1

        elif strategy == VisualizationStrategy.PIE_CHART:
            distribution = report_data.charts.get("risk_distribution") or []
            if not distribution:
                continue
            blocks.append(
                VisualizationBlock(
                    title="Distribution Overview",
                    type=strategy,
                    description="Share of categories across the dataset.",
                    data={"series": distribution},
                    priority=priority,
                    decision_question="Where is concentration highest?",
                )
            )
            priority += 1

        elif strategy == VisualizationStrategy.TABLE_ONLY:
            if report_type == ReportType.MEETING:
                actions = _extract_action_items(text)
                if not actions:
                    continue
                blocks.append(
                    VisualizationBlock(
                        title="Action Tracker",
                        type=strategy,
                        description="Assigned actions, owners, and deadlines.",
                        data={"rows": actions},
                        priority=priority,
                        decision_question="Who owns what, and by when?",
                    )
                )
                priority += 1
            elif data_profile.contains_numeric_tables:
                blocks.append(
                    VisualizationBlock(
                        title="Evidence Table",
                        type=strategy,
                        description="Structured evidence supporting conclusions.",
                        data={"note": "See narrative tables for detailed evidence."},
                        priority=priority,
                        decision_question="What evidence supports the recommendation?",
                    )
                )
                priority += 1

        elif strategy == VisualizationStrategy.ORGANIZATIONAL_FLOW:
            blocks.append(
                VisualizationBlock(
                    title="Stakeholder Map",
                    type=strategy,
                    description="Key stakeholders and implementation relationships.",
                    data={
                        "nodes": [
                            {"label": "Objectives"},
                            {"label": "Stakeholders"},
                            {"label": "Compliance"},
                            {"label": "Implementation"},
                        ]
                    },
                    priority=priority,
                    decision_question="Who must align for successful implementation?",
                )
            )
            priority += 1

    return sorted(blocks, key=lambda block: block.priority)


def apply_visualizations(
    report_data: ReportData,
    *,
    user_report_type: str = "",
    document_text: str = "",
    include_charts: bool = True,
    force_generate: bool = False,
    append_only: bool = False,
    reporting_period: str = "",
) -> ReportData:
    """
    Classify the report, score visualization confidence, and attach blocks when appropriate.

    High-confidence reports auto-generate charts. Medium and low confidence reports
    store the decision for the Explore Visual Insights flow unless force_generate=True.
    """

    from services.visualization_decision import (
        evaluate_visualization_decision,
        low_confidence_user_message,
    )

    resolved_type = user_report_type or report_data.report_type
    decision = evaluate_visualization_decision(
        report_data,
        user_report_type=resolved_type,
        document_text=document_text,
        reporting_period=reporting_period,
    )

    detected_type = classify_report_type(
        report_data,
        document_text=document_text,
        user_report_type=resolved_type,
    )
    intent = classify_report_intent(resolved_type)
    data_profile = build_data_profile(report_data, document_text=document_text)

    charts = dict(report_data.charts)
    metadata = dict(report_data.metadata)
    charts["visualization_decision"] = decision.to_dict()
    charts["detected_report_type"] = detected_type.value
    charts["report_intent"] = intent.value
    charts["data_profile"] = data_profile.to_dict()
    metadata["detected_report_type"] = detected_type.value
    metadata["report_intent"] = intent.value
    metadata["data_profile"] = data_profile.to_dict()
    metadata["visualization_decision"] = decision.to_dict()

    should_generate = include_charts and (force_generate or decision.auto_generate)

    if not should_generate:
        charts["_suppress_theme_charts"] = True
        if force_generate and not decision.suggested_visualizations:
            decision.user_message = low_confidence_user_message()
            charts["visualization_decision"] = decision.to_dict()
            metadata["visualization_decision"] = decision.to_dict()

        return ReportData(
            report_type=report_data.report_type,
            title=report_data.title,
            narrative=report_data.narrative,
            metadata=metadata,
            metrics=dict(report_data.metrics),
            charts=charts,
            kpis=dict(report_data.kpis),
            source_documents=list(report_data.source_documents),
            executive_summary=dict(report_data.executive_summary),
            sections=list(report_data.sections),
            recommendations=list(report_data.recommendations),
            citations=list(report_data.citations),
        )

    strategies = decide_visualization_strategies(detected_type, data_profile, intent)
    blocks = build_visualization_blocks(
        detected_type,
        data_profile,
        strategies,
        report_data,
        document_text=document_text,
    )
    block_dicts = [block.to_dict() for block in blocks]

    if append_only:
        existing_titles = {
            str(item.get("title", "")).strip().lower()
            for item in charts.get("visualizations") or []
        }
        merged = list(charts.get("visualizations") or [])
        for block in block_dicts:
            title = str(block.get("title", "")).strip().lower()
            if title and title in existing_titles:
                continue
            merged.append(block)
            if title:
                existing_titles.add(title)
        block_dicts = merged

    if force_generate and not block_dicts:
        decision.user_message = low_confidence_user_message()
        charts["_suppress_theme_charts"] = True
        charts["visualization_decision"] = {
            **decision.to_dict(),
            "explored": True,
        }
        metadata["visualization_decision"] = charts["visualization_decision"]
        return ReportData(
            report_type=report_data.report_type,
            title=report_data.title,
            narrative=report_data.narrative,
            metadata=metadata,
            metrics=dict(report_data.metrics),
            charts=charts,
            kpis=dict(report_data.kpis),
            source_documents=list(report_data.source_documents),
            executive_summary=dict(report_data.executive_summary),
            sections=list(report_data.sections),
            recommendations=list(report_data.recommendations),
            citations=list(report_data.citations),
        )

    dashboard = _build_executive_dashboard(detected_type, report_data, blocks)
    charts["visualizations"] = block_dicts
    charts["executive_dashboard"] = dashboard.to_dict()
    charts["_suppress_theme_charts"] = True
    charts["visualization_decision"] = {
        **decision.to_dict(),
        "explored": force_generate,
        "auto_generate": decision.auto_generate,
    }
    metadata["visualization_decision"] = charts["visualization_decision"]
    metadata["include_charts"] = bool(block_dicts)

    return ReportData(
        report_type=report_data.report_type,
        title=report_data.title,
        narrative=report_data.narrative,
        metadata=metadata,
        metrics=dict(report_data.metrics),
        charts=charts,
        kpis=dict(report_data.kpis),
        source_documents=list(report_data.source_documents),
        executive_summary=dict(report_data.executive_summary),
        sections=list(report_data.sections),
        recommendations=list(report_data.recommendations),
        citations=list(report_data.citations),
    )


def uses_executive_dashboard(chart_data: dict[str, Any] | None) -> bool:
    if not chart_data:
        return False

    return bool(chart_data.get("visualizations")) or bool(chart_data.get("_suppress_theme_charts"))


def dashboard_section_heading(chart_data: dict[str, Any] | None) -> str:
    if uses_executive_dashboard(chart_data):
        return EXECUTIVE_DASHBOARD_HEADING
    return LEGACY_VISUAL_ANALYTICS_HEADING
