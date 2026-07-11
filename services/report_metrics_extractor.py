"""
Deterministic metric and chart extraction from source documents.

Same source documents always produce the same canonical metrics and chart values.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from typing import Any

from models.report_data import ReportData

SOURCE_DOCUMENT_PATTERN = re.compile(
    r"=== SOURCE DOCUMENT:\s*(.+?)\s*===\s*",
    re.MULTILINE,
)

THEME_TAXONOMY: dict[str, tuple[str, ...]] = {
    "Claims": ("claim", "claims", "settlement", "loss ratio"),
    "Capital": ("capital", "solvency", "adequacy", "reserves"),
    "Regulatory": ("regulatory", "regulation", "naicom", "compliance", "reform bill"),
    "Growth": ("growth", "premium", "gwp", "expansion", "market share"),
    "Risk": ("risk", "exposure", "volatility", "underwriting"),
    "Operations": ("operation", "operational", "efficiency", "process"),
    "Technology": ("digital", "technology", "automation", "platform", "erp"),
    "Governance": ("governance", "board", "executive", "tenure"),
    "Market": ("market", "industry", "sector", "competitive"),
    "Finance": ("revenue", "profit", "financial", "investment", "asset"),
}

STOPWORDS = frozenset(
    {
        "about",
        "after",
        "also",
        "been",
        "from",
        "have",
        "into",
        "more",
        "other",
        "report",
        "than",
        "that",
        "their",
        "there",
        "these",
        "through",
        "which",
        "while",
        "with",
        "would",
    }
)


def _split_source_documents(document_text: str) -> list[tuple[str, str]]:
    chunks = SOURCE_DOCUMENT_PATTERN.split(document_text.strip())

    if len(chunks) <= 1:
        return [("combined", document_text.strip())]

    documents: list[tuple[str, str]] = []
    index = 1

    while index < len(chunks):
        filename = chunks[index].strip()
        body = chunks[index + 1].strip() if index + 1 < len(chunks) else ""
        if body:
            documents.append((filename, body))
        index += 2

    return documents or [("combined", document_text.strip())]


def _count_theme_mentions(text: str, keywords: tuple[str, ...]) -> int:
    lowered = text.lower()
    return sum(lowered.count(keyword) for keyword in keywords)


def _theme_counts(text: str) -> dict[str, int]:
    return {
        theme: _count_theme_mentions(text, keywords)
        for theme, keywords in THEME_TAXONOMY.items()
    }


def _fallback_terms(text: str, *, limit: int = 5) -> list[str]:
    words = re.findall(r"\b[a-z]{5,}\b", text.lower())
    counts = Counter(word for word in words if word not in STOPWORDS)
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [word.title() for word, _ in ranked[:limit]]


def _normalize_topic_percentages(topics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not topics:
        return []

    total = sum(float(item["value"]) for item in topics) or 1.0
    normalized = [
        {"label": item["label"], "value": int(round(100 * float(item["value"]) / total))}
        for item in topics
    ]

    remainder = 100 - sum(item["value"] for item in normalized)
    if normalized and remainder:
        normalized[0]["value"] = max(0, normalized[0]["value"] + remainder)

    return normalized


def _build_topics(theme_totals: dict[str, int], *, fallback_text: str) -> list[dict[str, Any]]:
    ranked = sorted(
        ((theme, count) for theme, count in theme_totals.items() if count > 0),
        key=lambda item: (-item[1], item[0]),
    )

    if not ranked:
        fallback = _fallback_terms(fallback_text)
        if not fallback:
            return [{"label": "Document Themes", "value": 100}]
        return _normalize_topic_percentages(
            [{"label": label, "value": 1} for label in fallback],
        )

    return _normalize_topic_percentages(
        [{"label": theme, "value": count} for theme, count in ranked[:5]],
    )


def _aggregate_counts(rows: list[dict[str, int]]) -> dict[str, int]:
    totals: dict[str, int] = {theme: 0 for theme in THEME_TAXONOMY}

    for row in rows:
        for theme, count in row.items():
            totals[theme] = totals.get(theme, 0) + count

    return totals


def _build_trends(
    per_document_counts: list[dict[str, int]],
    topic_labels: list[str],
) -> list[dict[str, Any]]:
    if len(per_document_counts) < 2:
        return []

    split_at = max(1, len(per_document_counts) // 2)
    prior = _aggregate_counts(per_document_counts[:split_at])
    current = _aggregate_counts(per_document_counts[split_at:])

    trends: list[dict[str, Any]] = []

    for label in topic_labels:
        trends.append(
            {
                "label": label,
                "prior": prior.get(label, 0),
                "current": current.get(label, 0),
            }
        )

    return trends


def _risk_counts(combined_text: str) -> dict[str, int]:
    return {
        "Critical": len(re.findall(r"🔴|\bcritical\b", combined_text, re.IGNORECASE)),
        "High": len(re.findall(r"🟠|\bhigh(?:\s+priority)?\b", combined_text, re.IGNORECASE)),
        "Medium": len(re.findall(r"🟡|\bmedium\b", combined_text, re.IGNORECASE)),
    }


def _risk_distribution(combined_text: str) -> list[dict[str, Any]]:
    counts = _risk_counts(combined_text)

    if sum(counts.values()) == 0:
        return []

    return [{"label": label, "value": value} for label, value in counts.items() if value]


def _health_score(
    *,
    source_document_count: int,
    risk_distribution: list[dict[str, Any]],
    topic_count: int,
) -> int:
    critical = next((item["value"] for item in risk_distribution if item["label"] == "Critical"), 0)
    high = next((item["value"] for item in risk_distribution if item["label"] == "High"), 0)
    medium = next((item["value"] for item in risk_distribution if item["label"] == "Medium"), 0)

    score = 82
    score -= int(critical) * 8
    score -= int(high) * 4
    score -= int(medium) * 2
    score += min(6, max(0, source_document_count - 1) * 2)
    score += min(4, topic_count)

    return max(35, min(95, score))


def _content_hash(document_text: str) -> str:
    return hashlib.sha256(document_text.encode("utf-8")).hexdigest()


def build_report_data(
    *,
    document_text: str,
    report_type: str,
    source_documents: list[str] | None,
    report_context: dict[str, Any] | None,
    source_document_count: int | None,
    per_document_counts: list[dict[str, int]] | None = None,
    theme_totals: dict[str, int] | None = None,
    combined_text: str | None = None,
    chunk_summaries: list[dict[str, Any]] | None = None,
    processing_mode: str | None = None,
    chunk_count: int | None = None,
) -> ReportData:
    """Build canonical report metrics and chart data from source documents."""

    report_context = report_context or {}
    documents = _split_source_documents(document_text)
    resolved_combined = combined_text or "\n\n".join(body for _, body in documents)
    resolved_per_document_counts = per_document_counts or [
        _theme_counts(body) for _, body in documents
    ]
    resolved_theme_totals = theme_totals or _aggregate_counts(resolved_per_document_counts)

    topics = _build_topics(resolved_theme_totals, fallback_text=resolved_combined)
    topic_labels = [item["label"] for item in topics]
    trends = _build_trends(resolved_per_document_counts, topic_labels)
    risks = _risk_distribution(resolved_combined)
    risk_counts = _risk_counts(resolved_combined)
    document_count = source_document_count or len(documents)
    health_score = _health_score(
        source_document_count=document_count,
        risk_distribution=risks,
        topic_count=len(topics),
    )

    charts: dict[str, Any] = {
        "topics": topics,
        "health_score": health_score,
    }

    if trends:
        charts["trends"] = trends

    if risks and not topics:
        charts["risk_distribution"] = risks

    metrics = {
        "source_document_count": document_count,
        "reporting_period": report_context.get("reporting_period", "Not specified"),
        "theme_totals": resolved_theme_totals,
        "health_score": health_score,
        "top_themes": topic_labels,
    }

    if chunk_count is not None:
        metrics["chunks_analyzed"] = chunk_count

    if processing_mode:
        metrics["processing_mode"] = processing_mode

    kpis = {
        "documents_analyzed": document_count,
        "critical_risks": risk_counts.get("Critical", 0),
        "high_risks": risk_counts.get("High", 0),
        "medium_risks": risk_counts.get("Medium", 0),
        "health_score": health_score,
    }

    metadata = {
        "report_type": report_type,
        "content_hash": _content_hash(document_text),
        "extractor_version": "2",
    }

    if processing_mode:
        metadata["processing_mode"] = processing_mode

    if chunk_count is not None:
        metadata["chunk_count"] = chunk_count

    sections = list(chunk_summaries or [])

    return ReportData(
        metadata=metadata,
        metrics=metrics,
        charts=charts,
        kpis=kpis,
        source_documents=list(source_documents or report_context.get("source_documents") or []),
        sections=sections,
    )


def extract_report_data(
    *,
    document_text: str,
    report_type: str,
    source_documents: list[str] | None = None,
    report_context: dict[str, Any] | None = None,
    source_document_count: int | None = None,
) -> ReportData:
    """Build canonical report metrics and chart data from source documents."""

    return build_report_data(
        document_text=document_text,
        report_type=report_type,
        source_documents=source_documents,
        report_context=report_context,
        source_document_count=source_document_count,
    )
