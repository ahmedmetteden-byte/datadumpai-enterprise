"""Tests for multi-stage report chunk processing."""

from __future__ import annotations

from unittest.mock import MagicMock

from models.report_processing_mode import ReportProcessingMode
from services.report_chunk_processor import (
    extractive_chunk_summary,
    process_source_documents,
    should_use_multi_stage,
)


def test_should_use_multi_stage_for_large_documents():
    assert should_use_multi_stage("a" * 50000, processing_mode=ReportProcessingMode.FAST)
    assert not should_use_multi_stage("short text", processing_mode=ReportProcessingMode.FAST)


def test_process_source_documents_fast_mode_uses_extractive_summaries():
    body = "\n\n".join(
        f"## Section {index}\n\n" + ("Operational risk increased. " * 250)
        for index in range(12)
    )
    combined = f"=== SOURCE DOCUMENT: board_pack.txt ===\n\n{body}"

    report_data, synthesis = process_source_documents(
        document_text=combined,
        report_type="Executive Summary",
        processing_mode=ReportProcessingMode.FAST,
        ai_service=None,
        source_documents=["board_pack.txt"],
        report_context={},
        source_document_count=1,
    )

    assert report_data.metrics["chunks_analyzed"] > 1
    assert "SOURCE CHUNK" in synthesis
    assert report_data.charts["topics"]


def test_process_source_documents_comprehensive_mode_calls_ai_summaries():
    body = "\n\n".join(
        f"## Section {index}\n\n" + ("Claims exposure remained elevated. " * 250)
        for index in range(12)
    )
    combined = f"=== SOURCE DOCUMENT: claims.txt ===\n\n{body}"

    ai = MagicMock()
    ai.summarize_source_chunk.return_value = "Claims exposure remained elevated in this section."

    report_data, synthesis = process_source_documents(
        document_text=combined,
        report_type="Executive Summary",
        processing_mode=ReportProcessingMode.COMPREHENSIVE,
        ai_service=ai,
        source_documents=["claims.txt"],
        report_context={},
        source_document_count=1,
    )

    assert ai.summarize_source_chunk.call_count == report_data.metrics["chunks_analyzed"]
    assert "Claims exposure" in synthesis
    assert report_data.sections


def test_extractive_chunk_summary_is_bounded():
    text = "Important finding. " * 200
    summary = extractive_chunk_summary(text, max_chars=200)

    assert len(summary) <= 200
    assert summary
