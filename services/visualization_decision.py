"""
Visualization confidence scoring and decision model.

Charts are generated automatically only at high confidence (80+).
Medium-confidence reports defer visualization to the Explore Visual Insights flow.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from models.report_data import ReportData
from services.visualization_engine import (
    ReportIntent,
    ReportType,
    VisualizationStrategy,
    build_data_profile,
    build_visualization_blocks,
    classify_report_intent,
    classify_report_type,
    decide_visualization_strategies,
)

HIGH_CONFIDENCE_THRESHOLD = 80
MEDIUM_CONFIDENCE_THRESHOLD = 40


class VisualizationConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


HIGH_CONFIDENCE_USER_REPORT_TYPES: dict[str, int] = {
    "annual statistics": 92,
    "financial analysis": 90,
    "financial report": 90,
    "sales report": 88,
    "kpi report": 90,
    "performance report": 86,
    "survey results": 85,
    "operational metrics": 84,
    "executive intelligence dashboard": 88,
    "market intelligence report": 82,
    "management report": 82,
}

MEDIUM_CONFIDENCE_USER_REPORT_TYPES: dict[str, int] = {
    "full report": 68,
    "board report": 62,
    "management report": 58,
    "meeting intelligence report": 58,
    "meeting minutes": 55,
    "strategic planning report": 60,
    "regulatory compliance report": 55,
    "risk assessment report": 72,
    "executive summary": 52,
}

HIGH_CONFIDENCE_KEYWORDS: tuple[str, ...] = (
    "annual statistics",
    "annual report",
    "year-over-year",
    "kpi dashboard",
    "survey results",
    "operational metrics",
    "sales performance",
    "revenue trend",
)

STRATEGY_LABELS: dict[VisualizationStrategy, str] = {
    VisualizationStrategy.BAR_CHART: "Comparison Chart",
    VisualizationStrategy.LINE_CHART: "Trend Chart",
    VisualizationStrategy.PIE_CHART: "Distribution Chart",
    VisualizationStrategy.KPI_CARDS: "KPI Dashboard",
    VisualizationStrategy.TIMELINE: "Timeline",
    VisualizationStrategy.RISK_MATRIX: "Risk Matrix",
    VisualizationStrategy.DECISION_MATRIX: "Decision Matrix",
    VisualizationStrategy.TABLE_ONLY: "Summary Table",
    VisualizationStrategy.HEATMAP: "Heatmap",
    VisualizationStrategy.PROCESS_FLOW: "Process Flow",
    VisualizationStrategy.ORGANIZATIONAL_FLOW: "Organizational Flow",
}


@dataclass
class VisualizationDecision:
    confidence: int
    level: VisualizationConfidenceLevel
    auto_generate: bool
    detected_report_type: str
    document_type: str
    suggested_visualizations: list[str] = field(default_factory=list)
    reasoning: str = ""
    user_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["level"] = self.level.value
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> VisualizationDecision | None:
        if not data:
            return None

        level = data.get("level", VisualizationConfidenceLevel.LOW.value)
        try:
            confidence_level = VisualizationConfidenceLevel(str(level))
        except ValueError:
            confidence_level = VisualizationConfidenceLevel.LOW

        return cls(
            confidence=int(data.get("confidence", 0)),
            level=confidence_level,
            auto_generate=bool(data.get("auto_generate", False)),
            detected_report_type=str(data.get("detected_report_type", "")),
            document_type=str(data.get("document_type", "")),
            suggested_visualizations=list(data.get("suggested_visualizations") or []),
            reasoning=str(data.get("reasoning", "")),
            user_message=data.get("user_message"),
        )


def _confidence_level(score: int) -> VisualizationConfidenceLevel:
    if score >= HIGH_CONFIDENCE_THRESHOLD:
        return VisualizationConfidenceLevel.HIGH
    if score >= MEDIUM_CONFIDENCE_THRESHOLD:
        return VisualizationConfidenceLevel.MEDIUM
    return VisualizationConfidenceLevel.LOW


def _document_type_label(
    user_report_type: str,
    detected_type: ReportType,
    *,
    reporting_period: str = "",
) -> str:
    label = (user_report_type or detected_type.value.replace("_", " ").title()).strip()
    period = (reporting_period or "").strip()

    if period and "annual" in period.lower() and "statistics" not in label.lower():
        return f"{label} · {period}"

    return label or detected_type.value.replace("_", " ").title()


def _strategy_labels(strategies: list[VisualizationStrategy]) -> list[str]:
    labels: list[str] = []

    for strategy in strategies:
        if strategy == VisualizationStrategy.NONE:
            continue

        label = STRATEGY_LABELS.get(strategy, strategy.value.replace("_", " ").title())
        if label not in labels:
            labels.append(label)

    return labels


def _score_data_profile(profile) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []

    signal_map = (
        (profile.contains_numeric_tables, 8, "numeric tables"),
        (profile.contains_time_series, 10, "time-series data"),
        (profile.contains_currency, 8, "currency values"),
        (profile.contains_percentages, 8, "percentages"),
        (profile.contains_dates, 5, "dates"),
        (profile.contains_kpis, 10, "KPIs"),
        (profile.contains_categories, 5, "categories"),
        (profile.contains_scores, 6, "scores"),
        (profile.contains_rankings, 6, "rankings"),
        (profile.contains_geographic_breakdown, 6, "regional breakdown"),
    )

    for present, points, label in signal_map:
        if present:
            score += points
            reasons.append(label)

    return score, reasons


def _has_chartworthy_quantitative_signal(data_profile) -> bool:
    """Quantitative evidence suitable for chart generation (not theme analytics alone)."""

    return any(
        (
            data_profile.contains_numeric_tables,
            data_profile.contains_time_series,
            data_profile.contains_currency,
            data_profile.contains_percentages,
            data_profile.contains_kpis,
            data_profile.contains_rankings,
            data_profile.contains_geographic_breakdown,
        )
    )


def _profile_for_confidence(
    report_data: ReportData,
    *,
    document_text: str = "",
) -> Any:
    """Build a data profile from source text only, ignoring theme analytics."""

    source_text = document_text or report_data.narrative
    stripped = ReportData(
        report_type=report_data.report_type,
        title=report_data.title,
        narrative=source_text,
        metadata=report_data.metadata,
        metrics={},
        charts={},
        kpis={},
        source_documents=list(report_data.source_documents),
        executive_summary={},
        sections=[],
        recommendations=[],
        citations=[],
    )
    return build_data_profile(stripped, document_text=source_text)


def evaluate_visualization_decision(
    report_data: ReportData,
    *,
    user_report_type: str = "",
    document_text: str = "",
    reporting_period: str = "",
) -> VisualizationDecision:
    """Score how confidently this report should receive automatic visualizations."""

    resolved_type = user_report_type or report_data.report_type
    normalized_type = resolved_type.strip().lower()
    combined_text = "\n".join(
        part
        for part in (document_text, report_data.narrative, resolved_type, reporting_period)
        if part
    ).lower()

    detected_type = classify_report_type(
        report_data,
        document_text=document_text,
        user_report_type=resolved_type,
    )
    intent = classify_report_intent(resolved_type)
    data_profile = _profile_for_confidence(report_data, document_text=document_text)
    strategies = decide_visualization_strategies(detected_type, data_profile, intent)
    suggested_visualizations = _strategy_labels(strategies)

    score = 0
    reasons: list[str] = []

    if normalized_type in HIGH_CONFIDENCE_USER_REPORT_TYPES:
        score = max(score, HIGH_CONFIDENCE_USER_REPORT_TYPES[normalized_type])
        reasons.append(f"report type '{resolved_type}' is chart-friendly")
    elif normalized_type in MEDIUM_CONFIDENCE_USER_REPORT_TYPES:
        score = max(score, MEDIUM_CONFIDENCE_USER_REPORT_TYPES[normalized_type])
        reasons.append(f"report type '{resolved_type}' may include useful metrics")

    if "annual" in reporting_period.lower() or "annual statistics" in combined_text:
        score = max(score, 92)
        reasons.append("annual statistics pattern detected")

    for keyword in HIGH_CONFIDENCE_KEYWORDS:
        if keyword in combined_text:
            score = max(score, 85)
            reasons.append(f"detected '{keyword}'")
            break

    if detected_type in {ReportType.FINANCIAL, ReportType.SALES, ReportType.OPERATIONS}:
        score += 8
        reasons.append(f"content classified as {detected_type.value.lower()}")

    profile_score, profile_reasons = _score_data_profile(data_profile)
    score += profile_score
    reasons.extend(profile_reasons)

    chartworthy = _has_chartworthy_quantitative_signal(data_profile)

    if normalized_type not in HIGH_CONFIDENCE_USER_REPORT_TYPES:
        score = min(score, 79)

    if not chartworthy:
        score = min(score, 39)
        reasons.append("primarily narrative content without quantitative signals")
    elif not suggested_visualizations:
        score = min(score, 35)
        reasons.append("no suitable visualization strategies identified")

    score = max(0, min(100, score))
    level = _confidence_level(score)

    return VisualizationDecision(
        confidence=score,
        level=level,
        auto_generate=level == VisualizationConfidenceLevel.HIGH and bool(suggested_visualizations),
        detected_report_type=detected_type.value,
        document_type=_document_type_label(
            resolved_type,
            detected_type,
            reporting_period=reporting_period,
        ),
        suggested_visualizations=suggested_visualizations,
        reasoning="; ".join(dict.fromkeys(reasons)),
    )


def low_confidence_user_message() -> str:
    return (
        "No meaningful visualizations could be generated because this report is "
        "primarily narrative or descriptive."
    )


def preview_blocks_for_decision(
    report_data: ReportData,
    decision: VisualizationDecision,
    *,
    document_text: str = "",
    user_report_type: str = "",
) -> list[dict[str, Any]]:
    """Build visualization blocks without mutating report data."""

    detected_type = ReportType(decision.detected_report_type)
    intent = classify_report_intent(user_report_type or report_data.report_type)
    data_profile = build_data_profile(report_data, document_text=document_text)
    strategies = decide_visualization_strategies(detected_type, data_profile, intent)

    blocks = build_visualization_blocks(
        detected_type,
        data_profile,
        strategies,
        report_data,
        document_text=document_text,
    )
    return [block.to_dict() for block in blocks]
