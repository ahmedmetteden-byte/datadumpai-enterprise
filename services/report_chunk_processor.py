"""
Multi-stage analysis of large source documents for complete report coverage.
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from config import (
    AI_REPORT_CHUNK_SIZE_CHARS,
    AI_REPORT_CHUNK_SUMMARY_MAX_CHARS,
    AI_REPORT_DIRECT_MAX_CHARS,
    AI_REPORT_SYNTHESIS_MAX_CHARS,
)
from models.report_data import ReportData
from models.report_processing_mode import ReportProcessingMode
from services.ai_service import AIService
from services.document_chunking import DocumentChunk, chunk_combined_source_text
from services.report_metrics_extractor import (
    _aggregate_counts,
    _theme_counts,
    build_report_data,
)

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
THEME_HINT = re.compile(
    r"\b(?:risk|claim|capital|revenue|profit|growth|regulatory|compliance|"
    r"operation|market|governance|investment|loss|premium)\w*\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ChunkAnalysis:
    chunk: DocumentChunk
    theme_counts: dict[str, int]
    summary: str


def extractive_chunk_summary(chunk_text: str, *, max_chars: int) -> str:
    """Deterministic extractive summary used in fast mode."""

    text = chunk_text.strip()
    if not text:
        return ""

    if len(text) <= max_chars:
        return text

    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    summary_parts: list[str] = []
    used = 0

    if paragraphs:
        lead = paragraphs[0]
        if len(lead) > max_chars:
            lead = lead[: max_chars - 1].rstrip() + "…"
        summary_parts.append(lead)
        used += len(lead)

    bullet_lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip().startswith(("-", "•", "*")) or re.match(r"^\d+\.", line.strip())
    ]

    for line in bullet_lines:
        if used + len(line) + 2 > max_chars:
            break
        summary_parts.append(line)
        used += len(line) + 2

    if used < max_chars * 0.6:
        for sentence in SENTENCE_SPLIT.split(text):
            sentence = sentence.strip()
            if not sentence:
                continue
            if not THEME_HINT.search(sentence):
                continue
            if used + len(sentence) + 1 > max_chars:
                break
            summary_parts.append(sentence)
            used += len(sentence) + 1

    summary = "\n".join(summary_parts).strip()
    if len(summary) > max_chars:
        summary = summary[: max_chars - 1].rstrip() + "…"

    return summary or text[: max_chars - 1].rstrip() + "…"


def _summary_budget(chunk_count: int) -> int:
    if chunk_count <= 0:
        return AI_REPORT_CHUNK_SUMMARY_MAX_CHARS

    header_overhead = 120
    per_chunk = (AI_REPORT_SYNTHESIS_MAX_CHARS // chunk_count) - header_overhead
    return max(180, min(AI_REPORT_CHUNK_SUMMARY_MAX_CHARS, per_chunk))


def _analyze_chunk(
    chunk: DocumentChunk,
    *,
    processing_mode: ReportProcessingMode,
    ai_service: AIService | None,
    report_type: str,
    summary_budget: int,
) -> ChunkAnalysis:
    theme_counts = _theme_counts(chunk.text)

    if processing_mode == ReportProcessingMode.COMPREHENSIVE and ai_service is not None:
        summary = ai_service.summarize_source_chunk(
            source_document=chunk.source_document,
            heading=chunk.heading,
            chunk_text=chunk.text,
            report_type=report_type,
            max_summary_chars=summary_budget,
        )
    else:
        summary = extractive_chunk_summary(
            chunk.text,
            max_chars=summary_budget,
        )

    return ChunkAnalysis(chunk=chunk, theme_counts=theme_counts, summary=summary)


def build_synthesis_document(analyses: list[ChunkAnalysis]) -> str:
    """Merge every chunk summary into the narrative synthesis input."""

    blocks = [
        (
            f"=== SOURCE CHUNK: {analysis.chunk.source_document} "
            f"({analysis.chunk.chunk_index}/{analysis.chunk.total_chunks}) — "
            f"{analysis.chunk.heading} ===\n"
            f"{analysis.summary.strip()}"
        )
        for analysis in analyses
    ]

    return "\n\n".join(blocks)


def should_use_multi_stage(
    document_text: str,
    *,
    processing_mode: ReportProcessingMode,
) -> bool:
    if processing_mode == ReportProcessingMode.COMPREHENSIVE:
        return len(document_text.strip()) > AI_REPORT_DIRECT_MAX_CHARS

    return len(document_text.strip()) > AI_REPORT_DIRECT_MAX_CHARS


def process_source_documents(
    *,
    document_text: str,
    report_type: str,
    processing_mode: ReportProcessingMode,
    ai_service: AIService | None,
    source_documents: list[str] | None,
    report_context: dict[str, Any] | None,
    source_document_count: int | None,
) -> tuple[ReportData, str]:
    """
    Analyse source documents and return canonical ReportData plus narrative input text.

    Every chunk is analysed. Large documents are processed in stages; nothing substantive
    is discarded.
    """

    report_context = report_context or {}
    normalized_text = document_text.strip()

    if not should_use_multi_stage(normalized_text, processing_mode=processing_mode):
        report_data = build_report_data(
            document_text=normalized_text,
            report_type=report_type,
            source_documents=source_documents,
            report_context=report_context,
            source_document_count=source_document_count,
            processing_mode=processing_mode.value,
            chunk_count=1,
        )
        return report_data, normalized_text

    chunks = chunk_combined_source_text(
        normalized_text,
        chunk_size=AI_REPORT_CHUNK_SIZE_CHARS,
    )

    if not chunks:
        report_data = build_report_data(
            document_text=normalized_text,
            report_type=report_type,
            source_documents=source_documents,
            report_context=report_context,
            source_document_count=source_document_count,
            processing_mode=processing_mode.value,
            chunk_count=0,
        )
        return report_data, normalized_text

    summary_budget = _summary_budget(len(chunks))
    max_workers = min(4, len(chunks))
    analyses: list[ChunkAnalysis]

    if processing_mode == ReportProcessingMode.COMPREHENSIVE and ai_service is not None:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            analyses = list(
                executor.map(
                    lambda chunk: _analyze_chunk(
                        chunk,
                        processing_mode=processing_mode,
                        ai_service=ai_service,
                        report_type=report_type,
                        summary_budget=summary_budget,
                    ),
                    chunks,
                )
            )
    else:
        analyses = [
            _analyze_chunk(
                chunk,
                processing_mode=processing_mode,
                ai_service=None,
                report_type=report_type,
                summary_budget=summary_budget,
            )
            for chunk in chunks
        ]

    theme_totals = _aggregate_counts([analysis.theme_counts for analysis in analyses])
    chunk_summaries = [
        {
            "source_document": analysis.chunk.source_document,
            "heading": analysis.chunk.heading,
            "chunk_index": analysis.chunk.chunk_index,
            "total_chunks": analysis.chunk.total_chunks,
            "summary": analysis.summary,
            "theme_counts": analysis.theme_counts,
        }
        for analysis in analyses
    ]

    report_data = build_report_data(
        document_text=normalized_text,
        report_type=report_type,
        source_documents=source_documents,
        report_context=report_context,
        source_document_count=source_document_count,
        theme_totals=theme_totals,
        combined_text=normalized_text,
        chunk_summaries=chunk_summaries,
        processing_mode=processing_mode.value,
        chunk_count=len(chunks),
    )

    synthesis_text = build_synthesis_document(analyses)
    return report_data, synthesis_text
